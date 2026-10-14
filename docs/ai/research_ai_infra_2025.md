# Nghiên Cứu Hạ Tầng AI Agent — Lựa Chọn GitHub Repository Tốt Nhất (2025–2026)

**Mục tiêu**: Tìm các công cụ mã nguồn mở, phổ biến nhất trên GitHub để xây dựng hạ tầng AI Agent 7 cột mốc cho dự án **Privacy Shield** — cung cấp đủ ngữ cảnh, bộ nhớ, khả năng kiểm soát và giám sát để AI nắm rõ toàn bộ đồ án.

---

## 1. ORCHESTRATION — Điều phối

### ✅ Lựa chọn: `langchain-ai/langgraph`

**GitHub**: https://github.com/langchain-ai/langgraph  
**Stars**: ~11k+ ⭐ (growing fast, mid-2026)

**Tại sao LangGraph thắng tất cả?**

| Đối thủ | Lý do loại |
| :--- | :--- |
| **CrewAI** | Dễ demo nhanh, nhưng state management yếu, khó debug khi luồng phức tạp |
| **AutoGen** | Phù hợp nghiên cứu multi-agent, cấu trúc "chat-based" khó kiểm soát flow |
| **LangChain** | Chạy tuyến tính, không có vòng lặp, không quản lý state tốt |
| **PydanticAI** | Mới, type-safe tốt nhưng ecosystem còn non trẻ |

**LangGraph nổi bật vì**:
- **Nodes làm việc, Edges điều hướng** — kiến trúc Đồ thị (State Graph) cho phép Agent lập kế hoạch → thực thi → kiểm tra lỗi → tự sửa (Self-reflection loop).
- Hỗ trợ **Human-in-the-loop (HITL)**: dừng và hỏi ý kiến người dùng trước khi ghi/xóa file trong dự án.
- **Persistent state** với checkpoint backend (Redis hoặc PostgreSQL) — agent không bị "quên" khi restart.
- Tích hợp sâu nhất với LangSmith/Langfuse để debug time-travel (xem lại từng bước quyết định).

**Cách dùng cho dự án này**:
```python
# Agent nhận câu hỏi: "Tối ưu detector.py để đạt 30 FPS"
# LangGraph Graph Flow:
# START → RAG_search → plan_steps → ask_permission → edit_code → run_tests → END
```

---

## 2. CONTEXT & MEMORY — Ngữ cảnh & Bộ nhớ

### ✅ Lựa chọn: `mem0ai/mem0` + `pgvector/pgvector`

**Mem0 GitHub**: https://github.com/mem0ai/mem0  
**Stars**: ~28k+ ⭐

**So sánh 3 giải pháp Memory hàng đầu**:

| Framework | Triết lý | Khi nào dùng |
| :--- | :--- | :--- |
| **Mem0** ✅ | Memory Layer bổ sung | Tích hợp nhanh vào LangGraph hiện có, tự động trích xuất facts từ hội thoại |
| **Letta (MemGPT)** | Agent Runtime đầy đủ | Muốn Agent tự quản lý bộ nhớ như một "hệ điều hành". Phức tạp hơn. |
| **Zep** | Knowledge Graph temporal | Khi cần track "sự kiện thay đổi theo thời gian" (VD: user đổi stack, thay đổi quyết định thiết kế) |

**Lựa chọn cho dự án Privacy Shield**:
- **Mem0** làm **Long-term Memory layer**: Tự động nhớ các quyết định thiết kế (VD: "Dùng PySide6 thay vì Tkinter", "YOLOv8n ưu tiên Recall > Precision"), sở thích cấu hình model.
- **pgvector** (extension của PostgreSQL) làm **Semantic Memory/RAG Store**: Lưu trữ toàn bộ docs dự án, codebase được vector hóa để Agent có thể tìm kiếm ngữ nghĩa.

**Phân tầng bộ nhớ cuối cùng**:
```
Bộ nhớ ngắn hạn (Short-term)  → Redis (LangGraph Checkpointer)
Bộ nhớ dài hạn (Long-term)    → Mem0 → PostgreSQL (facts/decisions)
Tri thức ngoài (RAG)           → pgvector (docs, code embeddings)
```

---

## 3. AGENTOPS — Vận hành & Giám sát

### ✅ Lựa chọn: `langfuse/langfuse`

**GitHub**: https://github.com/langfuse/langfuse  
**Stars**: ~10k+ ⭐  
**License**: MIT (hoàn toàn mã nguồn mở, self-hosted miễn phí)

**So sánh 3 nền tảng AgentOps**:

