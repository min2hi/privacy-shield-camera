"""
style_sheets.py — Hệ thống Design Tokens & QSS chuẩn Studio Dark (Linear / Camo Studio style).
Sử dụng bảng màu Obsidian Zinc, viền mảnh 1px tinh tế và điểm nhấn Emerald trầm chuẩn phần mềm chuyên nghiệp.
"""

# ============================================================
# STUDIO DESIGN TOKENS — Refined Dark Palette
# ============================================================
MINT_PRIMARY = "#10b981"       # Studio Emerald (dịu mắt, chuyên nghiệp)
MINT_BRIGHT = "#34d399"        # Emerald sáng cho số liệu nổi bật
MINT_HOVER = "#059669"
MINT_PRESSED = "#047857"
MINT_SUBTLE = "rgba(16, 185, 129, 0.12)"
MINT_BORDER = "rgba(16, 185, 129, 0.35)"

DANGER_PRIMARY = "#f43f5e"     # Studio Rose/Crimson
DANGER_HOVER = "rgba(244, 63, 94, 0.14)"
WARNING_PRIMARY = "#f59e0b"    # Studio Amber

BG_DARK = "#0b0d10"            # Nền tổng thể Obsidian sâu
BG_VIEWPORT = "#07080a"        # Nền khung ngắm camera chuẩn broadcast
BG_SIDEBAR = "#101318"         # Nền thanh bên
BG_CARD = "#151920"            # Nền thẻ nhóm điều khiển (Tactile Card)
BG_CONTROL = "#1a1f28"         # Nền input / combobox / button

TEXT_PRIMARY = "#f3f4f6"       # Trắng dịu (Gray 100)
TEXT_SECONDARY = "#d1d5db"     # Xám sáng (Gray 300)
TEXT_MUTED = "#717a8a"         # Xám ghi kỹ thuật (Slate Muted)

BORDER_SUBTLE = "#212732"      # Viền mảnh 1px chuẩn Linear
BORDER_HOVER = "#333c4d"       # Viền khi di chuột


