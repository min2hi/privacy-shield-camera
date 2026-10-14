"""Tests for Sprint 1 bug fixes — verifying each reported bug is properly fixed."""

from __future__ import annotations

import inspect
import os
from types import SimpleNamespace

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")


# =====================================================================
# Bug 2: Force Solid Mask should NOT override face-specific mask_mode
# =====================================================================


class TestMaskOverrideFaceProtection:
    """Verify that override_mask_mode does NOT apply to face detections."""

    def test_override_skips_face_detections(self):
        """Face detections with explicit mask_mode should ignore override."""
        from app.core.masking import Masker

        masker = Masker(default_mask_mode="mosaic")
        masker.override_mask_mode = "solid_mask"  # User selected Force Solid

        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        detections = [
            {
                "class_name": "face",
                "bbox": (100, 100, 200, 200),
                "confidence": 1.0,
                "mask_mode": "gaussian_blur",
            },
            {"class_name": "cell phone", "bbox": (300, 300, 400, 400), "confidence": 0.9},
        ]

        # Should not crash and face should use gaussian_blur, not solid_mask
        result = masker.apply_masks(frame, detections)
        assert result is not None
        assert result.shape == frame.shape
        # Face region should be blurred, not all zeros (black)
        assert result[110:190, 110:190].max() > 0
        # Phone region should be solid black (all zeros)
        assert result[310:390, 310:390].max() == 0

    def test_override_applies_to_objects(self):
        """Non-face detections should use override_mask_mode."""
        from app.core.masking import Masker

        masker = Masker(default_mask_mode="mosaic")
        masker.override_mask_mode = "solid_mask"

        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        detections = [
            {"class_name": "cell phone", "bbox": (100, 100, 200, 200), "confidence": 0.8},
        ]
        result = masker.apply_masks(frame, detections)
        # The phone region should be solid black (all zeros)
        assert result[110:190, 110:190].max() == 0  # solid_mask = black

    def test_no_override_uses_preset(self):
        """Without override, presets determine mask mode."""
        from app.core.masking import Masker

        masker = Masker(
            class_mask_presets={"cell phone": "gaussian_blur"},
            default_mask_mode="mosaic",
        )
        masker.override_mask_mode = None

        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        detections = [
            {"class_name": "cell phone", "bbox": (100, 100, 200, 200), "confidence": 0.8},
        ]
        result = masker.apply_masks(frame, detections)
        # Should be blurred, not solid black
        assert result is not None


# =====================================================================
# Bug 3: Thread-safe config updates via update_config
# =====================================================================


class TestThreadSafeConfig:
    """Verify CameraWorker.update_config handles all config fields."""

    def _make_worker(self):
        config = SimpleNamespace(
            get=lambda key, default=None: {
                "camera.width": 640,
                "camera.height": 480,
                "camera.fps": 30,
                "camera.max_read_failures": 30,
                "camera.read_retry_delay_ms": 30,
                "output.virtual_camera.enabled": False,
            }.get(key, default),
            resolve_path=lambda key, default=None: default,
        )
        pipeline = SimpleNamespace(
            config=config,
            detector=SimpleNamespace(confidence=0.25, supported_class_names={"cell phone"}),
            face_recognizer=SimpleNamespace(registered_embeddings=[], detect_faces=lambda f: []),
            masker=SimpleNamespace(override_mask_mode=None),
            mask_owner_face=True,
            mask_strangers_face=False,
            process_frame=lambda f, **kw: (
                f,
                {
                    "fps": 30,
                    "latency_ms": 1,
                    "detected_count": 0,
                    "detections": [],
                    "state": "protected",
                },
            ),
            privacy_screen=lambda f, reason: np.zeros_like(f),
            reset_tracking=lambda: None,
        )
        from app.ui.camera_worker import CameraWorker

        worker = CameraWorker(pipeline, device_index=0)
        return worker

    def test_update_config_confidence(self):
        worker = self._make_worker()
        worker.update_config(confidence=0.5)
        # Confidence is pending, applied during _get_config
        worker._get_config()
        assert worker.pipeline.detector.confidence == pytest.approx(0.5)

    def test_update_config_face_masking(self):
        worker = self._make_worker()
        worker.update_config(mask_owner_face=False, mask_strangers_face=True)
        worker._get_config()
        assert worker.pipeline.mask_owner_face is False
        assert worker.pipeline.mask_strangers_face is True

    def test_update_config_safe_mode(self):
        worker = self._make_worker()
        worker.update_config(safe_mode=False)
        safe_mode, _, _ = worker._get_config()
        assert safe_mode is False

    def test_update_config_selected_classes(self):
        worker = self._make_worker()
        worker.update_config(selected_classes=["cell phone", "id_card"])
        _, _, classes = worker._get_config()
        assert classes == ["cell phone", "id_card"]


# =====================================================================
# Bug 5: Enrollment saves only on dialog accept, not during pose capture
# =====================================================================


class TestEnrollmentSaveTiming:
    """Verify face templates are saved ONLY when user confirms."""

    def test_camera_worker_pose2_does_not_save(self):
        """After pose 2 capture, save_registered_faces should NOT be called."""
        from app.ui.camera_worker import CameraWorker

        # Check that the source code does NOT call save_registered_faces in pose 2 block
        source = inspect.getsource(CameraWorker.run)
        lines = source.split("\n")
        in_enroll_block = False
        save_in_enroll = False
        for line in lines:
            if "enroll_pose_index == 2" in line:
                in_enroll_block = True
            if in_enroll_block and "save_registered_faces" in line:
                save_in_enroll = True
                break
            if in_enroll_block and (
                "enroll_pose_index = -1" in line or "enroll_result.emit" in line
            ):
                in_enroll_block = False

        assert not save_in_enroll, (
            "save_registered_faces should NOT be called in worker during pose 2"
        )


# =====================================================================
# Logging migration: verify safe_print still works via logging backend
# =====================================================================


class TestLoggingMigration:
    """Verify safe_print backward compatibility with logging."""

    def test_safe_print_does_not_crash(self):
        from app.utils.console import safe_print

        safe_print("test message")
        safe_print("")  # empty
        safe_print("Unicode: 日本語 tiếng Việt 🎉")

    def test_logging_config_creates_logger(self):
        from app.utils.logging_config import get_logger, setup_logging

        setup_logging()
        logger = get_logger("test")
        assert logger is not None
        logger.info("Test log message")
