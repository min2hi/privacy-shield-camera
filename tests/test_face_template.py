from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def recognizer_without_runtime(tmp_path: Path):
    from app.core.face_recognizer import FaceRecognizer

    recognizer = FaceRecognizer.__new__(FaceRecognizer)
    recognizer.registered_face_path = tmp_path / "registered_face.npy"
    recognizer.model_path = tmp_path / "mobilefacenet.onnx"
    recognizer.model_path.write_bytes(b"model fixture")
    recognizer.embedding_dimension = 4
    recognizer.registered_embeddings = []
    return recognizer


def test_face_template_save_load_and_delete_lifecycle(tmp_path):
    recognizer = recognizer_without_runtime(tmp_path)
    recognizer.registered_embeddings = [
        np.array([1, 2, 3, 4], dtype=np.float32),
        np.array([4, 3, 2, 1], dtype=np.float32),
    ]

    assert recognizer.save_registered_faces()
    metadata_path = tmp_path / "registered_face.npy.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["schema_version"] == 1
    assert metadata["embedding_dimension"] == 4
    assert metadata["embedding_count"] == 2

    loaded = recognizer.load_registered_face()
    assert len(loaded) == 2
    np.testing.assert_array_equal(loaded[0], [1, 2, 3, 4])

    assert recognizer.delete_registered_faces()
    assert recognizer.registered_embeddings == []
    assert not recognizer.registered_face_path.exists()
    assert not metadata_path.exists()


def test_corrupt_or_wrong_dimension_template_is_rejected(tmp_path):
    recognizer = recognizer_without_runtime(tmp_path)
    np.save(recognizer.registered_face_path, np.ones((2, 3), dtype=np.float32))
    assert recognizer.load_registered_face() == []


def test_non_finite_embedding_is_not_saved(tmp_path):
    recognizer = recognizer_without_runtime(tmp_path)
    recognizer.registered_embeddings = [
        np.array([1, 2, np.nan, 4], dtype=np.float32)
    ]
    assert not recognizer.save_registered_faces()
    assert not recognizer.registered_face_path.exists()


def test_face_template_is_encrypted_at_rest(tmp_path):
    recognizer = recognizer_without_runtime(tmp_path)
    recognizer.registered_embeddings = [
        np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    ]
    assert recognizer.save_registered_faces()
    raw = recognizer.registered_face_path.read_bytes()
    # Encrypted Fernet token should not have plaintext numpy magic bytes
    assert raw[:6] != b"\x93NUMPY"
    loaded = recognizer.load_registered_face()
    assert len(loaded) == 1
    np.testing.assert_array_equal(loaded[0], [1.0, 2.0, 3.0, 4.0])


def test_face_template_legacy_plaintext_backward_compatible(tmp_path):
    recognizer = recognizer_without_runtime(tmp_path)
    plain_array = np.array([[5.0, 6.0, 7.0, 8.0]], dtype=np.float32)
    np.save(recognizer.registered_face_path, plain_array, allow_pickle=False)
    # Verify file is plaintext .npy
    assert recognizer.registered_face_path.read_bytes()[:6] == b"\x93NUMPY"
    loaded = recognizer.load_registered_face()
    assert len(loaded) == 1
    np.testing.assert_array_equal(loaded[0], [5.0, 6.0, 7.0, 8.0])


def test_face_template_invalid_encrypted_data(tmp_path):
    recognizer = recognizer_without_runtime(tmp_path)
    recognizer.registered_face_path.write_bytes(b"not_a_valid_fernet_token_or_numpy")
    assert recognizer.load_registered_face() == []

