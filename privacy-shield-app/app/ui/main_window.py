"""
main_window.py — Cửa sổ giao diện chính (MainWindow) của Privacy Shield App.
Thiết kế tối giản hiện đại, kế thừa phong cách chuyên nghiệp của PyDracula và Mint Green.
"""

import sys
from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

# Thêm đường dẫn dự án để import các module của app
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.pipeline import PrivacyPipeline
from app.ui.camera_worker import CameraWorker
from app.ui.custom_widgets import MetricCard, ToggleSwitch
from app.ui.style_sheets import APP_STYLE
from app.utils.config_loader import ConfigLoader
from app.utils.console import safe_print


class MainWindow(QMainWindow):
    def __init__(self, config_path="configs/default.yaml", pipeline=None, auto_start=True):
        super().__init__()
        
        # 1. Tải cấu hình và khởi tạo AI pipeline
        self.config = ConfigLoader(config_path)
        self.pipeline = pipeline or PrivacyPipeline(self.config)
        self.worker = None
        
        # Lấy danh sách các lớp đối tượng bảo vệ mặc định
        self.class_presets = self.config.get("model.class_mask_presets", {})
        self.selected_classes = list(self.class_presets.keys())
        
        # Thiết lập thông số Window chính
        self.setWindowTitle("Privacy Shield Camera")
        self.resize(1000, 680)
        self.setMinimumSize(900, 600)
        
        # Khởi tạo Giao diện
        self.init_ui()
        
        # Áp dụng stylesheet phong cách PyDracula + Mint
        self.setStyleSheet(APP_STYLE)
        
        # Khởi chạy luồng camera
        if auto_start:
            self.start_camera()
        else:
            self.video_label.setText("Fixture mode — camera/model disabled")
            self.update_status_bar()

    def init_ui(self):
        """Khởi tạo toàn bộ layout của ứng dụng."""
        # Widget trung tâm
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        # Layout tổng thể (Ngang: Sidebar bên trái | Vùng chính bên phải)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ──────────────────────────────────────────────────────────
        # SIDEBAR BÊN TRÁI
        # ──────────────────────────────────────────────────────────
        sidebar = QFrame(self)
        sidebar.setObjectName("sidebar_container")
        sidebar.setFixedWidth(280)
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 25, 20, 25)
        sidebar_layout.setSpacing(15)
        
        # Brand Header (App Title)
        brand_layout = QVBoxLayout()
        brand_layout.setSpacing(2)
        
        title_label = QLabel("PRIVACY SHIELD", self)
        title_label.setObjectName("app_title")
        
        subtitle_label = QLabel("Real-time Camera Protection", self)
        subtitle_label.setObjectName("app_subtitle")
        
        brand_layout.addWidget(title_label)
        brand_layout.addWidget(subtitle_label)
        sidebar_layout.addLayout(brand_layout)
        
        # Separator Line
        line = QFrame(self)
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); max-height: 1px; border: none;")
        sidebar_layout.addWidget(line)
        
        # SECTION 1: Cấu hình Thiết bị (Camera Input)
        cam_label = QLabel("WEBCAM INPUT", self)
        cam_label.setObjectName("section_header")
        sidebar_layout.addWidget(cam_label)
        
        self.camera_combo = QComboBox(self)
        # Hỗ trợ nhanh 2 webcam index thông dụng
        self.camera_combo.addItems(["Camera Index 0 (Mặc định)", "Camera Index 1 (Phụ)"])
        device_idx = self.config.get("camera.device_index", 0)
        self.camera_combo.setCurrentIndex(0 if device_idx == 0 else 1)
        self.camera_combo.currentIndexChanged.connect(self.on_camera_changed)
        sidebar_layout.addWidget(self.camera_combo)
        
        # SECTION 2: Trạng thái Safe Mode (Protection Switch)
        safe_mode_label = QLabel("PROTECTION SYSTEM", self)
        safe_mode_label.setObjectName("section_header")
        sidebar_layout.addWidget(safe_mode_label)
        
        protection_layout = QHBoxLayout()
        protection_status_lbl = QLabel("Bảo Vệ Hoạt Động:", self)
        self.protection_switch = ToggleSwitch(self)
        self.protection_switch.setChecked(True)
        self.protection_switch.toggled.connect(self.on_protection_toggled)
        
        protection_layout.addWidget(protection_status_lbl)
        protection_layout.addWidget(self.protection_switch, 0, Qt.AlignRight)
        sidebar_layout.addLayout(protection_layout)
        
        # SECTION 3: Chế độ che phủ (Mask Mode Override)
        mask_label = QLabel("MASKING MODE", self)
        mask_label.setObjectName("section_header")
        sidebar_layout.addWidget(mask_label)
        
        self.mask_mode_combo = QComboBox(self)
        self.mask_mode_combo.addItems([
            "Risk Presets (Theo YAML)",
            "Force Solid (Che đen)",
            "Force Blur (Làm mờ)",
            "Force Mosaic (Pixel hóa)"
        ])
        self.mask_mode_combo.currentIndexChanged.connect(self.on_mask_mode_changed)
        sidebar_layout.addWidget(self.mask_mode_combo)
        
        # SECTION 4: Độ nhạy nhận diện (Confidence)
        conf_label = QLabel("DETECTION CONFIDENCE", self)
        conf_label.setObjectName("section_header")
        sidebar_layout.addWidget(conf_label)
        
        conf_header_layout = QHBoxLayout()
        conf_title = QLabel("Độ Nhạy:", self)
        self.conf_val_label = QLabel("0.25", self)
        self.conf_val_label.setStyleSheet("color: #00f5a0; font-weight: bold;")
        conf_header_layout.addWidget(conf_title)
        conf_header_layout.addWidget(self.conf_val_label, 0, Qt.AlignRight)
        sidebar_layout.addLayout(conf_header_layout)
        
        self.conf_slider = QSlider(Qt.Horizontal, self)
        self.conf_slider.setRange(10, 90)
        self.conf_slider.setValue(25)  # 0.25 conf
        self.conf_slider.valueChanged.connect(self.on_confidence_changed)
        sidebar_layout.addWidget(self.conf_slider)
        
        # SECTION 4.5: Nhận diện Khuôn Mặt (Face Protection)
        face_section_label = QLabel("FACE PROTECTION", self)
        face_section_label.setObjectName("section_header")
        sidebar_layout.addWidget(face_section_label)
        
        # Hộp chứa các nút & checkbox cho khuôn mặt để phong cách đồng bộ card
        face_widget = QFrame(self)
        face_widget.setObjectName("face_control_card")
        face_widget.setStyleSheet("""
            QFrame#face_control_card {
                background-color: rgba(255, 255, 255, 0.02);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }
        """)
        face_layout = QVBoxLayout(face_widget)
        face_layout.setContentsMargins(12, 12, 12, 12)
        face_layout.setSpacing(10)
        
        # Nút Đăng ký khuôn mặt mẫu
        self.enroll_btn = QPushButton("Đăng Ký Mặt Mẫu", self)
        self.enroll_btn.setStyleSheet("""
            QPushButton {
                background-color: #00f5a0;
                color: #111215;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #00d48a;
            }
            QPushButton:pressed {
                background-color: #00b375;
            }
            QPushButton:disabled {
                background-color: #2c2f36;
                color: #7e8492;
            }
        """)
        self.enroll_btn.clicked.connect(self.on_enroll_clicked)
        face_layout.addWidget(self.enroll_btn)
        
        # Label hiển thị trạng thái khuôn mặt mẫu
        self.face_status_lbl = QLabel(self)
        has_face = len(self.pipeline.face_recognizer.registered_embeddings) > 0
        status_text = "Mẫu mặt: Đã đăng ký" if has_face else "Mẫu mặt: Chưa có"
        self.face_status_lbl.setText(status_text)
        self.face_status_lbl.setStyleSheet("color: #00f5a0; font-size: 8.5pt; font-weight: bold;" if has_face else "color: #7e8492; font-size: 8.5pt;")
        face_layout.addWidget(self.face_status_lbl)
        
        # Checkbox che mặt chủ sở hữu
        self.cb_mask_owner = QCheckBox("Che mặt chủ sở hữu", self)
        self.cb_mask_owner.setChecked(self.pipeline.mask_owner_face)
        self.cb_mask_owner.stateChanged.connect(self.on_face_config_changed)
        face_layout.addWidget(self.cb_mask_owner)
        
        # Checkbox che mặt người lạ
        self.cb_mask_stranger = QCheckBox("Che mặt người lạ", self)
        self.cb_mask_stranger.setChecked(self.pipeline.mask_strangers_face)
        self.cb_mask_stranger.stateChanged.connect(self.on_face_config_changed)
        face_layout.addWidget(self.cb_mask_stranger)

        self.btn_reset_face = QPushButton("Xóa mẫu khuôn mặt", self)
        self.btn_reset_face.clicked.connect(self.on_reset_face_clicked)
        face_layout.addWidget(self.btn_reset_face)
        
        sidebar_layout.addWidget(face_widget)
        
        # SECTION 5: Lọc các lớp đối tượng (Protected Classes)
        classes_label = QLabel("PROTECTED OBJECTS", self)
        classes_label.setObjectName("section_header")
        sidebar_layout.addWidget(classes_label)
        
        # Cuộn khu vực checkboxes
        scroll = QScrollArea(self)
        scroll.setObjectName("scroll_area")
        scroll.setWidgetResizable(True)
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(5, 5, 5, 5)
        scroll_layout.setSpacing(8)
        
        self.class_checkboxes = {}
        supported_classes = getattr(self.pipeline.detector, "supported_class_names", set())
        for cls_name in self.class_presets.keys():
            cb = QCheckBox(cls_name.replace("_", " ").title(), self)
            is_supported = cls_name in supported_classes
            cb.setChecked(is_supported)
            cb.setEnabled(is_supported)
            if not is_supported:
                cb.setToolTip("Model hiện tại không hỗ trợ lớp này")
            cb.stateChanged.connect(self.on_classes_changed)
            self.class_checkboxes[cls_name] = cb
            scroll_layout.addWidget(cb)

        self.selected_classes = [
            name for name, checkbox in self.class_checkboxes.items() if checkbox.isChecked()
        ]
            
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        sidebar_layout.addWidget(scroll)
        
        # ──────────────────────────────────────────────────────────
        # VÙNG HIỂN THỊ CHÍNH (BÊN PHẢI)
        # ──────────────────────────────────────────────────────────
        content_pane = QWidget(self)
        content_layout = QVBoxLayout(content_pane)
        content_layout.setContentsMargins(25, 25, 25, 25)
        content_layout.setSpacing(20)
        
        # Video Container Frame (Bo góc)
        self.video_frame = QFrame(self)
        self.video_frame.setObjectName("card_container")
        self.video_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        video_frame_layout = QVBoxLayout(self.video_frame)
        video_frame_layout.setContentsMargins(6, 6, 6, 6)
        
        # Video Label (nơi render ảnh camera)
        self.video_label = QLabel(self.video_frame)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setText("Đang khởi động Camera...")
        self.video_label.setStyleSheet("color: #7e8492; font-size: 12pt; font-weight: bold; background-color: #0b0c0e; border-radius: 8px;")
        video_frame_layout.addWidget(self.video_label)
        
        content_layout.addWidget(self.video_frame)
        
        # Thống kê hiệu năng (Metric Cards)
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(15)
        
        self.card_fps = MetricCard("FPS (Độ mượt)", "0.0", "Hz", self)
        self.card_latency = MetricCard("LATENCY (AI Latency)", "0.0", "ms", self)
        self.card_objects = MetricCard("SHIELDED (Số vùng che)", "0", "", self)
        
        metrics_layout.addWidget(self.card_fps)
        metrics_layout.addWidget(self.card_latency)
        metrics_layout.addWidget(self.card_objects)
        
        content_layout.addLayout(metrics_layout)
        
        # Lắp ghép chính
        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_pane, 1)
        
        # ──────────────────────────────────────────────────────────
        # STATUS BAR DƯỚI CÙNG
        # ──────────────────────────────────────────────────────────
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.update_status_bar()

    # ──────────────────────────────────────────────────────────
    # CÁC HÀM XỬ LÝ SỰ KIỆN & ĐIỀU KHIỂN DỘNG
    # ──────────────────────────────────────────────────────────
    def start_camera(self):
        """Khởi động luồng webcam phụ."""
        # Giải phóng luồng cũ nếu đang chạy
        if self.worker is not None:
            self.worker.stop()
            
        device_idx = self.camera_combo.currentIndex()
        
        # Tạo và liên kết luồng camera mới
        self.worker = CameraWorker(
            pipeline=self.pipeline,
            device_index=device_idx,
            selected_classes=self.selected_classes
        )
        self.worker.frame_ready.connect(self.on_frame_ready)
        self.worker.camera_error.connect(self.on_camera_error)
        
        # Đồng bộ các thiết lập hiện tại của GUI vào worker trước khi chạy
        self.on_confidence_changed(self.conf_slider.value())
        self.on_mask_mode_changed(self.mask_mode_combo.currentIndex())
        self.worker.safe_mode_active = self.protection_switch.isChecked()
        
        self.worker.start()
        self.update_status_bar()

    @Slot(QImage, dict)
    def on_frame_ready(self, q_img, metrics):
        """Callback nhận frame ảnh từ luồng phụ và cập nhật giao diện chính."""
        # 1. Hiển thị hình ảnh giữ nguyên tỷ lệ khung hình
        scaled_pixmap = QPixmap.fromImage(q_img).scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.FastTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)
        
        # 2. Cập nhật các thẻ thông số Metric Cards
        fps = metrics.get("fps", 0.0)
        latency = metrics.get("latency_ms", 0.0)
        count = metrics.get("detected_count", 0)
        
        self.card_fps.update_value(f"{fps}", "Hz")
        self.card_latency.update_value(f"{latency}", "ms")
        self.card_objects.update_value(f"{count}")
        
        # 3. Thay đổi màu sắc thông số linh hoạt theo hiệu năng (Senior UX Touch)
        # FPS Color: Xanh nếu mượt, Cam nếu chấp nhận được, Đỏ nếu lag
        if fps >= 24.0:
            self.card_fps.set_value_color("#00f5a0")
        elif fps >= 12.0:
            self.card_fps.set_value_color("#ffb900")
        else:
            self.card_fps.set_value_color("#ff4a6b")
            
        # Latency Color: Xanh nếu nhanh (< 35ms), Đỏ nếu chậm (> 75ms)
        if latency <= 35.0:
            self.card_latency.set_value_color("#00f5a0")
        elif latency <= 75.0:
            self.card_latency.set_value_color("#ffb900")
        else:
            self.card_latency.set_value_color("#ff4a6b")
            
        # Objects Shielded Color: Đỏ cảnh báo nếu phát hiện đối tượng nhạy cảm cần che
        if count > 0:
            self.card_objects.set_value_color("#ff4a6b")  # Đỏ phát sáng báo động che
        else:
            self.card_objects.set_value_color("#7e8492")  # Màu xám bình thường

        unsupported = metrics.get("unsupported_classes", [])
        if unsupported:
            self.status_bar.showMessage(
                "Model hiện tại không hỗ trợ: " + ", ".join(unsupported), 5000
            )

    @Slot(str)
    def on_camera_error(self, message):
        self.status_bar.showMessage(message, 8000)

    def on_camera_changed(self, index):
        """Thay đổi thiết bị webcam đầu vào."""
        safe_print(f"GUI: switch camera to index {index}")
        self.start_camera()

    def on_protection_toggled(self, checked):
        """Bật / Tắt hệ thống bảo vệ Safe Mode."""
        if self.worker:
            self.worker.safe_mode_active = checked
        self.update_status_bar()
        # Đổi màu nhãn Switch
        status_text = "HỆ THỐNG AN TOÀN CHỦ ĐỘNG" if checked else "HỆ THỐNG TẠM NGƯNG BẢO VỆ"
        self.status_bar.showMessage(f"Trạng thái: {status_text} | Camera Index: {self.camera_combo.currentIndex()}", 5000)

    def on_mask_mode_changed(self, index):
        """Cập nhật đè phương pháp che phủ."""
        if not self.worker:
            return
            
        if index == 0:
            self.worker.override_mask_mode = None  # Theo Preset rủi ro của từng class
            safe_print("GUI: use per-class risk presets")
        elif index == 1:
            self.worker.override_mask_mode = "solid_mask"
            safe_print("GUI: force solid mask")
        elif index == 2:
            self.worker.override_mask_mode = "gaussian_blur"
            safe_print("GUI: force gaussian blur")
        elif index == 3:
            self.worker.override_mask_mode = "mosaic"
            safe_print("GUI: force mosaic")

    def on_confidence_changed(self, value):
        """Thay đổi độ nhạy Confidence Threshold của detector."""
        conf_float = value / 100.0
        self.conf_val_label.setText(f"{conf_float:.2f}")
        # Cập nhật trực tiếp vào detector trong pipeline của worker
        self.pipeline.detector.confidence = conf_float

    def on_classes_changed(self):
        """Bật/tắt lọc đối tượng nhạy cảm cụ thể theo Checkboxes."""
        self.selected_classes = []
        for cls_name, cb in self.class_checkboxes.items():
            if cb.isChecked():
                self.selected_classes.append(cls_name)
        
        # Cập nhật trực tiếp danh sách filter của worker
        if self.worker:
            self.worker.selected_classes = self.selected_classes
            
        safe_print(f"GUI: protected classes changed: {self.selected_classes}")

    def update_status_bar(self):
        """Cập nhật dòng trạng thái chân trang."""
        safe_mode = "SAFE MODE ACTIVE (Đã bảo vệ)" if self.protection_switch.isChecked() else "SAFE MODE DISABLED (Chưa bảo vệ)"
        dev_idx = self.camera_combo.currentIndex()
        self.status_bar.showMessage(f"Trạng thái: {safe_mode} | Thiết bị: Camera Index {dev_idx}")

    def on_enroll_clicked(self):
        """Mở hộp thoại đăng ký khuôn mặt mẫu đa góc (Multi-Pose Wizard)."""
        if not self.worker:
            self.status_bar.showMessage("Không thể đăng ký: Camera chưa hoạt động!", 3000)
            return
            
        from app.ui.enroll_dialog import FaceEnrollmentDialog
        dialog = FaceEnrollmentDialog(self.worker, self)
        
        # Kết nối tín hiệu của worker với slot trong Dialog
        self.worker.enroll_result.connect(dialog.on_enroll_result)
        
        # Chạy dialog dạng block (modal)
        dialog.exec()
        
        # Hủy kết nối sau khi đóng dialog để tránh trùng lặp tín hiệu
        self.worker.enroll_result.disconnect(dialog.on_enroll_result)
        
        # Cập nhật nhãn trạng thái mặt mẫu trên sidebar chính
        self.update_face_status_label()

    def update_face_status_label(self):
        """Cập nhật nhãn thông báo mẫu mặt chủ sở hữu trên sidebar."""
        has_face = len(self.pipeline.face_recognizer.registered_embeddings) > 0
        if has_face:
            self.face_status_lbl.setText("Mẫu mặt: Đã đăng ký")
            self.face_status_lbl.setStyleSheet("color: #00f5a0; font-size: 8.5pt; font-weight: bold;")
        else:
            self.face_status_lbl.setText("Mẫu mặt: Chưa có")
            self.face_status_lbl.setStyleSheet("color: #7e8492; font-size: 8.5pt;")

    def on_reset_face_clicked(self):
        """Require explicit confirmation before deleting local biometric data."""
        choice = QMessageBox.question(
            self,
            "Xóa mẫu khuôn mặt",
            "Xóa toàn bộ mẫu khuôn mặt đã đăng ký trên máy này?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if choice != QMessageBox.Yes:
            return
        removed = self.pipeline.face_recognizer.delete_registered_faces()
        self.update_face_status_label()
        message = "Đã xóa mẫu khuôn mặt" if removed else "Không có mẫu khuôn mặt để xóa"
        self.status_bar.showMessage(message, 5000)

    def on_face_config_changed(self):
        """Cập nhật cấu hình che mặt của pipeline trực tiếp từ checkboxes."""
        self.pipeline.mask_owner_face = self.cb_mask_owner.isChecked()
        self.pipeline.mask_strangers_face = self.cb_mask_stranger.isChecked()
        safe_print(
            "GUI: face masking changed "
            f"owner={self.pipeline.mask_owner_face} strangers={self.pipeline.mask_strangers_face}"
        )

    def closeEvent(self, event):
        """Xử lý dọn dẹp luồng chạy camera khi đóng cửa sổ ứng dụng."""
        safe_print("GUI: closing and releasing resources")
        if self.worker:
            self.worker.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
