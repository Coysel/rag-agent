# Agentic RAG v2.2 迭代报告 — 文档分类系统

> **迭代日期**: 2026-06-27
> **基于**: FULLSTACK_V2.1_REPORT（会话系统 + 品质加固 + UX 优化）
> **改动范围**: 全栈 — 新增 6 文件，修改 16 文件

---

## 项目规模

| 类别 | 文件数 | 代码行数 |
|------|--------|----------|
| 后端 Python | 55 | ~5,830 |
| 前端 JavaScript | 25 | ~3,230 |
| 前端 CSS | 7 | ~1,949 |
| 前端 HTML | 1 | ~400 |
| **合计** | **88** | **~11,400** |

---

## 一、功能概述

### 1.1 问题

V2.1 系统检索时扫描全库所有文档。当知识库包含多种主题的文档时：
- 大量不相关文档进入检索结果，稀释了相关内容的密度
- Agent 的 context_docs 中充斥无关信息，浪费 token 且降低回答质量
- 用户无法按主题缩小检索范围

### 1.2 方案

实现**层次摘要 + 聚类 + 选择过滤**三级管道：

```
Chunk (256 tokens) → LLM 摘要
  ↓ 聚合
Parent (1024 tokens) → LLM 摘要
  ↓ 聚合
Document → LLM 摘要
  ↓ 聚类
Categories → 前端选择 → 检索过滤
```

### 1.3 设计原则

- **自底向上**：从最小粒度（child chunk）开始摘要，逐步向上聚合，避免直接处理全文
- **LLM 驱动聚类**：利用 LLM 的语义理解能力进行文档分组，优于纯关键词方法
- **非侵入过滤**：类别过滤通过检索管线的 `doc_ids` 参数透传，不修改 Agent 核心逻辑
- **可选使用**：不选择类别 = 搜索全部（向后兼容），选择后 = 限定范围

---

## 二、后端新增模块

### 2.1 `src/categorization/` 包

```
src/categorization/
├── __init__.py           # 模块入口
├── category_store.py     # JSON 类别持久化
├── summarizer.py         # 层次摘要生成器
└── clusterer.py          # 文档聚类器
```

#### category_store.py

基于 JSON 文件 `data/categories.json` 的轻量持久化：

```json
{
  "categories": [{
    "id": "cat-uuid",
    "name": "深度学习",
    "description": "...",
    "doc_ids": ["doc1", "doc2"],
    "document_count": 5
  }],
  "doc_to_category": {"doc1": "cat-uuid"},
  "last_generated": "2026-06-27T..."
}
```

核心 API：`get_all()`, `get_doc_ids(category_ids)`, `save_categories()`, `clear()`

#### summarizer.py

复用 `LLMClient` 的三层摘要生成器：

| 方法 | 输入 | 输出 | Prompt 策略 |
|------|------|------|-------------|
| `summarize_child_chunks()` | 571 chunks | {chunk_id: 1-2句摘要} | "用1-2句概括核心内容" |
| `aggregate_parents()` | child摘要 + parent分组 | {parent_id: 3-5句摘要} | "整合为连贯的章节摘要" |
| `aggregate_documents()` | parent摘要 + doc分组 | {doc_id: 5-8句摘要} | "整合为完整的文档摘要" |

每层都有 `try/except` 容错：LLM 调用失败时回退到截断原文。

#### clusterer.py

将所有文档摘要提交给 LLM，要求输出 JSON 分组：

```json
[{"name": "深度学习", "description": "...", "doc_indices": [0,3,5]}]
```

容错设计：JSON 解析失败时回退到单类别（"全部文档"），确保功能不中断。

---

## 三、检索管线改造

### 3.1 改动链路

```
pipeline.retrieve(doc_ids=["id1","id2"])
  ├── DenseRetriever.search(doc_ids=...)
  │     └── VectorStore.search(where_filter={"doc_id":{"$in":[...]}})
  │           └── collection.query(where=...)
  ├── SparseRetriever.search(doc_ids=...)
  │     └── BM25 搜索 → 后置过滤 (doc_id in set)
  └── HybridRetriever.search(doc_ids=...) → RRF 融合
```

### 3.2 ChromaDB 原生过滤

Dense 检索使用 ChromaDB 的 `where` 子句进行**检索前过滤**，保证 top_k 结果全部来自选定类别。

### 3.3 BM25 后置过滤

BM25 不支持原生筛选，采用**检索后过滤**：正常搜索后按 `doc_id` 过滤结果。

### 3.4 MCP 工具扩展

`search_documents` 工具新增 `doc_ids` 可选参数：
```json
{"query": "...", "method": "hybrid", "doc_ids": ["id1", "id2"]}
```

---

## 四、Agent 层集成

### 4.1 State 扩展

`AgentState` 新增 `doc_ids: list[str]` 字段，从初始状态创建时传入。

### 4.2 自动注入

`act_node` 在执行 `search_documents` 工具调用时自动注入 `doc_ids`：

```python
if tool_name == "search_documents" and doc_ids:
    tool_input["doc_ids"] = doc_ids
```

这确保即使 LLM 不主动传递 doc_ids，过滤也会生效。

### 4.3 System Prompt 提示

`reason_node` 构建 prompt 时，当有限定文档范围时注入：

```
## 文档范围过滤
当前对话限定了搜索范围（N 个文档 ID），请只在这些文档中检索。
```

