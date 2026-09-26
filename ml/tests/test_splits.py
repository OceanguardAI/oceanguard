import pytest

from datasets.splits import assign_split, build_split_manifest


def test_split_assignment_is_deterministic_and_group_safe():
    records = [
        {"id": "a-1", "sequence_id": "a"},
        {"id": "a-2", "sequence_id": "a"},
        {"id": "b-1", "sequence_id": "b"},
        {"id": "c-1", "sequence_id": "c"},
    ]
    first = build_split_manifest(records, dataset_id="demo", seed=7)
    second = build_split_manifest(records, dataset_id="demo", seed=7)
    assert first == second
    assert first["records"][0]["split"] == first["records"][1]["split"]


def test_split_assignment_changes_with_seed():
    assert assign_split("sequence-a", seed=3) != assign_split("sequence-a", seed=5)


def test_split_manifest_requires_group_and_id():
    with pytest.raises(ValueError):
        build_split_manifest([{"id": "missing-group"}], dataset_id="demo")
