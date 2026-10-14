# 用 REA 学习与自逆向 AI-Test

本仓库已接入 [REA（morluto/rea）](https://github.com/morluto/rea)：通过 Cursor 的本地 MCP，让 Agent 检查程序并带证据解释行为。

> 路径说明：项目在 `D:\AI-test`（不是 `D:\AItest`）。

## 和「配置中心 → MCP」的区别

| | Cursor + REA | 网关配置中心 MCP |
|---|---|---|
| 用途 | 开发期逆向 / 学习：检查本机产物、前端包、浏览器行为 | 运行期给引擎注入外部工具 |
| 传输 | 本地 **stdio**（`rea-agents mcp`） | **HTTP / SSE** |
| 是否写入业务库 | 否 | 是（项目级 MCP 配置） |

因此：REA **接在 Cursor**，不接到网关的 MCP 列表。网关只支持远程 HTTP/SSE，装不上 REA 的 stdio 服务。

## 一次性安装

### 方式 A：项目脚本

```bat
scripts\setup-rea.cmd
```

### 方式 B：命令行

```bat
npx -y rea-agents@latest setup --client cursor --yes
```

安装会：

1. 写入 Cursor MCP（用户级 `~/.cursor/mcp.json`；本仓库另有 `.cursor/mcp.json`）
2. 安装技能到 `~/.agents/skills/reverse-engineer-anything`

然后**完全退出并重启 Cursor**，在 MCP 面板确认 `rea` 已连接。

检查：

```bat
npx -y rea-agents@latest doctor --client cursor --format json
```

## 本项目适合练什么

AI-Test 是「Vue 前端 + FastAPI 网关/引擎」。学 REA 时建议按难度递进：

1. **前端静态包（最适合入门）**  
   先构建，再让 REA 分析产物（模拟「没有源码、只有打包结果」）：

   ```bat
   cd frontend
   npm install
   npm run build
   ```

   目标目录：`D:\AI-test\frontend\dist`（或构建输出目录）。

2. **开发中的前端源码树**  
   路径：`D:\AI-test\frontend`  
   适合问路由、API 客户端、宠物系统、配置中心页面如何串起来。

3. **浏览器运行时（进阶）**  
   本地起前端 `http://127.0.0.1:5190`，用 REA 的浏览器工作流观察脚本与请求（需 Chrome 系浏览器）。

4. **原生二进制（可选，后续）**  
   需要 Ghidra / Hopper / IDA。Python 服务本身一般直接读源码即可，不必上原生引擎。

## 练习提示词（复制到 Cursor）

把路径按你机器改好后直接问 Agent：

### 练习 1：打包产物里的路由

```text
Use REA to analyze D:\AI-test\frontend\dist as a JavaScript application.
Explain how the SPA routes to 配置中心 / MCP / RAG pages. Show modules, imports, and evidence.
Do not invent file paths that REA did not return.
```

### 练习 2：宠物系统行为

```text
Use REA to analyze D:\AI-test\frontend.
How does the pet adopt / feed / play flow work? Trace storage keys (e.g. localStorage), UI entry points, and state updates. Cite evidence from REA.
```

### 练习 3：网关 API 调用面

```text
Use REA to analyze D:\AI-test\frontend.
List how the UI talks to the gateway (base URL, auth header, SSE). Show the relevant modules and call sites with evidence.
```

### 练习 4：对照源码（学习闭环）

```text
After REA analysis, compare findings with the source under frontend/src.
Point out what the bundled/dist view hides vs what source makes obvious. Summarize 3 takeaways for learning reverse engineering.
```

## CLI 不经过 Agent 时

```bat
npx -y rea-agents@latest analyze-javascript-application D:\AI-test\frontend\dist --json
```

或对源码树：

```bat
npx -y rea-agents@latest analyze-javascript-application D:\AI-test\frontend --json
```

## 更新 REA

```bat
npx -y rea-agents@latest setup --client cursor --yes
```

然后重启 Cursor。项目内 `.cursor/mcp.json` 若钉死了旧版本号，请同步改成新版本。

## 负责任使用

- 只分析**你拥有或已获授权**的软件（本仓库即你的项目）。
- 不要用 REA 破解授权、绕过付费或未授权目标。
- 分析结果会进入当前对话模型的上下文，遵守你所用模型的数据策略。

## 参考

- 官网：https://morluto.github.io/rea/
- FAQ：https://morluto.github.io/rea/faq/
- GitHub：https://github.com/morluto/rea
