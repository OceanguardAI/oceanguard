"""Compare two GFW SAR-presence dataset versions over an identical fixed window.

GFW announced that data pipeline v5 becomes the ``latest`` alias on 2026-10-21.
This tool measures how much the activity layer OceanGuard consumes would change,
so the version can be chosen from evidence rather than assumed:

    python -m app.tools.compare_gfw_versions \\
        --start 2026-08-01 --end 2026-08-31 --bbox 79.4,8.0,79.9,8.8 \\
        --out gfw_v4_vs_v5.json

It calls the live GFW API with GFW_API_TOKEN (two report requests). Use a window
that ended well before today: the most recent days can differ for processing
latency rather than because of the dataset version.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date, datetime, timezone
from math import sqrt
from typing import Any, Callable, Iterable, Mapping

Cell = tuple[float, float]


def _cells(rows: Iterable[Mapping[str, Any]]) -> dict[Cell, int]:
    counts: Counter[Cell] = Counter()
    for row in rows:
        try:
            key = (round(float(row["lat"]), 5), round(float(row["lon"]), 5))
            counts[key] += int(row.get("detections", 1) or 0)
        except (KeyError, TypeError, ValueError):
            continue
    return dict(counts)


def _pearson(pairs: list[tuple[int, int]]) -> float | None:
    if len(pairs) < 2:
        return None
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sx = sqrt(sum((x - mx) ** 2 for x in xs))
    sy = sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in pairs) / (sx * sy)


def _top_overlap(a: dict[Cell, int], b: dict[Cell, int], n: int) -> float | None:
    top_a = {c for c, _ in sorted(a.items(), key=lambda kv: (-kv[1], kv[0]))[:n]}
    top_b = {c for c, _ in sorted(b.items(), key=lambda kv: (-kv[1], kv[0]))[:n]}
    if not top_a and not top_b:
        return None
    return len(top_a & top_b) / max(len(top_a), len(top_b))


def compare_activity(
    rows_a: Iterable[Mapping[str, Any]],
    rows_b: Iterable[Mapping[str, Any]],
    *,
    classify: Callable[[float, float], str] | None = None,
    top_n: int = 50,
) -> dict[str, Any]:
    """Summarise how activity differs between two report row sets.

    ``rows_*`` are report rows with ``lat``, ``lon`` and ``detections``.
    ``classify`` optionally labels a cell centre (e.g. inside/near/open water) so
    totals can be compared per context. Nothing here decides which version is
    "right": it reports agreement so the difference can be judged.
    """
    a, b = _cells(rows_a), _cells(rows_b)
    shared = set(a) & set(b)
    union = set(a) | set(b)
    total_a, total_b = sum(a.values()), sum(b.values())
    pairs = [(a[c], b[c]) for c in sorted(shared)]

    result: dict[str, Any] = {
        "cells": {
            "a": len(a),
            "b": len(b),
            "shared": len(shared),
            "only_a": len(set(a) - shared),
            "only_b": len(set(b) - shared),
            "jaccard": (len(shared) / len(union)) if union else None,
        },
        "detections": {
            "a": total_a,
            "b": total_b,
            "ratio_b_over_a": (total_b / total_a) if total_a else None,
        },
        "shared_cells": {
            "mean_abs_count_difference": (
                sum(abs(x - y) for x, y in pairs) / len(pairs) if pairs else None
            ),
            "pearson_r": _pearson(pairs),
        },
        f"top_{top_n}_cell_overlap": _top_overlap(a, b, top_n),
    }
    if classify is not None:
        by_label: dict[str, dict[str, int]] = {}
        for version, cells in (("a", a), ("b", b)):
            for (lat, lon), count in cells.items():
                bucket = by_label.setdefault(classify(lat, lon), {"a": 0, "b": 0})
                bucket[version] += count
        result["by_context"] = dict(sorted(by_label.items()))
    return result


def _mpa_context(lat: float, lon: float) -> str:
    from app.services import mpa_index

    _, _, inside, near = mpa_index.get_index().nearest(lat, lon)
    return "inside_mpa" if inside else "near_mpa" if near else "open_water"


def _parse_bbox(value: str) -> tuple[float, float, float, float]:
    west, south, east, north = (float(part) for part in value.split(","))
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise argparse.ArgumentTypeError("bbox must be west,south,east,north within valid ranges")
    return west, south, east, north


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end", required=True, type=date.fromisoformat)
    parser.add_argument("--bbox", required=True, type=_parse_bbox, help="west,south,east,north")
    parser.add_argument("--dataset-a", default="public-global-sar-presence:v4.0")
    parser.add_argument("--dataset-b", default="public-global-sar-presence:v5.0")
    parser.add_argument("--out", help="write the JSON report to this path")
    args = parser.parse_args(argv)

    if args.end < args.start:
        parser.error("--end must not be before --start")
    if (args.end - args.start).days > 365:
        parser.error("GFW reports accept date ranges of at most one year")
    if (datetime.now(timezone.utc).date() - args.end).days < 7:
        print(
            "note: the window ends within a week of today; recent days can differ for "
            "processing latency, not because of the dataset version.",
            file=sys.stderr,
        )

    from app.services import gfw_ingest

    if not gfw_ingest.ingestion_enabled():
        parser.error("GFW_API_TOKEN is not configured (set it in backend/.env)")

    start, end = args.start.isoformat(), args.end.isoformat()
    rows_a, _, _ = gfw_ingest._fetch_sar_report(
        dataset=args.dataset_a, start=start, end=end, bbox=args.bbox)
    rows_b, _, _ = gfw_ingest._fetch_sar_report(
        dataset=args.dataset_b, start=start, end=end, bbox=args.bbox)

    report = {
        "dataset_a": args.dataset_a,
        "dataset_b": args.dataset_b,
        "window": [start, end],
        "bbox": list(args.bbox),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **compare_activity(rows_a, rows_b, classify=_mpa_context),
    }
    text = json.dumps(report, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
