"""
style_sheets.py — Bộ định nghĩa CSS/QSS cho Privacy Shield Desktop App.
Kế thừa cấu trúc chuyên nghiệp từ PyDracula và bảng màu Mint Green.
"""

# ============================================================
# THEME TOKENS — Centralized design constants
# ============================================================
MINT_PRIMARY = "#00f5a0"
MINT_HOVER = "#00d48a"
MINT_PRESSED = "#00b375"
DANGER_PRIMARY = "#ff4a6b"
DANGER_HOVER = "rgba(255, 74, 107, 0.15)"
WARNING_PRIMARY = "#ffb900"
BG_DARK = "#111215"
BG_SIDEBAR = "#16171b"
BG_CARD = "rgba(22, 23, 27, 0.75)"
TEXT_PRIMARY = "#f0f2f5"
TEXT_SECONDARY = "#eef1f5"
TEXT_MUTED = "#7e8492"
BORDER_SUBTLE = "rgba(255, 255, 255, 0.06)"
BORDER_HOVER = "rgba(255, 255, 255, 0.20)"


APP_STYLE = """
/* Thiết lập font chữ mặc định cho toàn bộ ứng dụng */
QWidget {
    color: #f0f2f5;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
    font-size: 10pt;
}

/* Khung cửa sổ chính */
QMainWindow {
    background-color: #111215;
}

/* Card Container dạng kính mờ (Glassmorphism) */
QFrame#card_container {
    background-color: rgba(22, 23, 27, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
}

/* Sidebar Container */
QFrame#sidebar_container {
    background-color: #16171b;
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}

/* Tooltip (Dracula-style với viền Mint phát sáng) */
QToolTip {
    color: #ffffff;
    background-color: rgba(33, 37, 43, 220);
    border: none;
    border-left: 3px solid #00f5a0;
    text-align: left;
    padding: 6px 10px;
    border-radius: 4px;
}

/* Tiêu đề ứng dụng */
QLabel#app_title {
    font-size: 16pt;
    font-weight: bold;
    color: #00f5a0;
    background: transparent;
}

QLabel#app_subtitle {
    font-size: 8.5pt;
    color: #7e8492;
    background: transparent;
}

/* Nhãn thông số (Labels) */
QLabel {
    color: #eef1f5;
}

QLabel#section_header {
    font-size: 11pt;
    font-weight: bold;
    color: #7e8492;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    padding-bottom: 4px;
    margin-top: 10px;
    margin-bottom: 5px;
}

/* Nút bấm phẳng hiện đại (Modern Flat Button) */
QPushButton {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    color: #eef1f5;
    padding: 10px 16px;
    font-size: 9.5pt;
    font-weight: bold;
}

QPushButton:hover {
    background-color: rgba(0, 245, 160, 0.10);
    border: 1px solid #00f5a0;
    color: #00f5a0;
}

QPushButton:pressed {
    background-color: rgba(0, 245, 160, 0.20);
    border: 1px solid #00f5a0;
}

/* Nút bấm Cảnh báo (Danger Button) */
QPushButton#danger_button {
    background-color: rgba(255, 74, 107, 0.05);
    border: 1px solid rgba(255, 74, 107, 0.15);
    color: #ff4a6b;
}

QPushButton#danger_button:hover {
    background-color: rgba(255, 74, 107, 0.15);
    border: 1px solid #ff4a6b;
    color: #ff4a6b;
}

QPushButton#danger_button:pressed {
    background-color: rgba(255, 74, 107, 0.25);
}

/* Dropdown (ComboBox) */
QComboBox {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 8px 12px;
    color: #eef1f5;
    min-width: 150px;
}

QComboBox:hover {
    border: 1px solid rgba(255, 255, 255, 0.20);
    background-color: rgba(255, 255, 255, 0.06);
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px; 
    border-left: 1px solid rgba(255, 255, 255, 0.08);
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}

QComboBox::down-arrow {
    image: none;
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #7e8492;
    margin-right: 6px;
}

QComboBox::down-arrow:hover {
    border-top: 6px solid #00f5a0;
}

QComboBox QAbstractItemView {
    background-color: #16171b;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 8px;
    selection-background-color: rgba(0, 245, 160, 0.15);
    selection-color: #00f5a0;
    color: #eef1f5;
    padding: 6px;
    outline: 0px;
}

/* Slider trượt ngang (Horizontal Slider) */
QSlider {
    background: transparent;
    height: 24px;
}

QSlider::groove:horizontal {
    height: 6px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f5a0, stop:1 #00d48a);
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #00f5a0;
    width: 16px;
    height: 16px;
    margin: -5px 0px; /* Căn giữa tay kéo trên rãnh */
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #00f5a0;
    border: 2px solid #ffffff;
    width: 18px;
    height: 18px;
    margin: -6px 0px;
    border-radius: 9px;
}

/* CheckBox индикатор (Bộ lọc đối tượng) */
QCheckBox {
    spacing: 8px;
    color: #eef1f5;
    background: transparent;
}

QCheckBox::indicator {
    border: 2px solid rgba(255, 255, 255, 0.15);
    width: 16px;
    height: 16px;
    border-radius: 4px;
    background-color: rgba(255, 255, 255, 0.03);
}

QCheckBox::indicator:hover {
    border: 2px solid #00f5a0;
    background-color: rgba(0, 245, 160, 0.05);
}

QCheckBox::indicator:checked {
    border: 2px solid #00f5a0;
    background-color: #00f5a0;
    image: none;
}

QCheckBox::indicator:checked:hover {
    background-color: #00d48a;
    border: 2px solid #00d48a;
}

/* Disabled states */
QCheckBox:disabled {
    color: rgba(255, 255, 255, 0.3);
}

QCheckBox::indicator:disabled {
    border: 2px solid rgba(255, 255, 255, 0.08);
    background-color: rgba(255, 255, 255, 0.02);
}

QComboBox:disabled {
    background-color: rgba(255, 255, 255, 0.02);
    color: rgba(255, 255, 255, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.04);
}

QSlider:disabled::groove:horizontal {
    background: rgba(255, 255, 255, 0.04);
}

QSlider:disabled::sub-page:horizontal {
    background: rgba(255, 255, 255, 0.08);
}

QSlider:disabled::handle:horizontal {
    background: rgba(255, 255, 255, 0.15);
    border: 2px solid rgba(255, 255, 255, 0.1);
}

QPushButton:disabled {
    background-color: rgba(255, 255, 255, 0.02);
    color: rgba(255, 255, 255, 0.25);
    border: 1px solid rgba(255, 255, 255, 0.04);
}

/* Thanh cuộn dọc (Scrollbar) của PyDracula */
QScrollBar:vertical {
    border: none;
    background: rgba(22, 23, 27, 0.3);
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {	
    background: rgba(255, 255, 255, 0.12);
    min-height: 25px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {	
    background: #00f5a0;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* Scroll Area */
QScrollArea {
    border: none;
    background-color: transparent;
}

/* Status Bar */
QStatusBar {
    background-color: #16171b;
    color: #7e8492;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
}

QStatusBar::item {
    border: none;
}

/* Input fields */
QLineEdit {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 8px 12px;
    color: #eef1f5;
    selection-background-color: rgba(0, 245, 160, 0.3);
    selection-color: #ffffff;
}

QLineEdit:focus {
    border: 1px solid #00f5a0;
}

/* Progress Bar */
QProgressBar {
    background-color: rgba(255, 255, 255, 0.06);
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f5a0, stop:1 #00d48a);
    border-radius: 4px;
}

/* Dialog boxes */
QDialog {
    background-color: #111215;
}

QMessageBox {
    background-color: #111215;
}

QMessageBox QLabel {
    color: #eef1f5;
    font-size: 10pt;
}

QMessageBox QPushButton {
    min-width: 80px;
    padding: 8px 20px;
}

/* SpinBox */
QSpinBox, QDoubleSpinBox {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 6px 10px;
    color: #eef1f5;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #00f5a0;
}
"""
