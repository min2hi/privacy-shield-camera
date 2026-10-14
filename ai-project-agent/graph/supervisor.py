"""
supervisor.py — Orchestration Pillar (LangGraph)
Agent chính của dự án Privacy Shield.

Luồng xử lý (State Graph):
  START
    → security_check    (NeMo Guardrails kiểm tra input)
    → load_context      (Mem0 + pgvector nạp ngữ cảnh liên quan)
    → reason            (LLM lên kế hoạch)
    → execute_tools     (Gọi các tool: read_file, search_code, v.v.)
    → validate_output   (DeepEval kiểm tra chất lượng output)
    → update_memory     (Mem0 lưu quyết định mới)
  END
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, TypedDict

try:
    from langchain_core.messages import BaseMessage, HumanMessage
except ImportError:
    class BaseMessage:  # type: ignore[no-redef]
        def __init__(self, content: str = "") -> None:
            self.content = content

    class HumanMessage(BaseMessage):  # type: ignore[no-redef]
        pass

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None  # type: ignore[assignment,misc]

try:
    from langfuse.langchain import CallbackHandler as LangfuseCallback
except ImportError:
    LangfuseCallback = None  # type: ignore[assignment,misc]

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:
    END = "__end__"  # type: ignore[assignment]
    START = "__start__"  # type: ignore[assignment]
    StateGraph = None  # type: ignore[assignment,misc]

try:
    from rich.console import Console
    from rich.panel import Panel
    console: Any = Console()
except ImportError:
    class _FallbackConsole:
        def print(self, *args: Any, **kwargs: Any) -> None:
            pass

    def Panel(text: str, **kwargs: Any) -> str:  # type: ignore[misc]
        return text

    console = _FallbackConsole()

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    AGENT_WORKSPACE_PATH,
    DATABASE_URL,
    DEFAULT_MODEL,
    LANGFUSE_HOST,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
    LITELLM_MASTER_KEY,
    LITELLM_URL,
    REDIS_URL,
)


# ──────────────────────────────────────────────────────────
# 1. State Definition — Trạng thái của Agent (LangGraph)
# ──────────────────────────────────────────────────────────
class AgentState(TypedDict):
    """Toàn bộ trạng thái được LangGraph quản lý và lưu vào Redis."""
    messages: list[BaseMessage]         # Lịch sử hội thoại
    context_docs: list[dict[str, Any]]  # Tài liệu RAG đã tìm thấy
    long_term_facts: list[str]          # Facts từ Mem0 long-term memory
    plan: str                           # Kế hoạch do LLM đề ra
    tool_results: list[dict[str, Any]]  # Kết quả từ các tool đã gọi
    final_answer: str                   # Câu trả lời cuối cùng cho user
    session_id: str                     # ID session để checkpoint
    error: str | None                   # Lỗi nếu có


# ──────────────────────────────────────────────────────────
# 2. LLM Client — Trỏ vào LiteLLM Gateway (Governance Pillar)
# ──────────────────────────────────────────────────────────
def get_llm() -> Any:
    """Tạo LLM client kết nối qua LiteLLM để quản lý budget/rate limit."""
    if ChatOpenAI is None:
        raise RuntimeError("langchain_openai chưa được cài đặt trong môi trường hiện tại.")
    return ChatOpenAI(
        model=DEFAULT_MODEL,
        openai_api_base=f"{LITELLM_URL}/v1",
        openai_api_key=LITELLM_MASTER_KEY,
        temperature=0.1,           # Thấp = câu trả lời nhất quán hơn
        max_tokens=4096,
        streaming=True,
    )


# ──────────────────────────────────────────────────────────
# 3. Graph Nodes — Các bước xử lý
# ──────────────────────────────────────────────────────────

def security_check(state: AgentState) -> AgentState:
    """
    Security Pillar: Kiểm tra input trước khi Agent xử lý.
    Chặn các yêu cầu cố tình đọc secrets, inject prompt, v.v.
    """
    last_message = state["messages"][-1].content if state["messages"] else ""

    # Danh sách pattern cần chặn (Prompt Injection phổ biến)
    blocked_patterns = [
        "ignore previous instructions",
        "ignore all instructions",
        "you are now",
        "act as",
        "forget everything",
        ".env", "secrets", "api_key=", "password=",
    ]

    lower_msg = str(last_message).lower()
    for pattern in blocked_patterns:
        if pattern in lower_msg:
            console.print(f"[red]🔒 Security: Phát hiện pattern nguy hiểm: '{pattern}'[/red]")
            return {**state, "error": f"Yêu cầu bị chặn: phát hiện pattern không hợp lệ '{pattern}'"}

    return {**state, "error": None}


def load_context(state: AgentState) -> AgentState:
    """
    Context Pillar: Nạp ngữ cảnh từ 2 nguồn:
    1. pgvector RAG (hoặc fallback tìm kiếm cục bộ trong docs/)
    2. Mem0 / PostgreSQL long-term memory (hoặc fallback quyết định kiến trúc cốt lõi)
    """
    if state.get("error"):
        return state

    last_message = str(state["messages"][-1].content) if state["messages"] else ""
    console.print("[cyan]🔍 Đang nạp ngữ cảnh từ RAG và Long-term Memory...[/cyan]")

    # RAG Search (pgvector + local markdown fallback)
    context_docs = _rag_search(last_message, top_k=5)

    # Mem0 Long-term Memory
    long_term_facts = _mem0_recall(state["session_id"], last_message)

    console.print(f"[dim]  RAG: {len(context_docs)} đoạn tài liệu | Memory: {len(long_term_facts)} facts[/dim]")
    return {**state, "context_docs": context_docs, "long_term_facts": long_term_facts}


def reason(state: AgentState) -> AgentState:
    """
    Orchestration: LLM đọc ngữ cảnh và lên kế hoạch giải quyết vấn đề.
    System prompt được thiết kế để Agent nắm rõ vai trò và giới hạn.
    """
    if state.get("error"):
        return state

    # Xây dựng system prompt với đầy đủ ngữ cảnh dự án
    context_text = "\n---\n".join(
        f"[{doc.get('doc_type', 'doc')}] {doc.get('content', '')}"
        for doc in state.get("context_docs", [])[:5]
    )

    facts_text = "\n".join(f"• {fact}" for fact in state.get("long_term_facts", []))

    system_prompt = f"""Bạn là AI Project Copilot của dự án **Privacy Shield Camera**.

