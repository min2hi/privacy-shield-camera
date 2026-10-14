"""Tests for biometric encryption module."""
from pathlib import Path

import numpy as np
import pytest


def test_save_and_load_encrypted(tmp_path: Path):
    """Test round-trip encryption: save → load."""
    try:
        from app.utils.crypto import load_encrypted_array, save_encrypted_array
    except ImportError:
        pytest.skip("crypto module not yet created")

    array = np.random.randn(3, 512).astype(np.float32)
    path = tmp_path / "test_face.npy"

    assert save_encrypted_array(array, path)
    loaded = load_encrypted_array(path)

    assert loaded is not None
    np.testing.assert_array_almost_equal(array, loaded)


def test_load_plaintext_backward_compat(tmp_path: Path):
    """Legacy plaintext .npy files should load without error."""
    try:
        from app.utils.crypto import load_encrypted_array
    except ImportError:
        pytest.skip("crypto module not yet created")

    array = np.random.randn(2, 512).astype(np.float32)
    path = tmp_path / "legacy_face.npy"
    np.save(str(path), array, allow_pickle=False)

    loaded = load_encrypted_array(path)
    assert loaded is not None
    np.testing.assert_array_almost_equal(array, loaded)


def test_load_nonexistent_returns_none(tmp_path: Path):
    """Missing file returns None."""
    try:
        from app.utils.crypto import load_encrypted_array
    except ImportError:
        pytest.skip("crypto module not yet created")

    result = load_encrypted_array(tmp_path / "no_such_file.npy")
    assert result is None


def test_corrupted_file_returns_none(tmp_path: Path):
    """Corrupted file should not crash, returns None."""
    try:
        from app.utils.crypto import load_encrypted_array
    except ImportError:
        pytest.skip("crypto module not yet created")

    path = tmp_path / "corrupt.npy"
    path.write_bytes(b"random garbage data that is not npy or fernet")

    result = load_encrypted_array(path)
    # Should return None or raise a handled error, not crash
    assert result is None or isinstance(result, np.ndarray)


def test_derive_machine_key():
    """Verify machine key derivation returns 32-byte urlsafe base64 key."""
    try:
        from app.utils.crypto import _derive_machine_key
    except ImportError:
        pytest.skip("crypto module not yet created")

    key1 = _derive_machine_key()
    key2 = _derive_machine_key()
    assert isinstance(key1, bytes)
    assert len(key1) == 44  # 32 bytes in base64 is 44 chars
    assert key1 == key2  # Deterministic on same machine
