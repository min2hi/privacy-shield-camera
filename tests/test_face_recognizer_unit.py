"""Unit tests for FaceRecognizer verify_face and pose estimation logic."""
import numpy as np


def make_recognizer_stub():
    """Create a FaceRecognizer-like stub without loading real models."""
    from types import SimpleNamespace
    rec = SimpleNamespace()
    rec.threshold = 1.10
    rec.embedding_dimension = 512
    rec.registered_embeddings = []
    
    # Import the actual methods we want to test
    from app.core.face_recognizer import FaceRecognizer
    rec.verify_face = FaceRecognizer.verify_face.__get__(rec)
    rec.estimate_head_pose = FaceRecognizer.estimate_head_pose.__get__(rec)
    return rec


def test_verify_face_no_registered():
    rec = make_recognizer_stub()
    embedding = np.random.randn(512).astype(np.float32)
    matched, dist = rec.verify_face(embedding)
    assert matched is False
    assert dist == 999.0


def test_verify_face_match():
    rec = make_recognizer_stub()
    template = np.random.randn(512).astype(np.float32)
    template = template / np.linalg.norm(template)
    rec.registered_embeddings = [template]
    # Same embedding should match (distance ~0)
    matched, dist = rec.verify_face(template)
    assert matched is True
    assert dist < 0.01


def test_verify_face_no_match():
    rec = make_recognizer_stub()
    t1 = np.random.randn(512).astype(np.float32)
    t1 = t1 / np.linalg.norm(t1)
    t2 = -t1  # Opposite direction = max distance
    rec.registered_embeddings = [t1]
    matched, dist = rec.verify_face(t2)
    assert matched is False
    assert dist > rec.threshold


def test_estimate_head_pose_frontal():
    rec = make_recognizer_stub()
    # Simulate symmetric face landmarks (frontal)
    face = np.zeros(15, dtype=np.float32)
    face[4] = 100   # x_eye1
    face[5] = 100   # y_eye1
    face[6] = 200   # x_eye2
    face[7] = 100   # y_eye2
    face[8] = 150   # x_nose (centered)
    face[9] = 140   # y_nose
    face[11] = 180  # y_mouth1
    face[13] = 180  # y_mouth2
    pose = rec.estimate_head_pose(face)
    assert pose == 0  # Frontal


def test_estimate_head_pose_left():
    rec = make_recognizer_stub()
    face = np.zeros(15, dtype=np.float32)
    face[4] = 100
    face[5] = 100
    face[6] = 200
    face[7] = 100
    face[8] = 110   # nose very close to left eye
    face[9] = 140
    face[11] = 180
    face[13] = 180
    pose = rec.estimate_head_pose(face)
    assert pose == 1  # Left


def test_estimate_head_pose_right():
    rec = make_recognizer_stub()
    face = np.zeros(15, dtype=np.float32)
    face[4] = 100
    face[5] = 100
    face[6] = 200
    face[7] = 100
    face[8] = 195   # nose very close to right eye
    face[9] = 140
    face[11] = 180
    face[13] = 180
    pose = rec.estimate_head_pose(face)
    assert pose == 2  # Right