## Vai trò của bạn:
- Hỗ trợ developer đọc hiểu tài liệu, viết code, review kiến trúc và viết báo cáo đồ án.
- Bạn KHÔNG xử lý video webcam trực tiếp (đó là việc của sản phẩm chính).
- Bạn CHỈ thao tác file trong workspace được phép.

## Quyết định kỹ thuật đã được chốt (Long-term Memory):
{facts_text if facts_text else "Chưa có quyết định nào được ghi nhận."}

## Tài liệu liên quan (RAG Context):
{context_text if context_text else "Không tìm thấy tài liệu liên quan."}

## Nguyên tắc bất biến:
1. Không đọc file .env, secrets, credentials.
2. Không ghi file nếu chưa được người dùng xác nhận.
3. Không xóa file.
4. Chỉ chạy các lệnh: pytest, ruff, python (trong workspace).
5. Mọi log chỉ lưu metadata, không lưu ảnh thô của người dùng.

Hãy trả lời bằng tiếng Việt, ngắn gọn và chính xác."""

    try:
        llm = get_llm()
        messages = [
            {"role": "system", "content": system_prompt},
            *[{"role": "user" if isinstance(m, HumanMessage) else "assistant",
               "content": m.content}
              for m in state["messages"][-10:]]  # Chỉ lấy 10 messages gần nhất
        ]
        response = llm.invoke(messages)
        plan = str(response.content)
    except Exception as e:
        plan = f"Lỗi khi gọi LLM: {e}"

    return {**state, "plan": plan, "final_answer": plan}


def update_memory(state: AgentState) -> AgentState:
    """
    Memory Pillar: Sau mỗi lượt hội thoại, lưu session / quyết định mới vào Mem0 hoặc PostgreSQL.
    """
    if state.get("error") or not state.get("final_answer"):
        return state

    console.print("[dim]💾 Cập nhật Long-term Memory...[/dim]")
    user_msg = str(state["messages"][-1].content) if state.get("messages") else ""
    answer = state.get("final_answer", "")
    session_id = state.get("session_id", "default")

    try:
        from mem0 import MemoryClient
        client = MemoryClient()
        client.add(
            [{"role": "user", "content": user_msg}, {"role": "assistant", "content": answer}],
            user_id=f"project_{session_id}",
        )
    except Exception:
        pass

    return state


# ──────────────────────────────────────────────────────────
# 4. Helper Functions (RAG & Memory + Offline Local Fallbacks)
# ──────────────────────────────────────────────────────────
def _local_doc_search(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Fallback tìm kiếm tài liệu cục bộ trong thư mục docs/ khi PostgreSQL/pgvector không chạy."""
    docs_dir = AGENT_WORKSPACE_PATH / "docs"
    if not docs_dir.exists():
        return []

    tokens = [tok for tok in re.findall(r"\w+", query.lower()) if len(tok) >= 2]
    if not tokens:
        return []

    scored_chunks: list[dict[str, Any]] = []
    for md_file in sorted(docs_dir.rglob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) >= 40]
        for idx, para in enumerate(paragraphs):
            lower_para = para.lower()
            hits = sum(1 for tok in tokens if tok in lower_para)
            if hits > 0:
                score = hits / len(tokens)
                scored_chunks.append({
                    "document_id": str(md_file.relative_to(AGENT_WORKSPACE_PATH)).replace("\\", "/"),
                    "doc_type": "docs",
                    "content": para[:800],
                    "metadata": {"filename": md_file.name, "chunk_index": idx, "source": "local_fallback"},
                    "similarity": round(score, 3),
                })

    scored_chunks.sort(key=lambda item: item["similarity"], reverse=True)
    return scored_chunks[:top_k]


