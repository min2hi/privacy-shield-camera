"""Tests for FaceEnrollmentDialog UI logic."""
import os
from types import SimpleNamespace

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

_qapp = QApplication.instance() or QApplication([])


def _make_mock_worker(with_embeddings=False):
    """Create a mock CameraWorker with pipeline and face_recognizer."""
    embeddings = [np.random.randn(512).astype(np.float32)] if with_embeddings else []
    save_calls = []
    face_recognizer = SimpleNamespace(
        registered_embeddings=list(embeddings),
        save_registered_faces=lambda: save_calls.append(True) or True,
    )
    pipeline = SimpleNamespace(face_recognizer=face_recognizer)
    worker = SimpleNamespace(
        pipeline=pipeline,
        enroll_pose_index=-1,
        request_pose_enrollment=lambda idx: None,
        enroll_result=SimpleNamespace(
            connect=lambda slot: None,
            disconnect=lambda slot: None,
        ),
    )
    return worker, save_calls, embeddings


def test_dialog_initializes_at_step_0():
    worker, _, _ = _make_mock_worker()
    from app.ui.enroll_dialog import FaceEnrollmentDialog

    dialog = FaceEnrollmentDialog(worker)
    assert dialog.current_step == 0
    assert dialog.capture_btn.text() == "CHỤP GÓC 1/3"
    dialog.close()


def test_dialog_backup_embeddings_on_init():
    worker, _, original = _make_mock_worker(with_embeddings=True)
    from app.ui.enroll_dialog import FaceEnrollmentDialog

    dialog = FaceEnrollmentDialog(worker)
    assert dialog._backup_embeddings is not None
    assert len(dialog._backup_embeddings) == 1
    dialog.close()


def test_dialog_advances_step_on_success():
    worker, _, _ = _make_mock_worker()
    from app.ui.enroll_dialog import FaceEnrollmentDialog

    dialog = FaceEnrollmentDialog(worker)
    dialog.on_enroll_result(True, "Đã quét thành công góc mặt 1/3!")
    assert dialog.current_step == 1
    dialog.on_enroll_result(True, "Đã quét thành công góc mặt 2/3!")
    assert dialog.current_step == 2
    dialog.close()


def test_dialog_shows_completion_on_final_step():
    worker, _, _ = _make_mock_worker()
    from app.ui.enroll_dialog import FaceEnrollmentDialog

    dialog = FaceEnrollmentDialog(worker)
    dialog.current_step = 2
    dialog.on_enroll_result(True, "Đã quét thành công góc mặt 3/3!")
    assert "HOÀN THÀNH" in dialog.capture_btn.text()
    dialog.close()


def test_dialog_reject_reverts_embeddings():
    worker, _, original = _make_mock_worker(with_embeddings=True)
    from app.ui.enroll_dialog import FaceEnrollmentDialog

    dialog = FaceEnrollmentDialog(worker)
    # Simulate pose capture modifying embeddings
    worker.pipeline.face_recognizer.registered_embeddings = [None, None, None]
    dialog.reject()
    # Should revert to backup
    assert len(worker.pipeline.face_recognizer.registered_embeddings) == 1


def test_dialog_accept_saves_to_disk():
    worker, save_calls, _ = _make_mock_worker(with_embeddings=True)
    from app.ui.enroll_dialog import FaceEnrollmentDialog

    dialog = FaceEnrollmentDialog(worker)
    dialog.accept()
    assert len(save_calls) == 1


def test_dialog_failure_allows_retry():
    worker, _, _ = _make_mock_worker()
    from app.ui.enroll_dialog import FaceEnrollmentDialog

    dialog = FaceEnrollmentDialog(worker)
    dialog.on_enroll_result(False, "Đăng ký thất bại: timeout")
    assert dialog.capture_btn.isEnabled()
    assert "THỬ LẠI" in dialog.capture_btn.text()
    dialog.close()


def test_dialog_capture_button_triggers_worker():
    requested_steps = []
    worker, _, _ = _make_mock_worker()
    worker.request_pose_enrollment = lambda idx: requested_steps.append(idx)
    from app.ui.enroll_dialog import FaceEnrollmentDialog

    dialog = FaceEnrollmentDialog(worker)
    dialog.on_capture_clicked()
    assert requested_steps == [0]
    assert not dialog.capture_btn.isEnabled()
    dialog.close()
