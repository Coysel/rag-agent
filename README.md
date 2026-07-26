# Agentic RAG — 多智能体检索增强生成系统

基于 LangGraph ReAct Agent + 混合检索 + MCP 工具协议 + 百度联网搜索的智能问答系统。

## 核心能力

- **ReAct Agent 推理循环** — LangGraph 编排 reason → act → observe → reflect → answer 多步推理，Agent 自主判断工具调用
- **混合检索** — BM25 稀疏检索 + 向量稠密检索 + 加权 RRF 融合排序，父子分块策略（256/1024 token）
- **联网搜索** — 百度搜索 API (千帆 AppBuilder)，Agent 自主判断是否需要联网，每日 100 次免费额度
- **MCP 协议工具层** — 文档检索、SQLite 查询、Web 搜索三大 MCP Server，统一的 JSON-RPC 协议通信
- **流式响应** — FastAPI + SSE，逐句推送，思考过程完整可视化
- **RAGAS 幻觉检测** — 四维评测（Faithfulness/AnswerRelevancy/ContextRelevancy/ContextRecall），环形仪表盘可视化
- **文档智能分类** — 增量式分层聚类，自动摘要生成，支持按类别限定检索范围
- **多轮对话** — SQLite 持久化 + localStorage 双重备份，会话切换/恢复/自动清理

## 项目结构

```
rag/
├── src/
│   ├── agent/          # LangGraph ReAct Agent (graph, nodes, tools, state, llm_client)
│   ├── retrieval/      # 混合检索 (dense, sparse, hybrid, router, pipeline, parent_retriever)
│   ├── categorization/ # 文档分类 (聚类, 摘要, 增量更新)
│   ├── indexing/       # 文档索引 (BM25, ChromaDB, embeddings)
│   ├── mcp/            # MCP 协议工具服务器 (doc_server, sqlite_server, web_server)
│   ├── api/            # FastAPI 路由 (chat, admin, eval, health) + 中间件
│   ├── evaluation/     # RAGAS 评估框架
│   ├── storage/        # 会话持久化 (SQLite session_store)
│   ├── core/           # 核心模块 (异常, 安全, 配置)
│   └── utils/          # 工具 (日志, 上下文管理)
├── frontend/           # Vanilla JS SPA (零框架)
│   ├── js/pages/       # 聊天, 管理, 评测, 检索对比, 设置
│   ├── js/components/  # 气泡, 思考时间线, Markdown 渲染, 来源面板, Toast
│   ├── js/api/         # API 客户端 + SSE 流解析
│   ├── js/store/       # 状态管理 (localStorage + Store)
│   └── css/            # 样式 (CSS 变量 + 响应式)
├── tests/              # pytest 测试 (31 个)
├── scripts/            # 工具脚本 (索引文档, 运行评估)
├── docs/               # 迭代报告 (fullstack-iterations/)
├── data/documents/     # 知识库文档
├── config.py           # 全局配置 (pydantic-settings)
├── main.py             # 入口 (FastAPI + lifespan)
└── requirements.txt    # 依赖
```

## 快速开始

### 环境要求

- Python 3.10+
- Windows / Linux / macOS

### 安装

```bash
# 克隆仓库
git clone https://github.com/Coysel/rag-agent.git
cd rag-agent

# 创建虚拟环境
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 配置

复制环境变量模板并填入 API Key：

```bash
cp .env.example .env
```

编辑 `.env`，至少配置一项 LLM 提供商和百度搜索 API：

```env
# LLM 提供商 (deepseek 或 anthropic)
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-deepseek-api-key

# 百度搜索 API (联网搜索)
# 申请地址: https://qianfan.cloud.baidu.com/appbuilder
BAIDU_API_KEY=your-baidu-api-key
```

可选配置项：Embedding 模型（BGE / OpenAI / Voyage）、端口号、上下文窗口大小、速率限制等。详见 `.env.example`。

### 启动

```bash
python main.py
```

服务启动后访问 `http://localhost:8001`。

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 前端聊天界面 (SPA) |
| `POST` | `/chat` | 单轮对话 (SSE 流式 / JSON) |
| `POST` | `/chat/session` | 多轮对话 (session_id 关联) |
| `GET` | `/chat/sessions` | 列出所有会话 |
| `DELETE` | `/chat/sessions/{id}` | 删除会话 |
| `GET` | `/health` | 健康检查 (索引状态 + 配置) |
| `GET` | `/health/deep` | 深度健康检查 (真实 LLM + 检索调用) |
| `GET` | `/llm-test` | LLM 连通性测试 |
| `POST` | `/admin/documents/upload` | 上传文档 |
| `DELETE` | `/admin/documents/{id}` | 删除文档 |
| `POST` | `/admin/index/rebuild` | 重建索引 |
| `POST` | `/eval/run` | 运行 RAGAS 评估 |
| `GET` | `/eval/results` | 获取历史评估结果 |