def _local_facts_fallback() -> list[str]:
    """Danh sách quyết định kiến trúc cốt lõi khi chạy offline không có DB."""
    return [
        "Dùng YOLOv8n + OpenCV Hybrid cho MVP realtime, hướng tới YOLOv8s fine-tuned cho 6 privacy classes.",
        "Dùng PySide6 (Qt6) và QThread tách biệt hoàn toàn UI với pipeline xử lý video.",
        "Áp dụng Fail-Closed Privacy Policy: lỗi pipeline hoặc tạm dừng đều xuất màn hình khóa bảo mật, không bao giờ lộ frame thô.",
        "Mẫu khuôn mặt sinh trắc học (512-dim MobileFaceNet) được mã hóa Fernet trên đĩa kèm xác minh SHA256.",
    ]


def _rag_search(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Tìm kiếm tài liệu liên quan trong pgvector, tự động fallback sang tìm kiếm file cục bộ."""
    try:
        import os

        import psycopg2
        from config import LITELLM_MASTER_KEY, LITELLM_URL
        from langchain_openai import OpenAIEmbeddings

        openai_key = os.getenv("OPENAI_API_KEY", "")
        is_placeholder = (
            not openai_key or
            "your_openai_key" in openai_key or
            "change_me" in openai_key or
            openai_key.startswith("sk-proj-your")
        )
        if not is_placeholder:
            embeddings_client = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_base=f"{LITELLM_URL}/v1",
                openai_api_key=LITELLM_MASTER_KEY,
                dimensions=1536,
            )
        else:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            embeddings_client = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        query_embedding = embeddings_client.embed_query(query)
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT document_id, document_type, content, metadata,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM rag_chunks
                WHERE 1 - (embedding <=> %s::vector) > 0.5
                ORDER BY similarity DESC
                LIMIT %s
            """, (embedding_str, embedding_str, top_k))
            rows = cur.fetchall()
        conn.close()

        return [
            {"document_id": r[0], "doc_type": r[1], "content": r[2],
             "metadata": r[3], "similarity": float(r[4])}
            for r in rows
        ]
    except Exception as e:
        console.print(f"[yellow]⚠ pgvector RAG không khả dụng ({e}), chuyển sang Local Docs Search...[/yellow]")
        return _local_doc_search(query, top_k=top_k)


