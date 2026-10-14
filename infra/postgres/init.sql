-- ============================================================
-- PostgreSQL Initialization Script
-- Chạy tự động khi container khởi động lần đầu
-- ============================================================

-- 1. Kích hoạt pgvector extension (RAG vector search)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Kích hoạt uuid extension (tạo ID duy nhất)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- SCHEMA: Agent Long-term Memory (Mem0 compatible)
-- ============================================================

-- Bảng lưu các sự kiện / quyết định kỹ thuật của dự án
CREATE TABLE IF NOT EXISTS project_decisions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project     VARCHAR(100) NOT NULL DEFAULT 'privacy_shield',
    category    VARCHAR(50) NOT NULL,  -- 'tech_stack', 'architecture', 'data', 'security'
    decision    TEXT NOT NULL,
    rationale   TEXT,
    status      VARCHAR(20) DEFAULT 'active',  -- 'active', 'superseded', 'revoked'
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Bảng lưu cấu hình kỹ thuật dự án (structured facts)
CREATE TABLE IF NOT EXISTS project_config (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key         VARCHAR(100) UNIQUE NOT NULL,
    value       TEXT NOT NULL,
    description TEXT,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Bảng lưu lịch sử hội thoại / session của Agent
CREATE TABLE IF NOT EXISTS agent_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      VARCHAR(100) UNIQUE NOT NULL,
    user_message    TEXT,
    agent_response  TEXT,
    tools_called    JSONB DEFAULT '[]',
    token_used      INTEGER DEFAULT 0,
    latency_ms      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SCHEMA: RAG Vector Store (pgvector)
-- ============================================================

-- Bảng lưu chunks tài liệu đã được embedding (docs, codebase)
CREATE TABLE IF NOT EXISTS rag_chunks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     VARCHAR(200) NOT NULL,       -- đường dẫn file nguồn
    document_type   VARCHAR(50) NOT NULL,         -- 'docs', 'code', 'architecture'
    chunk_index     INTEGER NOT NULL,             -- thứ tự chunk trong file
    content         TEXT NOT NULL,               -- nội dung text thô
    embedding       vector(384),                 -- vector 384 chiều (all-MiniLM-L6-v2 local mặc định) hoặc 1536 (OpenAI)
    metadata        JSONB DEFAULT '{}',          -- {filename, language, last_modified}
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(document_id, chunk_index)
);

-- Index HNSW để tìm kiếm vector nhanh hơn (recommended cho pgvector)
CREATE INDEX IF NOT EXISTS rag_chunks_embedding_idx
    ON rag_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Index thường để lọc theo loại tài liệu
CREATE INDEX IF NOT EXISTS rag_chunks_doc_type_idx ON rag_chunks(document_type);
CREATE INDEX IF NOT EXISTS rag_chunks_doc_id_idx ON rag_chunks(document_id);

-- ============================================================
-- INITIAL DATA: Seed cấu hình dự án
-- ============================================================

INSERT INTO project_config (key, value, description) VALUES
    ('project_name',      'Privacy Shield Camera',           'Tên đầy đủ của đồ án'),
    ('primary_language',  'Python',                          'Ngôn ngữ lập trình chính'),
    ('cv_framework',      'OpenCV + Ultralytics YOLOv8',     'Thư viện thị giác máy tính'),
    ('gui_framework',     'PySide6 (Qt6)',                   'Framework giao diện Desktop'),
    ('virtual_cam',       'pyvirtualcam',                    'Thư viện xuất camera ảo'),
    ('model_priority',    'Recall > Precision',              'Chiến lược tối ưu model CV'),
    ('privacy_policy',    'No Raw Frame Policy',             'Không lưu/log frame thô'),
    ('masking_default',   'Mosaic (medium)',                 'Chế độ che mặc định'),
    ('target_fps',        '30',                              'Mục tiêu FPS tối thiểu'),
    ('agent_role',        'Project Copilot (Dev Assistant)', 'Vai trò của AI Agent trong dự án')
ON CONFLICT (key) DO NOTHING;

INSERT INTO project_decisions (category, decision, rationale, status) VALUES
    ('tech_stack',    'Dùng YOLOv8n cho phiên bản MVP, YOLOv8s cho bản hoàn chỉnh',      'YOLOv8n nhẹ hơn, đạt >25 FPS trên CPU không GPU. YOLOv8s chính xác hơn cho custom training.', 'active'),
    ('tech_stack',    'Dùng PySide6 thay vì Tkinter hoặc Electron',                        'PySide6 (Qt6) render OpenCV frame mượt hơn nhờ QImage, không gây memory leak khi stream liên tục.', 'active'),
    ('architecture',  'AI Agent KHÔNG nằm trong pipeline xử lý video realtime',           'Pipeline video cần <33ms/frame. Gọi LLM qua Agent sẽ gây lag 500ms-3s. Hai hệ thống phải tách biệt hoàn toàn.', 'active'),
    ('security',      'Áp dụng No Raw Frame Policy',                                       'App bảo vệ privacy thì chính nó phải privacy-first. Không lưu ảnh CCCD/thẻ ngân hàng thật.', 'active'),
    ('data',          'Dùng dữ liệu giả lập (synthetic) cho training dataset',             'Tránh rủi ro pháp lý khi xử lý thông tin cá nhân thật. Tuân thủ GDPR và Luật ATTTM Việt Nam.', 'active'),
    ('model',         'Ưu tiên tối ưu Recall > Precision',                                  'Bỏ sót CCCD/thẻ ngân hàng (False Negative) nguy hiểm hơn che nhầm vật thể bình thường (False Positive).', 'active'),
    ('infra',         'AI Agent dùng LangGraph + Mem0 + pgvector + Redis + Langfuse',     'Stack tốt nhất 2025-2026 cho stateful agent có memory và observability đầy đủ, chạy hoàn toàn offline.', 'active')
ON CONFLICT DO NOTHING;

-- ============================================================
-- Verify setup
-- ============================================================
SELECT 'pgvector extension: OK' AS status WHERE EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')
UNION ALL
SELECT 'Tables created: OK' AS status WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'rag_chunks');
