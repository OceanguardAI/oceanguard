"""Leakage-safe, deterministic dataset split utilities.

Records are assigned by a group such as sequence, scene, or capture session.
This prevents neighboring frames or tiles from leaking across train, validation,
and test sets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping


def _validate_ratios(ratios: Mapping[str, float]) -> None:
    if set(ratios) != {"train", "validation", "test"}:
        raise ValueError("ratios must contain train, validation, and test")
    if any(value <= 0 for value in ratios.values()) or abs(sum(ratios.values()) - 1.0) > 1e-9:
        raise ValueError("split ratios must be positive and sum to 1")


def assign_split(
    group_id: str,
    *,
    seed: int = 20260926,
    ratios: Mapping[str, float] | None = None,
) -> str:
    """Assign a group to a split using a stable hash, never random state."""
    selected = ratios or {"train": 0.70, "validation": 0.15, "test": 0.15}
    _validate_ratios(selected)
    digest = hashlib.sha256(f"{seed}:{group_id}".encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:8], "big") / 2**64
    cumulative = 0.0
    for name in ("train", "validation", "test"):
        cumulative += selected[name]
        if bucket < cumulative:
            return name
    return "test"


def build_split_manifest(
    records: Iterable[Mapping[str, Any]],
    *,
    dataset_id: str,
    group_key: str = "sequence_id",
    id_key: str = "id",
    seed: int = 20260926,
    ratios: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Build a manifest and fail if a record lacks an identity or split group."""
    selected = dict(ratios or {"train": 0.70, "validation": 0.15, "test": 0.15})
    _validate_ratios(selected)
    items: list[dict[str, str]] = []
    groups: dict[str, str] = {}
    for record in records:
        if id_key not in record or group_key not in record:
            raise ValueError(f"each record must include {id_key!r} and {group_key!r}")
        record_id = str(record[id_key])
        group_id = str(record[group_key])
        split = groups.setdefault(group_id, assign_split(group_id, seed=seed, ratios=selected))
        items.append({"id": record_id, "group_id": group_id, "split": split})

    counts = Counter(item["split"] for item in items)
    return {
        "schema_version": "dataset-split-v1",
        "dataset_id": dataset_id,
        "group_key": group_key,
        "seed": seed,
        "ratios": selected,
        "group_count": len(groups),
        "record_count": len(items),
        "counts": {name: counts.get(name, 0) for name in ("train", "validation", "test")},
        "groups": [{"group_id": key, "split": groups[key]} for key in sorted(groups)],
        "records": sorted(items, key=lambda item: item["id"]),
    }


def load_records(path: Path) -> list[dict[str, Any]]:
    """Read either a JSON list or newline-delimited JSON records."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        payload = json.loads(text)
        if not isinstance(payload, list):
            raise ValueError("JSON input must be a list of records")
        return payload
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a leakage-safe dataset split manifest")
    parser.add_argument("--input", type=Path, required=True, help="JSON list or JSONL records")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--group-key", default="sequence_id")
    parser.add_argument("--id-key", default="id")
    parser.add_argument("--seed", type=int, default=20260926)
    args = parser.parse_args()
    manifest = build_split_manifest(
        load_records(args.input),
        dataset_id=args.dataset,
        group_key=args.group_key,
        id_key=args.id_key,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
