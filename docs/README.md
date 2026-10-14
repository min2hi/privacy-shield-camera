# Privacy Shield Camera — Bộ tài liệu dự án

Tài liệu là contract giữa ý tưởng, implementation và bằng chứng chạy thật. README/roadmap phải cập nhật cùng code; không dùng tài liệu để tuyên bố tính năng chưa có.

## Đọc theo nhu cầu

- Mới vào dự án: 01 → 02 → 05 → 16.
- Làm CV/model: 04 → 06 → 08 → 15 → 17.
- Làm UI/runtime: 03 → 06 → 07 → 09 → 13.
- Làm agent/infra: 10 → 11 → 12.
- Chuẩn bị release: 17 → 18 → 19 → 20.

## Mục lục

| Tài liệu | Nội dung |
|---|---|
| [01 — Project Overview](01_Project_Overview.md) | Mục tiêu, phạm vi, success criteria |
| [02 — Problem Definition](02_Problem_Definition.md) | Bài toán, đối tượng và trạng thái unsupported |
| [03 — Privacy Threat Model](03_Privacy_Threat_Model.md) | Tài sản, threat, fail-closed policy |
| [04 — Data & Model Strategy](04_Data_Model_Strategy.md) | Synthetic data, labels, provenance, evaluation |
| [05 — System Architecture](05_System_Architecture.md) | Product, training và agent boundaries |
| [06 — Runtime Pipeline](06_Runtime_Pipeline.md) | Frame flow, latency và failure states |
| [07 — Face Privacy](07_Face_Privacy.md) | Embedding, enrollment, consent và deletion |
| [08 — Model Training](08_Model_Training.md) | Dataset → train → bundle → promotion |
| [09 — Virtual Camera](09_Virtual_Camera.md) | Output contract và fail-closed behavior |
| [10 — Agent Infrastructure](10_Agent_Infrastructure.md) | RAG/LLM scope và trust boundary |
| [11 — Configuration](11_Configuration.md) | Schema, path, secrets và validation |
| [12 — Observability](12_Observability.md) | Metadata-only logs và evidence |
| [13 — UI Architecture](13_UI_Architecture.md) | QThread, state, accessibility, shutdown |
| [14 — Project Structure](14_Project_Structure.md) | Source-of-truth tree và generated artifacts |
| [15 — Module Specification](15_Module_Specification.md) | Interfaces và ownership |
| [16 — Development Roadmap](16_Development_Roadmap.md) | Phase 0–12 và acceptance |
| [17 — Testing Strategy](17_Testing_Strategy.md) | Test matrix và hardware acceptance |
| [18 — Release & Packaging](18_Release_Packaging.md) | Windows package, install và rollback |
| [19 — Risks & Limitations](19_Risks_and_Limitations.md) | Hạn chế phải công bố |
| [20 — Final Implementation Plan](20_Final_Implementation_Plan.md) | Checkpoint và Definition of Final |
| [CHANGELOG](CHANGELOG.md) | Lịch sử implementation/evidence |

Các tài liệu cũ trong `docs/architecture`, `docs/ai` và `docs/ui` là nguồn thiết kế ban đầu. Nếu mâu thuẫn, bộ 01–20 và code/test hiện tại là nguồn ưu tiên; quyết định phải được ghi vào changelog.
