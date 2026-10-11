# AI 自动化测试平台 — 开发文档（MVP）

> 版本：v0.2  
> 英文版：[DEVELOPMENT.en.md](./DEVELOPMENT.en.md)  
> 状态：可作为后续开发依据  
> 目标读者：前后端 / 引擎开发  
> 更新原则：架构边界与接口契约变更必须同步改中英文文档

### 相对 v0.1 的增量

- **流水线实体** `Pipeline`：关联项目，步骤 `req|cases|report`
- **DeepSeek / OpenAI 兼容**：密钥仅在引擎 `.env`
- **前端 i18n**：`zh-CN` / `en-US`，右上角切换

---

## 1. 产品定位

构建一个**接口测试向**的 AI 自动化平台：用户在前端完成「测试点生成 → 测试用例生成 → 测试执行与报告」三条流水线；AI 能力通过可切换引擎提供，项目维度可挂载 RAG 与用例模板，支撑多轮人机交互。

### 1.1 MVP 范围（做）

| 能力 | 说明 |
|------|------|
| 应用层 | Vue3 + Element Plus；项目/会话/产物管理；SSE 多轮对话 UI |
| 网关层 | FastAPI；业务持久化；引擎路由与切换；公共能力（置信度等） |
| 引擎层 | FastAPI + LangGraph；Agent 编排；SSE 流式输出；不落业务库 |
| 三条流程 | 测试点生成、测试用例生成、测试执行报告 |
| RAG | 项目维度配置；MVP 向量实现 + 可替换抽象 |
| 模板 | 按项目绑定用例模板，生成时注入 |
| 多引擎 | 配置级切换，对应用层透明（类似 Cursor 切模型） |

### 1.2 非目标（MVP 不做）

- UI 自动化 / 性能压测 / 安全扫描
- 生产级向量库（Milvus）实装（只预留接口）
- 网关内编写 Prompt / 业务 Agent 逻辑
- 引擎直连前端或引擎写业务库
- 复杂权限体系（MVP 单用户或简单 API Key 即可）

---

## 2. 三层架构与职责铁律

