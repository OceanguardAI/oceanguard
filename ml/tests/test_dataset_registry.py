from __future__ import annotations

import json
from pathlib import Path

from collect_datasets import build_manifest, load_registry


def test_registry_has_required_collection_fields() -> None:
    datasets = load_registry()["datasets"]
    assert len(datasets) >= 8
    assert all(
        item["id"] and item["source_url"] and item["tasks"] and item["license_status"]
        for item in datasets
    )


def test_empty_manifest_is_explicit(tmp_path: Path) -> None:
    dataset = load_registry()["datasets"][0]
    manifest = build_manifest(dataset, tmp_path / dataset["id"])
    assert manifest["dataset_id"] == dataset["id"]
    assert manifest["file_count"] == 0
    assert manifest["files"] == []
