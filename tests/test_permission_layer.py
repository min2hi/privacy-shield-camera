from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT_ROOT = ROOT / "ai-project-agent"
sys.path.insert(0, str(AGENT_ROOT))

spec = importlib.util.spec_from_file_location(
    "permission_layer", AGENT_ROOT / "tools" / "permission_layer.py"
)
permission_layer = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(permission_layer)


def test_face_template_is_never_readable():
    allowed, reason = permission_layer.check_read_permission(
        str(ROOT / "privacy-shield-app" / "configs" / "registered_face.npy")
    )
    assert not allowed
    assert "CHẶN" in reason


def test_private_data_directories_are_sensitive_even_inside_workspace(tmp_path):
    path = ROOT / "data" / "sample.txt"
    assert permission_layer._is_sensitive_file(path)


def test_read_outside_workspace_is_denied(tmp_path):
    path = tmp_path / "outside.txt"
    path.write_text("secret", encoding="utf-8")
    allowed, _ = permission_layer.check_read_permission(str(path))
    assert not allowed


def test_unlisted_command_is_denied():
    allowed, reason = permission_layer.check_command_permission("powershell Get-ChildItem")
    assert not allowed
    assert "whitelist" in reason


def test_python_inline_code_is_denied():
    allowed, _ = permission_layer.check_command_permission('python -c "print(1)"')
    assert not allowed
