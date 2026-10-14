# 13 — UI Architecture

Qt main thread chỉ render và điều khiển state. Camera/inference chạy worker thread; signals chuyển immutable/copy-owned image data. State tối thiểu: STARTING, PROTECTED, PAUSED_SAFE, DEGRADED, ERROR và STOPPED.

Đổi camera dừng/release worker cũ trước khi mở worker mới. Close có timeout và không treo UI. Controls phải phản ánh capability thật: unsupported class bị disable/cảnh báo; virtual output có trạng thái riêng; lỗi camera/pipeline hiển thị privacy screen.
