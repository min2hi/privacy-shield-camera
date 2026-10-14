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


class MockPipelineForFeatures:
    def __init__(self, config):
        self.config = config
        self.detector = type(
            "DetectorFixture",
            (),
            {"confidence": 0.25, "supported_class_names": {"cell phone"}},
        )()
        self.face_recognizer = type("FaceFixture", (), {"registered_embeddings": []})()
        self.masker = type(
            "MaskFixture",
            (),
            {"override_mask_mode": None, "default_mask_mode": "mosaic", "expand_ratio": 0.15},
        )()
        self.smoothing = type("SmoothFixture", (), {"hold_frames": 5})()
        self.scheduler = type("SchedFixture", (), {"enabled": True, "skip_ratio": 2})()
        self.reset_tracking_called = False
        self.mask_owner_face = True
        self.mask_strangers_face = False

    def reset_tracking(self):
        self.reset_tracking_called = True


def test_status_banner_and_presets_and_settings():
    from PySide6.QtCore import QSettings

    app = QApplication.instance() or QApplication([])
    config = ConfigLoader(APP_ROOT / "configs" / "default.yaml")
    pipeline = MockPipelineForFeatures(config)
    window = MainWindow(
        config_path=APP_ROOT / "configs" / "default.yaml",
        pipeline=pipeline,
        auto_start=False,
    )
    try:
        # 1. Test Status Banner initial state & updates
        assert "\u25cf PROTECTED" in window.status_banner.text()
        
        window._update_status_banner("paused_safe")
        assert "\u25cf PAUSED" in window.status_banner.text()
        
        window._update_status_banner("error")
        assert "\u25cf ERROR" in window.status_banner.text()
        
        window._update_status_banner("starting")
        assert "\u25cb STARTING" in window.status_banner.text()
        
        # Test toggling safe mode updates banner
        window.on_protection_toggled(False)
        assert "\u25cf PAUSED" in window.status_banner.text()
        
        window.on_protection_toggled(True)
        assert "\u25cf PROTECTED" in window.status_banner.text()
        
        # Test camera error updates banner
        window.on_camera_error("Test error")
        assert "\u25cf ERROR" in window.status_banner.text()

        # 2. Test Privacy Presets selector
        assert window.preset_combo.count() == 3
        # Switch to Low preset (index 0)
        window.preset_combo.setCurrentIndex(0)
        assert pipeline.masker.default_mask_mode == "gaussian_blur"
        assert pipeline.masker.expand_ratio == 0.05
        assert pipeline.smoothing.hold_frames == 2
        assert pipeline.scheduler.enabled is True
        assert pipeline.scheduler.skip_ratio == 3
        assert pipeline.reset_tracking_called is True

        # Switch to High preset (index 2)
        pipeline.reset_tracking_called = False
        window.preset_combo.setCurrentIndex(2)
        assert pipeline.masker.default_mask_mode == "solid_mask"
        assert pipeline.masker.expand_ratio == 0.25
        assert pipeline.smoothing.hold_frames == 8
        assert pipeline.scheduler.enabled is False
        assert pipeline.reset_tracking_called is True

        # 3. Test Settings Persistence
        settings = QSettings("PrivacyShield", "PrivacyShieldCamera")
        window.conf_slider.setValue(42)
        window.mask_mode_combo.setCurrentIndex(2)
        window.preset_combo.setCurrentIndex(0)
        window._save_settings()

        assert int(settings.value("confidence")) == 42
        assert int(settings.value("mask_mode_index")) == 2
        assert int(settings.value("preset_index")) == 0

        # Change values and reload
        window.conf_slider.setValue(80)
        window.mask_mode_combo.setCurrentIndex(1)
        window.preset_combo.setCurrentIndex(2)
        window._load_settings()

        assert window.conf_slider.value() == 42
        assert window.mask_mode_combo.currentIndex() == 2
        assert window.preset_combo.currentIndex() == 0
    finally:
        # Clean up settings
        settings = QSettings("PrivacyShield", "PrivacyShieldCamera")
        settings.remove("confidence")
        settings.remove("mask_mode_index")
        settings.remove("preset_index")
        window.close()
        app.processEvents()


def test_virtual_camera_ui_controls():
    app = QApplication.instance() or QApplication([])
    config = ConfigLoader(APP_ROOT / "configs" / "default.yaml")
    pipeline = MockPipelineForFeatures(config)
    window = MainWindow(
        config_path=APP_ROOT / "configs" / "default.yaml",
        pipeline=pipeline,
        auto_start=False,
    )
    try:
        assert hasattr(window, "vcam_switch")
        assert hasattr(window, "vcam_status_lbl")
        assert window.vcam_switch.isChecked() == config.get("output.virtual_camera.enabled", False)
        assert "Inactive" in window.vcam_status_lbl.text()

        window.vcam_switch.setChecked(True)
        assert "Active" in window.vcam_status_lbl.text()

        window.vcam_switch.setChecked(False)
        assert "Inactive" in window.vcam_status_lbl.text()
    finally:
        window.close()
        app.processEvents()


def test_fixture_pipeline_smoke():
    import numpy as np
    from main import FixturePipeline

    config = ConfigLoader(APP_ROOT / "configs" / "default.yaml")
    fixture = FixturePipeline(config)
    assert fixture.detector.confidence == config.get("model.confidence", 0.25)
    assert fixture.detector.supported_class_names == {"cell phone"}
    assert fixture.face_recognizer.detect_faces(None) == []
    assert fixture.face_recognizer.extract_embedding(None) is None
    assert fixture.face_recognizer.estimate_head_pose(None) == 0
    assert fixture.face_recognizer.register_face_pose(None, None, 0) is False
    assert fixture.face_recognizer.save_registered_faces() is False
    assert fixture.face_recognizer.delete_registered_faces() is False
    assert fixture.face_recognizer.load_registered_face() == []
    assert fixture.masker.default_mask_mode == "mosaic"
    assert fixture.scheduler.enabled is True
    assert fixture.smoothing.hold_frames == 5
    fixture.reset_tracking()

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    screen = fixture.privacy_screen(frame)
    assert screen.shape == (480, 640, 3)


