# 04 — Data & Model Strategy

ID/payment card dùng mẫu giả, số/tên ngẫu nhiên và không mô phỏng danh tính thật. Receipt/document/phone/QR cần ghi rõ nguồn, license/consent và split theo scene/template để tránh leakage.

Mỗi dataset snapshot phải có manifest gồm ID, path, class, split group, source/license, SHA256, dimensions và annotation status. Không train trực tiếp từ thư mục ảnh không có manifest.

Đánh giá tối thiểu: per-class precision/recall/AP, confusion/support, false-negative review cho critical classes, latency CPU, size groups, rotation/light/occlusion slices và external holdout. Promotion chỉ dùng validation; test không dùng để tune.

Raw/private data, labels có thông tin cá nhân và weights generated không commit Git. Release model bundle phải có class map, thresholds, training config, dataset snapshot hash, library versions và metrics report.
