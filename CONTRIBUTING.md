# Contributing to AI-Test

中文说明见下方；English follows.

## 中文

感谢贡献！请先阅读 [`docs/DEVELOPMENT.md`](./docs/DEVELOPMENT.md)。

### 开发原则

1. **三层职责严守**：前端不直连引擎；网关不写 Prompt；引擎不落业务库。
2. **契约优先**：改 `EngineRequest` / `EngineEvent` 先改 `packages/contracts` 与中英文文档。
3. **密钥不入库**：只用 `.env.example`，真实 Key 留本地。
4. **中英文同步**：用户可见文案走 `frontend/src/i18n/locales/*`；文档中英文一起改。

### 提交流程

1. Fork / 建分支：`feat/...` 或 `fix/...`
2. 本地验证：
   ```bash
   cd frontend && npm run build
   pip install -e packages/contracts -r engine/requirements.txt -r gateway/requirements.txt
   ```
3. 开 PR，说明动机与测试步骤

### 代码风格

- Python：类型注解 + 明确错误码（网关）
- Vue：Composition API；用户文案禁止硬编码中文（用 `t('...')`）
- 提交信息：简洁说明「为什么」

---

## English

Please read [`docs/DEVELOPMENT.en.md`](./docs/DEVELOPMENT.en.md) first.

### Rules

1. Keep the three-layer boundaries.
2. Change contracts before implementations; update zh+en docs.
3. Never commit secrets.
4. UI strings go through vue-i18n locales.

### PR flow

1. Branch from `main`
2. Run frontend build + install Python deps
3. Open a PR with motivation and a short test plan
