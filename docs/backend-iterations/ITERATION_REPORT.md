# Agentic RAG 项目 — 迭代改进详细解析文档

> 本次迭代日期：2026-06-26
> 总计改动：8 项改动组，25 个模块通过导入验证，20 个测试用例（19 通过 / 1 跳过）

---

## Phase A：降低复杂度 & 消除死代码

### A1. 新建 `src/retrieval/pipeline.py` — 统一检索入口

**删除了什么：**
- `doc_server.py` 中 `_search_documents()` 的 30 行检索逻辑（直接调用 3 个检索器 + parent 展开）
- `ragas_eval.py` 中 `_retrieve_docs()` 的 25 行重复检索逻辑

**修改了什么：**
- 新建 `src/retrieval/pipeline.py`，提供单一函数 `retrieve()` 作为全项目所有检索调用的唯一入口
- `doc_server.py:_search_documents()` → 改为 1 行委托调用 `retrieve()`
- `ragas_eval.py:_retrieve_docs()` → 改为 1 行委托调用 `retrieve()`

**为什么要改：**
项目中存在三套完全并行的检索代码：MCP Agent 用的一套、RAGAS 评测用的一套、前端检索对比用的一套。三套代码逻辑相同但实现有微妙差异（比如有的调了 `expand_to_parents()` 有的没调），导致线上行为和评测行为不一致。

**目的达成情况：** ✅ 达成。所有检索调用现在走同一路径，行为保证一致。后续要修改检索逻辑只需改一个文件。

---

### A2. 激活 Router 分类 → 接入检索策略

**删除了什么：**
- 无删除（原有 Router 分类代码保留，只是之前的结果从未被使用）

**修改了什么：**
- `config.py`：新增 `DENSE_WEIGHT = 1.0` 和 `SPARSE_WEIGHT = 1.0` 配置项
- `src/retrieval/hybrid_retriever.py`：`reciprocal_rank_fusion()` 新增 `dense_weight` / `sparse_weight` 参数，实现加权 RRF
- `src/agent/nodes.py`：新增 `_get_retrieval_hint()` 函数，根据 `query_type` 生成检索策略提示；`reason_node` 读取 `query_type` 并注入 system prompt

**为什么要改：**
`QueryRouter.classify()` 对每条查询做了分类（factual/conceptual/multi_hop），但分类结果只写入了 State，从未被任何 Agent 节点读取。这导致 Router 成了死代码——分类了但没人用。现在分类结果直接影响 Agent 的检索策略选择。

**目的达成情况：** ✅ 达成。factual 查询提示 Agent 优先用 BM25 关键词检索，conceptual 查询提示优先用 Dense 语义检索，multi_hop 查询提示链式调用多个工具。加权 RRF 在 config 层预留了动态调整能力。

---

### A3. 删除 `tools.py` 硬编码工具定义

**删除了什么：**
- `src/agent/tools.py` 中 98 行的 `OPENAI_TOOL_DEFINITIONS` 硬编码列表
- 74 行的 `ANTHROPIC_TOOL_DEFINITIONS` 硬编码列表
- `get_tool_definitions()` 原始函数（回退到硬编码的逻辑）

**修改了什么：**
- `tools.py` 保留单一函数 `get_tool_definitions()` → 直接从 MCP `client_manager` 动态获取
- MCP 未初始化时主动抛出 `RuntimeError`（而非静默回退到不一致的硬编码定义）
- `nodes.py` 导入 `get_dynamic_tool_definitions` → 改为 `get_tool_definitions`

**为什么要改：**
维护两套工具定义（MCP 动态发现 + 硬编码）是典型的"看起来安全实际有害"的实践。MCP 初始化失败时整个系统不可用，回退到硬编码定义没有意义。而且存在硬编码版本和 MCP Server 定义不一致的风险（比如有人改了 Server 的 tool schema 但忘了同步更新 tools.py）。

**目的达成情况：** ✅ 达成。工具定义唯一来源于 MCP Server 的 `list_tools()`，保证了一致性。

---

## Phase B：企业级能力

### B1. 结构化日志 + 请求追踪

**新增了什么：**
- 新建 `src/utils/logging.py`：基于 loguru 的统一日志系统
  - 每请求自动生成 `correlation_id`（8 位 uuid）
  - 开发环境：彩色文本格式；生产环境：JSON 格式
  - `ContextVar` 保证协程安全
- 新建 `src/utils/__init__.py`

**修改了什么：**
- `main.py`：lifespan 启动时调用 `setup_logging()`，所有 `print()` 改为 logger 调用
- `src/api/routes.py`：每个 `/chat` 请求生成 `correlation_id`，记录请求到达
- `src/agent/nodes.py`：5 个节点（reason/act/observe/reflect/answer）全部增加耗时记录和结构化日志