## 技术栈

| 层级 | 技术 |
|------|------|
| Agent 框架 | LangGraph (ReAct 循环) |
| LLM | DeepSeek-chat / Claude (Anthropic) |
| 向量存储 | ChromaDB |
| 稀疏检索 | BM25 (rank-bm25) |
| Embedding | BGE-small-zh-v1.5 / OpenAI / Voyage |
| 联网搜索 | 百度搜索 API (千帆 AppBuilder) |
| 后端 | FastAPI + SSE (sse-starlette) |
| 前端 | Vanilla JavaScript (零框架 SPA) |
| 评估 | RAGAS (LLM-as-Judge) |
| MCP | MCP Python SDK |
| Token 计数 | tiktoken |

---

## 架构详解

### 1. ReAct Agent 推理引擎

系统的核心是一个基于 LangGraph 构建的 ReAct Agent。用户提问后，查询路由器自动判断问题类型（factual / conceptual / multi_hop），然后进入 reason → act → observe → reflect → answer 循环。每轮 Agent 决定是继续检索还是信息已足够，最多迭代 5 轮。回答按句子拆分通过 SSE 流式推送到前端，用户可看到每一步推理过程和答案逐句呈现。

**关键模块**：[src/agent/graph.py](src/agent/graph.py)（图编排）、[src/agent/nodes.py](src/agent/nodes.py)（节点逻辑，含 System Prompt 和 Answer Prompt）、[src/agent/llm_client.py](src/agent/llm_client.py)（LLM 客户端）。

**上下文管理**：使用 tiktoken 精确计数，当检索文档总量超出 LLM 上下文窗口（默认 80K tokens）时，按相关性分数从低到高动态截断，防止超长报错。

**Answer Prompt 设计**（v2.1 重构）：采用五段式结构（角色 / 背景 / 任务 / 约束 / 输出格式），使用 `[来源N]` 简化引用格式，引入"积极利用"约束——即使信息只有部分相关也提取有用部分作答，避免 DeepSeek 模型过度退避。同时区分 🌐 网页和 📄 文档，标注日期和来源站名。

### 2. 混合检索

BM25 稀疏检索 + 向量稠密检索的混合方案，用加权 RRF（倒数排名融合）合并结果。选择 RRF 而非直接加权原始分数的原因是：BM25 分数无上界而余弦相似度在 0~1 之间，两者不可比——用排名代替分数绕过了这个问题。

文档分块采用父子策略：子块 256 token 用于检索（精度高），父块 1024 token 作为上下文喂给 LLM（信息完整）。

**关键模块**：[src/retrieval/hybrid_retriever.py](src/retrieval/hybrid_retriever.py)（RRF 融合）、[src/retrieval/pipeline.py](src/retrieval/pipeline.py)（检索管线）、[src/retrieval/parent_retriever.py](src/retrieval/parent_retriever.py)（父子展开）。

### 3. 联网搜索 (v2.1 重大更新)

**从 Bing HTML 抓取迁移到百度搜索 API (千帆 AppBuilder)**。旧方案用正则从 Bing 搜索结果页 HTML 里提取内容，稳定性差（页面结构变动即失效）且无官方 API 支持。新方案使用百度搜索 API v2 (`web_search` endpoint)，支持：

- 标准 Bearer Token 鉴权
- 返回完整字段：title、url、content、snippet、website、date、rerank_score、authority_score
- 组合评分：`rerank × (0.5 + 0.5 × authority)` 用于 RRF 区间排序
- 每日 100 次免费额度
- 底层的 HTTP 错误解析和超时处理

Agent 在推理阶段自动判断——实时信息（天气、新闻、最新版本）直接调 web_search；普通知识问答先查本地知识库，检索结果不够再补一刀联网。

**关键模块**：[src/mcp/web_server.py](src/mcp/web_server.py)（百度 API 调用）、[src/mcp/client_manager.py](src/mcp/client_manager.py)（结果格式化 + 评分融合）。

### 4. 来源引用与可溯源性

v2.1 重构了来源引用流程，解决"LLM 不引用来源"的问题：

- **生成阶段**：Answer Prompt 强制要求每条要点至少引用一个来源，使用简单 `[来源N]` 数字格式
- **渲染阶段**：前端 `_renderSourceLinks()` 将 `[来源N]` 替换为 `📎 来源N` 可点击标签，同时兼容旧格式 `[来源: XXX]`
- **来源面板**：点击引用标签自动展开 SourcePanel 并高亮对应来源项
- **去重优化**：使用 `title|url` 去重而非仅 title，避免同名网页丢失

### 5. 多轮对话与历史记录

对话历史通过 SQLite 做后端持久化，前端用 localStorage 做双重备份。支持创建、切换、删除会话，刷新页面后历史消息自动恢复。后端自动清理过期会话。

