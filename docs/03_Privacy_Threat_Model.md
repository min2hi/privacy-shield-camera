# 03 — Privacy Threat Model

## Tài sản cần bảo vệ

Raw frame, vùng văn bản/QR/thẻ, face embeddings, model/dataset provenance, secrets của agent và log runtime.

## Threat chính

- Model miss hoặc bbox chớp tắt làm lộ dữ liệu.
- Exception, camera reconnect hoặc virtual-camera failure trả raw frame.
- UI “protection off” bypass pipeline ngoài ý muốn.
- Log/screenshot/debug lưu frame.
- Face template bị commit, sao lưu hoặc đọc ngoài ý muốn.
- Agent/RAG ingest dữ liệu sinh trắc hoặc secrets.

## Policy

Production luôn fail closed. Mọi bypass raw preview phải là developer-only build flag, không có trong release. Log chỉ chứa timestamp, class, confidence, bbox ratios, latency và error code; không chứa pixels, OCR text hoặc embeddings. Face template phải local-only, có reset/delete và không được RAG ingest.
