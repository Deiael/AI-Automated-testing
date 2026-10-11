# AI-Test

中文 | [English](./README.en.md)

**AI 自动化接口测试平台**：三层架构（应用层 / 网关层 / 引擎层），支持项目维度 RAG、用例模板、多引擎切换与 SSE 多轮生成。

## 页面
<img width="1178" height="914" alt="image" src="https://github.com/user-attachments/assets/ac8fb02e-79a1-4648-974f-be7a4fd096ba" />


## 架构一览

```
浏览器 (Vue3) ──REST/SSE──► 网关 Gateway (FastAPI)
                              │ 业务库 / RAG / 置信度 / 引擎路由
                              └──SSE──► 引擎 Engine (FastAPI + LangGraph)
                                         Prompt / Agent / 不落业务库
```

| 层 | 技术 | 默认端口 | 职责 |
|---|---|---|---|
| 应用层 | Vue 3 + Element Plus + vue-i18n | 5190 | UI、流水线向导、中英文切换 |
| 网关层 | FastAPI + SQLAlchemy | 8100 | 持久化、RAG、引擎切换、后处理 |
| 引擎层 | FastAPI + LangGraph | 8200 | Agent 编排、SSE 流式输出 |

设计文档：[`docs/DEVELOPMENT.md`](./docs/DEVELOPMENT.md)（中文）· [`docs/DEVELOPMENT.en.md`](./docs/DEVELOPMENT.en.md)（English）

## 功能

- **测试流水线**：创建流水线并关联项目 → 上传需求 → 生成测试点/用例 → 执行报告
- **项目空间**：引擎绑定、Base URL、RAG、用例模板
- **多引擎切换**：`EngineProfile` 配置，网关路由（类似 Cursor 切模型）
- **DeepSeek / OpenAI 兼容**：引擎 `.env` 配置 `OPENAI_BASE_URL` + Key
- **中英文界面**：右上角一键切换，偏好写入 `localStorage`

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 20+
- （可选）Docker Compose

### 1. 克隆与虚拟环境

```bash
git clone <your-repo-url> AI-Test
cd AI-Test

python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -e ./packages/contracts
pip install -r ./engine/requirements.txt
pip install -r ./gateway/requirements.txt
```

### 2. 配置

```bash
cp engine/.env.example engine/.env
cp gateway/.env.example gateway/.env
# 编辑 engine/.env：填入 DeepSeek / OpenAI 兼容 Key
# OPENAI_API_KEY=sk-...
# OPENAI_BASE_URL=https://api.deepseek.com/v1
# OPENAI_MODEL=deepseek-chat
```

> **切勿**把真实 Key 提交到 Git。`engine/.env` / `gateway/.env` 已在 `.gitignore` 中。

### 3. 启动（三个终端）

```bash
# 终端 1 — 引擎
cd engine && uvicorn app.main:app --host 127.0.0.1 --port 8200

# 终端 2 — 网关
cd gateway && uvicorn app.main:app --host 127.0.0.1 --port 8100

# 终端 3 — 前端
cd frontend && npm install && npm run dev
```

Windows 也可使用：

```powershell
.\scripts\start-all.ps1
```

打开 http://127.0.0.1:5190 ，默认网关 API Key：`dev-key`（与 `gateway/.env` 中 `API_KEY` 一致）。

检查引擎是否启用 LLM：

```bash
curl http://127.0.0.1:8200/health
# 期望 llm_enabled: true
```

### Docker Compose

```bash
cp .env.example .env
docker compose up -d --build
```

## 推荐使用路径

1. **项目空间**：创建项目，配置 Base URL（如 `https://httpbin.org`）
2. **测试流水线**：创建流水线并关联该项目
3. 上传需求 → 生成测试点并确认 → 生成用例并确认 → 执行看报告
4. **引擎配置**：探测健康；DeepSeek Key 在引擎 `.env`，不在前端

## 仓库结构

```
AI-Test/
├── frontend/          # 应用层 Vue3
├── gateway/           # 网关层 FastAPI
├── engine/            # 引擎层 FastAPI + LangGraph
├── packages/contracts # 共享 EngineRequest / EngineEvent
├── docs/              # 设计文档（中/英）
├── scripts/           # 启动与工具脚本
└── docker-compose.yml
```

## 开发与贡献

见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

本地检查：

```bash
# 前端
cd frontend && npm run build

# 后端（语法/导入）
python -c "from ai_test_contracts import EngineRequest; print('ok')"
```

CI：`.github/workflows/ci.yml` 会跑前端构建与 Python 安装校验。

## 安全提示

- LLM Key **只放引擎** `engine/.env`
- 前端只持有网关 `X-API-Key`（开发默认 `dev-key`，生产请更换）
- 不要提交 `*.db`、`.venv`、`node_modules`、真实 `.env`

## 许可证

[MIT](./LICENSE)
