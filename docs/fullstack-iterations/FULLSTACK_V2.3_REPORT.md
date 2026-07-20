# Agentic RAG v2.3 迭代报告 — 联网搜索 + 增量分类加固

> **迭代日期**: 2026-06-29
> **基于**: FULLSTACK_V2.2_REPORT（文档分类系统）
> **改动范围**: 全栈 — 新增 1 文件，修改 14 文件

---

## 项目规模

| 类别 | 文件数 | 代码行数 |
|------|--------|----------|
| 后端 Python | 57 | ~6,200 |
| 前端 JavaScript | 25 | ~3,300 |
| 前端 CSS | 7 | ~2,000 |
| 前端 HTML | 1 | ~420 |
| **合计** | **90** | **~11,900** |

---

## 一、联网搜索功能（新增）

### 1.1 问题

当前 RAG 系统只能检索本地知识库，用户无法获取实时信息（最新新闻、版本更新、天气等）。

### 1.2 方案

新增 `web_search` MCP 工具，遵循 `doc_server` / `sqlite_server` 相同的 MCP Server 模式。底层使用 **Bing + httpx** 直接搜索，零配置、免费。

### 1.3 架构

```
Agent ReAct 循环
  │
  ├─ reason_node → LLM 决定调用 web_search
  ├─ act_node → MCPClientManager.execute_tool("web_search", ...)
  │     └─ web_server (in-memory MCP)
  │           └─ httpx → cn.bing.com → HTML 解析 → 结果
  ├─ observe_node → 搜索结果加入 context_docs
  └─ answer_node → 结合网页结果 + 本地知识回答
```

### 1.4 关键设计决策

#### 为什么不外挂 MCP 包？

项目已使用官方 `mcp` Python SDK 实现 3 个轻量 MCP Server（doc / sqlite / web），通过 in-memory transport 同进程通信：
- 零进程管理开销
- 统一配置（config.py）
- 输出格式和 Agent 对齐
- 新增一个 Server 仅 ~50 行代码

外挂 MCP 包需要独立进程、独立配置、独立生命周期管理，得不偿失。

#### 为什么选 Bing + httpx？

| 方案 | 结果 |
|------|------|
| DuckDuckGo (`ddgs`) | 国内超时，连不上 |
| DuckDuckGo Lite | 同上 |
| Bing `cn.bing.com` | ✅ 国内能访问，HTML 正则解析 |
| 百度 | 反爬太严 |
| SearXNG 自建 | 需要额外部署 |

最终用 `httpx`（项目已有依赖）+ 正则解析 Bing HTML 结果，零额外依赖。

#### asyncio 兼容

`httpx.Client` 是同步的，在 MCP `call_tool` (async) 内调用会阻塞事件循环。解决：`await asyncio.to_thread(_search_sync, query, max_results)` 在独立线程中执行。

### 1.5 行为约束

通过 system prompt 控制，仅当用户明确要求时使用：

```
你有 web_search 工具可用。
当用户要求联网搜索或问题涉及实时信息时，直接调用 web_search。
```

前端 🔒 默认关闭 toggle，用户需手动开启。

---

## 二、增量分类加固（V2.2 续）

在 V2.2 全量分类基础上新增增量分类：

| 特性 | 实现 |
|------|------|
| 上传后自动分类 | `IncrementalCategorizer` 编排器 |
| 归入已有类别 / 创建新类别 | `Clusterer.assign_to_category()` |
| CategoryStore 增量更新 | `create_category()`, `add_doc_to_category()` |
| 可配置关闭 | `AUTO_CATEGORIZE_ON_UPLOAD` + 前端 toggle |

---

## 三、改动文件清单

### 新增文件

| 文件 | 说明 | 行数 |
|------|------|------|
| `src/mcp/web_server.py` | 联网搜索 MCP Server | 157 |
| `src/categorization/incremental.py` | 增量分类编排器 | 100+ |
| `docs/fullstack-iterations/FULLSTACK_V2.3_REPORT.md` | 本报告 | — |

### 修改文件