```
┌─────────────────────────────────────────────────────────────┐
│  应用层 Application（Vue3 + Element Plus）                    │
│  · 页面交互 / 多轮对话 UI / SSE 消费                           │
│  · 只调网关 REST + SSE，不直连引擎                             │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP / SSE
┌───────────────────────────▼─────────────────────────────────┐
│  网关层 Gateway（FastAPI）                                    │
│  · 业务库 CRUD / 会话与产物持久化                              │
│  · 项目 RAG 检索 → 组装 EngineRequest（上下文封装）             │
│  · 引擎路由、切换、健康检查、超时重试                            │
│  · 公共后处理：置信度评分、字段规范化、模板校验                   │
│  · ❌ 不做 Prompt 拼装与 Agent 编排                            │
└───────────────────────────┬─────────────────────────────────┘
                            │ 内部协议 HTTP / SSE
┌───────────────────────────▼─────────────────────────────────┐
│  引擎层 Engine（FastAPI + LangGraph）                         │
│  · Prompt / Tool / Graph 编排                                 │
│  · SSE 流式 token / 结构化事件                                │
│  · 无状态：结果经 SSE/最终包回传网关                            │
│  · ❌ 不做前端、❌ 不落业务库、❌ 不感知项目表结构               │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 职责划界（必须遵守）

| 层 | 允许 | 禁止 |
|----|------|------|
| **应用层** | UI、调用网关、展示流式结果、人工确认/编辑产物 | 直连引擎；持有 LLM Key；写向量库 |
| **网关层** | 业务持久化；项目配置；RAG 检索与上下文打包；引擎切换；置信度等后处理；鉴权 | 写 Prompt；跑 LangGraph；硬编码某一引擎的私有协议（须走适配器） |
| **引擎层** | Agent、Prompt、Tool、LangGraph、流式推理 | 连业务 MySQL；暴露给浏览器；依赖网关表结构 |

### 2.2 数据所有权

- **业务真相源**：仅网关 MySQL（项目、会话、测试点、用例、报告、模板、引擎配置、RAG 文档元数据）。
- **引擎**：只接收 `EngineRequest`，只产出 `EngineEvent` / `EngineResult`；可短暂持有 graph checkpoint（内存或独立 Redis），**不写业务表**。
- **向量数据**：网关侧通过 `VectorStore` 抽象读写；引擎若需检索结果，由网关在请求里以 `context_chunks` 传入（MVP 推荐），避免引擎直连向量库。

---

## 3. 技术栈

| 层 | 技术 | 端口（建议） |
|----|------|-------------|
| 应用层 | Vue 3 + Vite + TypeScript + Element Plus + Pinia | 5190 |
| 网关层 | Python 3.12 + FastAPI + SQLAlchemy / Alembic + MySQL 8 | 8100 |
| 引擎层 | Python 3.12 + FastAPI + LangGraph + langchain-* | 8200 |
| 向量库 MVP | 本地实现（如 Chroma / FAISS / SQLite+embedding 文件） | — |
| 向量库预留 | Milvus | — |
| 部署 | 同仓库 Docker Compose：frontend + gateway + engine + mysql | — |

---

## 4. 同仓库目录结构（目标态）

```
ai-test/
├── docs/
│   └── DEVELOPMENT.md          # 本文档
├── docker-compose.yml
├── .env.example
├── frontend/                   # 应用层
│   ├── package.json
│   └── src/
│       ├── api/                # 仅指向网关
│       ├── views/              # 项目 / 测试点 / 用例 / 报告 / 设置
│       ├── components/chat/    # 多轮 SSE 对话
│       └── stores/
├── gateway/                    # 网关层
│   ├── pyproject.toml / requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── api/                # REST + SSE 入口（对前端）
│   │   ├── domain/             # 实体与用例服务
│   │   ├── persistence/        # ORM / repository
│   │   ├── rag/                # 文档入库、检索、上下文组装
│   │   ├── vector/             # VectorStore 抽象 + MVP 实现
│   │   ├── engine_client/      # 多引擎适配器 + 路由器
│   │   ├── postprocess/        # 置信度、规范化
│   │   └── schemas/            # Pydantic DTO
│   └── alembic/
├── engine/                     # 引擎层（可多实例，接口一致）
│   ├── pyproject.toml / requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── api/stream.py       # SSE 入口（对网关）
│   │   ├── graphs/             # LangGraph：testpoint / testcase / execute
│   │   ├── prompts/
│   │   ├── tools/
│   │   └── schemas/            # EngineRequest / EngineEvent（与网关契约共享）
│   └── README.md
└── packages/                   # 可选：共享 Pydantic 契约包
    └── contracts/
```

> 说明：现有 `ai-test` 下 Go 原型 / mock-server 可逐步废弃或仅作对照，**新开发以 `frontend` + `gateway` + `engine` 为准**。

---

## 5. 核心业务对象

### 5.1 领域模型（网关持久化）

| 实体 | 关键字段 | 说明 |
|------|----------|------|
| `Project` | id, name, description, engine_profile_id, status | 项目维度隔离 |
| `RagCorpus` | id, project_id, name | 项目下知识库 |
| `RagDocument` | id, corpus_id, title, source, status, chunk_count | 上传文档元数据 |
| `CaseTemplate` | id, project_id, name, schema_json, prompt_hint | 用例模板 |
| `EngineProfile` | id, name, engine_base_url, model, extra_json | 可切换引擎配置 |
| `Session` | id, project_id, flow_type, status, title | 多轮会话 |
| `Message` | id, session_id, role, content, event_type, created_at | 对话消息 |
| `TestPoint` | id, project_id, session_id, title, content_json, version, status | 测试点产物 |
| `TestCase` | id, project_id, session_id, test_point_id?, template_id, content_json, confidence, status | 用例产物 |
| `TestRun` | id, project_id, session_id, case_ids_json, status | 一次执行 |
| `TestReport` | id, run_id, summary_json, detail_json, status | 执行报告 |

`flow_type` 枚举：`TEST_POINT` | `TEST_CASE` | `TEST_EXECUTE`。

### 5.2 状态机（会话）

```
CREATED → STREAMING → WAITING_USER → STREAMING → … → COMPLETED
                              ↓
                           CANCELLED / FAILED
