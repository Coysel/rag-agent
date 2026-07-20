# 文档分类系统 — 层次摘要 + 聚类 + 检索过滤

**日期**: 2026-06-27
**类型**: feature
**影响范围**: 全栈（backend + frontend）

## 概述

实现文档自动分类功能：对已索引文档进行层次摘要生成（chunk → parent → document），然后基于文档摘要进行语义聚类，将相似文档归入类别。用户可在前端选择类别，检索时仅搜索选中类别的文档，从而减少 token 消耗、提高回答精度。

## 架构

```
Chunks (256 tokens)
  │  LLM: 每个 chunk → 1-2句摘要
  ▼
Parent 摘要（聚合 child 摘要）
  │  LLM: 合并 child 摘要
  ▼
Document 摘要（聚合 parent 摘要）
  │  LLM: 合并 parent 摘要
  ▼
聚类（所有文档摘要 → 类别分组）
  │  LLM: 输出 [{name, description, doc_indices}]
  ▼
JSON 存储 (data/categories.json)
  │
  ▼
前端选择类别 → 聊天时带 categories 参数
  │
  ▼
检索管线过滤 (doc_ids → ChromaDB where + BM25 后置)
```

## Token 估算

以 114 篇文档（当前索引规模）为例：
- 571 child chunks × ~300 tokens = ~171K
- ~200 parent × ~650 tokens = ~130K
- 114 document × ~1,000 = ~114K
- 1 次聚类 ~5K
- **总计: ~420K tokens（一次性）**

后续每次查询因缩小检索范围可节省 50-80% context token。

## 新增文件

| 文件 | 说明 |
|------|------|
| `src/categorization/__init__.py` | 模块入口 |
| `src/categorization/category_store.py` | JSON 类别持久化 |
| `src/categorization/summarizer.py` | 层次摘要生成器 |
| `src/categorization/clusterer.py` | 文档聚类器 |
| `src/api/routes/categories.py` | 类别 API 端点 |
| `frontend/js/api/categories.js` | 前端类别 API 封装 |

## 修改文件

| 文件 | 改动 |
|------|------|
| `config.py` | 新增 `CATEGORY_SUMMARY_MODEL` |
| `src/agent/state.py` | 新增 `doc_ids: list[str]` 字段 |
| `src/agent/graph.py` | `get_initial_state()` 接受 `doc_ids` |
| `src/agent/nodes.py` | `act_node` 自动注入 doc_ids, system_prompt 注入过滤提示 |
| `src/indexing/vector_store.py` | `search()` 增加 `where_filter` 参数 |
| `src/retrieval/dense_retriever.py` | `search()` 增加 `doc_ids` 参数 |
| `src/retrieval/sparse_retriever.py` | `search()` 增加 `doc_ids` 参数（后置过滤） |
| `src/retrieval/hybrid_retriever.py` | `search()` 增加 `doc_ids` 参数 |
| `src/retrieval/pipeline.py` | `retrieve()` 增加 `doc_ids` 参数 |
| `src/mcp/doc_server.py` | Tool schema + handler 增加 `doc_ids` |
| `src/api/schemas/chat.py` | `ChatRequest` 增加 `categories: list[str]` |
| `src/api/routes/chat.py` | 端点解析 categories → doc_ids → Agent state |
| `src/api/routes/__init__.py` | 注册 categories 路由 |
| `frontend/index.html` | 设置页新增类别 section + script 引入 |
| `frontend/js/config.js` | 新增 categories 端点 |
| `frontend/js/api/chat.js` | `sendMessage()` 附加 categories |
| `frontend/js/store/state.js` | settings 增加 `filters.categories` |
| `frontend/js/pages/settings.js` | 类别 tags 渲染 + 生成按钮 + 选择交互 |

## 新增 API 端点

| Method | Path | 说明 |
|--------|------|------|
| GET | `/categories` | 获取所有类别 |
| POST | `/admin/categories/generate` | 生成类别（需 Admin Key） |

## 验证

- ✅ `GET /categories` → 200
- ✅ `POST /chat` 接受 `categories` 参数
- ✅ Dense 检索支持 ChromaDB where 过滤
- ✅ BM25 检索支持后置 doc_id 过滤
- ✅ Agent state 透传 doc_ids
- ✅ `act_node` 自动注入 doc_ids 到 search_documents
- ✅ system_prompt 含类别过滤提示
- ✅ 前端类别 tags 渲染 + 选中交互
- ✅ 所有 23 个路由注册成功
- ✅ 不影响已有功能（chat/retrieval/eval/admin/settings）
