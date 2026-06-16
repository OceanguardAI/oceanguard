import json

import run_inference_from_tif as workflow


def test_run_inference_pipeline_orchestrates_all_steps(tmp_path, monkeypatch):
    tif_path = tmp_path / "VH_dB.tif"
    model_path = tmp_path / "best.pt"
    tiles_dir = tmp_path / "tiles"
    output_path = tmp_path / "outputs" / "detections_scene1_georef.json"
    checkpoint_path = tmp_path / "outputs" / "detect_checkpoint.json"

    tif_path.write_text("placeholder", encoding="utf-8")
    model_path.write_text("placeholder", encoding="utf-8")

    calls: list[tuple[str, object]] = []

    def fake_tile_sar(tif: str, output_dir: str, tile_size: int = 640):
        calls.append(("tile", tif, output_dir, tile_size))
        return [(0, 0, str(tiles_dir / "tile_r0000_c0000.png"))]

    def fake_detect_tiles(
        tile_dir: str,
        model: str,
        conf_threshold: float = 0.45,
        chunk_size: int = 25,
        checkpoint_path: str | None = None,
    ):
        calls.append(("detect", tile_dir, model, conf_threshold, chunk_size, checkpoint_path))
        return [
            {
                "tile": str(tiles_dir / "tile_r0000_c0000.png"),
                "row_off": 0,
                "col_off": 0,
                "x_center_px": 100.0,
                "y_center_px": 200.0,
                "width_px": 20.0,
                "height_px": 10.0,
                "confidence": 0.75,
            }
        ]

    def fake_georeference_detections(detections: list[dict]):
        calls.append(("georef", len(detections)))
        return [{**detections[0], "lat": 7.23, "lon": 4.56}]

    monkeypatch.setattr(workflow, "tile_sar", fake_tile_sar)
    monkeypatch.setattr(workflow, "detect_tiles", fake_detect_tiles)
    monkeypatch.setattr(workflow, "georeference_detections", fake_georeference_detections)

    summary = workflow.run_inference_pipeline(
        tif_path=tif_path,
        model_path=model_path,
        tiles_dir=tiles_dir,
        output_path=output_path,
        checkpoint_path=checkpoint_path,
        tile_size=512,
        conf_threshold=0.5,
        chunk_size=10,
    )

    assert summary["tile_count"] == 1
    assert summary["detection_count"] == 1
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload[0]["lat"] == 7.23
    assert payload[0]["lon"] == 4.56

    assert calls[0][0] == "tile"
    assert calls[1][0] == "detect"
    assert calls[2][0] == "georef"


def test_run_inference_pipeline_requires_existing_inputs(tmp_path):
    tif_path = tmp_path / "missing.tif"
    model_path = tmp_path / "best.pt"
    model_path.write_text("placeholder", encoding="utf-8")

    try:
        workflow.run_inference_pipeline(
            tif_path=tif_path,
            model_path=model_path,
            tiles_dir=tmp_path / "tiles",
            output_path=tmp_path / "outputs" / "detections.json",
            checkpoint_path=tmp_path / "outputs" / "checkpoint.json",
        )
    except FileNotFoundError as exc:
        assert "GeoTIFF" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError for missing tif")
