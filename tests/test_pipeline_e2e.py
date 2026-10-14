"""End-to-end pipeline tests with mocked detector and face recognizer."""
import numpy as np


class StubDetector:
    def __init__(self, detections=None):
        self.confidence = 0.25
        self._detections = detections or []
        self.supported_class_names = {"cell phone", "id_card"}
    
    def detect(self, frame, selected_classes=None):
        if selected_classes:
            return [d for d in self._detections if d["class_name"] in selected_classes]
        return list(self._detections)


class StubFaceRecognizer:
    def __init__(self):
        self.registered_embeddings = []
    
    def detect_faces(self, frame):
        return []


def make_pipeline(detections=None, face_rec=None):
    from app.core.pipeline import PrivacyPipeline
    from app.utils.config_loader import ConfigLoader
    config = ConfigLoader("privacy-shield-app/configs/default.yaml")
    detector = StubDetector(detections)
    face_recognizer = face_rec or StubFaceRecognizer()
    return PrivacyPipeline(config, detector=detector, face_recognizer=face_recognizer)


def test_happy_path_no_detections():
    pipeline = make_pipeline()
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    processed, metrics = pipeline.process_frame(frame)
    assert processed.shape == frame.shape
    assert metrics["detected_count"] == 0
    assert metrics["state"] == "protected"


def test_happy_path_with_detection():
    dets = [{
        "class_name": "cell phone",
        "confidence": 0.9,
        "bbox": (100, 100, 200, 200),
    }]
    pipeline = make_pipeline(detections=dets)
    frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
    frame[100:200, 100:200] = np.arange(100 * 100 * 3, dtype=np.uint8).reshape(100, 100, 3)
    processed, metrics = pipeline.process_frame(frame, selected_classes=["cell phone"])
    assert metrics["detected_count"] >= 1
    # The masked region should differ from original
    roi_orig = frame[100:200, 100:200]
    roi_proc = processed[100:200, 100:200]
    assert not np.array_equal(roi_orig, roi_proc)


def test_unsupported_classes_reported():
    pipeline = make_pipeline()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    _, metrics = pipeline.process_frame(frame, selected_classes=["cell phone", "qr_code"])
    assert "qr_code" in metrics["unsupported_classes"]


def test_frame_skipping_reuses_detections():
    dets = [{
        "class_name": "cell phone",
        "confidence": 0.9,
        "bbox": (50, 50, 150, 150),
    }]
    pipeline = make_pipeline(detections=dets)
    frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
    # Frame 1: should detect
    _, m1 = pipeline.process_frame(frame, selected_classes=["cell phone"])
    # Frame 2: should reuse (skip)
    _, m2 = pipeline.process_frame(frame, selected_classes=["cell phone"])
    assert m1["detected_count"] >= 1
    assert m2["detected_count"] >= 1  # Reused from cache


def test_metrics_contain_fps_and_latency():
    pipeline = make_pipeline()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    _, metrics = pipeline.process_frame(frame)
    assert "fps" in metrics
    assert "latency_ms" in metrics
    assert metrics["latency_ms"] >= 0
