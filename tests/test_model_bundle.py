from __future__ import annotations

import hashlib
import json

import pytest
from app.core.model_bundle import ModelManifest


def write_manifest(tmp_path, model_bytes=b"trusted model", classes=None):
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(model_bytes)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "model_sha256": hashlib.sha256(model_bytes).hexdigest(),
                "supported_privacy_classes": classes or ["cell phone"],
                "status": "development_only",
                "source": "test fixture",
            }
        ),
        encoding="utf-8",
    )
    return model_path, manifest_path


def test_manifest_validates_asset_and_runtime_classes(tmp_path):
    model_path, manifest_path = write_manifest(tmp_path)
    manifest = ModelManifest.load(manifest_path)
    manifest.validate_asset(model_path)
    manifest.validate_runtime_classes({"person", "cell phone"})
    assert manifest.supported_privacy_classes == ("cell phone",)


def test_modified_model_is_rejected(tmp_path):
    model_path, manifest_path = write_manifest(tmp_path)
    manifest = ModelManifest.load(manifest_path)
    model_path.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        manifest.validate_asset(model_path)


def test_declared_class_missing_from_runtime_is_rejected(tmp_path):
    _, manifest_path = write_manifest(tmp_path, classes=["id_card"])
    manifest = ModelManifest.load(manifest_path)
    with pytest.raises(ValueError, match="missing declared classes"):
        manifest.validate_runtime_classes({"cell phone"})


def test_invalid_manifest_digest_is_rejected(tmp_path):
    _, manifest_path = write_manifest(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["model_sha256"] = "not-a-digest"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA256"):
        ModelManifest.load(manifest_path)
