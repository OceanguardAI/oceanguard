"""Global Fishing Watch 4Wings report ingestion as aggregate activity."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any

import httpx

from app.core.config import settings
from app.models.schemas import ActivityAggregate

GFW_BASE_URL = "https://gateway.api.globalfishingwatch.org"
SAR_DATASET = "public-global-sar-presence:latest"


def ingestion_enabled() -> bool:
    return bool(settings.gfw_api_token)


def _report_window() -> tuple[str, str]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=settings.gfw_lookback_days)
    return start.isoformat(), end.isoformat()


def _fetch_sar_report() -> tuple[list[dict[str, Any]], str, str]:
    """Fetch a spatial report; each returned row is aggregate activity."""
    min_lon, min_lat, max_lon, max_lat = settings.gfw_region_bbox
    start, end = _report_window()
    params = {
        "spatial-resolution": "HIGH",
        "temporal-resolution": "ENTIRE",
        "datasets[0]": SAR_DATASET,
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
            for group in entry.values():
                if isinstance(group, list):
                    rows.extend(row for row in group if isinstance(row, dict))
    return rows, start, end


def fetch_activity() -> list[ActivityAggregate]:
    rows, start, end = _fetch_sar_report()
    ingested_at = datetime.now(timezone.utc)
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
        base = f"{SAR_DATASET}|{start}|{end}|{lat}|{lon}|{count}|{provider_time}|{source_id}"
        ordinal = occurrences.get(base, 0)
        occurrences[base] = ordinal + 1
        key = f"{base}|{ordinal}"
        row_id = sha256(key.encode("utf-8")).hexdigest()[:24]
        activity.append(ActivityAggregate(
            id=row_id,
            dataset=SAR_DATASET,
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
