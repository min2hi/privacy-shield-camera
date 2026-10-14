"""Trusted model manifest validation for runtime startup."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelManifest:
    schema_version: int
    model_sha256: str
    supported_privacy_classes: tuple[str, ...]
    status: str
    source: str

    @classmethod
    def load(cls, path: str | Path) -> ModelManifest:
        manifest_path = Path(path)
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        required = {
            "schema_version",
            "model_sha256",
            "supported_privacy_classes",
            "status",
            "source",
        }
        missing = required - payload.keys()
        if missing:
            raise ValueError(f"Model manifest missing fields: {sorted(missing)}")
        classes = payload["supported_privacy_classes"]
        if not isinstance(classes, list) or not all(
            isinstance(name, str) and name for name in classes
        ):
            raise ValueError("supported_privacy_classes must be a list of names")
        if len(classes) != len(set(classes)):
            raise ValueError("supported_privacy_classes contains duplicates")
        digest = str(payload["model_sha256"]).lower()
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("model_sha256 must be a lowercase SHA256 hex digest")
        return cls(
            schema_version=int(payload["schema_version"]),
            model_sha256=digest,
            supported_privacy_classes=tuple(classes),
            status=str(payload["status"]),
            source=str(payload["source"]),
        )

    def validate_asset(self, model_path: str | Path) -> None:
        actual = sha256_file(model_path)
        if actual != self.model_sha256:
            raise ValueError(
                f"Model SHA256 mismatch: expected {self.model_sha256}, got {actual}"
            )

    def validate_runtime_classes(self, runtime_names: Iterable[str]) -> None:
        runtime_names = {str(name) for name in runtime_names}
        missing = sorted(set(self.supported_privacy_classes) - runtime_names)
        if missing:
            raise ValueError(f"Model runtime is missing declared classes: {missing}")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
