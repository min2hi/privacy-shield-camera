# 05 — System Architecture

Ba subsystem độc lập:

1. Desktop runtime: camera → detector/face privacy → smoothing → masking → preview/virtual camera.
2. Offline model pipeline: manifest → validation → train → evaluation → trusted model bundle.
3. Project agent: docs/code RAG, LLM gateway và observability; không nhận webcam pixels/embeddings.

Desktop app phải chạy khi agent/Redis/PostgreSQL/Langfuse không tồn tại. Model bundle và config được validate trước khi mở camera. Runtime components nhận dependency qua constructor để test bằng fake detector/camera/output.
