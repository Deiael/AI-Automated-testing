# AI-Test

[中文](./README.md) | English

**AI-powered API testing platform** with a strict three-layer architecture (App / Gateway / Engine), project-scoped RAG, Skills, MCP, case templates, multi-engine switching, true SSE token streaming, and an adoptable Q-style pet buddy.

## Architecture

```
Browser (Vue3) ──REST/SSE──► Gateway (FastAPI)
                              │ DB / RAG / Skills / MCP / confidence / routing
                              └──SSE──► Engine (FastAPI + LangGraph)
                                         Prompts / agents / no business DB
```

| Layer | Stack | Port | Responsibility |
|---|---|---|---|
| App | Vue 3 + Element Plus + vue-i18n | 5190 | UI, pipeline, settings hub, pets, zh/en |
| Gateway | FastAPI + SQLAlchemy | 8100 | Persistence, RAG, Skills, MCP, routing |
| Engine | FastAPI + LangGraph | 8200 | Agent graphs, true token SSE streaming |

Design docs: [`docs/DEVELOPMENT.en.md`](./docs/DEVELOPMENT.en.md) · [`docs/DEVELOPMENT.md`](./docs/DEVELOPMENT.md) (Chinese)

## Features

- **Pipelines**: create a pipeline linked to a project → requirements → cases → report
- **Settings hub**: top-bar project switcher; **Project space** (Overview / RAG / Skill / MCP) + **Engines**
- **Multi-engine**: `EngineProfile` + gateway router (Cursor-like switching)
- **DeepSeek / OpenAI-compatible**: configure engine `.env`
- **True SSE streaming**: tokens stream live during chat generation
- **Clarification cards**: when the engine asks for more info, pick cards (or “Other”) and reply
- **i18n**: language toggle (top-right), preference in `localStorage`

### RAG (project knowledge)

Manage docs under **Settings → Project space → RAG**:

- Project-scoped ingest and retrieval
- Gateway retrieves snippets and injects them into engine context when generating points/cases
- Better recall of API contracts, business rules, and team conventions

### Skills

Maintain reusable skills under **Settings → Project space → Skill**:

- Named skills with description, body, and enable flag
- Enabled skills are injected into session artifacts / retrieval context
- Good for assertion style, priority rules, naming conventions, etc.

### MCP

Configure MCP servers (HTTP/SSE), probe tool lists; enabled tool summaries are injected into sessions so the engine knows available external tools.

### Background removal (rembg)

Under **Settings → Tools**, upload an image; the gateway uses open-source [rembg](https://github.com/danielgatis/rembg) to export a transparent PNG. First use downloads the ONNX model; install `rembg[cpu]` and `pillow` in the gateway environment.

### Pet system

Sidebar buddy you can adopt (Q-style boy/girl dolls, cat, dog):

- **Adopt / switch**: full-body transparent PNGs; click name to rename
- **Play zone**: drag to the bottom-right zone for idle sway / happy hop
- **Newbie quests**: open settings, create a project, etc. → earn drumsticks
- **Feed & level up**: spend drumsticks; state in `localStorage` (`ai-test-pet-v1`)

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

1. **Settings → Project space**: create a project and set Base URL
2. (Optional) upload RAG docs; add Skills / MCP
3. **Pipelines**: create a pipeline linked to that project
4. Upload requirements → confirm points → confirm cases → run & report
5. **Engines**: health-check profiles; keep LLM keys only in `engine/.env`
6. (Optional) adopt a pet and complete newbie quests

## Repository layout

```
AI-Test/
├── frontend/
│   ├── public/pets/          # Q-style character PNGs (transparent)
│   └── src/components/pet/   # Pet UI (avatar / drag / play zone / quests)
├── gateway/                  # RAG / Skill / MCP APIs
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