```

- **WAITING_USER**：测试点/用例生成过程中需要用户确认、补充、删改。
- 用户提交反馈后再次进入 STREAMING，网关携带完整历史 + RAG 上下文调引擎。

---

## 6. 三条业务流程

### 6.1 测试点生成（多轮）

```
用户选择项目 → 新建 Session(flow=TEST_POINT)
     → 输入需求/接口说明
     → 网关：加载项目 RAG Top-K + 历史消息 → EngineRequest
     → 引擎：LangGraph(testpoint) 流式产出候选测试点
     → 网关：落 Message；解析结构化结果为草稿 TestPoint
     → 前端：用户编辑/勾选/追问（多轮）
     → 用户确认 → TestPoint.status = CONFIRMED
```

### 6.2 测试用例生成（多轮）

```
用户选择项目 +（可选）已确认测试点 + 用例模板
     → Session(flow=TEST_CASE)
     → 网关：RAG + 模板 schema + 测试点内容 → EngineRequest
     → 引擎：LangGraph(testcase) 按模板字段生成
     → 网关：后处理置信度 → 落草稿 TestCase
     → 用户多轮修订 → 确认落库
```

### 6.3 测试执行与报告

```
用户选择用例集 → Session(flow=TEST_EXECUTE) 或直接 Run
     → 网关：组装执行请求（用例 + 环境配置）
     → 引擎：LangGraph(execute) 或执行 Agent（可调 HTTP 工具）
     → 流式进度事件 → 最终 Report JSON
     → 网关：持久化 TestRun / TestReport
     → 前端：报告页展示
```

MVP 执行侧可先：引擎根据用例生成「可执行请求草案」并对 Mock/真实 BaseURL 发请求；真实环境配置放在项目设置中，由网关注入 `runtime` 字段。

---

## 7. 层间契约

### 7.1 网关 → 引擎：`EngineRequest`

```json
{
  "request_id": "uuid",
  "flow": "TEST_POINT | TEST_CASE | TEST_EXECUTE",
  "model": "gpt-4o-mini",
  "session_id": "gateway-session-id",
  "messages": [
    {"role": "user|assistant|system", "content": "..."}
  ],
  "context_chunks": [
    {"doc_id": "...", "title": "...", "text": "...", "score": 0.82}
  ],
  "template": {
    "name": "api-case-v1",
    "schema_json": {},
    "prompt_hint": "..."
  },
  "artifacts": {
    "test_points": [],
    "test_cases": []
  },
  "runtime": {
    "base_url": "https://api.example.com",
    "headers": {}
  },
  "options": {
    "temperature": 0.2,
    "locale": "zh-CN"
  }
}
```

约定：

- 网关负责填充 `context_chunks` / `template` / `artifacts` / `runtime`。
- 引擎**只信任本结构**，不回调网关查库（MVP）。
- `system` 消息：由**引擎**根据 `flow` 内部注入；网关不得下发业务 Prompt 正文（可下发非 Prompt 的结构化约束，如 template.schema）。

### 7.2 引擎 → 网关：SSE `EngineEvent`

Content-Type: `text/event-stream`  
每条 `data:` 为 JSON：

| event | 含义 | data 要点 |
|-------|------|-----------|
| `meta` | 流开始 | request_id, flow, model |
| `token` | 增量文本 | delta |
| `message` | 完整一轮助手话术 | content |
| `artifact` | 结构化产物片段 | kind=test_point\|test_case\|report, payload |
| `progress` | 执行进度 | percent, step |
| `ask_user` | 需要用户补充 | questions[] |
| `error` | 错误 | code, message |
| `done` | 结束 | usage, finish_reason |

网关将 SSE **透传或轻度包装**给前端（可增加 `gateway_ts`、落库后的 `artifact_id`），但不得改写引擎生成的语义内容。

### 7.3 前端 → 网关（应用 API 草案）

| 方法 | 路径 | 说明 |
|------|------|------|
| CRUD | `/api/projects` | 项目 |
| CRUD | `/api/projects/{id}/templates` | 用例模板 |
| CRUD | `/api/projects/{id}/rag/docs` | RAG 文档上传/列表/删除 |
| POST | `/api/projects/{id}/rag/reindex` | 重建索引 |
| GET/PUT | `/api/engine-profiles` | 引擎配置；项目绑定 profile |
| POST | `/api/sessions` | 创建会话 `{projectId, flowType}` |
| GET | `/api/sessions/{id}/messages` | 历史消息 |
| POST | `/api/sessions/{id}/messages` | 用户发言（非流式落库） |
| GET | `/api/sessions/{id}/stream` | SSE：触发/继续生成（query: message?） |
| POST | `/api/sessions/{id}/cancel` | 取消流 |
| GET/PATCH | `/api/test-points` | 测试点确认/编辑 |
| GET/PATCH | `/api/test-cases` | 用例确认/编辑 |
| POST | `/api/test-runs` | 发起执行 |
| GET | `/api/test-reports/{id}` | 报告详情 |

> SSE 具体用 `GET .../stream` 还是 `POST .../chat` + SSE body，实现时二选一，**全项目统一**；推荐 `POST /api/sessions/{id}/chat` 返回 `text/event-stream`，便于带 JSON body。

---

## 8. 多引擎切换设计

### 8.1 目标体验

管理端维护多个 `EngineProfile`（不同 `engine_base_url` / model / vendor）。  
项目绑定一个 profile；会话或单次请求可覆盖（类似 Cursor 切模型）。

### 8.2 网关路由器

```
EngineRouter
  ├─ resolve(project_id, override_profile_id?) → EngineProfile
  ├─ adapters: Dict[vendor, EngineAdapter]
  │     · OpenAICompatibleAdapter
  │     · LocalLangGraphAdapter  # 默认指向本仓库 engine 服务
  └─ stream(profile, EngineRequest) -> AsyncIterator[EngineEvent]
