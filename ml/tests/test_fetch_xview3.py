import gzip
import tarfile

from cloud.fetch_xview3 import ingest_file, merge_labels


def test_ingest_extracts_scenes_and_merges_labels(tmp_path):
    scene_src = tmp_path / "src" / "sceneA"
    scene_src.mkdir(parents=True)
    (scene_src / "VH_dB.tif").write_bytes(b"x")
    archive = tmp_path / "sceneA.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(scene_src, arcname="sceneA")

    train = tmp_path / "train.csv.gz"
    train.write_bytes(gzip.compress(b"scene_id,a\nsceneA,1\n"))
    valid = tmp_path / "validation.csv"
    valid.write_text("scene_id,a\nsceneB,2\n", encoding="utf-8")

    out = tmp_path / "out"
    assert ingest_file(archive, out) == "scene-archive"
    assert ingest_file(train, out) == "labels"
    assert ingest_file(valid, out) == "labels"

    assert merge_labels(out) == 2
    assert (out / "sceneA" / "VH_dB.tif").exists()
    assert (out / "labels.csv").read_text(encoding="utf-8").splitlines() == [
        "scene_id,a", "sceneA,1", "sceneB,2",
    ]
    assert not (out / "_labels").exists()