| Nền tảng | Open Source | Self-host | Phù hợp dự án |
| :--- | :--- | :--- | :--- |
| **Langfuse** ✅ | Có (MIT) | Đầy đủ (Docker) | **Tốt nhất** — Không phụ thuộc cloud, chạy local hoàn toàn |
| **LangSmith** | Không (Proprietary) | Chỉ Enterprise trả phí | Không phù hợp — tốn tiền, data lên server bên ngoài |
| **Arize Phoenix** | Có (Elastic 2.0) | Có | Tốt, nhưng phức tạp hơn Langfuse |

**Langfuse cung cấp**:
- Dashboard theo dõi từng **trace** của LLM: xem Agent đã nghĩ gì, gọi tool nào, mất bao lâu.
- Đo **chi phí token** và **độ trễ** của từng node.
- **Prompt management** — quản lý version của system prompt.
- **Evaluation** tích hợp — chạy bộ test case ngay trong dashboard.
- Cài đặt qua **Docker Compose** — 1 lệnh dựng xong, không cần cấu hình phức tạp.

---

## 4. GOVERNANCE — Quản trị

### ✅ Lựa chọn: `BerriAI/litellm`

**GitHub**: https://github.com/BerriAI/litellm  
**Stars**: ~20k+ ⭐

**LiteLLM đóng vai trò "LLM Gateway" trung tâm**:

```
AI Agent Code
      │  (Gọi API theo chuẩn OpenAI)
      ▼
[LiteLLM Proxy Gateway]
      │
      ├─── OpenAI GPT-4o
      ├─── Google Gemini 2.0
      ├─── Anthropic Claude
      └─── Ollama (local, miễn phí hoàn toàn)
```

**Tính năng Governance cốt lõi**:
- **Budget Caps**: Giới hạn chi tiêu tối đa theo ngày/tuần cho từng "Virtual API Key" riêng biệt.
- **Rate Limiting**: Kiểm soát RPM (Request Per Minute) và TPM (Token Per Minute) để tránh API bị tràn.
- **Audit Log**: Ghi lại mọi request với timestamp, model, token count và chi phí.
- **Multi-provider routing**: Nếu OpenAI lỗi, tự động chuyển sang Gemini mà không cần sửa code.

**Lợi ích thực tế cho đồ án**: Khi đang phát triển, bạn có thể dùng Ollama (chạy model local miễn phí) để tiết kiệm chi phí. Khi cần demo chất lượng cao, chỉ cần đổi 1 dòng config để chuyển sang GPT-4o hoặc Gemini.

---

## 5. SECURITY — Bảo mật

### ✅ Lựa chọn: `NVIDIA/NeMo-Guardrails` + Custom Permission Layer

**GitHub**: https://github.com/NVIDIA/NeMo-Guardrails  
**Stars**: ~4.5k+ ⭐

**So sánh 2 giải pháp Security**:

| Công cụ | Tính chất | Phù hợp cho |
| :--- | :--- | :--- |
| **NeMo Guardrails** ✅ | Framework điều phối + kiểm soát luồng | Định nghĩa "Agent được phép làm gì" và "không được làm gì" |
| **Llama Guard** | Mô hình phân loại nội dung | Lọc content độc hại trong input/output |

**Kiến trúc Security cho dự án Privacy Shield Agent**:
```
User Input
    │
    ▼
[NeMo Guardrails] ──> Kiểm tra: có Prompt Injection không?
    │                           Có yêu cầu đọc .env/secrets không?
    │                           Có yêu cầu xóa file ngoài workspace không?
    ▼
[Permission Layer (Custom)] ──> Bảng whitelist tool & file path
    │
    ▼
[Agent thực thi]
```

**Quan trọng nhất cho dự án này**: Vì Agent có khả năng đọc/ghi file trong codebase, cần một **Permission Layer tùy chỉnh** (viết bằng Python thuần) theo bảng sau:

| Tool | Quyền | Chi tiết |
| :--- | :--- | :--- |
| `read_file` | Cho phép | Chỉ trong workspace dự án |
| `write_file` | Cần xác nhận | Phải hỏi user trước khi ghi |
| `delete_file` | Bị chặn | Cấm hoàn toàn |
| `run_command` | Whitelist | Chỉ: `pytest`, `ruff`, `python` scripts đã duyệt |
| `read .env` | Bị chặn | Không bao giờ đọc secrets |
| `git_commit` | Cần xác nhận | Không tự commit |

---

## 6. EVALUATION — Đánh giá

### ✅ Lựa chọn: `confident-ai/deepeval` + `explodinggradients/ragas`

**DeepEval GitHub**: https://github.com/confident-ai/deepeval  
**Stars**: ~6k+ ⭐

