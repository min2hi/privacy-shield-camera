"""
permission_layer.py — Security Pillar
Kiểm soát quyền hạn của AI Agent: file nào được đọc,
lệnh nào được chạy, đường dẫn nào được phép truy cập.

Tuân thủ nguyên tắc Least Privilege (quyền tối thiểu cần thiết).
"""
import shlex
import subprocess
from pathlib import Path
from typing import Literal

from config import AGENT_WORKSPACE_PATH, ALLOWED_COMMANDS


def _interactive_console():
    from rich.console import Console
    from rich.prompt import Confirm

    return Console(), Confirm

# ──────────────────────────────────────────────────────────
# Loại quyền và mức xác nhận
# ──────────────────────────────────────────────────────────
PermissionLevel = Literal["allow", "confirm", "deny"]


def _is_within_workspace(path: str | Path) -> bool:
    """Kiểm tra đường dẫn có nằm trong workspace được phép không."""
    try:
        resolved = Path(path).resolve()
        return resolved.is_relative_to(AGENT_WORKSPACE_PATH)
    except (ValueError, OSError):
        return False


def _is_sensitive_file(path: str | Path) -> bool:
    """Kiểm tra file có chứa thông tin nhạy cảm không."""
    sensitive_names = {".env", ".env.local", ".env.production", "secrets.yaml",
                       "secrets.json", "credentials.json", "private_key.pem",
                       "registered_face.npy"}
    sensitive_parts = {"data", "datasets", "runs", "logs", "checkpoints"}
    candidate = Path(path)
    return (
        candidate.name.lower() in sensitive_names
        or any(part.lower() in sensitive_parts for part in candidate.parts)
        or candidate.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}
    )


# ──────────────────────────────────────────────────────────
# READ FILE — Cho phép nếu trong workspace, không phải secret file
# ──────────────────────────────────────────────────────────
def check_read_permission(file_path: str) -> tuple[bool, str]:
    """
    Kiểm tra quyền đọc file.
    Returns: (allowed: bool, reason: str)
    """
    path = Path(file_path)

    if _is_sensitive_file(path):
        return False, f"🔒 CHẶN: Không được đọc file nhạy cảm: {path.name}"

    if not _is_within_workspace(path):
        return False, f"🔒 CHẶN: File nằm ngoài workspace được phép: {file_path}"

    if not path.exists():
        return False, f"⚠ File không tồn tại: {file_path}"

    return True, "✓ Cho phép đọc"


# ──────────────────────────────────────────────────────────
# WRITE FILE — Yêu cầu xác nhận từ người dùng
# ──────────────────────────────────────────────────────────
def check_write_permission(file_path: str, preview_content: str | None = None,
                            auto_confirm: bool = False) -> tuple[bool, str]:
    """
    Kiểm tra quyền ghi file. Luôn hỏi người dùng trừ khi auto_confirm=True.
    Returns: (allowed: bool, reason: str)
    """
    path = Path(file_path)

    if _is_sensitive_file(path):
        return False, f"🔒 CHẶN: Không được ghi vào file nhạy cảm: {path.name}"

    if not _is_within_workspace(path):
        return False, f"🔒 CHẶN: File nằm ngoài workspace: {file_path}"

    if auto_confirm:
        return True, "✓ Auto-confirmed"

    # Hiển thị preview để người dùng review
    console, confirm = _interactive_console()
    console.print(f"\n[yellow]⚠ Agent muốn GHI FILE:[/yellow] {file_path}")
    if preview_content:
        preview = preview_content[:300] + "..." if len(preview_content) > 300 else preview_content
        console.print(f"[dim]Preview (300 ký tự đầu):\n{preview}[/dim]\n")

    confirmed = confirm.ask("Bạn cho phép ghi file này không?", default=False)
    if confirmed:
        return True, "✓ Người dùng đã xác nhận"
    return False, "✗ Người dùng từ chối"


# ──────────────────────────────────────────────────────────
# DELETE FILE — Bị chặn hoàn toàn theo mặc định
# ──────────────────────────────────────────────────────────
def check_delete_permission(file_path: str,
                             force_allow: bool = False) -> tuple[bool, str]:
    """
    Xóa file bị chặn mặc định. Chỉ cho phép khi force_allow=True
    (phải do người dùng chủ động bật).
    """
    if not force_allow:
        return False, f"🔒 CHẶN: Xóa file bị cấm theo mặc định. File: {file_path}"

    if not _is_within_workspace(file_path):
        return False, f"🔒 CHẶN: File nằm ngoài workspace: {file_path}"

    console, confirm = _interactive_console()
    console.print(f"\n[bold red]⚠ CẢNH BÁO NGHIÊM TRỌNG: Agent muốn XÓA FILE:[/bold red] {file_path}")
    confirmed = confirm.ask("Bạn CÓ CHẮC muốn xóa file này không? (Không thể hoàn tác!)", default=False)
    if confirmed:
        return True, "✓ Người dùng xác nhận xóa"
    return False, "✗ Người dùng hủy thao tác xóa"


# ──────────────────────────────────────────────────────────
# RUN COMMAND — Chỉ chạy lệnh trong whitelist
# ──────────────────────────────────────────────────────────
def check_command_permission(command: str) -> tuple[bool, str]:
    """
    Kiểm tra lệnh có trong whitelist không.
    Whitelist: pytest, ruff, python (chỉ chạy script trong workspace)
    """
    try:
        parts = shlex.split(command, posix=False)
    except ValueError:
        return False, "Cú pháp lệnh không hợp lệ"
    if not parts:
        return False, "Lệnh rỗng"

    base_cmd = parts[0].lower()

    # Kiểm tra base command có trong whitelist không
    if base_cmd not in ALLOWED_COMMANDS:
        return False, f"🔒 CHẶN: Lệnh '{base_cmd}' không có trong whitelist. Allowed: {ALLOWED_COMMANDS}"

    # Nếu là python, kiểm tra script có trong workspace không
    if base_cmd == "python" and len(parts) > 1:
        script_path = parts[1].strip('"')
        if script_path.startswith("-"):
            return False, "🔒 CHẶN: Python flags/inline code không được phép"
        candidate = Path(script_path)
        if candidate.suffix.lower() != ".py":
            return False, "🔒 CHẶN: Python chỉ được chạy file .py trong workspace"
        if not _is_within_workspace(candidate):
            return False, f"🔒 CHẶN: Script nằm ngoài workspace: {script_path}"
        if not candidate.is_file():
            return False, f"⚠ Script không tồn tại: {script_path}"

    return True, f"✓ Cho phép chạy: {command}"


def run_safe_command(command: str, cwd: str | None = None) -> tuple[str, str, int]:
    """
    Chạy lệnh đã được phép trong workspace.
    Returns: (stdout, stderr, return_code)
    """
    allowed, reason = check_command_permission(command)
    if not allowed:
        return "", reason, 1

    work_dir = cwd or str(AGENT_WORKSPACE_PATH)
    result = subprocess.run(
        shlex.split(command, posix=False),
        cwd=work_dir,
        capture_output=True,
        text=True,
        timeout=120  # Timeout 2 phút
    )
    return result.stdout, result.stderr, result.returncode
