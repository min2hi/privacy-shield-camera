"""
crypto.py — Mã hóa dữ liệu sinh trắc học tại chỗ (at-rest encryption).
Sử dụng Fernet symmetric encryption với machine-derived key.
"""
from __future__ import annotations

import base64
import hashlib
import io
import os
import platform
from pathlib import Path

import numpy as np

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def _derive_machine_key() -> bytes:
    """Tạo key mã hóa duy nhất cho máy hiện tại.
    
    Key được derive từ: hostname + machine-id (hoặc username nếu không có).
    Không hoàn hảo như DPAPI nhưng tương thích đa nền tảng.
    """
    machine_info = platform.node()
    
    # Thêm machine-id nếu có (Windows: MachineGuid, Linux: /etc/machine-id)
    machine_id_path = Path("/etc/machine-id")
    if machine_id_path.exists():
        machine_info += machine_id_path.read_text().strip()
    else:
        # Windows fallback: dùng username + node
        machine_info += os.environ.get("USERNAME", os.environ.get("USER", "default"))
    
    # Derive 32-byte key từ machine info
    key_bytes = hashlib.sha256(machine_info.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(key_bytes)


def save_encrypted_array(array: np.ndarray, path: Path) -> bool:
    """Lưu numpy array đã mã hóa ra file.
    
    Format: Fernet token chứa .npy bytes.
    Fallback: lưu plaintext nếu cryptography chưa cài.
    """
    try:
        from cryptography.fernet import Fernet
        
        key = _derive_machine_key()
        fernet = Fernet(key)
        
        # Serialize numpy array to bytes
        buffer = io.BytesIO()
        np.save(buffer, array, allow_pickle=False)
        raw_bytes = buffer.getvalue()
        
        # Encrypt
        encrypted = fernet.encrypt(raw_bytes)
        
        # Atomic write
        temp_path = path.with_name(f".{path.name}.tmp")
        temp_path.write_bytes(encrypted)
        os.replace(temp_path, path)
        
        logger.info("Biometric template encrypted and saved: %s", path.name)
        return True
    except ImportError:
        logger.warning(
            "cryptography package not installed — saving biometric template WITHOUT encryption. "
            "Run: pip install cryptography"
        )
        # Fallback: save plaintext (backward compatible)
        temp_path = path.with_name(f".{path.name}.tmp")
        with temp_path.open("wb") as f:
            np.save(f, array, allow_pickle=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
        return True
    except Exception as e:
        logger.error("Failed to save encrypted template: %s", e)
        return False


def load_encrypted_array(path: Path) -> np.ndarray | None:
    """Tải numpy array đã mã hóa từ file.
    
    Tự động detect: encrypted (Fernet token) vs plaintext (.npy header).
    """
    if not path.exists():
        return None
    
    raw = path.read_bytes()
    
    # Detect format: .npy files start with \x93NUMPY
    if raw[:6] == b"\x93NUMPY":
        # Plaintext .npy format (backward compatible)
        logger.info("Loading plaintext biometric template (legacy format)")
        return np.load(str(path), allow_pickle=False)
    
    # Try decryption
    try:
        from cryptography.fernet import Fernet, InvalidToken
        
        key = _derive_machine_key()
        fernet = Fernet(key)
        
        try:
            decrypted = fernet.decrypt(raw)
        except InvalidToken:
            logger.error(
                "Cannot decrypt biometric template — likely created on a different machine. "
                "Please re-enroll face templates."
            )
            return None
        
        buffer = io.BytesIO(decrypted)
        array = np.load(buffer, allow_pickle=False)
        logger.info("Loaded encrypted biometric template: %s", path.name)
        return array
    except ImportError:
        logger.error(
            "Cannot load encrypted template without cryptography package. "
            "Run: pip install cryptography"
        )
        return None
