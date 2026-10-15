"""
main_window.py — Cửa sổ giao diện chính (MainWindow) của Privacy Shield App.
Thiết kế chuẩn Studio Dark (Linear / Camo Studio / OBS Broadcast style):
- Bảng màu Obsidian Zinc sâu (#0b0d10 / #101318 / #14181f) với viền mảnh 1px (#202632)
- Các cụm điều khiển gom nhóm thành thẻ Tactile Card rõ ràng, không dùng emoji màu mè
- Thanh trạng thái Monitor Header Bar và Telemetry Dock dùng font số liệu Monospace
"""

import sys

from app.core.pipeline import PrivacyPipeline
from app.ui.camera_worker import CameraWorker
from app.ui.custom_widgets import MetricCard, ToggleSwitch
from app.ui.style_sheets import APP_STYLE
from app.utils.config_loader import ConfigLoader
from app.utils.logging_config import get_logger
from PySide6.QtCore import QSettings, Qt, Slot
from PySide6.QtGui import QAction, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QStatusBar,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

logger = get_logger(__name__)

# Nhãn hiển thị chuyên nghiệp cho từng lớp đối tượng nhạy cảm
CLASS_DISPLAY_NAMES: dict[str, str] = {
    "cell phone": "Cell Phone · Điện thoại",
    "credit_card": "Credit Card · Thẻ ngân hàng",
    "id_card": "ID Card · CCCD / Định danh",
    "driver_license": "Driver License · Bằng lái xe",
    "passport": "Passport · Hộ chiếu",
    "document": "Document · Tài liệu / Hóa đơn",
    "screen": "Screen · Màn hình phụ",
}


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
        self.setWindowTitle("Privacy Shield Studio")
        self.resize(1160, 760)
        self.setMinimumSize(980, 650)

        # Khởi tạo Giao diện
        self.init_ui()

        # Load saved user preferences
        self._load_settings()

        # Áp dụng stylesheet phong cách Studio Dark
        self.setStyleSheet(APP_STYLE)

        # Khởi tạo System Tray
        self.tray_icon = None
        self.init_system_tray()

        # Khởi chạy luồng camera
        if auto_start:
            self.start_camera()
        else:
            self.video_label.setText("STUDIO STANDBY — CAMERA STREAM DISABLED")
            self.update_status_bar()

    @staticmethod
    def _create_divider(parent: QWidget) -> QFrame:
        """Tạo đường kẻ phân cách mảnh 1px bên trong thẻ điều khiển."""
        line = QFrame(parent)
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #1f2530; max-height: 1px; border: none;")
        return line

    def init_ui(self):
        """Khởi tạo toàn bộ layout chuẩn Studio Monitor của ứng dụng."""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ──────────────────────────────────────────────────────────
        # SIDEBAR BÊN TRÁI (356px — CÁC MODULE ĐIỀU KHIỂN DẠNG THẺ)
        # ──────────────────────────────────────────────────────────
        sidebar_outer = QFrame(self)
        sidebar_outer.setObjectName("sidebar_container")
        sidebar_outer.setFixedWidth(356)
        sidebar_outer_layout = QVBoxLayout(sidebar_outer)
        sidebar_outer_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_outer_layout.setSpacing(0)

        sidebar_scroll = QScrollArea(sidebar_outer)
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar_content")

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(8)

        # ── Brand Header ──
        brand_header = QVBoxLayout()
        brand_header.setSpacing(2)

        title_row = QHBoxLayout()
        title_label = QLabel("PRIVACY SHIELD", self)
        title_label.setObjectName("app_title")

        engine_badge = QLabel("STUDIO v1.0", self)
        engine_badge.setObjectName("engine_badge")

        title_row.addWidget(title_label)
        title_row.addStretch()
        title_row.addWidget(engine_badge)

        subtitle_label = QLabel("Real-time Video Sanitization Engine", self)
        subtitle_label.setObjectName("app_subtitle")

        brand_header.addLayout(title_row)
        brand_header.addWidget(subtitle_label)
        sidebar_layout.addLayout(brand_header)

        # ── Privacy Status Banner ──
        self.status_banner = QLabel("\u25cf PROTECTED", self)
        self.status_banner.setAlignment(Qt.AlignCenter)
        self.status_banner.setFixedHeight(30)
        self._update_status_banner("protected")
        sidebar_layout.addWidget(self.status_banner)

        # ── GROUP 1: VIDEO INPUT & ENGINE ──
        input_sec_label = QLabel("VIDEO INPUT & ENGINE", self)
        input_sec_label.setObjectName("section_header")
        sidebar_layout.addWidget(input_sec_label)

        input_card = QFrame(self)
        input_card.setObjectName("section_card")
        input_card_layout = QVBoxLayout(input_card)
        input_card_layout.setContentsMargins(12, 10, 12, 10)
        input_card_layout.setSpacing(8)

        cam_field_lbl = QLabel("Thiết bị thu hình", self)
        cam_field_lbl.setObjectName("field_label")
        input_card_layout.addWidget(cam_field_lbl)

        self.camera_combo = QComboBox(self)
        self.camera_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.camera_combo.setMinimumContentsLength(14)
        self.camera_combo.addItems([
            "Camera 0 · Thiết bị chính",
            "Camera 1 · Thiết bị phụ",
            "Studio Demo · Luồng mô phỏng",
        ])
        device_idx = self.config.get("camera.device_index", 0)
        self.camera_combo.setCurrentIndex(device_idx if device_idx in (0, 1, 2) else 0)
        self.camera_combo.currentIndexChanged.connect(self.on_camera_changed)
        input_card_layout.addWidget(self.camera_combo)

        input_card_layout.addWidget(self._create_divider(input_card))

        # Công tắc Safe Mode
        protection_layout = QHBoxLayout()
        protection_status_lbl = QLabel("Bảo vệ chủ động", self)
        self.protection_switch = ToggleSwitch(self)
        self.protection_switch.setChecked(True)
        self.protection_switch.toggled.connect(self.on_protection_toggled)
        protection_layout.addWidget(protection_status_lbl)
        protection_layout.addStretch()
        protection_layout.addWidget(self.protection_switch)
        input_card_layout.addLayout(protection_layout)

        input_card_layout.addWidget(self._create_divider(input_card))

        # Công tắc Virtual Camera
        vcam_toggle_layout = QHBoxLayout()
        vcam_title_lbl = QLabel("Virtual Camera (OBS)", self)
        self.vcam_switch = ToggleSwitch(self)
        vcam_enabled = self.config.get("output.virtual_camera.enabled", False)
        self.vcam_switch.setChecked(vcam_enabled)
        self.vcam_switch.toggled.connect(self.on_vcam_toggled)
        vcam_toggle_layout.addWidget(vcam_title_lbl)
        vcam_toggle_layout.addStretch()
        vcam_toggle_layout.addWidget(self.vcam_switch)
        input_card_layout.addLayout(vcam_toggle_layout)

        self.vcam_status_lbl = QLabel(self)
        self.vcam_status_lbl.setText("Status: Active (Streaming)" if vcam_enabled else "Status: Inactive")
        self.vcam_status_lbl.setStyleSheet(
            "color: #34d399; font-size: 8pt; font-family: 'Cascadia Mono', 'Consolas', monospace;"
            if vcam_enabled
            else "color: #6b7280; font-size: 8pt; font-family: 'Cascadia Mono', 'Consolas', monospace;"
        )
        input_card_layout.addWidget(self.vcam_status_lbl)

        sidebar_layout.addWidget(input_card)

        # ── GROUP 2: SANITIZATION POLICY ──
        policy_sec_label = QLabel("SANITIZATION POLICY", self)
        policy_sec_label.setObjectName("section_header")
        sidebar_layout.addWidget(policy_sec_label)

        policy_card = QFrame(self)
        policy_card.setObjectName("section_card")
        policy_layout = QVBoxLayout(policy_card)
        policy_layout.setContentsMargins(12, 10, 12, 10)
        policy_layout.setSpacing(8)

        preset_lbl = QLabel("Cấp độ bảo mật (Preset)", self)
        preset_lbl.setObjectName("field_label")
        policy_layout.addWidget(preset_lbl)

        self.preset_combo = QComboBox(self)
        self.preset_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.preset_combo.setMinimumContentsLength(14)
        self.preset_combo.addItems([
            "Low · Ưu tiên tốc độ",
            "Medium · Cân bằng chuẩn",
            "High · Bảo mật tối đa",
        ])
        current_preset = self.config.get("app.privacy_mode", "medium")
        preset_map = {"low": 0, "medium": 1, "high": 2}
        self.preset_combo.setCurrentIndex(preset_map.get(current_preset, 1))
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        policy_layout.addWidget(self.preset_combo)

        mask_lbl = QLabel("Phương thức làm mờ", self)
        mask_lbl.setObjectName("field_label")
        policy_layout.addWidget(mask_lbl)

        self.mask_mode_combo = QComboBox(self)
        self.mask_mode_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.mask_mode_combo.setMinimumContentsLength(14)
        self.mask_mode_combo.addItems([
            "Risk Presets · Tự động theo rủi ro",
            "Force Solid · Che kín hoàn toàn",
            "Force Blur · Làm mờ Gaussian",
            "Force Mosaic · Pixel hóa vùng che",
        ])
        self.mask_mode_combo.currentIndexChanged.connect(self.on_mask_mode_changed)
        policy_layout.addWidget(self.mask_mode_combo)

        policy_layout.addWidget(self._create_divider(policy_card))

        conf_header_layout = QHBoxLayout()
        conf_title = QLabel("Ngưỡng phát hiện", self)
        conf_title.setObjectName("field_label")
        self.conf_val_label = QLabel("0.25", self)
        self.conf_val_label.setObjectName("mono_pill")
        conf_header_layout.addWidget(conf_title)
        conf_header_layout.addStretch()
        conf_header_layout.addWidget(self.conf_val_label)
        policy_layout.addLayout(conf_header_layout)

        self.conf_slider = QSlider(Qt.Horizontal, self)
        self.conf_slider.setRange(10, 90)
        self.conf_slider.setValue(25)
        self.conf_slider.valueChanged.connect(self.on_confidence_changed)
        policy_layout.addWidget(self.conf_slider)

        sidebar_layout.addWidget(policy_card)

        # ── GROUP 3: BIOMETRIC IDENTITY ──
        face_section_label = QLabel("BIOMETRIC IDENTITY", self)
        face_section_label.setObjectName("section_header")
        sidebar_layout.addWidget(face_section_label)

        face_widget = QFrame(self)
        face_widget.setObjectName("face_control_card")
        face_layout = QVBoxLayout(face_widget)
        face_layout.setContentsMargins(12, 10, 12, 10)
        face_layout.setSpacing(8)

        # Hàng trạng thái khuôn mặt
        face_status_row = QHBoxLayout()
        face_status_title = QLabel("Mẫu định danh", self)
        face_status_title.setObjectName("field_label")
        self.face_status_lbl = QLabel(self)
        face_status_row.addWidget(face_status_title)
        face_status_row.addStretch()
        face_status_row.addWidget(self.face_status_lbl)
        face_layout.addLayout(face_status_row)
        self.update_face_status_label()

        face_layout.addWidget(self._create_divider(face_widget))

        # Checkboxes che mặt
        self.cb_mask_owner = QCheckBox("Che mặt chủ sở hữu", self)
        self.cb_mask_owner.setChecked(self.pipeline.mask_owner_face)
        self.cb_mask_owner.stateChanged.connect(self.on_face_config_changed)
        face_layout.addWidget(self.cb_mask_owner)

        self.cb_mask_stranger = QCheckBox("Che mặt người lạ", self)
        self.cb_mask_stranger.setChecked(self.pipeline.mask_strangers_face)
        self.cb_mask_stranger.stateChanged.connect(self.on_face_config_changed)
        face_layout.addWidget(self.cb_mask_stranger)

        # Cụm 2 nút thao tác ngang gọn gàng
        face_btn_row = QHBoxLayout()
        face_btn_row.setSpacing(8)

        self.enroll_btn = QPushButton("Đăng ký mặt mẫu", self)
        self.enroll_btn.setObjectName("primary_button")
        self.enroll_btn.setCursor(Qt.PointingHandCursor)
        self.enroll_btn.clicked.connect(self.on_enroll_clicked)

        self.btn_reset_face = QPushButton("Xóa mẫu", self)
        self.btn_reset_face.setObjectName("danger_button")
        self.btn_reset_face.setCursor(Qt.PointingHandCursor)
        self.btn_reset_face.clicked.connect(self.on_reset_face_clicked)

        face_btn_row.addWidget(self.enroll_btn, 3)
        face_btn_row.addWidget(self.btn_reset_face, 2)
        face_layout.addLayout(face_btn_row)

        sidebar_layout.addWidget(face_widget)

        # ── GROUP 4: SENSITIVE TARGETS (PROTECTED OBJECTS) ──
        classes_header_row = QHBoxLayout()
        classes_label = QLabel("SENSITIVE TARGETS", self)
        classes_label.setObjectName("section_header")
        self.active_classes_badge = QLabel("0 ACTIVE", self)
        self.active_classes_badge.setObjectName("engine_badge")
        classes_header_row.addWidget(classes_label)
        classes_header_row.addStretch()
        classes_header_row.addWidget(self.active_classes_badge)
        sidebar_layout.addLayout(classes_header_row)

        targets_card = QFrame(self)
        targets_card.setObjectName("section_card")
        targets_layout = QVBoxLayout(targets_card)
        targets_layout.setContentsMargins(12, 10, 12, 10)
        targets_layout.setSpacing(6)

        self.class_checkboxes = {}
        supported_classes = getattr(self.pipeline.detector, "supported_class_names", set())
        for cls_name in self.class_presets.keys():
            display_label = CLASS_DISPLAY_NAMES.get(
                cls_name, cls_name.replace("_", " ").title()
            )
            cb = QCheckBox(display_label, self)
            is_supported = cls_name in supported_classes
            cb.setChecked(is_supported)
            cb.setEnabled(is_supported)
            if not is_supported:
                cb.setToolTip("Model hiện tại không hỗ trợ lớp đối tượng này")
            cb.stateChanged.connect(self.on_classes_changed)
            self.class_checkboxes[cls_name] = cb
            targets_layout.addWidget(cb)

        self.selected_classes = [
            name for name, checkbox in self.class_checkboxes.items() if checkbox.isChecked()
        ]
        self._update_active_classes_badge()

        sidebar_layout.addWidget(targets_card)
        sidebar_layout.addStretch()
        sidebar_scroll.setWidget(sidebar)
        sidebar_outer_layout.addWidget(sidebar_scroll)

        # ──────────────────────────────────────────────────────────
        # VÙNG MONITOR TRUNG TÂM (BÊN PHẢI)
        # ──────────────────────────────────────────────────────────
        content_pane = QWidget(self)
        content_layout = QVBoxLayout(content_pane)
        content_layout.setContentsMargins(20, 18, 20, 18)
        content_layout.setSpacing(14)

        # 1. Thanh Monitor Header Bar chuẩn Broadcast
        self.monitor_header = QFrame(self)
        self.monitor_header.setObjectName("monitor_header_bar")
        self.monitor_header.setFixedHeight(42)
        monitor_header_layout = QHBoxLayout(self.monitor_header)
        monitor_header_layout.setContentsMargins(14, 0, 14, 0)
        monitor_header_layout.setSpacing(10)

        self.live_dot_lbl = QLabel("\u25cf", self)
        self.live_dot_lbl.setStyleSheet("color: #10b981; font-size: 9pt; border: none;")

        self.stream_info_lbl = QLabel("LIVE VIEWPORT · REAL-TIME SANITIZATION", self)
        self.stream_info_lbl.setStyleSheet(
            "color: #9ca3af; font-family: 'Cascadia Mono', 'Consolas', monospace; "
            "font-size: 8.5pt; font-weight: 600; letter-spacing: 0.6px; border: none;"
        )

        self.live_detection_pill = QLabel("CLEAN STREAM · 0 MASKED", self)
        self.live_detection_pill.setStyleSheet(
            "color: #6b7280; background-color: #181c24; border: 1px solid #242b38; "
            "border-radius: 4px; padding: 3px 9px; "
            "font-family: 'Cascadia Mono', 'Consolas', monospace; font-size: 8pt; font-weight: 600;"
        )

        monitor_header_layout.addWidget(self.live_dot_lbl)
        monitor_header_layout.addWidget(self.stream_info_lbl)
        monitor_header_layout.addStretch()
        monitor_header_layout.addWidget(self.live_detection_pill)
        content_layout.addWidget(self.monitor_header)

        # 2. Khung ngắm Camera (Studio Viewfinder)
        self.video_frame = QFrame(self)
        self.video_frame.setObjectName("viewport_container")
        self.video_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        video_frame_layout = QVBoxLayout(self.video_frame)
        video_frame_layout.setContentsMargins(8, 8, 8, 8)

        self.video_label = QLabel(self.video_frame)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setText("INITIALIZING CAMERA PIPELINE...")
        self.video_label.setStyleSheet(
            "color: #6b7280; font-family: 'Cascadia Mono', 'Consolas', monospace; "
            "font-size: 10pt; font-weight: 600; letter-spacing: 1px; "
            "background-color: #07080a; border-radius: 6px; border: none;"
        )
        video_frame_layout.addWidget(self.video_label)

        content_layout.addWidget(self.video_frame, 1)

        # 3. Telemetry Dock (3 Metric Cards)
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(12)

        self.card_fps = MetricCard("FRAME RATE · TỐC ĐỘ KHUNG", "0.0", "Hz", self)
        self.card_latency = MetricCard("INFERENCE · ĐỘ TRỄ XỬ LÝ", "0.0", "ms", self)
        self.card_objects = MetricCard("SHIELDED · VÙNG ĐANG CHE", "0", "", self)

        metrics_layout.addWidget(self.card_fps)
        metrics_layout.addWidget(self.card_latency)
        metrics_layout.addWidget(self.card_objects)

        content_layout.addLayout(metrics_layout)

        # Lắp ghép chính
        main_layout.addWidget(sidebar_outer)
        main_layout.addWidget(content_pane, 1)

        # ──────────────────────────────────────────────────────────
        # STATUS BAR DƯỚI CÙNG
        # ──────────────────────────────────────────────────────────
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.update_status_bar()

    def _update_active_classes_badge(self) -> None:
        """Cập nhật bộ đếm số lượng lớp đối tượng đang kích hoạt."""
        if hasattr(self, "active_classes_badge") and hasattr(self, "class_checkboxes"):
            total = len(self.class_checkboxes)
            active = len(self.selected_classes)
            self.active_classes_badge.setText(f"{active}/{total} ACTIVE")

    # ──────────────────────────────────────────────────────────
    # CÁC HÀM XỬ LÝ SỰ KIỆN & ĐIỀU KHIỂN ĐỘNG
    # ──────────────────────────────────────────────────────────
    def start_camera(self):
        """Khởi động luồng webcam phụ."""
        if self.worker is not None:
            self.worker.stop()

        device_idx = self.camera_combo.currentIndex()

        self.worker = CameraWorker(
            pipeline=self.pipeline,
            device_index=device_idx,
            selected_classes=self.selected_classes,
        )
        self.worker.frame_ready.connect(self.on_frame_ready)
        self.worker.camera_error.connect(self.on_camera_error)
        self.worker.face_delete_result.connect(self._on_face_deleted)

        # Đồng bộ các thiết lập hiện tại của GUI vào worker trước khi chạy
        self.on_confidence_changed(self.conf_slider.value())
        self.on_mask_mode_changed(self.mask_mode_combo.currentIndex())
        self.worker.update_config(safe_mode=self.protection_switch.isChecked())

        self.worker.start()
        self.update_status_bar()

    @Slot(QImage, dict)
    def on_frame_ready(self, q_img, metrics):
        """Callback nhận frame ảnh từ luồng phụ và cập nhật giao diện chính."""
        scaled_pixmap = QPixmap.fromImage(q_img).scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.FastTransformation,
        )
        self.video_label.setPixmap(scaled_pixmap)

        fps = metrics.get("fps", 0.0)
        latency = metrics.get("latency_ms", 0.0)
        count = metrics.get("detected_count", 0)

        self.card_fps.update_value(f"{fps}", "Hz")
        self.card_latency.update_value(f"{latency}", "ms")
        self.card_objects.update_value(f"{count}")

        # Đổi màu thông số theo ngưỡng chuẩn Studio Emerald / Amber / Rose
        if fps >= 24.0:
            self.card_fps.set_value_color("#34d399")
        elif fps >= 12.0:
            self.card_fps.set_value_color("#fbbf24")
        else:
            self.card_fps.set_value_color("#fb7185")

        if latency <= 35.0:
            self.card_latency.set_value_color("#34d399")
        elif latency <= 75.0:
            self.card_latency.set_value_color("#fbbf24")
        else:
            self.card_latency.set_value_color("#fb7185")

        is_shielding = count > 0
        if is_shielding:
            self.card_objects.set_value_color("#fb7185")
            if getattr(self, "_last_pill_count", None) != count:
                self._last_pill_count = count
                self.live_detection_pill.setText(f"SHIELDING ACTIVE · {count} MASKED")
            if getattr(self, "_last_pill_shielding", None) is not True:
                self._last_pill_shielding = True
                self.live_detection_pill.setStyleSheet(
                    "color: #fda4af; background-color: rgba(244, 63, 94, 0.14); "
                    "border: 1px solid rgba(244, 63, 94, 0.35); border-radius: 4px; "
                    "padding: 3px 9px; font-family: 'Cascadia Mono', 'Consolas', monospace; "
                    "font-size: 8pt; font-weight: 700;"
                )
        else:
            self.card_objects.set_value_color("#9ca3af")
            if getattr(self, "_last_pill_count", None) != 0:
                self._last_pill_count = 0
                self.live_detection_pill.setText("CLEAN STREAM · 0 MASKED")
            if getattr(self, "_last_pill_shielding", None) is not False:
                self._last_pill_shielding = False
                self.live_detection_pill.setStyleSheet(
                    "color: #6b7280; background-color: #181c24; border: 1px solid #242b38; "
                    "border-radius: 4px; padding: 3px 9px; "
                    "font-family: 'Cascadia Mono', 'Consolas', monospace; "
                    "font-size: 8pt; font-weight: 600;"
                )

        state = metrics.get("state", "protected")
        self._update_status_banner(state)

        unsupported = metrics.get("unsupported_classes", [])
        if unsupported:
            msg = "Model hiện tại không hỗ trợ: " + ", ".join(unsupported)
            if getattr(self, "_last_unsupported_msg", None) != msg:
                self._last_unsupported_msg = msg
                self.status_bar.showMessage(msg, 5000)

    @Slot(str)
    def on_camera_error(self, message):
        self.status_bar.showMessage(message, 8000)
        self._update_status_banner("error")

    def on_camera_changed(self, index):
        """Thay đổi thiết bị webcam đầu vào."""
        logger.info("GUI: switch camera to index %d", index)
        self.start_camera()

    def on_protection_toggled(self, checked):
        """Bật / Tắt hệ thống bảo vệ Safe Mode."""
        if self.worker:
            self.worker.update_config(safe_mode=checked)
        self._update_status_banner("protected" if checked else "paused_safe")
        self.update_status_bar()
        status_text = "HỆ THỐNG AN TOÀN CHỦ ĐỘNG" if checked else "HỆ THỐNG TẠM NGƯNG BẢO VỆ"
        self.status_bar.showMessage(
            f"Trạng thái: {status_text} | Camera Index: {self.camera_combo.currentIndex()}",
            5000,
        )

    def on_mask_mode_changed(self, index):
        """Cập nhật đè phương pháp che phủ."""
        if not self.worker:
            return

        mode_map = {0: None, 1: "solid_mask", 2: "gaussian_blur", 3: "mosaic"}
        mode = mode_map.get(index)
        self.worker.update_config(override_mask=mode)
        mode_names = {
            None: "per-class risk presets",
            "solid_mask": "solid mask",
            "gaussian_blur": "gaussian blur",
            "mosaic": "mosaic",
        }
        logger.info("GUI: %s %s", "use" if mode is None else "force", mode_names.get(mode, mode))

    def on_preset_changed(self, index):
        """Áp dụng Privacy Preset (Low/Medium/High) — thread-safe qua update_config."""
        preset_names = ["low", "medium", "high"]
        if index < 0 or index >= len(preset_names):
            return
        preset_name = preset_names[index]
        preset_config = self.config.get(f"privacy_presets.{preset_name}", {})
        if not preset_config:
            logger.warning("GUI: preset '%s' not found in config", preset_name)
            return

        config_updates = {}
        if "mask_mode" in preset_config:
            config_updates["default_mask_mode"] = preset_config["mask_mode"]
        if "expand_bbox_ratio" in preset_config:
            config_updates["expand_ratio"] = preset_config["expand_bbox_ratio"]
        if "hold_frames" in preset_config:
            config_updates["hold_frames"] = preset_config["hold_frames"]
        if "frame_skipping" in preset_config:
            fs = preset_config["frame_skipping"]
            config_updates["scheduler_enabled"] = fs.get("enabled", True)
            config_updates["scheduler_skip_ratio"] = max(1, fs.get("skip_ratio", 2))

        if self.worker is not None and self.worker.isRunning():
            self.worker.update_config(**config_updates, reset_tracking=True)
        else:
            if self.worker is not None and config_updates:
                self.worker.update_config(**config_updates, reset_tracking=True)
            if hasattr(self.pipeline, "masker"):
                if "default_mask_mode" in config_updates:
                    self.pipeline.masker.default_mask_mode = config_updates["default_mask_mode"]
                if "expand_ratio" in config_updates:
                    self.pipeline.masker.expand_ratio = config_updates["expand_ratio"]
                if "hold_frames" in config_updates and hasattr(self.pipeline, "smoothing"):
                    self.pipeline.smoothing.hold_frames = config_updates["hold_frames"]
                if hasattr(self.pipeline, "scheduler"):
                    if "scheduler_enabled" in config_updates:
                        self.pipeline.scheduler.enabled = config_updates["scheduler_enabled"]
                    if "scheduler_skip_ratio" in config_updates:
                        self.pipeline.scheduler.skip_ratio = config_updates["scheduler_skip_ratio"]
                if hasattr(self.pipeline, "reset_tracking"):
                    self.pipeline.reset_tracking()
        logger.info("GUI: applied privacy preset '%s': %s", preset_name, preset_config)

    def on_confidence_changed(self, value):
        """Thay đổi độ nhạy Confidence Threshold của detector (thread-safe)."""
        conf_float = value / 100.0
        self.conf_val_label.setText(f"{conf_float:.2f}")
        if self.worker:
            self.worker.update_config(confidence=conf_float)

    def on_vcam_toggled(self, checked):
        """Bật/tắt Virtual Camera output (thread-safe)."""
        if checked:
            self.vcam_status_lbl.setText("Status: Active (Streaming)")
            self.vcam_status_lbl.setStyleSheet(
                "color: #34d399; font-size: 8pt; font-weight: 600; "
                "font-family: 'Cascadia Mono', 'Consolas', monospace;"
            )
        else:
            self.vcam_status_lbl.setText("Status: Inactive")
            self.vcam_status_lbl.setStyleSheet(
                "color: #6b7280; font-size: 8pt; "
                "font-family: 'Cascadia Mono', 'Consolas', monospace;"
            )
        if self.worker:
            self.worker.update_config(virtual_camera_enabled=checked)
        logger.info("GUI: virtual camera %s", "enabled" if checked else "disabled")

    def on_classes_changed(self):
        """Bật/tắt lọc đối tượng nhạy cảm cụ thể theo Checkboxes."""
        self.selected_classes = [
            cls_name for cls_name, cb in self.class_checkboxes.items() if cb.isChecked()
        ]
        self._update_active_classes_badge()

        if self.worker:
            self.worker.update_config(selected_classes=self.selected_classes)

        logger.info("GUI: protected classes changed: %s", self.selected_classes)

    def update_status_bar(self):
        """Cập nhật dòng trạng thái chân trang."""
        safe_mode = (
            "SAFE MODE ACTIVE (Đã bảo vệ)"
            if self.protection_switch.isChecked()
            else "SAFE MODE DISABLED (Tạm ngưng)"
        )
        dev_idx = self.camera_combo.currentIndex()
        self.status_bar.showMessage(f"ENGINE: {safe_mode}  ·  INPUT: Camera Index {dev_idx}")

    def _update_status_banner(self, state="protected"):
        """Cập nhật banner trạng thái privacy trên sidebar và đèn tín hiệu monitor."""
        if getattr(self, "_current_banner_state", None) == state:
            return
        self._current_banner_state = state
        states = {
            "protected": (
                "\u25cf PROTECTED · ACTIVE SHIELD",
                "rgba(16, 185, 129, 0.10)",
                "#34d399",
                "rgba(16, 185, 129, 0.30)",
            ),
            "paused_safe": (
                "\u25cf PAUSED · STANDBY MODE",
                "rgba(245, 158, 11, 0.12)",
                "#fbbf24",
                "rgba(245, 158, 11, 0.32)",
            ),
            "error": (
                "\u25cf ERROR · STREAM FAULT",
                "rgba(244, 63, 94, 0.12)",
                "#fb7185",
                "rgba(244, 63, 94, 0.32)",
            ),
            "starting": (
                "\u25cb STARTING · INITIALIZING",
                "rgba(255, 255, 255, 0.04)",
                "#9ca3af",
                "#262d3b",
            ),
        }
        text, bg, color, border = states.get(state, states["protected"])
        self.status_banner.setText(text)
        self.status_banner.setStyleSheet(
            f"""
            background-color: {bg};
            color: {color};
            font-family: 'Cascadia Mono', 'Consolas', monospace;
            font-size: 8.5pt;
            font-weight: 700;
            letter-spacing: 0.6px;
            border-radius: 6px;
            border: 1px solid {border};
            """
        )
        if hasattr(self, "live_dot_lbl"):
            self.live_dot_lbl.setStyleSheet(f"color: {color}; font-size: 9pt; border: none;")

    def on_enroll_clicked(self):
        """Mở hộp thoại đăng ký khuôn mặt mẫu đa góc (Multi-Pose Wizard)."""
        if not self.worker:
            self.status_bar.showMessage("Không thể đăng ký: Camera chưa hoạt động!", 3000)
            return

        from app.ui.enroll_dialog import FaceEnrollmentDialog

        dialog = FaceEnrollmentDialog(self.worker, self)
        self.worker.enroll_result.connect(dialog.on_enroll_result)
        dialog.exec()
        self.worker.enroll_result.disconnect(dialog.on_enroll_result)
        self.update_face_status_label()

    def update_face_status_label(self, has_face=None):
        """Cập nhật nhãn thông báo mẫu mặt chủ sở hữu trên sidebar."""
        if has_face is None:
            fr = self.pipeline.face_recognizer
            lock = getattr(fr, "_get_lock", lambda: None)()
            if lock is not None:
                with lock:
                    has_face = len(fr.registered_embeddings) > 0
            else:
                has_face = len(fr.registered_embeddings) > 0
        self._has_registered_face = has_face
        if has_face:
            self.face_status_lbl.setText("Mẫu mặt: Đã đăng ký")
            self.face_status_lbl.setStyleSheet(
                "color: #34d399; background-color: rgba(16, 185, 129, 0.10); "
                "border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 4px; "
                "padding: 1px 7px; font-size: 8pt; font-weight: 600;"
            )
        else:
            self.face_status_lbl.setText("Mẫu mặt: Chưa có")
            self.face_status_lbl.setStyleSheet(
                "color: #6b7280; background-color: #1a1f28; "
                "border: 1px solid #262d3b; border-radius: 4px; "
                "padding: 1px 7px; font-size: 8pt;"
            )

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
        self._on_face_deleted(removed)

    @Slot(bool)
    def _on_face_deleted(self, removed):
        """Callback sau khi hoàn thành xóa mẫu mặt."""
        self.update_face_status_label(has_face=False)
        message = "Đã xóa mẫu khuôn mặt" if removed else "Không có mẫu khuôn mặt để xóa"
        self.status_bar.showMessage(message, 5000)

    def on_face_config_changed(self):
        """Cập nhật cấu hình che mặt (thread-safe qua update_config)."""
        owner = self.cb_mask_owner.isChecked()
        stranger = self.cb_mask_stranger.isChecked()
        if self.worker:
            self.worker.update_config(mask_owner_face=owner, mask_strangers_face=stranger)
        logger.info("GUI: face masking changed owner=%s strangers=%s", owner, stranger)

    def _load_settings(self):
        """Tải các tùy chỉnh đã lưu của user."""
        settings = QSettings("PrivacyShield", "PrivacyShieldCamera")
        conf = settings.value("confidence", None)
        if conf is not None:
            conf_val = int(conf)
            if conf_val > 65:
                conf_val = 25
                settings.setValue("confidence", conf_val)
            self.conf_slider.setValue(conf_val)
        mask_idx = settings.value("mask_mode_index", None)
        if mask_idx is not None:
            self.mask_mode_combo.setCurrentIndex(int(mask_idx))
        preset_idx = settings.value("preset_index", None)
        if preset_idx is not None and hasattr(self, "preset_combo"):
            self.preset_combo.setCurrentIndex(int(preset_idx))

    def _save_settings(self):
        """Lưu tùy chỉnh hiện tại của user."""
        settings = QSettings("PrivacyShield", "PrivacyShieldCamera")
        settings.setValue("confidence", self.conf_slider.value())
        settings.setValue("mask_mode_index", self.mask_mode_combo.currentIndex())
        if hasattr(self, "preset_combo"):
            settings.setValue("preset_index", self.preset_combo.currentIndex())

    def init_system_tray(self):
        """Khởi tạo System Tray Icon nếu hệ thống hỗ trợ."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray_icon = QSystemTrayIcon(self)
        icon = self.windowIcon()
        if not icon.isNull():
            self.tray_icon.setIcon(icon)
        else:
            style = QApplication.style()
            self.tray_icon.setIcon(style.standardIcon(QStyle.SP_ComputerIcon))

        tray_menu = QMenu(self)
        show_action = QAction("Hiện ứng dụng", self)
        show_action.triggered.connect(self.showNormal)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()
        quit_action = QAction("Thoát", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("Privacy Shield Camera")
        self.tray_icon.show()

    def closeEvent(self, event):
        """Xử lý dọn dẹp luồng chạy camera khi đóng cửa sổ ứng dụng."""
        logger.info("GUI: closing and releasing resources")
        self._save_settings()
        if self.worker:
            self.worker.stop()
        if hasattr(self, "tray_icon") and self.tray_icon:
            self.tray_icon.hide()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