APP_STYLE = """
/* ─── Base Typography & Surface ─── */
QWidget {
    color: #f3f4f6;
    font-family: "Segoe UI Variable Text", "Segoe UI", -apple-system, BlinkMacSystemFont, "Inter", sans-serif;
    font-size: 9.5pt;
}

QMainWindow {
    background-color: #0b0d10;
}

/* ─── Sidebar & Tactile Group Cards ─── */
QFrame#sidebar_container {
    background-color: #101318;
    border-right: 1px solid #1e232d;
}

QWidget#sidebar_content {
    background-color: transparent;
}

QFrame#section_card, QFrame#vcam_control_card, QFrame#face_control_card {
    background-color: #14181f;
    border: 1px solid #202632;
    border-radius: 8px;
}

QFrame#card_container {
    background-color: #12151b;
    border: 1px solid #1f2530;
    border-radius: 10px;
}

QFrame#viewport_container {
    background-color: #07080a;
    border: 1px solid #1f2530;
    border-radius: 10px;
}

QFrame#monitor_header_bar {
    background-color: #12151b;
    border: 1px solid #1f2530;
    border-radius: 8px;
}

/* ─── Tooltip ─── */
QToolTip {
    color: #f3f4f6;
    background-color: #181c24;
    border: 1px solid #2c3444;
    padding: 6px 10px;
    border-radius: 5px;
    font-size: 8.5pt;
}

/* ─── Typography Labels ─── */
QLabel {
    color: #e5e7eb;
    background: transparent;
}

QLabel#app_title {
    font-size: 12.5pt;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: #f9fafb;
    background: transparent;
}

QLabel#app_subtitle {
    font-size: 8pt;
    color: #6b7280;
    background: transparent;
}

QLabel#engine_badge {
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 7.5pt;
    font-weight: 600;
    color: #9ca3af;
    background-color: #1a1f28;
    border: 1px solid #262d3b;
    border-radius: 4px;
    padding: 2px 6px;
}

QLabel#section_header {
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 1.1px;
    color: #6b7280;
    padding-top: 6px;
    padding-bottom: 2px;
    background: transparent;
}

QLabel#field_label {
    font-size: 9pt;
    color: #9ca3af;
    background: transparent;
}

QLabel#mono_pill {
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 8.5pt;
    font-weight: 600;
    color: #34d399;
    background-color: rgba(16, 185, 129, 0.10);
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 4px;
    padding: 1px 7px;
}

/* ─── Buttons ─── */
QPushButton {
    background-color: #1a1f28;
    border: 1px solid #28303e;
    border-radius: 6px;
    color: #e5e7eb;
    padding: 7px 12px;
    font-size: 9pt;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #222834;
    border: 1px solid #384357;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #151921;
    border: 1px solid #10b981;
}

QPushButton#primary_button {
    background-color: #10b981;
    border: 1px solid #059669;
    color: #06110c;
    font-weight: 700;
}

QPushButton#primary_button:hover {
    background-color: #34d399;
    border: 1px solid #10b981;
    color: #040d09;
}

QPushButton#primary_button:pressed {
    background-color: #059669;
}

QPushButton#danger_button {
    background-color: rgba(244, 63, 94, 0.08);
    border: 1px solid rgba(244, 63, 94, 0.25);
    color: #fb7185;
}

QPushButton#danger_button:hover {
    background-color: rgba(244, 63, 94, 0.16);
    border: 1px solid #f43f5e;
    color: #fda4af;
}

QPushButton#danger_button:pressed {
    background-color: rgba(244, 63, 94, 0.24);
}

QPushButton:disabled {
    background-color: #13161c;
    color: #4b5563;
    border: 1px solid #1c212b;
}

/* ─── ComboBox ─── */
QComboBox {
    background-color: #1a1f28;
    border: 1px solid #262d3b;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f3f4f6;
    font-size: 9pt;
    min-height: 18px;
}

QComboBox:hover {
    border: 1px solid #384357;
    background-color: #1e242f;
}

QComboBox:focus {
    border: 1px solid #10b981;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #262d3b;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}

QComboBox::down-arrow {
    image: none;
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #9ca3af;
    margin-right: 4px;
}

QComboBox::down-arrow:hover {
    border-top: 5px solid #f3f4f6;
}

QComboBox QAbstractItemView {
    background-color: #161a22;
    border: 1px solid #2b3343;
    border-radius: 6px;
    selection-background-color: rgba(16, 185, 129, 0.16);
    selection-color: #34d399;
    color: #e5e7eb;
    padding: 4px;
    outline: 0px;
}

/* ─── Horizontal Slider ─── */
QSlider {
    background: transparent;
    height: 22px;
}

QSlider::groove:horizontal {
    height: 4px;
    background: #252c3a;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #10b981;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #f9fafb;
    border: 2px solid #10b981;
    width: 12px;
    height: 12px;
    margin: -5px 0px;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #ffffff;
    border: 2px solid #34d399;
}

/* ─── CheckBox ─── */
QCheckBox {
    spacing: 8px;
    color: #d1d5db;
    font-size: 9pt;
    background: transparent;
    padding: 2px 0px;
}

QCheckBox:hover {
    color: #ffffff;
}

QCheckBox::indicator {
    border: 1px solid #364052;
    width: 15px;
    height: 15px;
    border-radius: 4px;
    background-color: #181c24;
}

QCheckBox::indicator:hover {
    border: 1px solid #10b981;
    background-color: rgba(16, 185, 129, 0.08);
}

QCheckBox::indicator:checked {
    border: 1px solid #10b981;
    background-color: #10b981;
}

QCheckBox::indicator:checked:hover {
    background-color: #059669;
    border: 1px solid #34d399;
}

QCheckBox:disabled {
    color: #4b5563;
}

QCheckBox::indicator:disabled {
    border: 1px solid #222733;
    background-color: #13161c;
}

/* ─── ScrollBar ─── */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
    margin: 2px 0px;
}

QScrollBar::handle:vertical {
    background: #28303e;
    min-height: 28px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #3b465c;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    border: none;
    background: none;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

/* ─── Status Bar ─── */
QStatusBar {
    background-color: #0e1015;
    color: #6b7280;
    border-top: 1px solid #1c212b;
    font-family: "Cascadia Mono", "Consolas", "Segoe UI", monospace;
    font-size: 8.5pt;
    padding: 2px 8px;
}

QStatusBar::item {
    border: none;
}

/* ─── Dialogs & MessageBox ─── */
QDialog, QMessageBox {
    background-color: #101318;
}

QMessageBox QLabel {
    color: #e5e7eb;
    font-size: 9.5pt;
}

QMessageBox QPushButton {
    min-width: 84px;
    padding: 6px 16px;
}
"""