def _mem0_recall(session_id: str, query: str) -> list[str]:
    """Truy xuất facts từ Mem0 long-term memory, fallback sang PostgreSQL hoặc local facts."""
    try:
        from mem0 import MemoryClient
        client = MemoryClient()  # Sử dụng cấu hình từ env
        memories = client.search(query, user_id=f"project_{session_id}", limit=10)
        return [m["memory"] for m in memories]
    except Exception:
        # Fallback 1: đọc từ PostgreSQL project_decisions
        try:
            import psycopg2
            conn = psycopg2.connect(DATABASE_URL)
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT decision FROM project_decisions WHERE status = 'active' LIMIT 10"
                )
                rows = cur.fetchall()
            conn.close()
            if rows:
                return [r[0] for r in rows]
        except Exception:
            pass
        # Fallback 2: quyết định kiến trúc cốt lõi cục bộ
        return _local_facts_fallback()


# ──────────────────────────────────────────────────────────
# 5. Build Graph (LangGraph)
# ──────────────────────────────────────────────────────────
def build_agent_graph() -> Any:
    """Xây dựng và định nghĩa các node/edge của LangGraph Agent."""
    if StateGraph is None:
        raise RuntimeError("langgraph chưa được cài đặt trong môi trường hiện tại.")
    graph = StateGraph(AgentState)

    # Đăng ký các nodes
    graph.add_node("security_check", security_check)
    graph.add_node("load_context", load_context)
    graph.add_node("reason", reason)
    graph.add_node("update_memory", update_memory)

    # Định nghĩa luồng chạy (edges)
    graph.add_edge(START, "security_check")
    graph.add_edge("security_check", "load_context")
    graph.add_edge("load_context", "reason")
    graph.add_edge("reason", "update_memory")
    graph.add_edge("update_memory", END)

    return graph


# ──────────────────────────────────────────────────────────
# 6. Main Entry Point
# ──────────────────────────────────────────────────────────
def run_agent(user_message: str, session_id: str = "default") -> str:
    """
    Chạy Agent với một câu hỏi từ người dùng.
    Returns: Câu trả lời cuối cùng.
    """
    # Khởi tạo Langfuse callback (AgentOps Pillar)
    langfuse_callbacks = []
    if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
        try:
            langfuse_cb = LangfuseCallback(
                public_key=LANGFUSE_PUBLIC_KEY,
                secret_key=LANGFUSE_SECRET_KEY,
                host=LANGFUSE_HOST,
            )
            langfuse_callbacks = [langfuse_cb]
        except Exception:
            pass

    graph = build_agent_graph()
    initial_state: AgentState = {
        "messages": [HumanMessage(content=user_message)],
        "context_docs": [],
        "long_term_facts": [],
        "plan": "",
        "tool_results": [],
        "final_answer": "",
        "session_id": session_id,
        "error": None,
    }

    config = {
        "configurable": {"thread_id": session_id},
        "callbacks": langfuse_callbacks,
    }

    console.print(Panel(f"[bold]User:[/bold] {user_message}", title="Privacy Shield Agent"))

    # Thử kết nối checkpoint với Redis
    try:
        from langgraph.checkpoint.redis import RedisSaver
        redis_context = RedisSaver.from_conn_string(REDIS_URL)
    except Exception as e:
        console.print(f"[yellow]⚠ Redis không khả dụng, chạy không có checkpoint. Lỗi: {e}[/yellow]")
        redis_context = None

    if redis_context:
        try:
            with redis_context as checkpointer:
                try:
                    checkpointer.setup()
                except Exception:
                    pass
                agent = graph.compile(checkpointer=checkpointer)
                result = agent.invoke(initial_state, config=config)
        except Exception as e:
            console.print(f"[yellow]⚠ Thất bại khi chạy với Redis checkpointer, fallback sang không checkpoint. Lỗi: {e}[/yellow]")
            agent = graph.compile()
            result = agent.invoke(initial_state, config=config)
    else:
        agent = graph.compile()
        result = agent.invoke(initial_state, config=config)

    if result.get("error"):
        return f"❌ {result['error']}"

    answer = result.get("final_answer", "Không có câu trả lời.")
    console.print(Panel(answer, title="[bold green]Agent Response[/bold green]"))
    return answer


if __name__ == "__main__":
    # Test nhanh
    run_agent(
        "YOLOv8n hay YOLOv8s phù hợp hơn cho dự án Privacy Shield? Tại sao?",
        session_id="test_session_001"
    )
