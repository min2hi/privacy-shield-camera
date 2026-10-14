"""
enroll_dialog.py — Hộp thoại đăng ký khuôn mặt mẫu đa hướng (Multi-Pose Face Enrollment).
Thiết kế Wizard 3 bước chuẩn UX cao cấp.
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
        if hasattr(worker, 'pipeline') and hasattr(worker.pipeline, 'face_recognizer'):
            fr = worker.pipeline.face_recognizer
            if hasattr(fr, 'registered_embeddings'):
                lock = getattr(fr, '_get_lock', lambda: None)() or nullcontext()
                with lock:
                    self._backup_embeddings = list(fr.registered_embeddings)  # shallow copy
        
        self.setWindowTitle("Đăng Ký Khuôn Mặt Mẫu (Multi-Pose)")
        self.setFixedSize(500, 360)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        
        # Apply Dracula/Mint Style Sheet
        self.setStyleSheet("""
            QDialog {
                background-color: #111215;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QLabel {
                color: #eef1f5;
                font-family: 'Segoe UI', 'Outfit', sans-serif;
            }
            QLabel#dialog_title {
                color: #00f5a0;
                font-size: 14pt;
                font-weight: bold;
            }
            QLabel#dialog_desc {
                color: #7e8492;
                font-size: 9.5pt;
            }
            QLabel#instruction {
                font-size: 10.5pt;
                font-weight: 500;
                line-height: 1.4;
            }
            QPushButton#capture_btn {
                background-color: #00f5a0;
                color: #111215;
                font-weight: bold;
                font-size: 10pt;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton#capture_btn:hover {
                background-color: #00d48a;
            }
            QPushButton#capture_btn:pressed {
                background-color: #00b375;
            }
            QPushButton#capture_btn:disabled {
                background-color: #2c2f36;
                color: #7e8492;
            }
            QPushButton#cancel_btn {
                background-color: transparent;
                color: #ff4a6b;
                font-weight: bold;
                border: 1px solid rgba(255, 74, 107, 0.3);
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton#cancel_btn:hover {
                background-color: rgba(255, 74, 107, 0.1);
            }
        """)
        
        self.setup_ui()
        self.update_step_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)
        
        # Header
        title = QLabel("ĐĂNG KÝ KHUÔN MẶT MẪU", self)
        title.setObjectName("dialog_title")
        layout.addWidget(title)
        
        desc = QLabel("Vui lòng thực hiện quét đủ 3 góc khuôn mặt để hệ thống bảo vệ toàn diện, nhận diện được bạn kể cả khi nghiêng đầu.", self)
        desc.setObjectName("dialog_desc")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Step Visualizer (3 circles/boxes)
        self.steps_layout = QHBoxLayout()
        self.steps_layout.setSpacing(12)
        
        self.step_widgets = []
        step_names = ["1. Nhìn Thẳng", "2. Nghiêng Trái", "3. Nghiêng Phải"]
        for name in step_names:
            box = QFrame(self)
            box.setFixedSize(130, 45)
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(5, 5, 5, 5)
            
            lbl = QLabel(name, box)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-weight: bold; font-size: 9pt;")
            box_layout.addWidget(lbl)
            
            self.steps_layout.addWidget(box)
            self.step_widgets.append((box, lbl))
            
        layout.addLayout(self.steps_layout)
        
        # Center display (Instruction & Image indicator space)
        self.content_frame = QFrame(self)
        self.content_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }
        """)
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(15, 15, 15, 15)
        
        self.instruction_lbl = QLabel(self)
        self.instruction_lbl.setObjectName("instruction")
        self.instruction_lbl.setAlignment(Qt.AlignCenter)
        self.instruction_lbl.setWordWrap(True)
        content_layout.addWidget(self.instruction_lbl)
        
        layout.addWidget(self.content_frame)
        
        # Buttons Bottom
        btn_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Hủy Đăng Ký", self)
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.capture_btn = QPushButton("CHỤP GÓC NÀY", self)
        self.capture_btn.setObjectName("capture_btn")
        self.capture_btn.clicked.connect(self.on_capture_clicked)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.capture_btn)
        
        layout.addLayout(btn_layout)

    def update_step_ui(self):
        """Cập nhật giao diện tương ứng với bước quét hiện tại."""
        instructions = [
            "👉 Hãy nhìn THẲNG trực diện vào camera.\nĐảm bảo khuôn mặt rõ nét và nhấn nút chụp.",
            "👉 Hãy nghiêng đầu nhẹ sang bên TRÁI.\nĐể camera chụp được góc nghiêng trái của bạn.",
            "👉 Hãy nghiêng đầu nhẹ sang bên PHẢI.\nĐể camera chụp được góc nghiêng phải cuối cùng."
        ]
        
        self.instruction_lbl.setText(instructions[self.current_step])
        self.instruction_lbl.setStyleSheet("color: #eef1f5;")
        self.capture_btn.setText(f"CHỤP GÓC {self.current_step + 1}/3")
        self.capture_btn.setEnabled(True)
        
        # Update step visual widgets
        for i, (box, lbl) in enumerate(self.step_widgets):
            if i < self.current_step:
                # Đã hoàn thành
                box.setStyleSheet("""
                    background-color: #00f5a0;
                    border: none;
                    border-radius: 6px;
                """)
                lbl.setStyleSheet("color: #111215; font-weight: bold; font-size: 9pt;")
            elif i == self.current_step:
                # Đang kích hoạt
                box.setStyleSheet("""
                    background-color: rgba(0, 245, 160, 0.1);
                    border: 2px solid #00f5a0;
                    border-radius: 6px;
                """)
                lbl.setStyleSheet("color: #00f5a0; font-weight: bold; font-size: 9pt;")
            else:
                # Chưa đến lượt
                box.setStyleSheet("""
                    background-color: transparent;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 6px;
                """)
                lbl.setStyleSheet("color: #7e8492; font-weight: bold; font-size: 9pt;")

    def on_capture_clicked(self):
        """Kích hoạt gửi tín hiệu đăng ký xuống CameraWorker."""
        self.capture_btn.setEnabled(False)
        self.instruction_lbl.setText("⚙ Đang xử lý và phân tích khuôn mặt...")
        self.instruction_lbl.setStyleSheet("color: #ffb900;")
        
        # Gọi xuống worker để chụp góc hiện tại
        self.worker.request_pose_enrollment(self.current_step)

    @Slot(bool, str)
    def on_enroll_result(self, success, message):
        """Callback xử lý kết quả đăng ký trả về từ CameraWorker."""
        if success:
            if self.current_step < 2:
                # Chuyển sang bước tiếp theo
                self.current_step += 1
                self.update_step_ui()
            else:
                # Đã xong cả 3 bước!
                self.instruction_lbl.setText("🎉 Chúc mừng! Đăng ký khuôn mặt mẫu đa góc thành công vĩnh viễn!")
                self.instruction_lbl.setStyleSheet("color: #00f5a0; font-weight: bold;")
                self.capture_btn.setText("HOÀN THÀNH")
                self.capture_btn.setEnabled(True)
                # Đổi chức năng nút thành nút đóng Dialog thành công
                self.capture_btn.clicked.disconnect()
                self.capture_btn.clicked.connect(self.accept)
                self.cancel_btn.hide()
        else:
            # Thất bại (timeout hoặc lỗi phát hiện mặt)
            self.instruction_lbl.setText(f"❌ {message}")
            self.instruction_lbl.setStyleSheet("color: #ff4a6b; font-weight: bold;")
            self.capture_btn.setEnabled(True)
            self.capture_btn.setText("THỬ LẠI GÓC NÀY")
            
    def reject(self):
        """Khôi phục trạng thái nhận diện bình thường và revert embeddings khi hủy đăng ký."""
        w_lock = getattr(self.worker, '_config_lock', None) or nullcontext()
        with w_lock:
            self.worker.enroll_pose_index = -1
        # Revert embeddings về trạng thái trước enrollment (thread-safe)
        if self._backup_embeddings is not None:
            if hasattr(self.worker, 'pipeline') and hasattr(self.worker.pipeline, 'face_recognizer'):
                fr = self.worker.pipeline.face_recognizer
                f_lock = getattr(fr, '_get_lock', lambda: None)() or nullcontext()
                with f_lock:
                    fr.registered_embeddings = self._backup_embeddings
        super().reject()
        
    def accept(self):
        """Lưu embeddings xuống đĩa và khôi phục trạng thái bình thường khi user xác nhận."""
        w_lock = getattr(self.worker, '_config_lock', None) or nullcontext()
        with w_lock:
            self.worker.enroll_pose_index = -1
        # Chỉ save khi user nhấn HOÀN THÀNH (không save sớm trong worker)
        if hasattr(self.worker, 'pipeline') and hasattr(self.worker.pipeline, 'face_recognizer'):
            saved = self.worker.pipeline.face_recognizer.save_registered_faces()
            if saved:
                logger.info("EnrollDialog: face templates saved to disk on user confirmation")
        super().accept()
