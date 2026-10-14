# 01 — Project Overview

Privacy Shield Camera che thông tin nhạy cảm ngay trên máy người dùng trước khi xuất video. Mục tiêu là một desktop product Windows có hành vi fail-closed, không phải hệ thống nhận diện tuyệt đối hay sản phẩm an toàn đã chứng nhận.

## Phạm vi final

1. Webcam preview và virtual camera ổn định.
2. Phát hiện các lớp đã train/đánh giá, không quảng bá lớp unsupported.
3. Solid/mosaic/blur với policy ưu tiên solid cho dữ liệu rủi ro cao.
4. Temporal continuity và đo hiệu năng thật.
5. Biometric enrollment có consent, reset và local-only storage.
6. Custom model pipeline có dataset provenance và reproducible evaluation.
7. Windows package, tests, documentation và demo evidence.

AI Project Agent là deliverable hỗ trợ tùy chọn. Nó không chặn MVP desktop và không được nằm trong realtime path.