**Ragas GitHub**: https://github.com/explodinggradients/ragas  
**Stars**: ~8k+ ⭐

**Kết hợp 2 công cụ, mỗi cái một vai trò**:

| Công cụ | Vai trò | Phù hợp với |
| :--- | :--- | :--- |
| **DeepEval** | Unit Testing cho Agent (CI/CD) | Test Agent có trả lời đúng requirement không? |
| **Ragas** | Đánh giá chất lượng RAG | Tài liệu được retrieve có đúng, đủ không? |

**Cách sử dụng thực tế**:
```python
# DeepEval: kiểm thử tự động
def test_agent_understands_yolo():
    output = agent.run("YOLOv8n phù hợp với máy không GPU không?")
    assert_metric(output, AnswerRelevancyMetric(threshold=0.7))

# Ragas: đánh giá RAG
ragas.evaluate(
    dataset=test_questions_about_architecture,
    metrics=[faithfulness, answer_relevancy, context_recall]
)
```

---

## 7. TOOLS — Công cụ hành động

### ✅ Lựa chọn: Custom Python Tools + MCP Protocol

Không cần framework lớn cho phần này. Tools của Agent cho dự án này là các hàm Python đơn giản được đăng ký với LangGraph:

| Tool | Chức năng | File |
| :--- | :--- | :--- |
| `read_file_tool` | Đọc nội dung file trong workspace | `file_tools.py` |
| `search_code_tool` | Tìm kiếm hàm/class trong codebase | `code_tools.py` |
| `run_pytest_tool` | Chạy pytest và trả về kết quả | `test_tools.py` |
| `rag_search_tool` | Tìm kiếm tài liệu bằng vector similarity | `rag_tools.py` |
| `write_decision_tool` | Ghi quyết định thiết kế vào long-term memory | `memory_tools.py` |

---

## 8. Bảng Tổng Kết Lựa Chọn Cuối Cùng

| Cột mốc | Công cụ chọn | Repo GitHub | Lý do ngắn gọn |
| :--- | :--- | :--- | :--- |
| **Orchestration** | LangGraph | `langchain-ai/langgraph` | State graph + self-reflection + HITL |
| **Short-term Memory** | Redis | `redis/redis` | Checkpoint LangGraph state, siêu nhanh |
| **Long-term Memory** | Mem0 | `mem0ai/mem0` | Tự động trích xuất facts từ hội thoại |
| **RAG Knowledge** | pgvector | `pgvector/pgvector` | Lưu vector trong PostgreSQL, chạy offline |
| **AgentOps** | Langfuse | `langfuse/langfuse` | MIT, self-hosted, dashboard đẹp, dễ dùng |
| **Governance** | LiteLLM | `BerriAI/litellm` | Gateway cho mọi LLM, budget/rate limit |
| **Security** | NeMo Guardrails + Custom | `NVIDIA/NeMo-Guardrails` | Kiểm soát luồng + Permission layer |
| **Evaluation** | DeepEval + Ragas | `confident-ai/deepeval` / `explodinggradients/ragas` | CI testing + RAG quality metrics |
| **Infra Runtime** | Docker Compose | — | Orchestrate tất cả services |

---

## 9. Cấu Hình Docker Compose Mục Tiêu

Toàn bộ Lớp C (AI Project Agent) sẽ chạy trong Docker:

```yaml
# infra/docker-compose.yml
services:
  postgres:      # PostgreSQL + pgvector extension
  redis:         # LangGraph Checkpoint + Mem0 cache  
  langfuse:      # AgentOps dashboard (self-hosted)
  langfuse-worker: # Background job worker của Langfuse
  litellm:       # LLM Gateway (route to Ollama/OpenAI/Gemini)
  ollama:        # LLM local (chạy hoàn toàn offline, miễn phí)
```

**Chi phí**: $0 khi dùng Ollama local. Chỉ tốn tiền khi gọi API OpenAI/Gemini.

---

## 10. Thứ Tự Cài Đặt Đề Xuất

```
Bước 1: Docker Compose UP
         └── PostgreSQL + pgvector
         └── Redis
         └── Langfuse + Worker
         └── LiteLLM Gateway
         └── Ollama (pull model local)

Bước 2: Ingest tài liệu vào RAG
         └── Đọc docs/ + codebase → chunk → embed → lưu pgvector

Bước 3: Setup Mem0 kết nối PostgreSQL
         └── Cấu hình extraction pipeline

Bước 4: Viết LangGraph Agent + Tools

Bước 5: Kết nối Langfuse trace
         └── Mọi LLM call tự động được log
```
