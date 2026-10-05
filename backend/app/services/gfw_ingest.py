"""Global Fishing Watch 4Wings report ingestion as aggregate activity."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any

import httpx

from app.core.config import settings
from app.models.schemas import ActivityAggregate

GFW_BASE_URL = "https://gateway.api.globalfishingwatch.org"
DEFAULT_SAR_DATASET = "public-global-sar-presence:v4.0"


def ingestion_enabled() -> bool:
    return bool(settings.gfw_api_token)


def requested_dataset() -> str:
    """Dataset id sent to GFW (``GFW_SAR_DATASET``).

    ``:latest`` is an alias that GFW re-points when a new pipeline version
    becomes the default, so the same request can return different data on
    different days. Pin an explicit version when results must be reproducible.
    """
    return settings.gfw_sar_dataset.strip() or DEFAULT_SAR_DATASET


def _report_window() -> tuple[str, str]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=settings.gfw_lookback_days)
    return start.isoformat(), end.isoformat()


def _fetch_sar_report(
    *,
    dataset: str | None = None,
    start: str | None = None,
    end: str | None = None,
    bbox: tuple[float, float, float, float] | None = None,
) -> tuple[list[dict[str, Any]], str, str]:
    """Fetch a spatial report; each returned row is aggregate activity.

    The keyword arguments override the configured dataset, rolling window and
    region. They exist so two dataset versions can be compared over an identical
    fixed window (see app/tools/compare_gfw_versions.py); normal ingestion uses
    the configured values.
    """
    min_lon, min_lat, max_lon, max_lat = bbox or settings.gfw_region_bbox
    if start is None or end is None:
        start, end = _report_window()
    params = {
        "spatial-resolution": "HIGH",
        "temporal-resolution": "ENTIRE",
        "datasets[0]": dataset or requested_dataset(),
        "date-range": f"{start},{end}",
        "format": "JSON",
    }
    body = {
        "geojson": {
            "type": "Polygon",
            "coordinates": [[
                [min_lon, min_lat], [max_lon, min_lat], [max_lon, max_lat],
                [min_lon, max_lat], [min_lon, min_lat],
            ]],
        }
    }
    with httpx.Client(timeout=90.0) as client:
        resp = client.post(
            f"{GFW_BASE_URL}/v3/4wings/report",
            params=params,
            json=body,
            headers={
                "Authorization": f"Bearer {settings.gfw_api_token}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        payload = resp.json()

    if not isinstance(payload, dict) or "entries" not in payload:
        raise ValueError("GFW report is missing entries")
    entries = payload["entries"]
    if not isinstance(entries, list):
        raise ValueError("GFW report entries must be a list")
    rows: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if "lat" in entry and "lon" in entry:
            rows.append(entry)
        else:
            # Grouped entries are keyed by the dataset id GFW actually served,
            # e.g. "public-global-sar-presence:v4.0". Keep it on each row: when
            # the request used the ":latest" alias, this is the only record of
            # which pipeline version produced the data.
            for group_key, group in entry.items():
                if not isinstance(group, list):
                    continue
                resolved = group_key if isinstance(group_key, str) and ":" in group_key else None
                for row in group:
                    if isinstance(row, dict):
                        rows.append({**row, "_dataset": resolved} if resolved else row)
    return rows, start, end


def fetch_activity() -> list[ActivityAggregate]:
    rows, start, end = _fetch_sar_report()
    ingested_at = datetime.now(timezone.utc)
    requested = requested_dataset()
    activity: list[ActivityAggregate] = []
    occurrences: dict[str, int] = {}
    for row in rows:
        try:
            lat, lon = float(row["lat"]), float(row["lon"])
            count = int(row["detections"])
            if not (-90 <= lat <= 90 and -180 <= lon <= 180 and count >= 0):
                continue
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        provider_time = row.get("entryTimestamp")
        source_id = str(row.get("id") or row.get("sourceId") or "")
        # Prefer the version GFW reports having served over the requested alias,
        # so v4 and v5 rows can never collapse into the same record.
        dataset = str(row.get("_dataset") or requested)
        base = f"{dataset}|{start}|{end}|{lat}|{lon}|{count}|{provider_time}|{source_id}"
        ordinal = occurrences.get(base, 0)
        occurrences[base] = ordinal + 1
        key = f"{base}|{ordinal}"
        row_id = sha256(key.encode("utf-8")).hexdigest()[:24]
        activity.append(ActivityAggregate(
            id=row_id,
            dataset=dataset,
            lat=lat,
            lon=lon,
            detection_count=count,
            report_start=start,
            report_end=end,
            provider_time=str(provider_time) if provider_time else None,
            ingested_at=ingested_at,
        ))
    if rows and not activity:
        raise ValueError("GFW report has no usable activity rows")
    return activity
