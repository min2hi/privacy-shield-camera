"""Deterministic environment and local-asset smoke check."""

from __future__ import annotations

import hashlib
import importlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "privacy-shield-app"
REQUIRED_MODULES = ("cv2", "numpy", "yaml", "PySide6", "ultralytics", "onnxruntime")
REQUIRED_ASSETS = (
    APP_ROOT / "models" / "yolov8n.pt",
    APP_ROOT / "models" / "face_detection_yunet.onnx",
    APP_ROOT / "models" / "mobilefacenet.onnx",
    APP_ROOT / "models" / "yolov8n.dev-manifest.json",
    APP_ROOT / "configs" / "default.yaml",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    report: dict[str, object] = {
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "modules": {},
        "assets": {},
        "errors": [],
    }

    for name in REQUIRED_MODULES:
        try:
            module = importlib.import_module(name)
            report["modules"][name] = getattr(module, "__version__", "imported")
        except Exception as exc:  # smoke report must include every failure
            report["errors"].append(f"import {name}: {exc}")

    for path in REQUIRED_ASSETS:
        if not path.is_file() or path.stat().st_size == 0:
            report["errors"].append(f"missing/empty asset: {path}")
            continue
        report["assets"][str(path.relative_to(ROOT))] = {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }

    sys.path.insert(0, str(APP_ROOT))
    try:
        from app.utils.config_loader import ConfigLoader

        config = ConfigLoader(APP_ROOT / "configs" / "default.yaml")
        report["config"] = {
            "name": config.get("app.name"),
            "model_path": str(config.resolve_path("model.path")),
            "manifest_path": str(config.resolve_path("model.manifest_path")),
        }
    except Exception as exc:
        report["errors"].append(f"config: {exc}")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