| 文件 | 改动 |
|------|------|
| `src/mcp/client_manager.py` | 注册第 3 个 MCP Server（web_search） |
| `src/agent/nodes.py` | System prompt 联网搜索约束 + web_search 条件注入 |
| `src/agent/state.py` | AgentState 新增 `web_search: bool` |
| `src/agent/graph.py` | `get_initial_state()` 新增 web_search 参数 |
| `src/api/routes/chat.py` | ChatRequest.web_search → AgentState |
| `src/api/schemas/chat.py` | ChatRequest 新增 `web_search` 字段 |
| `config.py` | WEB_SEARCH_ENABLED / MAX_RESULTS / TIMEOUT |
| `src/categorization/category_store.py` | 增量写入方法（create/add_doc_to_category） |
| `src/categorization/clusterer.py` | 单文档分类 `assign_to_category()` |
| `src/categorization/__init__.py` | 导出 IncrementalCategorizer |
| `src/indexing/index_manager.py` | `add_document()` 返回 chunks 数据 |
| `src/api/routes/admin.py` | 上传后触发增量分类 |
| `src/api/routes/categories.py` | 新增 `GET /admin/categories/progress` |
| `frontend/index.html` | 聊天页联网搜索 toggle + 设置页进度条 |
| `frontend/js/pages/chat.js` | Web search toggle 逻辑 |
| `frontend/js/api/chat.js` | `sendMessage()` 传递 web_search 标志 |
| `frontend/js/store/state.js` | settings 新增 webSearchEnabled |
| `frontend/css/chat.css` | .web-search-toggle 样式 |
| `frontend/js/pages/settings.js` | Auto-categorize toggle + 分类进度条 |
| `frontend/js/api/categories.js` | `CategoryAPI.progress()` |
| `frontend/js/config.js` | CATEGORIES_PROGRESS 端点 |

---

## 四、新增 API

| Method | Path | 说明 |
|--------|------|------|
| GET | `/admin/categories/progress` | 查询分类生成进度 |

### ChatRequest 新增字段

```python
web_search: bool = Field(default=False, description="是否允许联网搜索（默认关闭）")
```

---

## 五、测试结果

| # | 测试场景 | 预期 | 结果 |
|---|---------|------|------|
| 1 | 普通问题 "Python是什么" | 不触发 web_search | ✅ 用本地知识库 |
| 2 | "联网搜索 Python 最新版本" | 触发 web_search，返回网页 | ✅ 返回 5 条 Bing 结果 |
| 3 | web_search 来源注入 context_docs | LLM 引用网页来源 | ✅ 引用 "Welcome to Python.org" |
| 4 | web_search: false（默认） | 工具不可见 | ✅ 不触发 |
| 5 | 上传文档 → 自动分类 | 归入已有类别 | ✅ CSS → 前端模板 |
| 6 | 上传无关文档 → 新建类别 | 自动创建 | ✅ 量子计算 → 其他技术 |
| 7 | 超短文档 → 跳过 | skipped: true | ✅ |
| 8 | 服务启动 | 3 个 MCP Server | ✅ 5 个工具注册 |
| 9 | 前端 toggle 状态持久化 | localStorage | ✅ |
| 10 | 分类进度查询 | GET /admin/categories/progress | ✅ |

---

## 六、与 V2.2 的对比

| 维度 | V2.2 | V2.3 |
|------|------|------|
| **联网搜索** | 无 | MCP web_search 工具，Bing + httpx |
| **分类方式** | 仅全量生成 | 全量 + 增量（上传自动分类） |
| **分类进度** | 无 | 进度文件 + 前端轮询 + API |
| **MCP Server 数** | 2 (doc + sqlite) | 3 (+ web_search) |
| **工具数** | 4 | 5 (+ web_search) |
| **路由数** | 23 | 24 (+ /admin/categories/progress) |
| **ChatRequest 字段** | 5 | 6 (+ web_search) |
| **AgentState 字段** | 16 | 17 (+ web_search) |
| **依赖** | 无外部搜索 | httpx（已有） |

---

## 七、风险与局限

| 风险 | 缓解 |
|------|------|
| Bing HTML 结构变化 | 正则解析需维护；可切 SearXNG API |
| Bing 可能限流 | 当前 Agent 使用频率很低 |
| 搜索延时（~1-2s） | `asyncio.to_thread` 不阻塞 |
| DuckDuckGo 在国内不可用 | 已切 Bing |

---

## 八、未改动

- ReAct 5 节点核心逻辑
- 检索管线（Dense / BM25 / RRF）
- MCP 协议层架构（ClientManager 扩展，不重构）
- 索引层（ChromaDB + BM25 + Embeddings）
- 评测层（RAGAS）
- Session 持久化
- CSS 滚动体系
- 类别过滤检索逻辑
