d:\StudioProjects\AI project\
├── ARCHITECTURE_OVERVIEW.md     # Tài liệu kiến trúc tổng quan
│
├── infra/                       # Hạ tầng Docker (AI Project Agent)
│   ├── .env.example             # ← Copy thành .env và điền thông tin
│   ├── .env                     # (tạo thủ công, không commit lên git)
│   ├── docker-compose.yml       # Tất cả 5 services: postgres, redis, langfuse, litellm, ollama
│   ├── litellm_config.yaml      # Cấu hình LLM Gateway
│   ├── setup.ps1                # ← Chạy script này để setup toàn bộ hạ tầng
│   └── postgres/
│       └── init.sql             # Khởi tạo DB: pgvector, schema, seed data
│
├── ai-project-agent/            # Mã nguồn AI Agent (Python)
│   ├── requirements.txt         # Dependencies
│   ├── config.py                # Cấu hình tập trung (đọc từ .env)
│   ├── graph/
│   │   └── supervisor.py        # LangGraph Agent (Orchestration Pillar)
│   ├── tools/
│   │   └── permission_layer.py  # Kiểm soát quyền file/command (Security Pillar)
│   └── rag/
│       └── rag_ingest.py        # Nhúng tài liệu vào pgvector (Context Pillar)
│
├── privacy-shield-app/          # (Pha 0-5) Sản phẩm Desktop chính
│   └── ...
│
├── ml/                          # (Pha 4) Huấn luyện model YOLOv8
│   └── ...
│
└── docs/                        # Tài liệu dự án (được nhúng vào RAG)
    ├── 01_requirements.md
    ├── 02_architecture.md
    └── ...
