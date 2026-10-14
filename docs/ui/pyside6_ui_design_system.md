# Hướng Dẫn Thiết Kế Hệ Thống Giao Diện PySide6 (UI Design System)

Tài liệu này đóng vai trò là "Skill tham chiếu" để xây dựng giao diện ứng dụng Desktop Privacy Shield. Mục tiêu là tạo ra giao diện tối giản, hiện đại (Modern Glassmorphism) và kết hợp các ưu điểm của thư viện **PyDracula** (thanh cuộn Scrollbars, Tooltips, TextFields) với bảng màu Mint Green độc quyền của dự án.

---

## 🎨 1. Thiết Kế Màu Sắc & Tokens (Theme Tokens)

| Token | Giá trị QSS | Ý nghĩa |
|---|---|---|
| `@bg-main` | `#111215` | Màu nền tối sâu cho toàn bộ cửa sổ chính (tương tự PyDracula bgApp) |
| `@bg-card` | `rgba(22, 23, 27, 0.75)` | Nền xám mờ dạng kính (Glassmorphism) cho các bảng điều khiển |
| `@border-light`| `rgba(255, 255, 255, 0.06)` | Viền mịn bán trong suốt tạo chiều sâu nổi cho Card |
| `@text-primary`| `#f0f2f5` | Chữ chính trắng sáng mịn |
| `@text-muted`  | `#7e8492` | Chữ phụ, hướng dẫn màu xám nhạt |
| `@accent-mint` | `#00f5a0` | Màu Mint neon cho nút active, trạng thái Safe Mode tắt |
| `@accent-red`  | `#ff4a6b` | Màu đỏ neon cho nút ngắt, cảnh báo Safe Mode bật |

---

## 💅 2. Bộ Sưu Tập CSS Style Sheet (Custom QSS) - Kế Thừa Từ PyDracula

Dưới đây là mã QSS nền tảng được định nghĩa tập trung kết hợp cấu trúc chuyên nghiệp của PyDracula:

```css
/* Thiết lập chung font Segoe UI */
QWidget {
    color: #f0f2f5;
    font: 10pt "Segoe UI";
}

/* MainWindow & Frame chính */
QMainWindow {
    background-color: #111215;
}

QFrame#card_container {
    background-color: rgba(22, 23, 27, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
}

/* Tooltip (Mượn từ PyDracula và thay đổi viền sang Mint) */
QToolTip {
    color: #ffffff;
    background-color: rgba(33, 37, 43, 180);
    border-left: 3px solid #00f5a0;
    text-align: left;
    padding-left: 8px;
    margin: 0px;
}

/* Nút bấm Modern Flat Button */
QPushButton {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    color: #eef1f5;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: rgba(0, 245, 160, 0.1);
    border: 1px solid #00f5a0;
    color: #00f5a0;
}

QPushButton:pressed {
    background-color: rgba(0, 245, 160, 0.2);
    border: 1px solid #00f5a0;
}

QPushButton#danger_button:hover {
    background-color: rgba(255, 74, 107, 0.1);
    border: 1px solid #ff4a6b;
    color: #ff4a6b;
}

/* Combo Box (Dropdown) */
QComboBox {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 8px 12px;
    color: #eef1f5;
    min-width: 150px;
}

QComboBox:hover {
    border: 1px solid rgba(255, 255, 255, 0.2);
}

QComboBox::drop-down {
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #16171b;
    border: 1px solid rgba(255, 255, 255, 0.1);
    selection-background-color: rgba(0, 245, 160, 0.15);
    selection-color: #00f5a0;
    color: #eef1f5;
}

/* Slider (Thanh kéo thiết kế tinh tế) */
QSlider::groove:horizontal {
    height: 6px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #00f5a0;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #00f5a0;
    width: 14px;
    height: 14px;
    margin-top: -4px;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #00f5a0;
}

/* Scrollbars (Phong cách thanh cuộn siêu phẳng của PyDracula) */
QScrollBar:vertical {
    border: none;
    background: rgb(22, 23, 27);
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {	
    background: #00f5a0;
    min-height: 25px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {	
    background: rgba(0, 245, 160, 0.8);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
```

---

## 🛠️ 3. Cách Viết Các Custom Widgets Cao Cấp

Để giao diện không bị thô cứng, chúng ta không dùng các checkbox mặc định mà tự vẽ các control tùy chỉnh bằng PySide6:

### A. Custom Toggle Switch (Nút gạt iOS/macOS)
```python
from PySide6.QtWidgets import QAbstractButton
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import QRectF, Property, QPropertyAnimation, Qt

class ToggleSwitch(QAbstractButton):
    def __init__(self, parent=None, width=48, height=24):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(width, height)
        # Tọa độ x của nút tròn chạy trong switch
        self._thumb_position = 3.0
        self.anim = QPropertyAnimation(self, b"thumb_position")
        self.anim.setDuration(120)

    @Property(float)
    def thumb_position(self):
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, pos):
        self._thumb_position = pos
        self.update()

    def nextCheckState(self):
        super().nextCheckState()
        end_val = self.width() - self.height() + 3.0 if self.isChecked() else 3.0
        self.anim.stop()
        self.anim.setStartValue(self._thumb_position)
        self.anim.setEndValue(end_val)
        self.anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Vẽ thân switch
        bg_color = QColor("#00f5a0") if self.isChecked() else QColor("rgba(255, 255, 255, 0.1)")
        painter.setBrush(bg_color)
        painter.setPen(QPen(QColor("rgba(255, 255, 255, 0.05)"), 1))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), self.height()/2, self.height()/2)
        
        # Vẽ nút tròn (Thumb)
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(Qt.NoPen) # Đã được khắc phục nhờ import Qt
        r = self.height() - 6.0
        painter.drawEllipse(QRectF(self._thumb_position, 3.0, r, r))
```

---

## 🧵 4. Kiến Trúc Luồng Camera Phụ (Camera Threading Pattern)

Hàm `QThread` chuẩn để chạy webcam nền và liên kết dữ liệu với giao diện:

```python
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QImage
import cv2

class CameraWorker(QThread):
    # Signal truyền ảnh đã xử lý và metrics thống kê về UI Thread
    frame_ready = Signal(QImage, dict)
    
    def __init__(self, pipeline, device_index=0, selected_classes=None):
        super().__init__()
        self.pipeline = pipeline
        self.device_index = device_index
        self.selected_classes = selected_classes
        self.running = True

    def run(self):
        cap = cv2.VideoCapture(self.device_index)
        # Thiết lập kích thước
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        while self.running:
            ret, frame = cap.read()
            if not ret:
                continue
            
            # Lật gương
            frame = cv2.flip(frame, 1)
            
            # Xử lý qua pipeline
            processed_frame, metrics = self.pipeline.process_frame(frame, self.selected_classes)
            
            # Khắc phục lệch màu: Convert kênh màu BGR của OpenCV sang RGB chuẩn
            rgb_image = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # Phát tín hiệu về Main UI Thread
            self.frame_ready.emit(q_img, metrics)
            
        cap.release()

    def stop(self):
        self.running = False
        self.wait()
```
