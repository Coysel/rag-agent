# Agentic RAG v2.1 迭代报告 — 会话系统 + 品质加固 + UX 优化

> **迭代日期**: 2026-06-27
> **基于**: FULLSTACK_V2_REPORT（后端分层重构 + 前端模块化重写）
> **改动范围**: 前端会话持久化、CSS 滚动修复、输入框 UX 调整、前端代码去重、changelog 体系

---

## 项目规模

| 类别 | 文件数 | 代码行数 |
|------|--------|----------|
| 后端 Python | 50 | 5,315 |
| 前端 JavaScript | 24 | 3,030 |
| 前端 CSS | 7 | 1,949 |
| 前端 HTML | 1 | 390 |
| **合计** | **82** | **～10,700** |

---

## 一、前端对话记录系统（新增）

### 1.1 问题

V1/V2.0 的消息存储在 `rag_chat_history` —— 一个扁平数组。没有会话概念：
- 刷新页面后消息虽在 localStorage，但无法区分不同对话
- 侧栏会话列表只从后端 SQLite 读取，前端无本地会话管理
- 切换会话不加载历史消息
- 无法删除会话

### 1.2 架构

```
localStorage
├── rag_sessions          → [{id, title, messageCount, updatedAt}, ...]
├── rag_session_{id}      → [{role, content, sources, steps, queryType, timestamp}, ...]
└── rag_settings          → {llmProvider, maxSteps, ...}
```

- 每会话独立存储，上限 200 条/会话，最多 50 个会话
- Session ID = `crypto.randomUUID().slice(0, 8)`
- 标题自动提取自第一条用户消息（前 40 字符）

### 1.3 改动文件

#### [frontend/js/store/state.js](../../frontend/js/store/state.js) — 新增 6 个会话 API

```javascript
Store.createSession()              // 创建新会话，返回 sessionId
Store.saveSessionMessages(id, msgs) // 保存消息 + 更新元数据
Store.loadSessionMessages(id)      // 加载指定会话消息
Store.switchSession(id)            // 切换会话并返回消息
Store.deleteSession(id)            // 删除会话及消息
Store.loadSessionList()            // 获取所有会话元数据
```

#### [frontend/js/app.js](../../frontend/js/app.js) — 重写侧栏会话管理

- `_initSidebar()` — 新建按钮调用 `Store.createSession()`
- `_restoreLastSession()` — 启动时自动恢复上次会话
- `_renderSessionList()` — 渲染会话列表（当前高亮、hover 显示删除 ✕）
- `_renderMessagesFromHistory()` — 从 localStorage 重建聊天界面（含 Markdown + 来源面板）
- 订阅 `sessions` 变更 → 自动刷新侧栏
- 新增 `Ctrl+N` 快捷键新建会话

#### [frontend/js/pages/chat.js](../../frontend/js/pages/chat.js) — 接入会话系统

- `send()` — 无会话时自动 `Store.createSession()`
- `_saveToHistory()` — 保存为结构化消息 `{role, content, sources, steps, queryType, timestamp}`
- `renderHistory(messages)` — 从历史 JSON 渲染聊天界面

#### [frontend/css/layout.css](../../frontend/css/layout.css) — 会话列表样式

- `.session-item` / `.session-item.active` — 激活态蓝色高亮
- `.session-delete-btn` — hover 时显示，hover 变红

### 1.4 用户交互流程

1. **首次使用** → 输入问题 → 自动创建会话 → 对话实时保存
2. **刷新页面** → 自动恢复上次会话 → 消息完整展示（含 Markdown + 来源面板）
3. **点击侧栏会话** → 切换会话 → 加载完整历史
4. **"+ 新建会话"** → 清空聊天区 → 创建空白会话
5. **hover 会话项 → 点 ✕** → 删除会话及所有消息
6. **Ctrl+N** → 新建会话 | **Ctrl+K** → 清空聊天 | **Esc** → 停止生成

---

## 二、CSS 滚动修复

### 2.1 问题

