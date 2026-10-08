from __future__ import annotations

from datetime import datetime, timezone

from app.models.schemas import ActivityAggregate
from app.services import yolo_scan
from app.store.repository import RiskEventRepository


class _FakeIndex:
    """Cells near (8, 80) count as inside an MPA, near (9, 80) as near one."""

    def nearest(self, lat, lon):
        if abs(lat - 8.0) < 0.5:
            return "Test Reef", 0.0, True, False
        if abs(lat - 9.0) < 0.5:
            return "Test Reef", 4.0, False, True
        return None, float("inf"), False, False


def _cell(lat, lon, count):
    return ActivityAggregate(
        id=f"c{lat}{lon}", dataset="d", lat=lat, lon=lon, detection_count=count,
        report_start="2026-10-01", report_end="2026-10-08", provider_time=None,
        ingested_at=datetime.now(timezone.utc),
    )


def test_select_cells_prefers_mpa_then_count(monkeypatch):
    monkeypatch.setattr(yolo_scan.mpa_index, "get_index", lambda: _FakeIndex())
    cells = [_cell(20.0, 80.0, 99), _cell(9.0, 80.0, 1), _cell(8.0, 80.0, 1)]
    picked = yolo_scan.select_cells(cells, top_n=2)
    assert [c.lat for c in picked] == [8.0, 9.0]


def test_build_event_does_not_claim_dark_vessel(monkeypatch):
    monkeypatch.setattr(yolo_scan.mpa_index, "get_index", lambda: _FakeIndex())
    event = yolo_scan.build_event(
        {"lat": 8.0, "lon": 80.0, "confidence": 0.7}, _cell(8.0, 80.0, 3),
        datetime(2026, 10, 8, tzinfo=timezone.utc),
    )
    assert event.source == "YOLO_SAR"
    assert event.inside_mpa and event.risk_level == "CRITICAL"
    assert event.ais_matched is False and event.ais_data_available is False
    assert "not a confirmed dark vessel" in event.uncertainty


def test_scan_cells_upserts_and_survives_failures(monkeypatch):
    monkeypatch.setattr(yolo_scan.mpa_index, "get_index", lambda: _FakeIndex())
    repo = RiskEventRepository()
    monkeypatch.setattr("app.store.repository.repo", repo)
    monkeypatch.setattr(repo, "save", lambda: None)

    def fake_detect(lat, lon, date):
        if lat == 9.0:
            raise RuntimeError("sentinel hub down")
        return {"detections": [{"lat": lat, "lon": lon, "confidence": 0.6}]}

    monkeypatch.setattr(yolo_scan, "_detect", fake_detect)
    summary = yolo_scan.scan_cells([_cell(8.0, 80.0, 2), _cell(9.0, 80.0, 2)], top_n=5)
    assert summary["cells_scanned"] == 2
    assert summary["cells_failed"] == 1
    assert summary["events_upserted"] == 1
    assert len(repo.all(source="YOLO_SAR")) == 1
