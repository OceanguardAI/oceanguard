"""Catalog and verify external datasets without committing raw data."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REGISTRY = Path(__file__).resolve().parent / "datasets" / "registry.json"
DEFAULT_ROOT = Path(__file__).resolve().parent / "data" / "external"


def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def iter_files(root: Path) -> list[Path]:
    return sorted(
        path for path in root.rglob("*")
        if path.is_file()
        and ".git" not in path.relative_to(root).parts
        and path.name != "dataset-manifest.json"
    )


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(dataset: dict[str, Any], root: Path) -> dict[str, Any]:
    files = iter_files(root) if root.exists() else []
    return {
        "dataset_id": dataset["id"],
        "registry_version": load_registry()["registry_version"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_url": dataset["source_url"],
        "license_status": dataset["license_status"],
        "root": str(root),
        "file_count": len(files),
        "files": [
            {
                "path": str(path.relative_to(root)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in files
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="OceanGuard dataset catalog helper")
    parser.add_argument("--list", action="store_true", help="list all registry entries")
    parser.add_argument("--dataset", help="registry id; omit to list all datasets")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--check-only", action="store_true", help="do not create a manifest")
    args = parser.parse_args()

    registry = load_registry()
    datasets = registry["datasets"]
    if args.list or not args.dataset:
        for item in datasets:
            print(f'{item["id"]}: {item["priority"]} {item["status"]} - {item["purpose"]}')
        return 0

    matches = [item for item in datasets if item["id"] == args.dataset]
    if not matches:
        parser.error(f"unknown dataset: {args.dataset}")
    dataset = matches[0]
    root = args.root / dataset["id"]
    manifest = build_manifest(dataset, root)
    print(json.dumps({
        "dataset_id": dataset["id"],
        "source_url": dataset["source_url"],
        "access": dataset["access"],
        "local_root": str(root),
        "file_count": manifest["file_count"],
        "license_status": dataset["license_status"],
    }, indent=2))
    if not args.check_only:
        root.mkdir(parents=True, exist_ok=True)
        manifest_path = root / "dataset-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
