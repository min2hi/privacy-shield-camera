"""
custom_widgets.py — Các widget tùy chỉnh chuẩn Studio Hardware cho Privacy Shield App.
Bao gồm ToggleSwitch (công tắc cơ học mượt mà) và MetricCard (module đo lường thông số).
"""

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QFrame, QHBoxLayout, QLabel, QVBoxLayout


class ToggleSwitch(QAbstractButton):
    """
    Công tắc Bật/Tắt phong cách Studio Dark (Linear / macOS style)
    với chuyển động nội suy mượt và viền mảnh chuẩn xác.
    """

    def __init__(self, parent=None, width: int = 44, height: int = 22):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(width, height)
        self.setCursor(Qt.PointingHandCursor)

        # Tọa độ X của nút trượt (thumb)
        self._thumb_position = 3.0
        self.anim = QPropertyAnimation(self, b"thumb_position", self)
        self.anim.setDuration(140)
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)

    @Property(float)
    def thumb_position(self) -> float:
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, pos: float) -> None:
        self._thumb_position = pos
        self.update()

    def nextCheckState(self) -> None:
        super().nextCheckState()
        end_val = self.width() - self.height() + 3.0 if self.isChecked() else 3.0
        self.anim.stop()
        self.anim.setStartValue(self._thumb_position)
        self.anim.setEndValue(end_val)
        self.anim.start()

    def checkStateSet(self) -> None:
        """Đồng bộ vị trí thumb ngay lập tức khi setChecked() được gọi từ code."""
        super().checkStateSet()
        end_val = self.width() - self.height() + 3.0 if self.isChecked() else 3.0
        self.anim.stop()
        self._thumb_position = end_val
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Màu nền rãnh trượt (Track) và viền 1px
        if not self.isEnabled():
            bg_color = QColor("#161a22")
            border_color = QColor("#222834")
            thumb_color = QColor("#4b5563")
        elif self.isChecked():
            bg_color = QColor("#10b981")
            border_color = QColor("#059669")
            thumb_color = QColor("#f9fafb")
        else:
            bg_color = QColor("#202632")
            border_color = QColor("#303949")
            thumb_color = QColor("#d1d5db")

        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 1.0))
        radius = self.height() / 2.0
        painter.drawRoundedRect(
            QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0),
            radius,
            radius,
        )

        # Vẽ nút tròn di động (Thumb)
        painter.setBrush(thumb_color)
        painter.setPen(Qt.NoPen)
        r = self.height() - 6.0
        painter.drawEllipse(QRectF(self._thumb_position, 3.0, r, r))


class MetricCard(QFrame):
    """
    Thẻ hiển thị thông số kỹ thuật chuẩn Broadcast Telemetry:
    - Thanh chỉ báo trạng thái (Accent Bar) bên trái đổi màu theo ngưỡng
    - Font số liệu Monospace cố định độ rộng giúp không bị nhảy chữ
    """

    def __init__(self, title: str, value: str, unit: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("card_container")
        self.setMinimumSize(135, 74)
        self._current_color = "#f3f4f6"

        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(12, 10, 14, 10)
        outer_layout.setSpacing(10)

        # Thanh chỉ báo trạng thái mảnh bên trái
        self.accent_bar = QFrame(self)
        self.accent_bar.setFixedWidth(3)
        self.accent_bar.setStyleSheet(
            "background-color: #34d399; border-radius: 1px; border: none;"
        )
        outer_layout.addWidget(self.accent_bar)

        # Cột nội dung chính
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(3)

        # Nhãn tiêu đề kỹ thuật (Title)
        self.title_label = QLabel(title, self)
        self.title_label.setStyleSheet(
            "color: #6b7280; font-size: 7.5pt; font-weight: 700; "
            "letter-spacing: 0.8px; border: none; background: transparent;"
        )

        # Nhãn giá trị (Value) dùng font Monospace
        self.value_label = QLabel(f"{value} {unit}".strip(), self)
        self.value_label.setStyleSheet(
            "color: #f3f4f6; font-family: 'Cascadia Mono', 'Consolas', monospace; "
            "font-size: 14.5pt; font-weight: 700; border: none; background: transparent;"
        )

        content_layout.addWidget(self.title_label)
        content_layout.addWidget(self.value_label)
        outer_layout.addLayout(content_layout, 1)

    def update_value(self, value: str, unit: str = "") -> None:
        """Cập nhật giá trị hiển thị."""
        self.value_label.setText(f"{value} {unit}".strip())

    def set_value_color(self, color_hex: str) -> None:
        """Thay đổi màu chữ và thanh chỉ báo động — có cache để tránh re-parse CSS."""
        if getattr(self, "_current_color", None) == color_hex:
            return
        self._current_color = color_hex
        self.value_label.setStyleSheet(
            f"color: {color_hex}; font-family: 'Cascadia Mono', 'Consolas', monospace; "
            "font-size: 14.5pt; font-weight: 700; border: none; background: transparent;"
        )
        self.accent_bar.setStyleSheet(
            f"background-color: {color_hex}; border-radius: 1px; border: none;"
        )
