# 16 — Development Roadmap

## Quy tắc mỗi phase

- Đọc prerequisite và module contracts; không tự đổi privacy policy.
- Viết regression cho boundary/hành vi rủi ro và chạy test liên quan.
- Smoke đường thật sau unit test; hardware acceptance ghi riêng.
- Ghi changelog, command, kết quả và phần chưa đạt.
- Không sang phase phụ thuộc nếu acceptance cốt lõi chưa đạt.

## Phase 0 — Reproducible foundation

- **Goal:** README/docs, Git hygiene, Python 3.12 venv, config validation, environment report.
- **Files:** root metadata, `scripts/check_environment.py`, config tests.
- **Acceptance:** clean install; imports/model files/config validation; pytest green; không secret/private artifact được track.

## Phase 1 — Core contracts và privacy regressions

- **Goal:** khóa detection/masking/scheduler/smoothing/fail-safe behavior.
- **Tests:** bbox boundaries, mask modes, TTL/reset, detector errors, unsupported classes.
- **Acceptance:** exception không trả raw frame; metrics thật; state reset đúng.

## Phase 2 — Camera/UI lifecycle

- **Goal:** worker owned buffers, bounded disconnect, explicit runtime states, clean shutdown.
- **Acceptance:** fake camera integration xanh; manual camera switch/disconnect evidence; UI không treo.

## Phase 3 — Virtual camera

- **Goal:** processed-only output adapter và trạng thái UI.
- **Acceptance:** fake backend tests; OBS/Zoom manual smoke; output failure fail closed.

## Phase 4 — Face privacy hardening

- **Goal:** consent/quality/versioned template/reset, remove per-frame sensitive debug.
- **Acceptance:** enrollment/verify/delete tests; corrupt template handled; threshold evaluation plan frozen.

## Phase 5 — Dataset governance

- **Goal:** synthetic/private manifest, license ledger, group-disjoint splits và annotation QC.
- **Acceptance:** every sample traced/hashed or explicit rejected; no real ID/payment data.

## Phase 6 — Custom model baseline

- **Goal:** train/evaluate small detector and publish trusted bundle.
- **Acceptance:** cold load, class compatibility, per-class metrics/slices, CPU benchmark.

## Phase 7 — Model/runtime integration

- **Goal:** capability-aware UI/config and model bundle validation.
- **Acceptance:** unsupported labels blocked; corrupt/mismatched bundle fails before camera.

## Phase 8 — Performance/robustness

- **Goal:** profile capture/inference/masking/output; soak test; moving-object continuity.
- **Acceptance:** declared 720p target on named hardware, memory stable, low-light/rotation reports.

## Phase 9 — Agent/RAG completion

- **Goal:** consistent Compose topology, allowlisted ingestion, memory/checkpoint/evaluation.
- **Acceptance:** infra health checks, RAG citations, denylist tests; desktop remains independent.

## Phase 10 — Security/privacy verification

- **Goal:** secret scanning, data-flow audit, biometric deletion và crash behavior.
- **Acceptance:** no raw artifacts/logs; fail-closed fault injection; privacy checklist signed.

## Phase 11 — Windows packaging

- **Goal:** versioned executable/installer, asset licenses, clean-machine startup và rollback.
- **Acceptance:** install/run/uninstall on clean Windows VM; package hash/SBOM.

## Phase 12 — Final evaluation/demo/report

- **Goal:** freeze release candidate, results, limitations, demo and recovery plan.
- **Acceptance:** Definition of Final trong tài liệu 20 đạt; mọi pending item ghi rõ, không đổi thành pass.
