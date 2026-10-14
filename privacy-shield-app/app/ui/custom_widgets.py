"""
custom_widgets.py — Các widget tùy chỉnh chất lượng cao cho Privacy Shield App.
Gồm ToggleSwitch (iOS style) và MetricCard hiển thị thông số động.
"""

from PySide6.QtCore import Property, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QFrame, QLabel, QVBoxLayout


class ToggleSwitch(QAbstractButton):
    """
    Nút gạt Bật/Tắt phẳng (iOS/macOS Style) với hiệu ứng animation mượt mà.
    """
    def __init__(self, parent=None, width=48, height=24):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(width, height)
        self.setCursor(Qt.PointingHandCursor)
        
        # Tọa độ X của nút tròn (thumb)
        self._thumb_position = 3.0
        self.anim = QPropertyAnimation(self, b"thumb_position")
        self.anim.setDuration(120)  # Animation trong 120ms

    @Property(float)
    def thumb_position(self):
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, pos):
        self._thumb_position = pos
        self.update()

    def nextCheckState(self):
        # Đảo trạng thái check
        super().nextCheckState()
        # Tính toán điểm kết thúc mới của thumb
        end_val = self.width() - self.height() + 3.0 if self.isChecked() else 3.0
        self.anim.stop()
        self.anim.setStartValue(self._thumb_position)
        self.anim.setEndValue(end_val)
        self.anim.start()

    def checkStateSet(self):
        """Đồng bộ vị trí thumb khi setChecked() được gọi từ code."""
        super().checkStateSet()
        end_val = self.width() - self.height() + 3.0 if self.isChecked() else 3.0
        self.anim.stop()
        self._thumb_position = end_val
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Vẽ thân switch (Background)
        # Sử dụng xanh Mint neon khi Bật (#00f5a0) và xám mờ khi Tắt
        if not self.isEnabled():
            bg_color = QColor("rgba(255, 255, 255, 0.05)")
        elif self.isChecked():
            bg_color = QColor("#00f5a0")
        else:
            bg_color = QColor("rgba(255, 255, 255, 0.1)")
        painter.setBrush(bg_color)
        painter.setPen(QPen(QColor("rgba(255, 255, 255, 0.05)"), 1))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), self.height()/2, self.height()/2)
        
        # Vẽ nút tròn di động (Thumb)
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(Qt.NoPen)
        r = self.height() - 6.0
        painter.drawEllipse(QRectF(self._thumb_position, 3.0, r, r))


class MetricCard(QFrame):
    """
    Thẻ hiển thị thông số dạng kính mờ (Glassmorphism),
    có khả năng cập nhật giá trị và đổi màu chữ động.
    """
    def __init__(self, title, value, unit="", parent=None):
        super().__init__(parent)
        self.setObjectName("card_container")
        self.setMinimumSize(120, 70)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        
        # Nhãn tiêu đề (Title)
        self.title_label = QLabel(title, self)
        self.title_label.setStyleSheet("color: #7e8492; font-size: 8.5pt; font-weight: bold; border: none; background: transparent;")
        
        # Nhãn giá trị (Value)
        self.value_label = QLabel(f"{value} {unit}".strip(), self)
        self.value_label.setStyleSheet("color: #ffffff; font-size: 14pt; font-weight: bold; border: none; background: transparent;")
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        
    def update_value(self, value, unit=""):
        """Cập nhật giá trị hiển thị."""
        self.value_label.setText(f"{value} {unit}".strip())
        
    def set_value_color(self, color_hex):
        """Thay đổi màu chữ giá trị động — cache để tránh re-parse CSS 90 lần/giây."""
        if getattr(self, '_current_color', None) == color_hex:
            return
        self._current_color = color_hex
        self.value_label.setStyleSheet(f"color: {color_hex}; font-size: 14pt; font-weight: bold; border: none; background: transparent;")