所有页面（chat / retrieval / eval / admin / settings）内容超出视口时**完全无法滚动**。消息列表、文档表格等超出部分被裁切。

### 2.2 根因

CSS Flexbox 规范：flex 子元素默认 `min-height: auto`（= 内容高度）。即使设置了 `flex: 1` + `overflow-y: auto`，flex 容器会随内容膨胀而非约束子元素高度，滚动条永远不会触发。

受影响的 flex 链条：

```
.app-container (height: 100vh)
  → .main-content (flex column)
    → .page (flex: 1)
      → .chat-messages / .content-area (flex: 1, overflow-y: auto)  ← 卡在这里
```

### 2.3 修复

| 文件 | 选择器 | 改动 |
|------|--------|------|
| [layout.css](../../frontend/css/layout.css) | `.main-content` | 新增 `overflow: hidden` |
| [layout.css](../../frontend/css/layout.css) | `.page` | 新增 `min-height: 0` |
| [layout.css](../../frontend/css/layout.css) | `.content-area` | 新增 `min-height: 0` |
| [chat.css](../../frontend/css/chat.css) | `.chat-messages` | 新增 `min-height: 0` |

### 2.4 原理

`min-height: 0` 允许 flex 子元素被收缩到内容高度以下 → `overflow-y: auto` 才能正常触发滚动条。这是 CSS Flexbox 最常见但最隐蔽的陷阱之一。

---

## 三、输入框比例调整

### 3.1 迭代过程

| 版本 | 输入栏高 | 内容宽 | 输入框高 | 问题 |
|------|----------|--------|----------|------|
| V2.0 初始 | 72px | 900px | 40px | 太小太低 |
| 第一次调整 | 88px | 900px | 48px | 重心仍偏下 |
| 第二次调整 | 64px | 960px | 42px | 理解反向（太扁） |
| **最终版** | **100px** | **720px** | **52px** | ✅ 高而窄，下 1/3 重心 |

### 3.2 最终配置

| 属性 | 值 | 文件 |
|------|-----|------|
| `--input-bar-height` | 100px | [tokens.css](../../frontend/css/tokens.css) |
| `--max-content-width` | 720px | [tokens.css](../../frontend/css/tokens.css) |
| `.chat-input` min-height | 52px | [chat.css](../../frontend/css/chat.css) |
| `.chat-input` font-size | 15px (`--text-md`) | [chat.css](../../frontend/css/chat.css) |
| `.send-btn` | 46×46px | [chat.css](../../frontend/css/chat.css) |
| `.input-bar` padding | 20px 24px | [layout.css](../../frontend/css/layout.css) |

### 3.3 设计意图

宽高比从 15:1（扁长）调整为 7:1（挺拔）。内容区收窄到 720px 将视线聚焦到对话流，输入栏抬高到 100px 将视觉重心拉到屏幕下三分之一——符合人机对话的视线流动。

---

## 四、代码去重

在 V2 模块化基础上进一步消除重复：

| 文件 | 改动 | 影响 |
|------|------|------|
| [chat.js (routes)](../../src/api/routes/chat.py) | 提取 `_build_step_event()` | 两个 SSE 生成器共享 |
| [documents.py](../../src/api/routes/documents.py) | 提取 `_get_document_list()` | admin + public 端点复用 |
| [chat.js (page)](../../frontend/js/pages/chat.js) | 提取 `_handleStep()` | 4 个 ReAct handler 合并 |
| [eval.js](../../frontend/js/pages/eval.js) | 移除死代码 `_appendResultRow` | 精简 20+ 行 |

---

## 五、品质加固

