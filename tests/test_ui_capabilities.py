from __future__ import annotations

import os
from importlib import import_module

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PySide6 = pytest.importorskip("PySide6")

QApplication = import_module("PySide6.QtWidgets").QApplication
MainWindow = import_module("app.ui.main_window").MainWindow
config_module = import_module("app.utils.config_loader")
APP_ROOT = config_module.APP_ROOT
ConfigLoader = config_module.ConfigLoader


class FakePipeline:
    def __init__(self, config):
        self.config = config
        self.detector = type(
            "DetectorFixture",
            (),
            {"confidence": 0.25, "supported_class_names": {"cell phone"}},
        )()
        self.face_recognizer = type("FaceFixture", (), {"registered_embeddings": []})()
        self.masker = type("MaskFixture", (), {"override_mask_mode": None})()
        self.mask_owner_face = True
        self.mask_strangers_face = False


def test_unsupported_model_classes_are_disabled_in_ui():
    app = QApplication.instance() or QApplication([])
    config = ConfigLoader(APP_ROOT / "configs" / "default.yaml")
    window = MainWindow(
        config_path=APP_ROOT / "configs" / "default.yaml",
        pipeline=FakePipeline(config),
        auto_start=False,
    )
    try:
        assert window.class_checkboxes["cell phone"].isEnabled()
        assert window.class_checkboxes["cell phone"].isChecked()
        assert not window.class_checkboxes["id_card"].isEnabled()
        assert not window.class_checkboxes["id_card"].isChecked()
        assert window.selected_classes == ["cell phone"]
    finally:
        window.close()
        app.processEvents()
