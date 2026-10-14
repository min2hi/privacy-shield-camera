from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from app.utils.config_loader import APP_ROOT, ConfigLoader


def valid_config() -> dict:
    return {
        "app": {"name": "test"},
        "camera": {"device_index": 0, "width": 640, "height": 480, "fps": 30},
        "model": {
            "path": "models/yolov8n.pt",
            "confidence": 0.25,
            "iou": 0.45,
            "image_size": 320,
            "class_mask_presets": {"cell phone": "mosaic"},
        },
        "privacy": {
            "mask_mode": "mosaic",
            "expand_bbox_ratio": 0.15,
            "hold_frames": 5,
            "frame_skipping": {"enabled": True, "skip_ratio": 2},
        },
    }


def write_config(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


def test_default_config_resolves_model_from_app_root():
    config = ConfigLoader(APP_ROOT / "configs" / "default.yaml")
    assert config.resolve_path("model.path") == APP_ROOT / "models" / "yolov8n.pt"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("camera.width", 0),
        ("camera.fps", -1),
        ("model.confidence", 1.1),
        ("model.iou", -0.1),
        ("model.image_size", 0),
        ("privacy.expand_bbox_ratio", 1.1),
        ("privacy.hold_frames", 0),
        ("privacy.frame_skipping.skip_ratio", 0),
        ("privacy.mask_mode", "transparent"),
    ],
)
def test_invalid_config_is_rejected(tmp_path, key, value):
    payload = valid_config()
    target = payload
    parts = key.split(".")
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value

    with pytest.raises(ValueError, match=key.replace(".", r"\.")):
        ConfigLoader(write_config(tmp_path, payload))


def test_non_mapping_yaml_is_rejected(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("- not\n- a\n- mapping\n", encoding="utf-8")
    with pytest.raises(ValueError, match="YAML mapping"):
        ConfigLoader(path)
