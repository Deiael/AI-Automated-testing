# AI-Test

中文 | [English](./README.en.md)

**AI 自动化接口测试平台**：三层架构（应用层 / 网关层 / 引擎层），支持项目维度 RAG、Skill、MCP、用例模板、多引擎切换、SSE 真流式生成，以及可领养互动的 Q 版宠物伙伴。

## 页面
![Uploading da419ecc8579e50884f90a053d2dadb7.png…]()



## 架构一览

```
浏览器 (Vue3) ──REST/SSE──► 网关 Gateway (FastAPI)
                              │ 业务库 / RAG / Skill / MCP / 置信度 / 引擎路由
                              └──SSE──► 引擎 Engine (FastAPI + LangGraph)
                                         Prompt / Agent / 不落业务库
```

| 层 | 技术 | 默认端口 | 职责 |
|---|---|---|---|
| 应用层 | Vue 3 + Element Plus + vue-i18n | 5190 | UI、流水线、配置中心、宠物系统、中英文 |
| 网关层 | FastAPI + SQLAlchemy | 8100 | 持久化、RAG、Skill、MCP、引擎路由、后处理 |
| 引擎层 | FastAPI + LangGraph | 8200 | Agent 编排、SSE 真 token 流式输出 |

设计文档：[`docs/DEVELOPMENT.md`](./docs/DEVELOPMENT.md)（中文）· [`docs/DEVELOPMENT.en.md`](./docs/DEVELOPMENT.en.md)（English）

## 功能

- **测试流水线**：创建流水线并关联项目 → 上传需求 → 生成测试点/用例 → 执行报告
- **配置中心**：顶栏项目切换；**项目空间**（概览 / RAG / Skill / MCP）+ **引擎配置**
- **多引擎切换**：`EngineProfile` 配置，网关路由（类似 Cursor 切模型）
- **DeepSeek / OpenAI 兼容**：引擎 `.env` 配置 `OPENAI_BASE_URL` + Key
- **SSE 真流式**：对话生成按 token 实时回传，不再假回放
- **澄清卡片**：引擎「需要你补充」时以可选卡片展示，支持多选填写与「其他：自己补充」
- **中英文界面**：右上角一键切换，偏好写入 `localStorage`

### RAG（项目知识库）

在 **配置中心 → 项目空间 → RAG** 中管理文档：

- 按**项目**隔离入库与检索
- 生成测试点 / 用例时，网关检索相关片段注入引擎上下文
- 提升对接口约定、业务规则、历史规范的命中率

### Skill（项目技能）

在 **配置中心 → 项目空间 → Skill** 中维护可复用技能：

- 为项目编写命名 Skill（说明、正文、启用开关）
- 会话开始时网关把启用中的 Skill 注入引擎 artifacts / 检索上下文
- 适合沉淀团队约定：断言风格、优先级规则、命名规范等

### MCP（工具服务）

同页可配置 MCP Server（HTTP/SSE），探测工具列表；启用后工具摘要会随会话注入，便于引擎感知可用外部能力。

### 一键抠图（rembg）

在 **配置中心 → 实用工具** 上传图片，网关调用开源 [rembg](https://github.com/danielgatis/rembg) 分割主体并导出透明 PNG。首次使用会下载对应 ONNX 模型；需在网关环境安装 `rembg[cpu]` 与 `pillow`。

### 宠物系统

左侧任务栏提供可领养的 Q 版伙伴（男生 / 女生人偶、小猫、小狗）：

- **领养与切换**：透明底全身立绘；点击名称可自定义
- **玩耍区**：拖到右下角玩耍区，角色会待机晃动 / 欢快跳动
- **新手任务**：打开配置中心、创建项目等 → 奖励鸡腿
- **喂养升级**：消耗鸡腿提升饱食与等级；数据存 `localStorage`（`ai-test-pet-v1`）

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

1. **配置中心 → 项目空间**：创建项目，配置 Base URL（如 `https://httpbin.org`）
2. （可选）上传 RAG 文档；添加 Skill / MCP
3. **测试流水线**：创建流水线并关联该项目
4. 上传需求 → 生成测试点并确认 → 生成用例并确认 → 执行看报告
5. **引擎配置**：探测健康；DeepSeek Key 在引擎 `.env`，不在前端
6. （可选）领养宠物，完成新手任务赚鸡腿喂养

## 仓库结构

```
AI-Test/
├── frontend/                 # 应用层 Vue3
│   ├── public/pets/          # Q 版人物立绘（透明 PNG）
│   └── src/components/pet/   # 宠物 UI（头像 / 拖拽 / 玩耍区 / 任务）
├── gateway/                  # 网关层 FastAPI（RAG / Skill / MCP API）
├── engine/                   # 引擎层 FastAPI + LangGraph
├── packages/contracts        # 共享 EngineRequest / EngineEvent
├── docs/                     # 设计文档（中/英）
├── scripts/                  # 启动与工具脚本
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

## 开发者工具：REA（自逆向学习）

用 [REA](https://github.com/morluto/rea) 在 Cursor 里检查本仓库产物（前端包 / 行为），适合学习逆向。详见 [`docs/REA.md`](./docs/REA.md)。

```bat
scripts\setup-rea.cmd
```

装好后重启 Cursor。REA 走本地 stdio MCP，**不要**配进「配置中心 → MCP」（网关只支持 HTTP/SSE）。

## 安全提示

- LLM Key **只放引擎** `engine/.env`
- 前端只持有网关 `X-API-Key`（开发默认 `dev-key`，生产请更换）
- 不要提交 `*.db`、`.venv`、`node_modules`、真实 `.env`

## 许可证

[MIT](./LICENSE)