**关键模块**：[src/storage/session_store.py](src/storage/session_store.py)、[src/api/routes/chat.py](src/api/routes/chat.py)（_stream_chat_session）。

### 6. 文档管理

文档上传、删除和索引重建通过 Admin API 管理。上传后自动增量分类——先对文档内容做层次化摘要，再判断归入已有类别还是创建新类别。前端管理界面支持拖拽上传和可视化操作。

**关键模块**：[src/api/routes/admin.py](src/api/routes/admin.py)、[src/indexing/index_manager.py](src/indexing/index_manager.py)、[src/categorization/](src/categorization/)。

### 7. RAGAS 幻觉检测

内置 RAGAS 风格评测框架，LLM-as-Judge 方式从四个维度检测回答质量：

| 指标 | 含义 |
|------|------|
| Faithfulness | 回答中的陈述能否在检索文档中找到依据 |
| AnswerRelevancy | 答案是否切题 |
| ContextRelevancy | 检索结果是否相关 |
| ContextRecall | 该检索到的文档是否漏了 |

前端评测仪表盘用 SVG 环形图展示四项分数，绿（≥0.7）/ 黄（≥0.4）/ 红（<0.4）三档着色。支持预设 20 题测试集的 Dense vs Hybrid 对比实验，也支持自定义问题即时评测。

**关键模块**：[src/evaluation/ragas_eval.py](src/evaluation/ragas_eval.py)、[frontend/js/pages/eval.js](frontend/js/pages/eval.js)。

### 8. 系统健康自检

三级健康检查：`/health` 看索引状态和配置概况，`/health/deep` 真实调用一次 LLM 和检索管线验证连通性，`/llm-test` 单独测 LLM 返回完整响应和 token 用量。前端设置页有一键检查按钮。

**关键模块**：[src/api/routes/health.py](src/api/routes/health.py)。

### 9. 安全中间件

中间件层四件事：CORS 白名单控制跨域、滑动窗口速率限制（chat 30/min，eval 10/min）、安全响应头（CSP、X-Frame-Options 等）、每个请求注入 Correlation ID 方便日志追踪。

**关键模块**：[src/api/middleware.py](src/api/middleware.py)。

### 10. 前端

零框架原生 JavaScript SPA，五个页面：

| 页面 | 功能 |
|------|------|
| **Chat** | SSE 流式对话，思考过程可视化时间线，联网搜索开关，来源面板 |
| **Admin** | 文档上传/删除/索引重建，拖拽上传，类别管理 |
| **Eval** | 评测仪表盘，Dense vs Hybrid 对比，自定义问题评测 |
| **Retrieval** | BM25 / Dense / Hybrid 三种检索器并排对比 |
| **Settings** | 配置管理，健康检查，API Key 设置 |

**关键模块**：[frontend/](frontend/)。

---

## 目前效果

在 115 篇文档、572 个文本块的索引规模下（DeepSeek-chat + BGE 本地 Embedding），实测三个典型查询：

| 查询 | 耗时 | 步数 | 分类 | 来源 |
|------|------|------|------|------|
| RRF 融合检索的原理是什么？ | 9.3s | 1 轮 | conceptual ✓ | 7 篇 |
| LangGraph 的 ReAct 循环是如何工作的？ | 4.8s | 1 轮 | conceptual ✓ | 8 篇 |
| BM25 和向量检索在混合检索中分别起什么作用？ | 5.9s | 1 轮 | multi_hop ✓ | 8 篇 |

三个查询全部正确分类、准确检索、回答有据可查且标注来源。

系统具备的完整能力：基础问答（带来源引用）、Agent 自主判断联网搜索、多轮对话（历史持久化）、文档管理（上传/删除/重建/自动分类）、四维幻觉评测（环形仪表盘可视化）、系统自检（三级健康检查）、SSE 流式输出（思考过程可见）、以及按文档类别限定检索范围。

---

## 运行测试

```bash
pytest tests/ -v
```

---

## 已知局限

- **文档格式有限**：当前只处理纯文本（`.txt` `.md` `.py` `.html` `.json` 等 13 种格式），PDF、Word、Excel、PPT、图片均不支持
- **无用户认证系统**：Admin API 通过 HTTP Header 明文 key 鉴权，默认值硬编码，多人使用需引入完整登录和权限体系
- **LLM 生态单一**：目前仅支持 DeepSeek 和 Anthropic (Claude)，OpenAI、Gemini、Ollama 等不直接支持
- **联网搜索仅百度**：目前只接入百度搜索 API，未接入 SerpAPI、Tavily、Google 等搜索服务
- **前端无自动化测试**：前端使用 Vanilla JS 且无 Jest/Vitest 测试框架，依赖手动验证

---

## License

MIT
