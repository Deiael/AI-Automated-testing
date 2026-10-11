# AI-Test — Development Guide (English)

> Companion to [`DEVELOPMENT.md`](./DEVELOPMENT.md) (Chinese).  
> When architecture or contracts change, update **both** documents.

## Product

Interface-testing focused AI platform:

1. Upload / index requirements (project RAG)
2. Multi-turn generation of test points & cases (SSE)
3. Execute cases and persist reports

## Layer rules (hard)

| Layer | May | Must not |
|---|---|---|
| App | Call gateway only; show SSE; edit/confirm artifacts | Call engine; hold LLM keys |
| Gateway | Persist business data; RAG; engine routing; confidence | Write prompts; run LangGraph |
| Engine | Prompts, tools, LangGraph, SSE | Write business DB; serve browsers |

## Shared contract

`packages/contracts` defines `EngineRequest` / `EngineEvent`.

Gateway fills `context_chunks`, `template`, `artifacts`, `runtime`.  
Engine streams SSE events: `meta`, `token`, `message`, `artifact`, `ask_user`, `error`, `done`.

## Pipelines

Entity `Pipeline`: `name`, `project_id`, `step` (`req|cases|report`), `status`.

App entry: `/pipeline` (create & list) → `/pipelines/:id` (wizard).

## Vector store

`VectorStore` protocol + `MvpVectorStore` (file-backed).  
Set `VECTOR_STORE=milvus` later without changing business call sites.

## LLM (DeepSeek)

Configure **engine** `.env`:

```env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
LLM_FALLBACK_MOCK=false
ALLOW_MODEL_OVERRIDE=false
```

`GET /health` → `llm_enabled`, `model`, `base_url`.

## i18n

Frontend uses `vue-i18n` (`zh-CN` / `en-US`).  
Toggle in the top-right; stored as `localStorage.locale`.

## Local ports

| Service | Port |
|---|---|
| Frontend | 5190 |
| Gateway | 8100 |
| Engine | 8200 |

## PR checklist

- [ ] `frontend`: `npm run build`
- [ ] Contracts change → update gateway + engine + docs (zh+en)
- [ ] No secrets in the diff
- [ ] Layer boundaries preserved
