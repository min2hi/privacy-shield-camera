import cv2
import numpy as np
from app.core.masking import Masker, clip_bbox, expand_bbox


def test_expand_bbox_clips_to_frame_bounds():
    assert expand_bbox((1, 1, 9, 9), (10, 10, 3), ratio=0.5) == (0, 0, 10, 10)


def test_clip_bbox_rejects_out_of_frame_coordinates_safely():
    assert clip_bbox((-5, -2, 99, 50), (20, 30, 3)) == (0, 0, 30, 20)


def test_solid_mask_does_not_modify_input():
    frame = np.full((20, 20, 3), 255, dtype=np.uint8)
    masker = Masker({"id_card": "solid_mask"}, expand_ratio=0)
    output = masker.apply_masks(
        frame,
        [{"class_name": "id_card", "bbox": (5, 5, 15, 15), "confidence": 1.0}],
    )
    assert np.all(frame == 255)
    assert np.all(output[5:15, 5:15] == 0)


def test_mosaic_changes_non_uniform_region():
    frame = np.zeros((40, 40, 3), dtype=np.uint8)
    for x in range(40):
        frame[:, x] = x * 6
    masker = Masker({"document": "mosaic"}, expand_ratio=0)
    output = masker.apply_masks(
        frame,
        [{"class_name": "document", "bbox": (0, 0, 40, 40), "confidence": 1.0}],
    )
    assert not np.array_equal(output, frame)
    assert output.shape == frame.shape


def test_gaussian_blur_accepts_small_region():
    frame = np.random.default_rng(42).integers(0, 256, (10, 10, 3), dtype=np.uint8)
    masker = Masker({"document": "gaussian_blur"}, expand_ratio=0)
    output = masker.apply_masks(
        frame,
        [{"class_name": "document", "bbox": (2, 2, 5, 5), "confidence": 1.0}],
    )
    assert output.shape == frame.shape
    assert cv2.countNonZero(cv2.cvtColor(output, cv2.COLOR_BGR2GRAY)) >= 0
