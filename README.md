# Agentic RAG — 多智能体检索增强生成系统

基于 LangGraph 的 ReAct Agent + 混合检索 + MCP 工具层的智能问答系统。

## 核心能力

- **Multi-Agent 辩论验证** — LangGraph ReAct 循环，多智能体交叉验证答案
- **混合检索** — BM25 稀疏检索 + 向量稠密检索 + RRF 融合
- **文档智能分类** — 增量式分层聚类，自动摘要与分类
- **MCP 协议集成** — 支持文档服务器、SQLite 服务器、Web 搜索服务器
- **流式响应** — FastAPI + SSE，思考过程可视化
- **RAGAS 评估** — 内置检索增强生成质量评估

## 项目结构

```
rag/
├── src/
│   ├── agent/          # LangGraph ReAct Agent (graph, nodes, tools, state)
│   ├── retrieval/      # 混合检索 (dense, sparse, hybrid, router, pipeline)
│   ├── categorization/ # 文档分类 (聚类, 摘要, 增量更新)
│   ├── indexing/       # 文档索引 (BM25, ChromaDB, embeddings)
│   ├── mcp/            # MCP 协议工具服务器 (文档, SQLite, Web)
│   ├── api/            # FastAPI 路由 (chat, admin, eval, documents)
│   ├── evaluation/     # RAGAS 评估框架
│   ├── storage/        # 会话持久化 (SQLite)
│   ├── core/           # 核心模块 (异常, 安全)
│   └── utils/          # 工具 (日志)
├── frontend/           # 前端 (Vanilla JS SPA)
│   ├── js/pages/       # 页面 (chat, admin, eval, retrieval, settings)
│   ├── js/components/  # UI 组件 (bubble, thinking, markdown, toast)
│   └── css/            # 样式
├── tests/              # pytest 测试
├── scripts/            # 工具脚本 (索引文档, 运行评估)
├── docs/               # 迭代报告
├── data/documents/     # 知识库文档
├── config.py           # 全局配置 (pydantic-settings)
├── main.py             # 入口
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

编辑 `.env`，至少配置一项 LLM 提供商：

```env
# 选择 LLM 提供商 (deepseek 或 anthropic)
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-deepseek-api-key

# 或使用 Claude
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### 启动

```bash
python main.py
```

服务启动后访问 `http://localhost:8001`。

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 前端聊天界面 |
| `POST` | `/chat` | 对话接口 (SSE 流式) |
| `GET` | `/health` | 健康检查 |
| `GET` | `/admin` | 管理后台 |
| `POST` | `/documents/upload` | 上传文档 |
| `POST` | `/eval/run` | 运行 RAGAS 评估 |

## 技术栈

| 层级 | 技术 |
|------|------|
| Agent 框架 | LangGraph (ReAct 循环) |
| LLM | DeepSeek / Claude (Anthropic) |
| 向量存储 | ChromaDB |
| 稀疏检索 | BM25 (rank-bm25) |
| Embedding | BGE-small-zh-v1.5 / OpenAI / Voyage |
| 后端 | FastAPI + SSE (sse-starlette) |
| 前端 | Vanilla JavaScript (零框架 SPA) |
| 评估 | RAGAS |
| MCP | MCP Python SDK |

## 运行测试

```bash
pytest tests/ -v
```

## License

MIT
