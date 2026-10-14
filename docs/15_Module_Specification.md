# 15 — Module Specification

| Module | Contract chính |
|---|---|
| `ConfigLoader` | load/validate/resolve paths; fail trước side effects |
| `Detector` | BGR frame + supported filters → bounded detections |
| `FrameScheduler` | deterministic cadence/cache/reset |
| `TemporalSmoothing` | class-aware association + finite TTL/reset |
| `Masker` | copy input; clip bbox; apply declared policy |
| `FaceRecognizer` | detect/embed/verify/enroll/delete; no network after setup |
| `PrivacyPipeline` | processed frame or privacy screen + truthful metrics |
| `CameraWorker` | capture lifecycle, bounded failures, owned QImage, output send |
| `VirtualCameraOutput` | processed RGB frame only; open/send/close/status |
| Agent RAG | allowlisted text only; no media/secrets/biometrics |

Interfaces phải test được bằng dependency injection; constructor không nên tự tải network asset trong production startup.
