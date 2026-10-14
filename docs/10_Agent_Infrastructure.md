# 10 — Agent Infrastructure

Agent dùng LiteLLM, LangGraph, PostgreSQL/pgvector, Redis và Langfuse để tìm tài liệu và hỗ trợ phát triển. Nó không phải thành phần sản phẩm realtime.

RAG allowlist chỉ gồm source/docs/config mẫu; denylist gồm `.env`, biometric templates, datasets, runs, model private artifacts và raw media. Tool mutation phải qua permission layer và audit metadata.

Infrastructure images phải pin version/digest trước release. Setup phải nhất quán: Ollama chạy trên host hoặc trong Compose, không mô tả/call cả hai kiểu cùng lúc.
