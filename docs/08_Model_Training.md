# 08 — Model Training

Pipeline dự kiến gồm `src/training` hoặc `scripts/`: validate manifest, build split, train YOLO, evaluate, export ONNX/Torch bundle và tạo report. Mọi command nhận config và run directory mới; không ghi đè run frozen.

Baseline đầu tiên ưu tiên model nhỏ trên CPU. Chỉ đổi sang model lớn/GPU khi recall-latency trade-off được đo. Không gọi COCO `yolov8n.pt` là privacy model custom.

Acceptance: cold-load bundle cho cùng predictions trong tolerance; class map khớp config; corrupted/mismatched bundle bị startup chặn.
