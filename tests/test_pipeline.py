from __future__ import annotations

import numpy as np
from app.core.pipeline import PrivacyPipeline


class ExplodingDetector:
    supported_class_names = {"cell phone"}

    def detect(self, frame, selected_classes=None):
        raise RuntimeError("inference failed")


class AlwaysDetectScheduler:
    def should_detect(self):
        return True

    def update_detections(self, detections):
        raise AssertionError("unreachable")


def test_pipeline_exception_returns_privacy_screen_not_raw_frame():
    pipeline = PrivacyPipeline.__new__(PrivacyPipeline)
    pipeline.detector = ExplodingDetector()
    pipeline.scheduler = AlwaysDetectScheduler()
    pipeline.fail_safe = True

    raw = np.full((80, 160, 3), 173, dtype=np.uint8)
    output, metrics = pipeline.process_frame(raw, selected_classes=["cell phone"])

    assert metrics["state"] == "error"
    assert "inference failed" in metrics["error"]
    assert output.shape == raw.shape
    assert not np.array_equal(output, raw)
    assert np.any(output == 0)
