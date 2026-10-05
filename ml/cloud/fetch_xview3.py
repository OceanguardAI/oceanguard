"""Download xView3 scene archives and label files inside an Azure ML job.

URLs come from the XVIEW3_URLS environment variable (one per line) so signed
links never touch the repository or the local disk. Output layout::

    <out>/<scene_id>/VH_dB.tif ...
    <out>/labels.csv
"""
from __future__ import annotations

import gzip
import os
import shutil
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlparse


def _filename(url: str) -> str:
    return Path(unquote(urlparse(url).path)).name or "download.bin"


def ingest_file(path: Path, out_dir: Path) -> str:
    """Place one downloaded file into ``out_dir``; returns what it was treated as."""
    name = path.name.lower()
    out_dir.mkdir(parents=True, exist_ok=True)
    if name.endswith((".tar.gz", ".tgz", ".tar")):
        with tarfile.open(path) as archive:
            archive.extractall(out_dir, filter="data")
        return "scene-archive"
    if name.endswith(".zip"):
        with zipfile.ZipFile(path) as archive:
            archive.extractall(out_dir)
        return "scene-archive"
    if name.endswith(".csv.gz"):
        target = out_dir / "_labels" / (path.name[:-3])
        target.parent.mkdir(exist_ok=True)
        with gzip.open(path, "rb") as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)
        return "labels"
    if name.endswith(".csv"):
        target = out_dir / "_labels" / path.name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(path, target)
        return "labels"
    raise ValueError(f"unrecognised file type: {path.name}")


def merge_labels(out_dir: Path) -> int:
    """Concatenate all collected label CSVs into ``labels.csv`` (one header)."""
    parts = sorted((out_dir / "_labels").glob("*.csv")) if (out_dir / "_labels").exists() else []
    if not parts:
        return 0
    rows = 0
    with open(out_dir / "labels.csv", "w", encoding="utf-8", newline="") as dst:
        for index, part in enumerate(parts):
            with open(part, encoding="utf-8", newline="") as src:
                header = src.readline()
                if index == 0:
                    dst.write(header)
                for line in src:
                    dst.write(line)
                    rows += 1
    shutil.rmtree(out_dir / "_labels")
    return rows


def main() -> int:
    import requests

    urls = [u.strip() for u in os.environ.get("XVIEW3_URLS", "").splitlines() if u.strip()]
    if not urls:
        print("XVIEW3_URLS is empty", file=sys.stderr)
        return 2
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "xview3_out")

    with tempfile.TemporaryDirectory() as scratch:
        for url in urls:
            name = _filename(url)
            target = Path(scratch) / name
            print(f"downloading {name} ...", flush=True)
            with requests.get(url, stream=True, timeout=120) as response:
                response.raise_for_status()
                with open(target, "wb") as handle:
                    for chunk in response.iter_content(chunk_size=8 * 1024 * 1024):
                        handle.write(chunk)
            print(f"  {target.stat().st_size / 1e6:.0f} MB -> {ingest_file(target, out_dir)}", flush=True)
            target.unlink()

    labels = merge_labels(out_dir)
    scenes = [p.name for p in out_dir.iterdir() if p.is_dir()]
    print(f"scenes: {scenes}; label rows: {labels}")
    return 0 if scenes and labels else 1


if __name__ == "__main__":
    sys.exit(main())