**日志示例（开发环境）：**
```
14:32:05 | INFO    | a3f8b2c1  | 收到查询: PyTorch Conv2d 的 stride 默认值...
14:32:06 | INFO    | a3f8b2c1  | Reason(1/5) → 调用工具: ['search_documents'] | 1234ms | type=factual
14:32:06 | INFO    | a3f8b2c1  | Act → search_documents | 89ms | 返回 8 条
14:32:06 | INFO    | a3f8b2c1  | Observe → +5 篇, 共 5 篇 | doc1, doc2, doc3
14:32:07 | INFO    | a3f8b2c1  | Reflect → answer (信息充足) | 5 篇文档
14:32:08 | INFO    | a3f8b2c1  | Answer → 856 字符 | 5 篇来源 | 1023ms
```

**为什么要改：**
原项目全用 `print()` 做日志，无时间戳、无请求追踪、无结构化信息。在生产环境中排查问题时无法关联多行日志到同一个请求，也无法按级别过滤。新增的 `correlation_id` 让每个请求的所有节点日志可追踪，耗时记录可用来做性能分析。

**目的达成情况：** ✅ 达成。所有关键路径都有结构化日志覆盖。

---

### B2. 错误处理 & 韧性

**修改了什么：**
- `src/agent/llm_client.py`：
  - 新增 `MAX_RETRIES = 3` 和 `RETRY_BASE_DELAY = 1.0` 配置
  - `create_message()` 增加指数退避重试（1s → 2s → 4s）
  - 自动识别可重试错误（rate_limit/timeout/connection/server_error）
  - 不可重试的错误（如 auth 错误）直接抛出
- `src/api/routes.py`：
  - 新增 `GET /health/deep` 端点：验证 LLM 连通性 + 检索功能，返回各组件状态和延迟

**深度健康检查响应示例：**
```json
{
  "status": "ok",
  "checks": {
    "llm": {"status": "ok", "latency_ms": 456},
    "retrieval": {"status": "ok", "doc_count": 8, "latency_ms": 23}
  }
}
```

**为什么要改：**
LLM API 调用会因为限流、网络抖动、服务端临时故障而偶发失败。没有重试机制的话，用户看到的就是"请求失败"——实际上等 1 秒重试就成功了。普通的健康检查只验证"服务进程在运行"，不验证"LLM 能连通"，运维人员无法快速判断故障点。

**目的达成情况：** ✅ 达成。API 调用有 3 次重试，支持指数退避。深度健康检查可精确定位故障组件。

---

### B3. 增量索引 & 文档管理 API

**新增了什么：**
- 新建 `src/indexing/index_manager.py`：`IndexManager` 类
  - `add_document(content, title, source)` → 增量添加纯文本文档
  - `add_file(file_path)` → 增量添加文件
  - `remove_document(doc_id)` → 从 ChromaDB + BM25 + Parent 映射中完整移除
  - `rebuild_all()` → 全量重建（保留 CLI 兼容）
  - 全局单例 `get_index_manager()`
- 新建 `src/api/admin_routes.py`：Admin API 端点（需 API Key 鉴权）
  - `GET /admin/documents` — 列出所有文档
  - `POST /admin/documents` — 添加文档（JSON 格式）
  - `DELETE /admin/documents/{doc_id}` — 删除文档
  - `POST /admin/rebuild` — 全量重建索引

**修改了什么：**
- `src/indexing/vector_store.py`：新增 `delete_by_doc_id(doc_id)` — 按 doc_id 元数据过滤删除所有 chunks
- `src/indexing/bm25_index.py`：新增 `add_documents()` — 增量追加；`remove_by_doc_id()` — 按 doc_id 移除 chunks 并重建 BM25 索引
- `main.py`：注册 `admin_router`

**鉴权方式：**
```
Admin API Key: Header X-Admin-Key
环境变量 ADMIN_API_KEY（默认值：admin-secret-change-me）
```

**为什么要改：**
原来只能通过 CLI 脚本 `python scripts/index_documents.py` 全量重建索引——每次添加一篇文档需要重新处理所有文档，极其低效。现在支持 API 级别的增量操作：上传一篇新文档 → 只处理这一篇 → 追加到已有索引。生产环境中的知识库需要持续更新，全量重建不可接受。

**目的达成情况：** ✅ 达成。支持增量添加/删除文档。BM25 的增量实现是"重建索引对象"（因为 rank_bm25 无增量 API），但本质上是追加新 chunk 到 corpus 后重建——对于知识库更新场景（分钟级）足够快。

---

### B4. 多轮对话支持

**新增了什么：**
- 新建 `POST /chat/session` 端点：基于 `session_id` 的多轮对话
- 进程内会话存储 `_sessions: dict[str, list[dict]]`（保留最近 10 轮）
- SSE 流式版本的会话更新逻辑

**修改了什么：**
- `src/agent/state.py`：`AgentState` 新增 `conversation_history: list[dict]` 和 `session_id: str` 字段
- `src/agent/graph.py`：`get_initial_state()` 新增 `conversation_history` 和 `session_id` 参数
- `src/agent/nodes.py`：`_build_system_prompt()` 新增历史对话格式化 + "如果用户问题是对上一轮的追问，结合历史对话理解意图"规则
- `reason_node` 读取 `conversation_history` 传入 system prompt

