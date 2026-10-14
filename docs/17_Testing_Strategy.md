# 17 — Testing Strategy

## Test matrix

| Layer | Bắt buộc |
|---|---|
| Config | schema, bounds, path resolution, secrets absent |
| Unit CV | bbox clipping, blur/mosaic/solid, IoU/TTL, scheduler/reset |
| Pipeline | fake detector/face components, fail-safe, metrics, unsupported classes |
| Worker | fake capture/output, disconnect, stop, buffer ownership |
| Model | class map, cold reload, deterministic fixture, corrupt bundle |
| Agent | RAG allow/deny, permissions, unavailable dependency |
| Privacy | no raw disk/log/output under injected failures |
| Performance | warmup, p50/p95 latency, FPS, memory/CPU soak |

Unit tests không chứng minh webcam/driver/OBS hoạt động. Hardware checklist phải chạy thủ công trên thiết bị đích và lưu metadata/evidence không chứa frame nhạy cảm. Không dùng camera smoke để suy accuracy của model.

Lệnh chuẩn:

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m pytest --cov=privacy-shield-app/app --cov-report=term-missing
.venv/Scripts/python.exe scripts/check_environment.py
```