```

要求：

- 适配器只做**传输与事件映射**，不做 Prompt。
- 新增引擎 = 新进程或新 URL +（如有需要）新 Adapter；应用层无感知。
- 健康检查：`GET {engine}/health`；网关启动与定时探测，前端设置页展示可用状态。

---

## 9. RAG（项目维度）

### 9.1 流程

1. 用户在项目下上传文档（md/txt/openapi json/yaml 等）。
2. 网关切分 chunk → embedding → `VectorStore.upsert`。
3. 会话请求时：`query = 用户最新输入 (+ 可选标题)` → `similarity_search(project_id, query, top_k)`。
4. 结果写入 `EngineRequest.context_chunks`。

### 9.2 抽象接口（必须先落地）

```python
class VectorStore(Protocol):
    async def upsert(self, project_id: str, chunks: list[Chunk]) -> None: ...
    async def delete(self, project_id: str, doc_id: str) -> None: ...
    async def search(self, project_id: str, query: str, top_k: int) -> list[ScoredChunk]: ...
    async def drop_project(self, project_id: str) -> None: ...
```

| 实现 | 阶段 |
|------|------|
| `MvpVectorStore`（Chroma/FAISS/本地文件） | MVP 默认 |
| `MilvusVectorStore` | 后续替换，配置切换，业务代码不改 |

Embedding Provider 同样抽象（OpenAI / 本地 bge），配置放网关环境变量或设置表。

---

## 10. 用例模板

- 模板存网关：`schema_json` 描述字段（标题、前置、步骤、期望、优先级、标签等）。
- 生成时网关把模板放入 `EngineRequest.template`。
- 引擎按 schema 产出 JSON；网关用 jsonschema 校验，失败则要求引擎重试或标记 `ask_user`。
- 置信度：网关 `postprocess.confidence` 根据「字段完整度、与 RAG 引用重合、schema 校验结果、自洽性启发式」计算 0~1，写入 `TestCase.confidence`；**不在引擎内落库**。

---

## 11. 引擎层 LangGraph 编排（MVP）

建议三张图，共享基础节点：

```
graphs/
  testpoint_graph.py   # retrieve已在网关完成 → analyze → draft_points → critique → ask_or_finalize
  testcase_graph.py    # bind_template → draft_cases → validate_schema → ask_or_finalize
  execute_graph.py     # plan_requests → call_http → assert → summarize_report
