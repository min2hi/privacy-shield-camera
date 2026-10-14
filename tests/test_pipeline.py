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


def test_privacy_screen_none_frame():
    screen = PrivacyPipeline.privacy_screen(None)
    assert screen.shape == (480, 640, 3)

    custom_screen = PrivacyPipeline.privacy_screen(None, fallback_size=(100, 200))
    assert custom_screen.shape == (100, 200, 3)


def test_cache_invalidation_on_class_change():
    pipeline = PrivacyPipeline.__new__(PrivacyPipeline)
    reset_called = False

    def mock_reset():
        nonlocal reset_called
        reset_called = True

    pipeline.reset_tracking = mock_reset
    pipeline.detector = type("MockDetector", (), {"supported_class_names": {"cell phone", "laptop"}, "detect": lambda self, f, selected_classes=None: []})()
    pipeline.scheduler = type("MockScheduler", (), {"should_detect": lambda self: True, "update_detections": lambda self, d: None})()
    pipeline.face_rec_enabled = False
    pipeline.smoothing = type("MockSmoothing", (), {"update": lambda self, d: d})()
    pipeline.masker = type("MockMasker", (), {"apply_masks": lambda self, f, d: f})()
    pipeline.fail_safe = False
    pipeline.last_time = 0.0
    pipeline.fps = 0.0

    frame = np.zeros((10, 10, 3), dtype=np.uint8)

    # First run: initial classes
    pipeline.process_frame(frame, selected_classes=["cell phone"])
    assert not reset_called
    assert pipeline._last_effective_classes == ("cell phone",)

    # Same classes: should not reset
    pipeline.process_frame(frame, selected_classes=["cell phone"])
    assert not reset_called

    # Changed classes: should trigger reset_tracking
    pipeline.process_frame(frame, selected_classes=["laptop"])
    assert reset_called
    assert pipeline._last_effective_classes == ("laptop",)


def test_face_masking_fail_closed_owner():
    pipeline = PrivacyPipeline.__new__(PrivacyPipeline)
    pipeline.detector = type("MockDetector", (), {"supported_class_names": set(), "detect": lambda self, f, selected_classes=None: []})()
    pipeline.scheduler = type("MockScheduler", (), {"should_detect": lambda self: True, "update_detections": lambda self, d: None})()
    pipeline.face_rec_enabled = True
    pipeline.last_face_tracks = []
    pipeline.smoothing = type("MockSmoothing", (), {"update": lambda self, d: d})()
    pipeline.masker = type("MockMasker", (), {"apply_masks": lambda self, f, d: f})()
    pipeline.fail_safe = False
    pipeline.last_time = 0.0
    pipeline.fps = 0.0

    # Face recognizer returns 1 face, but verification fails (is_matched = False)
    mock_recognizer = type(
        "MockFaceRecognizer",
        (),
        {
            "detect_faces": lambda self, f: [{"bbox": (0, 0, 10, 10)}],
            "extract_embedding": lambda self, crop: np.zeros((128,)),
            "registered_embeddings": [np.ones((128,))],
            "verify_face": lambda self, emb: (False, 1.5),
        },
    )()
    pipeline.face_recognizer = mock_recognizer
    pipeline.mask_owner_face = True
    pipeline.mask_strangers_face = False

    frame = np.zeros((20, 20, 3), dtype=np.uint8)
    _, metrics = pipeline.process_frame(frame)

    # Fail-closed: unverified face masked with gaussian_blur because owner masking requested & registered embeddings present
    assert len(metrics["detections"]) == 1
    assert metrics["detections"][0]["class_name"] == "face"
    assert metrics["detections"][0]["mask_mode"] == "gaussian_blur"