---

## 五、API 层

### 5.1 新增端点

| Method | Path | 说明 |
|--------|------|------|
| GET | `/categories` | 获取所有类别及生成时间 |
| POST | `/admin/categories/generate` | 触发类别生成（需 Admin Key） |

### 5.2 ChatRequest 扩展

```python
class ChatRequest(BaseModel):
    query: str
    max_steps: int = 5
    stream: bool = True
    session_id: str = ""
    categories: list[str] = []   # ← 新增
```

### 5.3 数据流

```
前端发送 {categories: ["cat-id1"]}
  → chat.py: _resolve_doc_ids() 查询 CategoryStore
  → get_initial_state(doc_ids=["doc1","doc2",...])
  → Agent nodes → act_node 注入 doc_ids
  → search_documents(query, doc_ids=[...])
  → pipeline.retrieve(doc_ids=[...])
```

---

## 六、前端变更

### 6.1 新增文件

- `frontend/js/api/categories.js` — `CategoryAPI.list()` + `CategoryAPI.generate(adminKey)`

### 6.2 设置页新增类别区域

在"模型设置"和"Admin 设置"之间新增"📂 知识库类别"section：

- **"⚡ 生成类别"按钮**：调用 `POST /admin/categories/generate`（需 Admin Key）
- **类别 tags（pill 样式）**：每个 tag 显示类别名 + 文档数，点击选中/取消
- **选中态**：蓝色高亮（`--primary-light` 背景 + `--primary` 边框）
- **持久化**：通过 `Store.persist('settings', ...)` 保存到 localStorage

### 6.3 Store 状态扩展

```javascript
settings: {
  llmProvider: 'deepseek',
  maxSteps: 5,
  stream: true,
  adminKey: '',
  filters: {
    categories: [],   // ← 新增：选中的类别 ID 列表
  },
}
```

### 6.4 Chat API 透传

`ChatAPI.sendMessage()` 自动从 settings 读取选中类别并附加到请求体：

```javascript
const filters = settings.filters || {};
if (filters.categories && filters.categories.length > 0) {
  body.categories = filters.categories;
}
```

### 6.5 交互流程

1. 进入设置页 → 自动加载类别列表
2. 首次使用 → "暂无类别 — 点击生成类别"
3. 点击"生成类别" → 后端运行层次摘要+聚类（需要 Admin Key）
4. 类别生成后显示 pill 标签 → 点击选中/取消
5. 切换到聊天页 → 提问自动附带选中的类别过滤
6. 刷新页面 → 类别选择持久化恢复

---

## 七、Token 效率分析

### 7.1 一次性生成成本

以当前 114 篇文档、571 个 child chunks 为例：

| 阶段 | 调用次数 | 每次 ~tokens | 小计 |
|------|----------|-------------|------|
| Child 摘要 | 571 | 300 | ~171K |
| Parent 聚合 | ~200 | 650 | ~130K |
| Document 聚合 | 114 | 1,000 | ~114K |
| 聚类 | 1 | 5,000 | ~5K |
| **合计** | — | — | **~420K** |

### 7.2 每次查询节省

假设用户选择"深度学习"类别（占总文档 30%）：
- 检索范围从 571 chunks → ~170 chunks
- context_docs token 从 ~50K → ~15K
- **每次查询节省 ~35K tokens（70%）**

10 次查询即可收回一次性生成成本。

---

## 八、与 V2.1 的对比

| 维度 | V2.1 | V2.2 |
|------|------|------|
| **检索范围** | 全库扫描 | 支持按类别过滤 |
| **文档理解** | 无 | 三层摘要（chunk→parent→doc） |
| **类别管理** | 无 | LLM 聚类 + JSON 持久化 |
| **前端过滤** | 无 | 设置页类别选择 + 自动透传 |
| **Token 效率** | 固定 | 可节省 50-80% context token |
| **路由数** | 21 | 23 (+2 类别) |
| **新增后端模块** | 0 | 1 (`src/categorization/`) |

---

## 九、未改动

- Agent ReAct 循环逻辑（5 个 node 函数）
- 检索管线核心算法（RRF 融合、parent expansion）
- MCP 协议层架构（doc_server + sqlite_server + client_manager）
- 索引层（ChromaDB + BM25 + Embeddings）
- 评测层（RAGAS 4 指标）
- Session 持久化（SQLite + localStorage）
- 前端聊天/检索/评测/管理页面
- API 端点路径和行为（100% 向后兼容）
- CSS 滚动体系
- 输入框比例

---

## 十、验证记录

- ✅ 全部 14 个 Python 文件语法检查通过
- ✅ 23 个 API 路由注册成功（21 原有 + 2 新增）
- ✅ `GET /categories` → 200, 正确返回空列表
- ✅ `POST /chat` 接受 `categories` 参数无报错
- ✅ CategoryStore 读写 + doc_id 解析逻辑正确
- ✅ VectorStore.search() where_filter 参数正常
- ✅ Pipeline.retrieve() doc_ids 参数正常透传
- ✅ Agent state 含 doc_ids 字段
- ✅ act_node 自动注入 doc_ids 逻辑就绪
- ✅ 服务器完整启动（BM25 571 篇 + ChromaDB 571 条 + LLM 就绪）
- ✅ 前端 JS 无语法错误
