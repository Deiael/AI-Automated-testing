# AI-Test

[中文](./README.md) | English

**AI-powered API testing platform** with a strict three-layer architecture (App / Gateway / Engine), project-scoped RAG, case templates, multi-engine switching, and SSE multi-turn generation.

## Architecture

```
Browser (Vue3) ──REST/SSE──► Gateway (FastAPI)
                              │ DB / RAG / confidence / engine routing
                              └──SSE──► Engine (FastAPI + LangGraph)
                                         Prompts / agents / no business DB
```

| Layer | Stack | Port | Responsibility |
|---|---|---|---|
| App | Vue 3 + Element Plus + vue-i18n | 5190 | UI, pipeline wizard, zh/en switch |
| Gateway | FastAPI + SQLAlchemy | 8100 | Persistence, RAG, routing, post-process |
| Engine | FastAPI + LangGraph | 8200 | Agent graphs, SSE streaming |

Design docs: [`docs/DEVELOPMENT.en.md`](./docs/DEVELOPMENT.en.md) · [`docs/DEVELOPMENT.md`](./docs/DEVELOPMENT.md) (Chinese)

## Features

- **Pipelines**: create a pipeline linked to a project → requirements → cases → report
- **Projects**: engine binding, base URL, RAG, templates
- **Multi-engine**: `EngineProfile` + gateway router (Cursor-like switching)
- **DeepSeek / OpenAI-compatible**: configure engine `.env`
- **i18n**: language toggle (top-right), preference in `localStorage`

## Quick start

### Requirements

- Python 3.11+
- Node.js 20+
- Optional: Docker Compose

### 1. Clone & venv

```bash
git clone <your-repo-url> AI-Test
cd AI-Test

python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\activate

pip install -e ./packages/contracts
pip install -r ./engine/requirements.txt
pip install -r ./gateway/requirements.txt
```

### 2. Config

```bash
cp engine/.env.example engine/.env
cp gateway/.env.example gateway/.env
# Edit engine/.env with your DeepSeek / OpenAI-compatible key
```

> **Never** commit real secrets. `engine/.env` and `gateway/.env` are gitignored.

### 3. Run (3 terminals)

```bash
cd engine && uvicorn app.main:app --host 127.0.0.1 --port 8200
cd gateway && uvicorn app.main:app --host 127.0.0.1 --port 8100
cd frontend && npm install && npm run dev
```

Open http://127.0.0.1:5190 — default gateway API key: `dev-key`.

```bash
curl http://127.0.0.1:8200/health
# expect llm_enabled: true when a key is set
```

### Docker Compose

```bash
cp .env.example .env
docker compose up -d --build
```

## Suggested walkthrough

1. **Projects**: create a project and set Base URL
2. **Pipelines**: create a pipeline linked to that project
3. Upload requirements → confirm points → confirm cases → run & report
4. **Engines**: health-check profiles; keep LLM keys only in `engine/.env`

## Repository layout

```
AI-Test/
├── frontend/
├── gateway/
├── engine/
├── packages/contracts/
├── docs/
├── scripts/
└── docker-compose.yml
```

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

```bash
cd frontend && npm run build
python -c "from ai_test_contracts import EngineRequest; print('ok')"
```

CI: `.github/workflows/ci.yml`.

## Security

- LLM keys live **only** in the engine `.env`
- Frontend holds gateway `X-API-Key` only (change `dev-key` in production)
- Do not commit `*.db`, `.venv`, `node_modules`, or real `.env` files

## License

[MIT](./LICENSE)
