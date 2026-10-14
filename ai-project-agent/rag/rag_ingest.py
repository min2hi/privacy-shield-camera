"""
rag_ingest.py — RAG Knowledge Ingestion
Đọc toàn bộ tài liệu và codebase của dự án,
chunk ra và lưu vector embeddings vào PostgreSQL (pgvector).

Chạy script này mỗi khi có tài liệu mới hoặc code thay đổi lớn.
"""
import hashlib
import os
import sys
from collections.abc import Generator
from pathlib import Path

import psycopg2
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rich.console import Console
from rich.progress import track

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    AGENT_WORKSPACE_PATH,
    DATABASE_URL,
    LITELLM_MASTER_KEY,
    LITELLM_URL,
    RAG_CHUNK_OVERLAP,
    RAG_CHUNK_SIZE,
)

console = Console()

# ──────────────────────────────────────────────────────────
# Cấu hình loại file được đọc và xử lý
# ──────────────────────────────────────────────────────────
INGEST_TARGETS = {
    "docs": {
        "path": AGENT_WORKSPACE_PATH / "docs",
        "extensions": [".md", ".txt", ".pdf"],
        "doc_type": "docs",
    },
    "architecture": {
        "path": AGENT_WORKSPACE_PATH,
        "extensions": [".md"],
        "patterns": ["ARCHITECTURE*", "README*"],
        "doc_type": "architecture",
    },
    "code": {
        "path": AGENT_WORKSPACE_PATH / "privacy-shield-app",
        "extensions": [".py"],
        "doc_type": "code",
        "exclude_patterns": ["__pycache__", ".pyc", "venv", ".venv"],
    },
    "agent_code": {
        "path": AGENT_WORKSPACE_PATH / "ai-project-agent",
        "extensions": [".py"],
        "doc_type": "code",
        "exclude_patterns": ["__pycache__", "venv"],
    },
}

# ──────────────────────────────────────────────────────────
# File Scanner
# ──────────────────────────────────────────────────────────
def scan_files(config: dict) -> Generator[Path, None, None]:
    """Quét và trả về danh sách file hợp lệ, tự động bỏ qua môi trường ảo và thư mục hệ thống."""
    base_path: Path = config["path"]
    extensions: list = config["extensions"]
    exclude: list = config.get("exclude_patterns", []) + [".venv", "venv", "__pycache__", ".git", "node_modules", ".gemini", "dist", "build"]
    patterns: list = config.get("patterns", [])

    if not base_path.exists():
        console.print(f"[yellow]⚠ Bỏ qua (thư mục chưa tồn tại): {base_path}[/yellow]")
        return

    for file_path in base_path.rglob("*"):
        # Bỏ qua các thư mục bị loại trừ
        if any(excl in file_path.parts or excl in str(file_path) for excl in exclude):
            continue
        # Chỉ lấy file có extension phù hợp
        if file_path.suffix.lower() not in extensions:
            continue
        # Nếu có pattern thì phải match ít nhất 1 pattern
        if patterns:
            import fnmatch
            if not any(fnmatch.fnmatch(file_path.name, pat) for pat in patterns):
                continue
        yield file_path


def read_file_content(file_path: Path) -> str | None:
    """Đọc nội dung file, trả về None nếu lỗi."""
    try:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        console.print(f"[red]Lỗi đọc file {file_path}: {e}[/red]")
        return None


def get_file_hash(content: str) -> str:
    """Tạo hash của nội dung file để kiểm tra thay đổi."""
    return hashlib.md5(content.encode()).hexdigest()


# ──────────────────────────────────────────────────────────
# Embedding & Database
# ──────────────────────────────────────────────────────────
def get_embeddings_client() -> tuple[object, int]:
    """
    Khởi tạo embedding client.
    Nếu có OpenAI API key thật thì dùng Cloud (1536 dim), ngược lại dùng sentence-transformers local (384 dim).
    Returns: (client, dimension)
    """
    # Đọc OpenAI key từ file .env trực tiếp hoặc env var
    openai_key = os.getenv("OPENAI_API_KEY", "")
    is_placeholder = (
        not openai_key or
        "your_openai_key" in openai_key or
        "change_me" in openai_key or
        openai_key.startswith("sk-proj-your")
    )
    if not is_placeholder:
        console.print("[green]☁ Dùng OpenAI Cloud Embeddings (text-embedding-3-small, 1536 dim)[/green]")
        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_base=f"{LITELLM_URL}/v1",
            openai_api_key=LITELLM_MASTER_KEY,
            dimensions=1536,
        ), 1536

    # Fallback to local HuggingFace sentence-transformers
    console.print("[yellow]💻 Dùng Sentence-Transformers Local (all-MiniLM-L6-v2, 384 dim)[/yellow]")
    from langchain_community.embeddings import HuggingFaceEmbeddings
    # Dùng model nhẹ, tải nhanh và tốn ít RAM
    client = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return client, 384


def get_db_connection():
    """Kết nối PostgreSQL."""
    return psycopg2.connect(DATABASE_URL)


