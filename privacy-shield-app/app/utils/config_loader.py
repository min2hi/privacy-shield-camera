from pathlib import Path

import yaml

APP_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_MASK_MODES = {"solid_mask", "mosaic", "gaussian_blur"}


class ConfigLoader:
    def __init__(self, config_path="configs/default.yaml"):
        candidate = Path(config_path).expanduser()
        if not candidate.is_absolute():
            cwd_candidate = (Path.cwd() / candidate).resolve()
            candidate = cwd_candidate if cwd_candidate.exists() else (APP_ROOT / candidate).resolve()
        self.config_path = candidate.resolve()
        self.config = {}
        self.load_config()

    def load_config(self):
        if not self.config_path.is_file():
            raise FileNotFoundError(f"Không tìm thấy file cấu hình tại: {self.config_path}")

        with open(self.config_path, encoding="utf-8") as f:
            loaded = yaml.safe_load(f)

        if not isinstance(loaded, dict):
            raise ValueError("Cấu hình gốc phải là một YAML mapping")

        self.config = loaded
        self.validate()

    def get(self, key_path, default=None):
        """
        Lấy cấu hình theo key path dạng 'app.privacy_mode' hoặc 'privacy.mask_mode'.
        """
        keys = key_path.split(".")
        val = self.config
        try:
            for k in keys:
                val = val[k]
            return val
        except (KeyError, TypeError):
            return default

    def resolve_path(self, key_path, default=None):
        """Resolve a configured path against the desktop app root."""
        raw_path = self.get(key_path, default)
        if raw_path is None:
            return None
        path = Path(raw_path).expanduser()
        return path.resolve() if path.is_absolute() else (APP_ROOT / path).resolve()

    def validate(self):
        """Reject invalid runtime configuration before opening models or cameras."""
        errors = []

        def require_positive(key):
            value = self.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
                errors.append(f"{key} phải là số > 0")

        for key in ("camera.width", "camera.height", "camera.fps", "model.image_size"):
            require_positive(key)

        for key in ("camera.max_read_failures", "camera.read_retry_delay_ms"):
            value = self.get(key, 1)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                errors.append(f"{key} phải là số nguyên >= 1")

        for key in ("model.confidence", "model.iou"):
            value = self.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
                errors.append(f"{key} phải nằm trong [0, 1]")

        expansion = self.get("privacy.expand_bbox_ratio")
        if (
            not isinstance(expansion, (int, float))
            or isinstance(expansion, bool)
            or not 0 <= expansion <= 1
        ):
            errors.append("privacy.expand_bbox_ratio phải nằm trong [0, 1]")

        for key in ("privacy.hold_frames", "privacy.frame_skipping.skip_ratio"):
            value = self.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                errors.append(f"{key} phải là số nguyên >= 1")

        default_mode = self.get("privacy.mask_mode")
        if default_mode not in ALLOWED_MASK_MODES:
            errors.append(f"privacy.mask_mode không hợp lệ: {default_mode!r}")

        presets = self.get("model.class_mask_presets", {})
        if not isinstance(presets, dict) or not presets:
            errors.append("model.class_mask_presets phải là mapping không rỗng")
        elif invalid := {
            name: mode for name, mode in presets.items() if mode not in ALLOWED_MASK_MODES
        }:
            errors.append(f"class mask mode không hợp lệ: {invalid}")

        if errors:
            raise ValueError("Cấu hình không hợp lệ:\n- " + "\n- ".join(errors))

    def set(self, key_path, value):
        """
        Ghi đè cấu hình tạm thời trong bộ nhớ.
        """
        keys = key_path.split(".")
        val = self.config
        for k in keys[:-1]:
            if k not in val or not isinstance(val[k], dict):
                val[k] = {}
            val = val[k]
        val[keys[-1]] = value
