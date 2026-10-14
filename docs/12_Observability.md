# 12 — Observability

Desktop log dùng structured metadata: session ID ngẫu nhiên, monotonic/runtime timestamp, device ID, FPS/latency, detection class/confidence/area ratio, state transitions và error code. Không log pixel, OCR content, full filesystem secret path hoặc embedding.

Acceptance evidence nằm trong `runs/<phase>/<run-id>/` và bị Git ignore. Changelog chỉ ghi summary cùng command/test count; không thay thế artifact thật.
