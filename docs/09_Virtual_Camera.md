# 09 — Virtual Camera

Virtual camera nhận duy nhất frame đã xử lý hoặc privacy screen. Output contract khóa width/height/FPS/pixel format theo session; thay camera phải restart output có kiểm soát.

Nếu driver/backend không có, UI báo rõ và preview cục bộ vẫn có thể chạy. Nếu output đã mở rồi gặp lỗi, không được tiếp tục tuyên bố “Protected output active”. OBS/Zoom acceptance là hardware/manual test riêng, không suy từ unit test.
