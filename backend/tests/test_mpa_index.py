"""Tests for the multi-MPA spatial index (WDPA marine protected areas)."""
from __future__ import annotations

import json

import pytest

from app.services import mpa_index


@pytest.fixture
def two_mpa_file(tmp_path, monkeypatch):
    """Write a tiny two-MPA FeatureCollection and point the index at it."""
    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"NAME": "Test Reef A"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[79.6, 8.2], [79.8, 8.2], [79.8, 8.5], [79.6, 8.5], [79.6, 8.2]]],
                },
            },
            {
                "type": "Feature",
                "properties": {"NAME": "Test Reef B"},
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [[[[81.0, 6.0], [81.2, 6.0], [81.2, 6.2], [81.0, 6.2], [81.0, 6.0]]]],
                },
            },
        ],
    }
    (tmp_path / "mpas.geojson").write_text(json.dumps(fc), encoding="utf-8")
    monkeypatch.setattr(mpa_index.settings, "data_dir", tmp_path)
    idx = mpa_index.MPAIndex()
    idx.load()
    return idx


def test_loads_polygon_and_multipolygon(two_mpa_file):
    assert two_mpa_file.count == 2
    assert two_mpa_file.source == "mpas.geojson"


def test_point_inside_reports_zero_distance(two_mpa_file):
    name, dist, inside, near = two_mpa_file.nearest(8.35, 79.7)
    assert name == "Test Reef A"
    assert dist == 0.0
    assert inside is True
    assert near is False


def test_nearest_picks_correct_mpa(two_mpa_file):
    # A point near reef B should resolve to B, not A.
    name, dist, inside, near = two_mpa_file.nearest(6.1, 81.25)
    assert name == "Test Reef B"
    assert inside is False
    assert dist < mpa_index.NEAR_MPA_KM
    assert near is True


def test_far_point_not_near(two_mpa_file):
    name, dist, inside, near = two_mpa_file.nearest(8.35, 79.7 + 5.0)
    assert inside is False
    assert near is False
    assert dist > mpa_index.NEAR_MPA_KM


def test_empty_index_degrades_gracefully(tmp_path, monkeypatch):
    monkeypatch.setattr(mpa_index.settings, "data_dir", tmp_path)  # no files
    idx = mpa_index.MPAIndex()
    idx.load()
    assert idx.count == 0
    name, dist, inside, near = idx.nearest(8.0, 79.0)
    assert name is None
    assert inside is False and near is False
    assert dist == float("inf")
