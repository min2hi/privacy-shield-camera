# 06 — Runtime Pipeline

Luồng chuẩn: capture → mirror policy → scheduled object detection → face detection/verification → temporal association → bbox expansion → class policy mask → metrics → preview + virtual output.

Clock đo latency/FPS dùng monotonic high-resolution clock. Frame skip không được làm mask biến mất; detection cache phải reset khi đổi camera/model/class policy. Camera read failure có retry hữu hạn rồi chuyển privacy screen/error. Virtual output không bao giờ nhận raw frame.

Metrics phân biệt capture FPS, processing latency và output FPS. Không dùng số giả để làm UI xanh.
