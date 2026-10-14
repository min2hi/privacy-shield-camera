# 🛡️ Privacy Shield Camera

**Real-time AI-powered privacy protection for webcam feeds.**

Privacy Shield Camera tự động phát hiện và che phủ các đối tượng nhạy cảm (thẻ căn cước, thẻ ngân hàng, hóa đơn, QR code, điện thoại, tài liệu) trong luồng webcam thời gian thực, bảo vệ quyền riêng tư khi họp online, livestream, hoặc gọi video.

## ✨ Key Features

| Feature | Description |
|---|---|
| 🔍 **Object Detection** | YOLOv8n + OpenCV hybrid detection for 7 privacy-sensitive classes |
| 👤 **Face Recognition** | Multi-pose owner enrollment with YuNet + MobileFaceNet ONNX |
| 🛡️ **Fail-Safe Mode** | Never leaks raw video frames on error — privacy-first architecture |
| 🎭 **Smart Masking** | 3 modes: Solid, Gaussian Blur, Mosaic with per-class risk presets |
| 📹 **Virtual Camera** | Output to OBS/Zoom/Teams via pyvirtualcam |
| ⚡ **Real-time** | 25-30 FPS with frame skipping and temporal smoothing |
| 🔒 **Encrypted Biometrics** | Face templates encrypted at rest with machine-derived keys |
| 🌙 **Dark Mode UI** | PyDracula + Mint Green professional theme |

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Windows 10/11 (primary), Linux/macOS (experimental)
- Webcam

### Installation
```bash
# Clone the repository
git clone https://github.com/min2hi/privacy-shield-camera.git
cd privacy-shield-camera

# Create virtual environment
python -m venv privacy-shield-app/.venv
privacy-shield-app/.venv/Scripts/activate  # Windows
# source privacy-shield-app/.venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r privacy-shield-app/requirements.txt
pip install cryptography  # Optional: for biometric encryption
```

### Run
```bash
cd privacy-shield-app
python main.py
```

### Demo Mode (no webcam needed)
Select "🎬 Demo Trực Quan" from the camera dropdown to see the app in action with synthetic ID cards, credit cards, and receipts.

## 🏗️ Architecture

```
privacy-shield-app/
├── main.py                    # Entry point (PySide6 GUI)
├── app/
│   ├── core/                  # Zero Qt dependencies
│   │   ├── pipeline.py        # Main processing pipeline
│   │   ├── detector.py        # YOLOv8 + heuristic detection
│   │   ├── face_recognizer.py # YuNet + MobileFaceNet ONNX
│   │   ├── masking.py         # Privacy mask effects
│   │   ├── frame_scheduler.py # Frame skipping optimization
│   │   ├── temporal_smoothing.py # Anti-flicker tracking
│   │   ├── virtual_camera.py  # pyvirtualcam output
│   │   └── model_bundle.py    # SHA256 model verification
│   ├── ui/                    # PySide6 GUI layer
│   │   ├── main_window.py     # Main application window
│   │   ├── camera_worker.py   # QThread webcam worker
│   │   ├── enroll_dialog.py   # Multi-pose face enrollment
│   │   ├── custom_widgets.py  # ToggleSwitch, MetricCard
│   │   └── style_sheets.py    # PyDracula + Mint theme
│   └── utils/
│       ├── config_loader.py   # YAML config with validation
│       ├── logging_config.py  # Standard Python logging
│       ├── console.py         # Backward-compat print wrapper
│       └── crypto.py          # Biometric encryption
├── configs/
│   └── default.yaml           # Application configuration
└── models/                    # ONNX/PT model files
```

### Design Principles
- **Fail-Closed Privacy**: Raw video frames never reach output on any error
- **Dependency Injection**: All core components are injectable for testing
- **Thread Safety**: UI → Worker communication via `update_config()` with locks
- **Zero Qt in Core**: `app/core/` has no Qt dependencies, fully testable

## 🔧 Configuration

Edit `configs/default.yaml` to customize:

```yaml
camera:
  device_index: 0
  width: 640
  height: 480
  fps: 30

model:
  confidence: 0.25
  
privacy:
  mask_mode: mosaic        # solid_mask, gaussian_blur, mosaic
  expand_bbox_ratio: 0.15  # Bbox expansion (0-1)
  hold_frames: 5           # Temporal smoothing duration
```

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -q

# Run with coverage
python -m pytest tests/ --cov=privacy-shield-app/app --cov-report=term-missing

# Lint
ruff check privacy-shield-app/ tests/
```

**Current: 74+ tests, ~75% line coverage**

## 📋 Detection Classes

| Class | Detection Method | Status |
|---|---|---|
| `cell phone` | YOLOv8n (COCO) | ✅ ML-based |
| `id_card` | OpenCV heuristic | ⚠️ Experimental |
| `credit_card` | OpenCV heuristic | ⚠️ Experimental |
| `qr_code` | OpenCV QRCodeDetector | ✅ Reliable |
| `receipt` | OpenCV heuristic | ⚠️ Experimental |
| `document` | YOLO (book→document) | ⚠️ Remapped |
| `smartphone_screen` | Derived from cell phone | ⚠️ Derived |

> **Note**: Card/document detection uses OpenCV edge heuristics, not a trained ML model. For production use, consider training a custom YOLOv8 model on privacy-specific datasets.

## 🔒 Privacy & Security

- **Fail-safe**: Pipeline errors trigger black screen, never raw video
- **SHA256 verification**: ONNX models verified on download
- **Encrypted biometrics**: Face templates encrypted at rest (requires `cryptography`)
- **No cloud**: All processing is 100% local, no data leaves the device
- **Consent**: Face enrollment requires explicit user action

## 📦 Building

```bash
# Build Windows .exe
python scripts/build_exe.py

# Output: dist/PrivacyShieldCamera/
```

## 🗺️ Roadmap

- [x] Phase 1: Core pipeline with fail-safe
- [x] Phase 2: Face recognition (multi-pose enrollment)
- [x] Phase 3: Professional GUI (PyDracula theme)
- [x] Phase 4: Thread safety & logging overhaul
- [x] Phase 7: CI/CD pipeline
- [ ] Phase 5-6: Custom model training
- [ ] Phase 8: Performance profiling
- [ ] Phase 11: Windows installer
- [ ] Phase 12: Release & distribution

## 📄 License

MIT License — See [LICENSE](LICENSE) for details.

## 👨‍💻 Author

Built by [min2hi](https://github.com/min2hi)
