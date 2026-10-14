# Changelog

## 2026-10-08 — Phase 0 started

- Established root README, Git ignore policy, test/lint configuration and 01–20 documentation structure.
- Declared desktop app as primary product and isolated AI agent from realtime path.
- Recorded current limitations: COCO-only detector, no custom training/evaluation, no implemented virtual camera, no existing tests/package acceptance.
- Phase 0 remains in progress until clean Python 3.12 install, environment smoke and baseline tests pass.

## 2026-10-08 — Phase 1/2 safety baseline

- Added config bounds/path validation, injectable/lazy runtime dependencies and explicit model capability reporting.
- Added bbox clipping, small-ROI-safe blur and reset contracts for scheduler/tracks.
- Changed protection-off behavior to a privacy screen; removed fake FPS and per-frame face pose debug output.
- Added owned `QImage` copies, bounded camera read failure, disconnect privacy screen and processed-only virtual-camera adapter.
- Corrected Ollama topology: host-managed Ollama is checked with its CLI instead of calling a nonexistent Compose container.
- Expanded agent sensitive-path policy to deny biometric templates, data, datasets, runs, logs and checkpoints.
- Baseline regression: 25 tests passed under an existing Python 3.12 CV environment. Project `.venv` full dependency install remains pending because registry downloads stalled; this is not yet clean-environment acceptance.
