# 14 — Project Structure

```text
AI project/
├── README.md
├── pyproject.toml
├── requirements-dev.txt
├── docs/                 # source-of-truth contracts 01–20
├── tests/                # cross-component regression tests
├── scripts/              # environment/release checks
├── privacy-shield-app/   # desktop product
│   ├── app/{core,ui,utils}/
│   ├── configs/
│   └── models/           # dev assets; generated bundles ignored
├── ai-project-agent/     # optional development copilot
├── infra/                # local development services
└── references/           # non-production references
```

Generated/private directories `data/`, `runs/`, `logs/`, `dist/`, face template và checkpoints không commit. `references/` không được import vào product.
