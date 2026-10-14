# Privacy Shield Camera

Ứng dụng desktop xử lý webcam cục bộ để phát hiện và che vùng có nguy cơ lộ thông tin trước khi hình ảnh được đưa sang ứng dụng khác. Sản phẩm chính nằm trong `privacy-shield-app/`; `ai-project-agent/` là công cụ hỗ trợ phát triển độc lập, không nằm trên đường video realtime.

## Trạng thái hiện tại

- Prototype có PySide6 UI, YOLOv8, ba kiểu mask, frame skipping, temporal hold và nhận diện khuôn mặt cục bộ.
- Model `yolov8n.pt` hiện là COCO pretrained: chỉ lớp `cell phone` trong danh sách privacy có thể smoke test. Các lớp ID/thẻ/hóa đơn/tài liệu cần model custom đã được kiểm chứng.
- Virtual camera, custom training/evaluation, packaging và release acceptance chưa hoàn tất.
- AI agent có khung RAG/LangGraph và Docker services nhưng chưa phải dependency của desktop app.
- Không coi một phase hoàn thành nếu chưa đạt acceptance và có evidence trong `runs/` hoặc test report.

Xem [mục lục tài liệu](docs/README.md), [roadmap](docs/16_Development_Roadmap.md), [testing](docs/17_Testing_Strategy.md) và [giới hạn](docs/19_Risks_and_Limitations.md).

## Khởi tạo môi trường

PowerShell tại project root:

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe scripts/check_environment.py
```

Python 3.12 x64 là baseline phát hành. Python 3.13 có thể dùng để phát triển khi toàn bộ smoke test đạt, nhưng không tự động trở thành baseline release.

## Chạy ứng dụng

```powershell
Set-Location privacy-shield-app
..\.venv\Scripts\python.exe main.py
```

Smoke giao diện không mở model/camera:

```powershell
Set-Location privacy-shield-app
..\.venv\Scripts\python.exe main.py --fixture
```

CLI OpenCV tối giản:

```powershell
Set-Location privacy-shield-app
..\.venv\Scripts\python.exe -m app.main
```

Ứng dụng mặc định không lưu frame. Face embedding cục bộ là dữ liệu sinh trắc nhạy cảm và bị `.gitignore`; người dùng phải có khả năng xóa/reset trước release.

## Nguyên tắc an toàn

- Không ghi raw webcam frame vào log hoặc disk theo mặc định.
- Lỗi pipeline phải trả privacy screen, không được trả raw frame.
- Tắt protection trong UI chỉ được phép tạo privacy screen; không bypass che dữ liệu.
- Model chưa nhận diện được một lớp phải được báo là unsupported, không hiển thị như đã được bảo vệ.
- AI agent không được truy cập frame hoặc biometric template.

## Thành phần

| Thành phần | Vai trò | Trạng thái |
|---|---|---|
| `privacy-shield-app/` | Desktop product và realtime CV | Prototype đang harden |
| `docs/` | Contracts, roadmap, testing, release evidence | Đang chuẩn hóa |
| `ai-project-agent/` | RAG/project copilot | Experimental |
| `infra/` | PostgreSQL, Redis, Langfuse, LiteLLM | Development-only |
| `references/` | UI reference; không phải production code | Reference-only |

## Definition of Final

Final chỉ đạt khi unit/integration tests xanh, model custom có provenance và metrics, virtual camera fail-closed chạy trên Windows, camera disconnect không rò raw frame, packaging chạy trên máy sạch, privacy/biometric controls được nghiệm thu và báo cáo giới hạn khớp kết quả thật.
