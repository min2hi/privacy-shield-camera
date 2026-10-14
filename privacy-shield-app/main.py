"""GUI entry point for Privacy Shield Camera."""

from __future__ import annotations

import argparse
import sys
from types import SimpleNamespace

from app.ui.main_window import MainWindow
from app.utils.config_loader import ConfigLoader
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication


class FixturePipeline:
    """Side-effect-free UI fixture used for CI and clean-machine smoke tests."""

    def __init__(self, config):
        self.config = config
        supported = {"cell phone"}
        self.detector = SimpleNamespace(
            confidence=config.get("model.confidence", 0.25),
            supported_class_names=supported,
        )
        self.face_recognizer = SimpleNamespace(
            registered_embeddings=[],
            detect_faces=lambda frame: [],
            extract_embedding=lambda face_img: None,
            estimate_head_pose=lambda face_obj: 0,
            register_face_pose=lambda frame, bbox, idx: False,
            save_registered_faces=lambda: False,
            delete_registered_faces=lambda: False,
            load_registered_face=lambda: [],
        )
        self.masker = SimpleNamespace(
            override_mask_mode=None,
            default_mask_mode="mosaic",
            expand_ratio=0.15,
        )
        self.scheduler = SimpleNamespace(
            enabled=True,
            skip_ratio=2,
            reset=lambda: None,
        )
        self.smoothing = SimpleNamespace(
            hold_frames=5,
            reset=lambda: None,
        )
        self.mask_owner_face = config.get("face_recognition.mask_owner", True)
        self.mask_strangers_face = config.get("face_recognition.mask_stranger", False)

    def reset_tracking(self):
        pass

    @staticmethod
    def privacy_screen(frame, reason="SAFE MODE ACTIVE", *, fallback_size=(480, 640)):
        import numpy as np
        h, w = frame.shape[:2] if frame is not None else fallback_size
        return np.zeros((h, w, 3), dtype=np.uint8)


def main() -> int:
    parser = argparse.ArgumentParser(description="Privacy Shield Camera")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--fixture", action="store_true", help="Open UI without model/camera")
    parser.add_argument("--quit-after-ms", type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()

    app = QApplication(sys.argv)
    config = ConfigLoader(args.config)
    fixture_pipeline = FixturePipeline(config) if args.fixture else None
    window = MainWindow(
        config_path=args.config,
        pipeline=fixture_pipeline,
        auto_start=not args.fixture,
    )
    window.show()
    if args.quit_after_ms > 0:
        QTimer.singleShot(args.quit_after_ms, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
