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
        self.face_recognizer = SimpleNamespace(registered_embeddings=[])
        self.masker = SimpleNamespace(override_mask_mode=None)
        self.mask_owner_face = config.get("face_recognition.mask_owner", True)
        self.mask_strangers_face = config.get("face_recognition.mask_stranger", False)


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
