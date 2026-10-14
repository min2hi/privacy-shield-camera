"""
enroll_dialog.py — Hộp thoại đăng ký khuôn mặt mẫu đa hướng (Multi-Pose Face Enrollment).
Thiết kế Wizard 3 bước chuẩn Studio Dark (Obsidian Zinc + Studio Emerald).
"""

from contextlib import nullcontext

from app.utils.logging_config import get_logger
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

logger = get_logger(__name__)


class FaceEnrollmentDialog(QDialog):
    def __init__(self, worker, parent=None):
        super().__init__(parent)
        self.worker = worker
        self.current_step = 0  # 0: Nhìn thẳng, 1: Nghiêng trái, 2: Nghiêng phải

        # Sao lưu embeddings trước khi bắt đầu enrollment để revert nếu cancel (thread-safe)
        self._backup_embeddings = None
        if hasattr(worker, "pipeline") and hasattr(worker.pipeline, "face_recognizer"):
            fr = worker.pipeline.face_recognizer
            if hasattr(fr, "registered_embeddings"):
                lock = getattr(fr, "_get_lock", lambda: None)() or nullcontext()
                with lock:
                    self._backup_embeddings = list(fr.registered_embeddings)  # shallow copy

        self.setWindowTitle("Biometric Enrollment · Đăng Ký Khuôn Mặt Mẫu")
        self.setFixedSize(520, 370)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)

        # Apply Studio Dark Style Sheet
        self.setStyleSheet(
            """
            QDialog {
                background-color: #0e1116;
                border: 1px solid #202632;
            }
            QLabel {
                color: #f3f4f6;
                font-family: "Segoe UI Variable Text", "Segoe UI", -apple-system, sans-serif;
            }
            QLabel#dialog_badge {
                font-family: "Cascadia Mono", "Consolas", monospace;
                font-size: 7.5pt;
                font-weight: 700;
                color: #34d399;
                background-color: rgba(16, 185, 129, 0.10);
                border: 1px solid rgba(16, 185, 129, 0.28);
                border-radius: 4px;
                padding: 2px 7px;
            }
            QLabel#dialog_title {
                color: #f9fafb;
                font-size: 13pt;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            QLabel#dialog_desc {
                color: #9ca3af;
                font-size: 9pt;
            }
            QLabel#instruction {
                font-size: 10pt;
                font-weight: 500;
                color: #e5e7eb;
            }
            QPushButton#capture_btn {
                background-color: #10b981;
                color: #05110c;
                font-weight: 700;
                font-size: 9.5pt;
                border: 1px solid #059669;
                border-radius: 6px;
                padding: 9px 22px;
            }
            QPushButton#capture_btn:hover {
                background-color: #34d399;
                border: 1px solid #10b981;
            }
            QPushButton#capture_btn:pressed {
                background-color: #059669;
            }
            QPushButton#capture_btn:disabled {
                background-color: #181c24;
                color: #6b7280;
                border: 1px solid #222834;
            }
            QPushButton#cancel_btn {
                background-color: rgba(244, 63, 94, 0.08);
                color: #fb7185;
                font-weight: 600;
                font-size: 9pt;
                border: 1px solid rgba(244, 63, 94, 0.28);
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton#cancel_btn:hover {
                background-color: rgba(244, 63, 94, 0.16);
                border: 1px solid #f43f5e;
                color: #fda4af;
            }
            """
        )

        self.setup_ui()
        self.update_step_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        # Header Row
        header_row = QHBoxLayout()
        title = QLabel("ĐĂNG KÝ KHUÔN MẶT MẪU", self)
        title.setObjectName("dialog_title")

        badge = QLabel("3-POSE BIOMETRIC", self)
        badge.setObjectName("dialog_badge")

        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(badge)
        layout.addLayout(header_row)

        desc = QLabel(
            "Thực hiện quét 3 góc khuôn mặt để hệ thống trích xuất vector đặc trưng, "
            "giúp nhận diện chính xác chủ sở hữu ngay cả khi nghiêng đầu.",
            self,
        )
        desc.setObjectName("dialog_desc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Step Visualizer (3 cards)
        self.steps_layout = QHBoxLayout()
        self.steps_layout.setSpacing(10)

        self.step_widgets = []
        step_names = ["01 · Nhìn Thẳng", "02 · Nghiêng Trái", "03 · Nghiêng Phải"]
        for name in step_names:
            box = QFrame(self)
            box.setFixedSize(148, 44)
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(6, 4, 6, 4)

            lbl = QLabel(name, box)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                "font-family: 'Cascadia Mono', 'Consolas', 'Segoe UI', monospace; "
                "font-weight: 700; font-size: 8.5pt; border: none; background: transparent;"
            )
            box_layout.addWidget(lbl)

            self.steps_layout.addWidget(box)
            self.step_widgets.append((box, lbl))

        layout.addLayout(self.steps_layout)

        # Center display (Instruction card)
        self.content_frame = QFrame(self)
        self.content_frame.setStyleSheet(
            """
            QFrame {
                background-color: #14181f;
                border: 1px solid #202632;
                border-radius: 8px;
            }
            """
        )
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(18, 16, 18, 16)

        self.instruction_lbl = QLabel(self)
        self.instruction_lbl.setObjectName("instruction")
        self.instruction_lbl.setAlignment(Qt.AlignCenter)
        self.instruction_lbl.setWordWrap(True)
        content_layout.addWidget(self.instruction_lbl)

        layout.addWidget(self.content_frame, 1)

        # Buttons Bottom
        btn_layout = QHBoxLayout()

        self.cancel_btn = QPushButton("Hủy đăng ký", self)
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)

        self.capture_btn = QPushButton("CHỤP GÓC NÀY", self)
        self.capture_btn.setObjectName("capture_btn")
        self.capture_btn.setCursor(Qt.PointingHandCursor)
        self.capture_btn.clicked.connect(self.on_capture_clicked)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.capture_btn)

        layout.addLayout(btn_layout)

    def update_step_ui(self):
        """Cập nhật giao diện tương ứng với bước quét hiện tại."""
        instructions = [
            "BƯỚC 01/03 — Hãy nhìn THẲNG trực diện vào camera.\nGiữ khuôn mặt đủ sáng, rõ nét và nhấn nút chụp.",
            "BƯỚC 02/03 — Hãy xoay đầu nhẹ sang bên TRÁI (khoảng 15°–25°).\nGiữ ổn định và nhấn nút chụp.",
            "BƯỚC 03/03 — Hãy xoay đầu nhẹ sang bên PHẢI (khoảng 15°–25°).\nGiữ ổn định để hoàn tất góc quét cuối cùng.",
        ]

        self.instruction_lbl.setText(instructions[self.current_step])
        self.instruction_lbl.setStyleSheet("color: #e5e7eb; border: none; background: transparent;")
        self.capture_btn.setText(f"CHỤP GÓC {self.current_step + 1}/3")
        self.capture_btn.setEnabled(True)

        # Update step visual widgets
        for i, (box, lbl) in enumerate(self.step_widgets):
            if i < self.current_step:
                # Đã hoàn thành
                box.setStyleSheet(
                    """
                    background-color: #10b981;
                    border: 1px solid #059669;
                    border-radius: 6px;
                    """
                )
                lbl.setStyleSheet(
                    "color: #05110c; font-family: 'Cascadia Mono', 'Consolas', monospace; "
                    "font-weight: 700; font-size: 8.5pt; border: none; background: transparent;"
                )
            elif i == self.current_step:
                # Đang kích hoạt
                box.setStyleSheet(
                    """
                    background-color: rgba(16, 185, 129, 0.12);
                    border: 1px solid #10b981;
                    border-radius: 6px;
                    """
                )
                lbl.setStyleSheet(
                    "color: #34d399; font-family: 'Cascadia Mono', 'Consolas', monospace; "
                    "font-weight: 700; font-size: 8.5pt; border: none; background: transparent;"
                )
            else:
                # Chưa đến lượt
                box.setStyleSheet(
                    """
                    background-color: #14181f;
                    border: 1px solid #202632;
                    border-radius: 6px;
                    """
                )
                lbl.setStyleSheet(
                    "color: #6b7280; font-family: 'Cascadia Mono', 'Consolas', monospace; "
                    "font-weight: 600; font-size: 8.5pt; border: none; background: transparent;"
                )

    def on_capture_clicked(self):
        """Kích hoạt gửi tín hiệu đăng ký xuống CameraWorker."""
        self.capture_btn.setEnabled(False)
        self.instruction_lbl.setText("ĐANG PHÂN TÍCH — Hệ thống đang trích xuất đặc trưng khuôn mặt...")
        self.instruction_lbl.setStyleSheet(
            "color: #fbbf24; font-weight: 600; border: none; background: transparent;"
        )

        # Gọi xuống worker để chụp góc hiện tại
        self.worker.request_pose_enrollment(self.current_step)

    @Slot(bool, str)
    def on_enroll_result(self, success, message):
        """Callback xử lý kết quả đăng ký trả về từ CameraWorker."""
        if success:
            if self.current_step < 2:
                self.current_step += 1
                self.update_step_ui()
            else:
                self.instruction_lbl.setText(
                    "HOÀN TẤT — Đã trích xuất đủ 3 góc khuôn mặt mẫu. Nhấn HOÀN THÀNH để lưu mã hóa."
                )
                self.instruction_lbl.setStyleSheet(
                    "color: #34d399; font-weight: 700; border: none; background: transparent;"
                )
                self.capture_btn.setText("HOÀN THÀNH")
                self.capture_btn.setEnabled(True)
                self.capture_btn.clicked.disconnect()
                self.capture_btn.clicked.connect(self.accept)
                self.cancel_btn.hide()
        else:
            self.instruction_lbl.setText(f"CHƯA ĐẠT YÊU CẦU — {message}")
            self.instruction_lbl.setStyleSheet(
                "color: #fb7185; font-weight: 600; border: none; background: transparent;"
            )
            self.capture_btn.setEnabled(True)
            self.capture_btn.setText("THỬ LẠI GÓC NÀY")

    def reject(self):
        """Khôi phục trạng thái nhận diện bình thường và revert embeddings khi hủy đăng ký."""
        w_lock = getattr(self.worker, "_config_lock", None) or nullcontext()
        with w_lock:
            self.worker.enroll_pose_index = -1
        if self._backup_embeddings is not None:
            if hasattr(self.worker, "pipeline") and hasattr(self.worker.pipeline, "face_recognizer"):
                fr = self.worker.pipeline.face_recognizer
                f_lock = getattr(fr, "_get_lock", lambda: None)() or nullcontext()
                with f_lock:
                    fr.registered_embeddings = self._backup_embeddings
        super().reject()

    def accept(self):
        """Lưu embeddings xuống đĩa và khôi phục trạng thái bình thường khi user xác nhận."""
        w_lock = getattr(self.worker, "_config_lock", None) or nullcontext()
        with w_lock:
            self.worker.enroll_pose_index = -1
        if hasattr(self.worker, "pipeline") and hasattr(self.worker.pipeline, "face_recognizer"):
            saved = self.worker.pipeline.face_recognizer.save_registered_faces()
            if saved:
                logger.info("EnrollDialog: face templates saved to disk on user confirmation")
        super().accept()