def ensure_matching_table_dimension(conn, target_dim: int) -> None:
    """Kiểm tra và tự động điều chỉnh chiều vector cột embedding trong DB để khớp với model."""
    with conn.cursor() as cur:
        # Kiểm tra bảng đã tồn tại chưa
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'rag_chunks'
            );
        """)
        exists = cur.fetchone()[0]

        if exists:
            # Kiểm tra chiều vector hiện tại
            cur.execute("""
                SELECT atttypmod 
                FROM pg_attribute 
                WHERE attrelid = 'rag_chunks'::regclass 
                  AND attname = 'embedding';
            """)
            row = cur.fetchone()
            current_dim = row[0] if row else -1
            
            # Nếu chiều vector không khớp, drop bảng để re-create
            if current_dim != target_dim:
                console.print(f"[red]⚠ Phát hiện chiều vector hiện tại trong DB ({current_dim}) khác với chiều vector của model ({target_dim}). Đang re-create bảng...[/red]")
                cur.execute("DROP TABLE IF EXISTS rag_chunks CASCADE;")
                exists = False

        # Tạo bảng nếu chưa tồn tại
        if not exists:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    document_id     VARCHAR(200) NOT NULL,
                    document_type   VARCHAR(50) NOT NULL,
                    chunk_index     INTEGER NOT NULL,
                    content         TEXT NOT NULL,
                    embedding       vector({target_dim}),
                    metadata        JSONB DEFAULT '{{}}',
                    created_at      TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(document_id, chunk_index)
                );
                
                CREATE INDEX IF NOT EXISTS rag_chunks_embedding_idx
                    ON rag_chunks USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64);
                
                CREATE INDEX IF NOT EXISTS rag_chunks_doc_type_idx ON rag_chunks(document_type);
                CREATE INDEX IF NOT EXISTS rag_chunks_doc_id_idx ON rag_chunks(document_id);
            """)
    conn.commit()


def upsert_chunks(conn, chunks: list[dict]) -> int:
    """Insert hoặc update chunks vào database. Trả về số chunk đã xử lý."""
    if not chunks:
        return 0

    with conn.cursor() as cur:
        for chunk in chunks:
            # Vector phải được format đúng cho pgvector
            embedding_str = "[" + ",".join(map(str, chunk["embedding"])) + "]"
            cur.execute("""
                INSERT INTO rag_chunks
                    (document_id, document_type, chunk_index, content, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s::vector, %s::jsonb)
                ON CONFLICT (document_id, chunk_index)
                DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata,
                    created_at = NOW()
            """, (
                chunk["document_id"],
                chunk["doc_type"],
                chunk["chunk_index"],
                chunk["content"],
                embedding_str,
                __import__("json").dumps(chunk["metadata"]),
            ))
    conn.commit()
    return len(chunks)



# ──────────────────────────────────────────────────────────
# Main Ingestion Pipeline
# ──────────────────────────────────────────────────────────
def ingest_all() -> None:
    """Chạy toàn bộ pipeline ingestion."""
    console.print("\n[bold cyan]🚀 Bắt đầu RAG Ingestion Pipeline[/bold cyan]")
    console.print(f"Workspace: {AGENT_WORKSPACE_PATH}\n")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=RAG_CHUNK_SIZE,
        chunk_overlap=RAG_CHUNK_OVERLAP,
        length_function=len,
    )

    embeddings_client, dimension = get_embeddings_client()
    conn = get_db_connection()
    ensure_matching_table_dimension(conn, dimension)
    total_chunks = 0

    for target_name, config in INGEST_TARGETS.items():
        files = list(scan_files(config))
        if not files:
            console.print(f"[dim]  {target_name}: Không có file nào[/dim]")
            continue

        console.print(f"[green]📁 {target_name}:[/green] {len(files)} files")

        for file_path in track(files, description=f"  Xử lý {target_name}..."):
            content = read_file_content(file_path)
            if not content or len(content.strip()) < 50:
                continue  # Bỏ qua file rỗng hoặc quá ngắn

            # Tạo document_id từ đường dẫn tương đối
            rel_path = str(file_path.relative_to(AGENT_WORKSPACE_PATH))
            doc_id = rel_path.replace("\\", "/")

            # Chunk nội dung
            text_chunks = splitter.split_text(content)
            if not text_chunks:
                continue

            # Tạo embeddings theo batch (tiết kiệm API calls)
            try:
                embeddings = embeddings_client.embed_documents(text_chunks)
            except Exception as e:
                console.print(f"[red]    Lỗi embedding {doc_id}: {e}[/red]")
                continue

            # Chuẩn bị data để insert
            chunks_to_insert = []
            for i, (chunk_text, embedding) in enumerate(
                zip(text_chunks, embeddings, strict=True)
            ):
                chunks_to_insert.append({
                    "document_id": doc_id,
                    "doc_type": config["doc_type"],
                    "chunk_index": i,
                    "content": chunk_text,
                    "embedding": embedding,
                    "metadata": {
                        "filename": file_path.name,
                        "file_path": doc_id,
                        "file_extension": file_path.suffix,
                        "doc_type": config["doc_type"],
                        "chunk_count": len(text_chunks),
                    }
                })

            inserted = upsert_chunks(conn, chunks_to_insert)
            total_chunks += inserted

    conn.close()
    console.print(f"\n[bold green]✅ Hoàn thành! Tổng chunks đã nhúng: {total_chunks}[/bold green]")


if __name__ == "__main__":
    ingest_all()
