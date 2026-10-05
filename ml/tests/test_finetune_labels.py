from training.finetune_xview3 import box_side_px, tile_labels


def test_box_side_scales_with_length_and_is_clamped():
    assert box_side_px(None) == 12.0
    assert box_side_px(5) == 6.0
    assert box_side_px(100) == 13.0
    assert box_side_px(5000) == 64.0


def test_tile_labels_only_keeps_vessels_inside_the_tile():
    truth = [
        {"x_center_px": 700, "y_center_px": 100, "length_m": 100},
        {"x_center_px": 100, "y_center_px": 100, "length_m": 100},
    ]
    boxes = tile_labels(truth, row_off=0, col_off=640)
    assert len(boxes) == 1
    cx, cy, w, h = boxes[0]
    assert abs(cx - 60 / 640) < 1e-9 and abs(cy - 100 / 640) < 1e-9
    assert abs(w - 13 / 640) < 1e-9 and abs(h - 13 / 640) < 1e-9


def test_tile_labels_clips_boxes_at_the_tile_edge():
    truth = [{"x_center_px": 2, "y_center_px": 300, "length_m": 400}]
    (cx, _, w, _), = tile_labels(truth, row_off=0, col_off=0)
    assert w < 52 / 640
    assert cx - w / 2 >= 0