| 类别 | 改动 | 文件 |
|------|------|------|
| 速率限制 | 滑动窗口，chat 30/min, eval 10/min | [middleware.py](../../src/api/middleware.py) |
| 安全响应头 | CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy | [middleware.py](../../src/api/middleware.py) |
| CORS 白名单 | 从 `CORS_ORIGINS` 配置读取，不再 `"*"` | [middleware.py](../../src/api/middleware.py) |
| Admin Schema | `AddDocumentRequest` Pydantic 模型（min_length 校验） | [common.py](../../src/api/schemas/common.py) |
| HF 离线模式 | `HF_HUB_OFFLINE=1` 跳过网络检查，缓存秒加载 | [embeddings.py](../../src/indexing/embeddings.py) |
| `.gitignore` | Python + IDE + .env + data/ + logs 全覆盖 | [`.gitignore`](../../.gitignore) |
| pydantic-settings | `BaseSettings` 类型校验，`load_dotenv()` 注入 os.environ | [config.py](../../config.py) |

---

## 六、changelog 体系

建立 `changelogs/` 目录，每次代码修改生成独立 `.md` 文件：

```
changelogs/
├── README.md                                    # 命名规范 + 模板
├── 2026-06-27--fix-frontend-scroll.md           # CSS 滚动修复
├── 2026-06-27--enlarge-chat-input.md            # 输入框放大
├── 2026-06-27--rebalance-input-proportions.md   # 输入框比例再平衡
├── 2026-06-27--tall-narrow-input.md             # 高而窄最终方案
└── 2026-06-27--session-conversation-history.md  # 会话持久化
```

---

## 七、与 V2.0 的对比

| 维度 | V2.0 | V2.1 |
|------|------|------|
| **对话记录** | 扁平 localStorage 数组，无会话概念 | 多会话独立存储，侧栏管理，启动恢复 |
| **CSS 滚动** | flex 容器不滚动，内容裁切 | `min-height: 0` 修复，5 个区域全可滚动 |
| **输入框** | 900×72px，偏下偏小 | 720×100px，高而窄，下 1/3 视觉重心 |
| **代码去重** | 模块化已实现 | 进一步提取共享 helper（_build_step_event 等） |
| **安全** | 无速率限制，CORS `*` | 速率限制 + 安全头 + CORS 白名单 |
| **前端状态管理** | Store 基础功能 | + 6 个会话管理 API |
| **changelog** | 无 | 6 个变更日志 + README 规范 |

---

## 八、未改动

- Agent 层：ReAct 5 节点
- 检索层：混合检索管线
- 索引层：BM25 + ChromaDB + Embeddings
- MCP 层：doc-server + sqlite-server
- 评测层：RAGAS 4 指标
- 后端 Session 存储：SQLite（已存在，V2.1 前端接入）
- API 端点路径和行为：100% 向后兼容

---

## 九、验证记录

- ✅ 前端 5 个页面 (chat/retrieval/eval/admin/settings) 均正常滚动
- ✅ 会话持久化：刷新页面 → 自动恢复 → 消息完整 → 切换/删除正常
- ✅ 输入框比例：720×100px，视觉重心在下 1/3
- ✅ 速率限制 + 安全头配置生效
- ✅ HuggingFace 模型 4.5s 离线加载
- ✅ `python main.py` 启动正常，22 个路由注册成功

---

## 十、测试发现的 Bug（已修复）

### Bug 1: Store 订阅者不触发（state.js）

**根因**：`state.js` 中 5 个会话函数直接写 `_state.xxx = yyy`，绕过了 `setState()` 的通知机制。

**影响**：`Store.subscribe('sessions', ...)` 和 `Store.subscribe('currentSessionId', ...)` 永不触发。侧栏不会自动刷新。

**修复**：`createSession`, `saveSessionMessages`, `switchSession`, `deleteSession`, `loadSessionList` 全部改为使用 `setState({...})` 触发订阅通知。

### Bug 2: 无限递归（app.js）

**根因**：`_renderSessionList()` 调用 `Store.loadSessionList()` → `setState({sessions})` → 触发 `sessions` 订阅者 → 又调用 `_renderSessionList()` → 无限循环。

**修复**：`_renderSessionList()` 改为 `Store.get('sessions')` 只读取值，不触发 setState。仅 `_restoreLastSession()` 在初始化时调用 `loadSessionList()`。

详见 changelog: [2026-06-27--fix-session-store-subscriber-bugs.md](../../changelogs/2026-06-27--fix-session-store-subscriber-bugs.md)