**多轮对话示例：**
```
用户: "PyTorch Conv2d 有哪些参数？"
Agent: [检索] → 回答: stride, padding, kernel_size, dilation, groups...
用户: "stride 的默认值是多少？"
Agent: [历史上下文] 正在讨论 PyTorch Conv2d → [检索] → 回答: stride 默认为 1
```

**为什么要改：**
原系统每次 `/chat` 都是无状态单轮问答。用户追问"详细说下第二个参数"时，Agent 不知道"第二个参数"指的是上一轮回答中提到的 padding。多轮对话是现实使用场景的刚需。

**目的达成情况：** ✅ 达成。会话管理 + 历史注入 system prompt。当前使用进程内内存存储（`_sessions` dict），重启丢失——适合单机部署。如需跨实例/持久化，后续可切换为 Redis。

---

### B5. 测试体系搭建

**新增了什么：**
- `pytest.ini`：测试配置（asyncio auto 模式）
- `tests/conftest.py`：共享 fixtures（sample_documents, sample_chunks, sample_query）
- `tests/test_loader.py`：6 个测试 — `_split_by_tokens` 长短文本/空文本 + `chunk_documents` 字段完整性/parent 数量/映射一致性
- `tests/test_nodes.py`：7 个测试
  - `TestReasonNode`：LLM 无 tool_calls → 直接 answer、有 tool_calls → continue、LLM 异常 → 错误处理
  - `TestObserveNode`：ID 去重逻辑、空 ID 跳过（**验证之前的关键 bug 不会回归**）
  - `TestReflectNode`：max_steps 强制回答、无文档继续检索
- `tests/test_retrieval.py`：7 个测试
  - `TestParentRetriever`：映射构建、多 child→单 parent 去重、空结果
  - `TestRRF`：基本融合（1 doc）、去重融合（3 docs）、加权融合（权重为 0 时分数为 0）

**测试结果：**
```
tests/test_loader.py       — 6 passed
tests/test_nodes.py        — 7 passed
tests/test_retrieval.py    — 6 passed, 1 skipped
总计                       — 19 passed, 1 skipped
```

**为什么要改：**
项目零测试覆盖率，所有质量验证依赖手工操作。`observe_node` 的 id 缺失 bug 就是因为没有单元测试来验证去重逻辑。有了这层测试，后续修改节点逻辑或检索管线时，`pytest tests/ -v` 就能快速发现回归。

**目的达成情况：** ✅ 达成。20 个测试覆盖了检索管线、文档分块、Agent 节点三个核心模块。`test_empty_id_skipped` 专门防守之前最严重的 bug。

---

## 改动总结表

| 阶段 | 项目 | 新增文件 | 修改文件 | 删除代码行 | 新增代码行 |
|------|------|----------|----------|-----------|-----------|
| A1 | 统一检索管道 | `src/retrieval/pipeline.py` | `doc_server.py`, `ragas_eval.py` | ~55 | ~65 |
| A2 | Router 激活 | — | `config.py`, `hybrid_retriever.py`, `nodes.py` | 0 | ~50 |
| A3 | 清理硬编码 | — | `tools.py`, `nodes.py` | ~175 | ~25 |
| B1 | 日志系统 | `src/utils/__init__.py`, `src/utils/logging.py` | `main.py`, `nodes.py`, `routes.py` | ~5 | ~120 |
| B2 | 错误处理 | — | `llm_client.py`, `routes.py` | 0 | ~65 |
| B3 | 增量索引 | `src/indexing/index_manager.py`, `src/api/admin_routes.py` | `vector_store.py`, `bm25_index.py`, `main.py` | 0 | ~250 |
| B4 | 多轮对话 | — | `state.py`, `graph.py`, `nodes.py`, `routes.py` | 0 | ~120 |
| B5 | 测试体系 | `tests/`, `pytest.ini` | — | 0 | ~280 |
| **合计** | | **7 个新文件** | **14 个修改文件** | **~235** | **~975** |

## 验证记录

1. ✅ 25 个模块全部通过 Python import 验证
2. ✅ 20 个测试用例 19 通过 / 1 跳过
3. ✅ 启动日志包含 `correlation_id` 追踪
4. ✅ `GET /health/deep` 深度健康检查可用
5. ✅ Admin API 鉴权正确拒绝未授权请求

## 后续建议（未在本次迭代实施）

| 优先级 | 建议 | 说明 |
|--------|------|------|
| P1 | 会话存储迁移 Redis | 当前进程内存储重启丢失 |
| P1 | 前端引用高亮 | `[来源: 文档N]` 渲染为可点击链接 |
| P1 | 用户反馈收集 | `POST /feedback` + SQLite 存储 |
| P2 | LLM Provider 降级链 | DeepSeek → Anthropic 自动切换 |
| P2 | CI/CD 集成 | GitHub Actions 自动跑 pytest |
| P3 | 向量库抽象接口 | 支持 Qdrant/Milvus 切换 |
| P3 | 异步后台索引 | 大文档上传后后台处理，轮询状态 |
