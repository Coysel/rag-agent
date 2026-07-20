# 前端对话记录 — 会话持久化与历史管理

**日期**: 2026-06-27
**类型**: feature
**影响范围**: frontend

## 问题描述

聊天消息仅在当前页面生命周期内存在，刷新后全部丢失。无会话概念，无法查看历史对话、切换会话、或恢复之前的对话上下文。

## 实现内容

### 核心架构

```
localStorage
├── rag_sessions          → [{id, title, messageCount, updatedAt}, ...]  (会话元数据)
├── rag_session_{id1}     → [{role, content, sources, ...}, ...]         (会话消息)
├── rag_session_{id2}     → [...]
└── rag_settings          → {llmProvider, maxSteps, ...}                 (用户设置)
```

- 每个会话独立存储消息，上限 200 条/会话
- 最多保留 50 个会话
- Session ID 由 `crypto.randomUUID()` 生成（8 位短 ID）
- 会话标题自动从第一条用户消息提取（前 40 字符）

### 修改文件

#### [frontend/js/store/state.js](frontend/js/store/state.js) — 新增会话管理 API
- `Store.createSession()` — 创建新会话，设为当前
- `Store.saveSessionMessages(id, messages)` — 保存消息并更新元数据
- `Store.loadSessionMessages(id)` — 加载指定会话消息
- `Store.switchSession(id)` — 切换到指定会话
- `Store.deleteSession(id)` — 删除会话及消息
- `Store.loadSessionList()` — 加载所有会话元数据

#### [frontend/js/app.js](frontend/js/app.js) — 重写侧栏会话管理
- `_initSidebar()` — 新建会话按钮调用 `Store.createSession()`
- `_restoreLastSession()` — 启动时自动恢复上次会话
- `_renderSessionList()` — 渲染会话列表（高亮当前、hover 显示删除按钮）
- `_renderMessagesFromHistory()` — 从历史消息重建聊天界面
- `_highlightSession()` — 切换会话时刷新侧栏
- 新增 `Ctrl+N` 快捷键新建会话
- 订阅 `sessions` 变更自动刷新侧栏

#### [frontend/js/pages/chat.js](frontend/js/pages/chat.js) — 接入会话系统
- `send()` — 无会话时自动调用 `Store.createSession()`
- `_saveToHistory()` — 保存为结构化消息 `{role, content, sources, steps, queryType, timestamp}` 而非扁平数组
- `clear()` — 调用 `Store.createSession()` 后清空界面
- 新增 `renderHistory(messages)` — 从历史消息渲染聊天界面（含 Markdown 和来源面板）

#### [frontend/css/layout.css](frontend/css/layout.css) — 会话列表样式
- `.session-item` / `.session-item.active` — 会话项（激活态蓝色高亮）
- `.session-delete-btn` — hover 时显示删除按钮，hover 变红

## 用户交互流程

1. **首次使用** → 输入问题 → 自动创建会话 → 对话保存
2. **刷新页面** → 自动恢复上次会话 → 消息完整展示
3. **点击侧栏会话** → 切换会话 → 加载历史消息
4. **点击 "+ 新建会话"** → 创建空白会话 → 清空聊天区
5. **hover 会话项 → 点 ✕** → 删除会话及所有消息
6. **Ctrl+N** → 新建会话快捷键

## 影响评估
- ✅ 刷新页面不丢失对话
- ✅ 支持多会话切换
- ✅ 会话可删除
- ✅ 历史消息含 Markdown 渲染 + 来源引用面板
- ✅ 无后端依赖，完全离线可用
- ✅ 与后端 `/chat/session` API 兼容（session_id 同步发送）
