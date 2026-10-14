# 11 — Configuration

Config YAML được validate trước khi khởi tạo model/camera. Numeric bounds tối thiểu: width/height/FPS/image size > 0; confidence/IoU trong [0,1]; bbox expansion không âm; hold frames ≥ 1; skip ratio ≥ 1; mask mode thuộc allowlist.

Path tương đối resolve theo root của `privacy-shield-app`, không phụ thuộc current working directory. Secrets chỉ qua environment/`.env` không commit. Runtime config và training config tách riêng; frozen run lưu bản config đã resolve và hash.
