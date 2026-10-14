"""Unit tests for app.core.detector module."""
import numpy as np
import pytest


class FakeYOLOBox:
    """Mock YOLO box result."""
    def __init__(self, cls_id, conf, xyxy):
        import torch
        self.cls = torch.tensor([cls_id]).unsqueeze(0)
        self.conf = torch.tensor([conf]).unsqueeze(0)
        self.xyxy = torch.tensor([xyxy]).unsqueeze(0)


class FakeYOLOResult:
    def __init__(self, boxes):
        self.boxes = boxes


class FakeYOLOModel:
    """Mock YOLO model for deterministic testing."""
    def __init__(self):
        self.names = {0: "cell phone", 1: "person", 2: "id_card"}
    
    def predict(self, source=None, conf=0.25, iou=0.45, device="cpu", verbose=False, imgsz=640):
        # Return a fake detection: cell phone at (100,100,200,200) with conf 0.85
        boxes = [
            FakeYOLOBox(0, 0.85, [100, 100, 200, 200]),
            FakeYOLOBox(1, 0.70, [300, 300, 400, 400]),
        ]
        return [FakeYOLOResult(boxes)]


def make_detector_with_fake_model():
    """Create a Detector with injected fake YOLO model."""
    from app.core.detector import Detector
    det = object.__new__(Detector)
    det.model_path = "fake.pt"
    det.confidence = 0.25
    det.iou = 0.45
    det.device = "cpu"
    det.image_size = 640
    det.manifest = None
    det.model = FakeYOLOModel()
    return det


def test_detect_returns_all_classes():
    det = make_detector_with_fake_model()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    results = det.detect(frame)
    assert len(results) == 2
    assert results[0]["class_name"] == "cell phone"
    assert results[1]["class_name"] == "person"


def test_detect_filters_selected_classes():
    det = make_detector_with_fake_model()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    results = det.detect(frame, selected_classes=["cell phone"])
    assert len(results) == 1
    assert results[0]["class_name"] == "cell phone"
    assert results[0]["confidence"] == pytest.approx(0.85, abs=0.01)


def test_detect_returns_xyxy_bbox():
    det = make_detector_with_fake_model()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    results = det.detect(frame)
    bbox = results[0]["bbox"]
    assert len(bbox) == 4
    x1, y1, x2, y2 = bbox
    assert x1 < x2
    assert y1 < y2


def test_detect_no_model_returns_empty():
    det = make_detector_with_fake_model()
    det.model = None
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    results = det.detect(frame)
    assert results == []


def test_supported_class_names():
    det = make_detector_with_fake_model()
    names = det.supported_class_names
    assert "cell phone" in names
    assert "person" in names