```

节点职责示例：

| 节点 | 职责 |
|------|------|
| `draft_*` | LLM 生成结构化 JSON |
| `critique` | 自检覆盖度/重复 |
| `validate_schema` | 对照 template.schema |
| `ask_or_finalize` | 不确定则 `ask_user` 事件，否则 `artifact` + `done` |
| `call_http` | 执行接口（超时、鉴权头来自 runtime） |

Checkpoint：MVP 可用 MemorySaver；多实例再上 Redis。会话连续性以**网关 messages 全量回传**为主，引擎 checkpoint 为辅。

---

## 12. 应用层页面（MVP）

| 路由 | 页面 | 要点 |
|------|------|------|
| `/projects` | 项目列表 | 创建/进入 |
| `/projects/:id` | 项目概览 | 绑定引擎、模板、RAG 入口 |
| `/projects/:id/rag` | RAG 管理 | 上传、索引状态 |
| `/projects/:id/templates` | 模板管理 | JSON schema 编辑 |
| `/projects/:id/testpoints` | 测试点 | 会话式生成 + 列表确认 |
| `/projects/:id/testcases` | 测试用例 | 会话式生成 + 置信度展示 |
| `/projects/:id/runs` | 执行与报告 | 选用例执行、看报告 |
| `/settings/engines` | 引擎配置 | 增删改 profile、探测健康 |

对话组件统一：`ChatPanel` 消费 SSE 事件，区分 token 气泡 / artifact 卡片 / ask_user 表单。

---

## 13. 配置与密钥

| 配置项 | 存放 | 说明 |
|--------|------|------|
| MySQL | gateway `.env` | 仅网关 |
| LLM API Key | engine `.env`（或网关下发只读 model 名，Key 留引擎） | **推荐 Key 只在引擎**；网关只选 profile |
| Embedding Key | gateway `.env` | RAG 在网关 |
| 引擎 URL 列表 | 网关 DB `EngineProfile` | 可热切换 |
| 向量实现类型 | gateway env `VECTOR_STORE=mvp|milvus` | 抽象工厂 |

禁止：把 Prompt 写进网关配置文件当作业务逻辑；禁止前端持有 LLM Key。

---

## 14. 部署（同仓库 MVP）

`docker-compose.yml` 服务：

| 服务 | 镜像/构建 | 端口 | 依赖 |
|------|-----------|------|------|
| mysql | mysql:8 | 3306 | — |
| gateway | ./gateway | 8100 | mysql |
| engine | ./engine | 8200 | — |
| frontend | ./frontend | 5190 | gateway |

- 前端 Vite 代理：`/api` → `gateway:8100`
- 网关环境变量：`ENGINE_DEFAULT_URL=http://engine:8200`
- 引擎不暴露到公网（compose 内部网络即可）；仅网关可访问。

本地开发：

```bash
# 终端 1
cd ai-test/engine && uvicorn app.main:app --reload --port 8200

# 终端 2
cd ai-test/gateway && uvicorn app.main:app --reload --port 8100

# 终端 3
cd ai-test/frontend && npm run dev
```

---

## 15. 分期计划

### Phase 0 — 骨架（约 1~2 天）

- [ ] 建立 `gateway` / `engine` / `frontend` 目录与空 FastAPI、Vue 工程
- [ ] Compose + 健康检查
- [ ] 固化 `EngineRequest` / `EngineEvent` 契约（建议 `packages/contracts`）
- [ ] 网关 `EngineRouter` + 透传 SSE 的 hello 链路打通

### Phase 1 — 项目与配置

- [ ] Project / EngineProfile / CaseTemplate CRUD
- [ ] 前端项目页 + 引擎切换
- [ ] Alembic 首版 migration

