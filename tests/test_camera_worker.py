from __future__ import annotations

import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from app.ui.camera_worker import CameraWorker


class FakeConfig:
    values = {
        "camera.width": 8,
        "camera.height": 6,
        "camera.fps": 30,
        "camera.max_read_failures": 2,
        "camera.read_retry_delay_ms": 1,
        "output.virtual_camera.enabled": False,
    }

    def get(self, key, default=None):
        return self.values.get(key, default)


class FakePipeline:
    def __init__(self):
        self.config = FakeConfig()
        self.masker = type("MaskerFixture", (), {"override_mask_mode": None})()
        self.reset_count = 0

    @staticmethod
    def privacy_screen(frame, reason):
        return np.zeros_like(frame)

    def process_frame(self, frame, selected_classes=None):
        return frame + 1, {
            "fps": 30.0,
            "latency_ms": 1.0,
            "detected_count": 0,
            "detections": [],
            "state": "protected",
        }

    def reset_tracking(self):
        self.reset_count += 1


class FakeCapture:
    def __init__(self, frames, opened=True):
        self.frames = list(frames)
        self.opened = opened
        self.released = False

    def isOpened(self):
        return self.opened

    def set(self, *_args):
        return True

    def read(self):
        if self.frames:
            return True, self.frames.pop(0).copy()
        return False, None

    def release(self):
        self.released = True


def test_paused_worker_emits_privacy_screen_not_raw_frame():
    raw = np.full((6, 8, 3), 177, dtype=np.uint8)
    capture = FakeCapture([raw])
    pipeline = FakePipeline()
    worker = CameraWorker(
        pipeline,
        capture_factory=lambda _index: capture,
        sleep_fn=lambda _seconds: None,
    )
    worker.safe_mode_active = False
    emitted = []
    worker.frame_ready.connect(lambda image, metrics: emitted.append((image.copy(), metrics)))

    worker.run()

    assert emitted[0][1]["state"] == "paused_safe"
    image = emitted[0][0]
    assert image.pixelColor(0, 0).red() == 0
    assert image.pixelColor(0, 0).green() == 0
    assert image.pixelColor(0, 0).blue() == 0
    assert capture.released
    assert pipeline.reset_count == 1


def test_disconnect_is_bounded_and_emits_error_screen():
    capture = FakeCapture([])
    pipeline = FakePipeline()
    worker = CameraWorker(
        pipeline,
        capture_factory=lambda _index: capture,
        sleep_fn=lambda _seconds: None,
    )
    emitted = []
    errors = []
    worker.frame_ready.connect(lambda image, metrics: emitted.append(metrics))
    worker.camera_error.connect(errors.append)

    worker.run()

    assert emitted[-1]["state"] == "error"
    assert emitted[-1]["error"] == "camera disconnected"
    assert errors == ["Camera mất kết nối"]
    assert capture.released


def test_update_config_and_get_config():
    worker = CameraWorker(FakePipeline())
    worker.update_config(
        safe_mode=False,
        override_mask="solid_mask",
        selected_classes=["screen", "credit_card"],
    )
    safe_mode, override_mask, classes = worker._get_config()
    assert safe_mode is False
    assert override_mask == "solid_mask"
    assert classes == ["screen", "credit_card"]

    worker.update_config(safe_mode=True)
    safe_mode, override_mask, classes = worker._get_config()
    assert safe_mode is True
    assert override_mask == "solid_mask"
    assert classes == ["screen", "credit_card"]


def test_stop_sets_running_false_without_releasing_capture():
    capture = FakeCapture([])
    worker = CameraWorker(FakePipeline(), capture_factory=lambda _idx: capture)
    worker._capture = capture
    worker.stop()
    assert worker.running is False
    assert capture.released is False
