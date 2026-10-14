"""
config.py — Cấu hình tập trung cho toàn bộ AI Project Agent
Đọc từ .env file hoặc biến môi trường.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # Core security/config tests do not require the full agent stack.
    def load_dotenv(*args, **kwargs):
        return False

# Load .env từ thư mục infra
_env_path = Path(__file__).parent.parent / "infra" / ".env"
load_dotenv(_env_path)

# ──────────────────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://agent_user:changeme@localhost:5432/privacy_shield_agent"
)

# ──────────────────────────────────────────────────────────
# Redis
# ──────────────────────────────────────────────────────────
REDIS_URL: str = os.getenv(
    "REDIS_URL",
    "redis://:changeme@localhost:6379"
)

# ──────────────────────────────────────────────────────────
# LiteLLM Gateway (Governance)
# ──────────────────────────────────────────────────────────
LITELLM_URL: str = os.getenv("LITELLM_URL", "http://localhost:4000")
LITELLM_MASTER_KEY: str = os.getenv("LITELLM_MASTER_KEY", "sk-litellm-changeme")

# Model mặc định khi phát triển (dùng Ollama local, miễn phí)
DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "local/llama3.2")

# Model cho embedding (tạo vector cho RAG — mặc định dùng local 384 chiều)
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))

# ──────────────────────────────────────────────────────────
# Langfuse (AgentOps)
# ──────────────────────────────────────────────────────────
LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY_APP", "")
LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

# ──────────────────────────────────────────────────────────
# Workspace Security (Permission Layer)
# ──────────────────────────────────────────────────────────
AGENT_WORKSPACE_PATH: Path = Path(
    os.getenv("AGENT_WORKSPACE_PATH", str(Path(__file__).parent.parent))
).resolve()

# Danh sách lệnh được phép chạy (whitelist)
ALLOWED_COMMANDS: list[str] = ["pytest", "ruff", "python", "pip"]

# ──────────────────────────────────────────────────────────
# RAG Settings
# ──────────────────────────────────────────────────────────
RAG_CHUNK_SIZE: int = 800        # Số token mỗi chunk
RAG_CHUNK_OVERLAP: int = 150     # Overlap giữa các chunk
RAG_TOP_K: int = 5               # Số chunk trả về khi search

# ──────────────────────────────────────────────────────────
# Temporal Smoothing (cho bộ nhớ ngắn hạn Agent)
# ──────────────────────────────────────────────────────────
SESSION_TTL_SECONDS: int = 3600  # Session hết hạn sau 1 giờ không dùng

# ──────────────────────────────────────────────────────────
# Privacy Policy (Tuân thủ No Raw Frame Policy)
# ──────────────────────────────────────────────────────────
LOG_METADATA_ONLY: bool = True    # Chỉ log metadata, không log nội dung nhạy cảm
SAVE_RAW_FRAMES: bool = False     # Không bao giờ lưu ảnh webcam thô


def validate_config() -> None:
    """Kiểm tra cấu hình bắt buộc trước khi chạy Agent."""
    errors = []
    
    if "changeme" in DATABASE_URL:
        errors.append("DATABASE_URL chưa được cấu hình (vẫn dùng password mặc định)")
    
    if not AGENT_WORKSPACE_PATH.exists():
        errors.append(f"AGENT_WORKSPACE_PATH không tồn tại: {AGENT_WORKSPACE_PATH}")
    
    if errors:
        from rich.console import Console
        console = Console()
        console.print("[bold red]⚠ Lỗi cấu hình:[/bold red]")
        for err in errors:
            console.print(f"  [red]• {err}[/red]")
        console.print("\n[yellow]Hãy copy infra/.env.example thành infra/.env và điền thông tin.[/yellow]")


if __name__ == "__main__":
    validate_config()
    print(f"✓ Workspace: {AGENT_WORKSPACE_PATH}")
    print(f"✓ Default model: {DEFAULT_MODEL}")
    print(f"✓ Langfuse: {LANGFUSE_HOST}")
