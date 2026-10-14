# 18 — Release & Packaging

Release Windows dùng Python 3.12 x64 và dependency/model versions đã pin. Build output không chứa `.env`, dataset, runs, face template hoặc agent credentials. Models/assets kèm license, SHA256 và source metadata.

Pipeline: clean checkout → create venv → install lock → tests/lint → environment smoke → build → malware/secret scan → clean-VM install → camera/virtual-camera smoke → hash/SBOM → tag. Rollback giữ installer và model bundle trước đó.

Unsigned development build phải ghi rõ; production distribution nên code-sign sau khi publisher identity được quyết định.
