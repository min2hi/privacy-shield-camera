from app.core.temporal_smoothing import TemporalSmoothing, calculate_iou


def detection(bbox=(10, 10, 20, 20), class_name="document", mask_mode="mosaic"):
    return {
        "class_name": class_name,
        "bbox": bbox,
        "confidence": 0.9,
        "mask_mode": mask_mode,
    }


def test_iou_known_overlap():
    assert calculate_iou((0, 0, 10, 10), (5, 0, 15, 10)) == 1 / 3


def test_detection_is_held_then_expires():
    smoothing = TemporalSmoothing(hold_frames=2)
    assert len(smoothing.update([detection()])) == 1
    assert len(smoothing.update([])) == 1
    assert smoothing.update([]) == []


def test_different_classes_do_not_merge():
    smoothing = TemporalSmoothing(hold_frames=3)
    smoothing.update([detection(class_name="document")])
    output = smoothing.update([detection(class_name="receipt")])
    assert {item["class_name"] for item in output} == {"document", "receipt"}


def test_reset_drops_all_tracks():
    smoothing = TemporalSmoothing(hold_frames=3)
    smoothing.update([detection()])
    smoothing.reset()
    assert smoothing.update([]) == []