### Phase 2 — RAG MVP

- [ ] `VectorStore` 抽象 + MVP 实现
- [ ] 文档上传、切分、索引、检索
- [ ] 网关组装 `context_chunks` 联调

### Phase 3 — 测试点多轮生成

- [ ] Session/Message 模型
- [ ] engine `testpoint_graph` + SSE
- [ ] 前端 ChatPanel + 测试点确认

### Phase 4 — 测试用例多轮生成

- [ ] 模板注入 + schema 校验
- [ ] `testcase_graph`
- [ ] 网关置信度后处理 + 用例列表

### Phase 5 — 执行与报告

- [ ] `execute_graph` + HTTP tool
- [ ] TestRun / TestReport 持久化与报告页

### Phase 6 — 硬化

- [ ] 取消流、超时、错误码规范
- [ ] 基础单测（契约、置信度、VectorStore）
- [ ] 文档与示例项目种子数据

---

## 16. 错误码与可观测性（MVP 最低集）

| code | 含义 |
|------|------|
| `GATEWAY_VALIDATION` | 参数/模板校验失败 |
| `RAG_INDEX_FAILED` | 索引失败 |
| `ENGINE_UNAVAILABLE` | 引擎不可达 |
| `ENGINE_STREAM_ERROR` | 流中断 |
| `ENGINE_TIMEOUT` | 超时 |
| `SCHEMA_INVALID` | 产物不符合模板 |

日志字段建议：`request_id`, `session_id`, `project_id`, `flow`, `engine_profile`, `latency_ms`。

---

## 17. 开发铁律（Checklist）

1. **应用层永不直连引擎。**
2. **网关永不写 Prompt / 不跑 Graph。**
3. **引擎永不写业务库、不服务浏览器。**
4. **结构化产物必须经网关持久化后再给前端稳定 ID。**
5. **向量访问只通过 `VectorStore` 抽象。**
6. **新增引擎能力 = 新 Adapter 或新引擎服务，不改前端业务页。**
7. **契约变更先改 `docs/DEVELOPMENT.md` + contracts，再改实现。**

---

## 18. 与现有代码的关系

当前仓库 `ai-test/` 下存在早期 Go + Mock 原型（空间/平台配置/用例落库）。  
本文件定义的 **FastAPI 三层架构为新基线**：

- 可复用思路：项目（原「空间」）维度配置、模板校验、用例落库。
- 不建议在 Go 服务上继续堆 LangGraph；新功能在 `gateway` / `engine` 实现。
- 迁移策略：Phase 0 并行新建；Phase 1 后前端切到新网关；旧 Go 服务标记 deprecated。

---

## 19. 待决事项（实现前可快速拍板）

| 项 | 建议默认 |
|----|----------|
| SSE 入口方法 | `POST /api/sessions/{id}/chat` 返回 SSE |
| 向量 MVP | Chroma 持久化到 `gateway/data/chroma` |
| Embedding | 可配置；无 Key 时用 hash 伪向量仅打通链路（并打日志警告） |
| 鉴权 | MVP：网关 `X-API-Key` |
| 合约共享 | 先在 gateway/engine 各放一份 Pydantic，Phase 0 末抽到 `packages/contracts` |
| 执行环境 | 项目级 `base_url` + headers；默认打本地 mock |

---

## 20. 验收标准（MVP Done）

1. 同一前端可通过切换 `EngineProfile` 指向不同引擎实例，无需改页面代码。  
2. 项目 A 的 RAG 不会出现在项目 B 的上下文中。  
3. 测试点、测试用例支持至少 2 轮「生成 → 用户反馈 → 再生成 → 确认落库」。  
4. 用例带 `confidence` 字段，由网关计算。  
5. 执行流程能产出可查看的 `TestReport`。  
6. 引擎进程关闭业务库连接配置仍不存在；停掉引擎后网关返回 `ENGINE_UNAVAILABLE`，业务数据不丢。

---

*本文档是后续开发的依据。实现细节 PR 中若偏离边界，优先改代码对齐本文档，或先修订本文档再合并。*
