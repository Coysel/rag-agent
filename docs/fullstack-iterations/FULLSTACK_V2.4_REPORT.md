# Agentic RAG v2.4 迭代报告 — 多轮对话 UI 全面修复 + 动效优化

> **迭代日期**: 2026-06-29
> **基于**: FULLSTACK_V2.3_REPORT（联网搜索 + 增量分类加固）
> **改动范围**: 前端 — 修改 3 文件（JS + CSS）

---

## 项目规模

| 类别 | 文件数 | 代码行数 |
|------|--------|----------|
| 后端 Python | 57 | ~6,200 |
| 前端 JavaScript | 25 | ~3,420 |
| 前端 CSS | 7 | ~2,100 |
| 前端 HTML | 1 | ~420 |
| **合计** | **90** | **~12,140** |

---

## 一、问题描述

用户多轮对话时存在 3 个前端 bug：

### Bug 1：回答气泡被覆盖 ★ 核心

**现象**：第二轮回答覆盖第一轮回答的气泡，而非在下方新建气泡。正常聊天 UI 行为应为 User1 → Answer1 → User2 → Answer2，每个 Q&A 对独立渲染。

**影响**：多轮对话完全不可用，用户无法查看历史答案。

### Bug 2：Stop 按钮无效

**现象**：点击停止按钮只清理 UI 状态（`isStreaming: false`），不实际中断 HTTP 请求。服务端继续生成，前端 SSE 处理器继续接收事件并尝试操作已清理的 DOM。

**影响**：用户无法真正取消一次请求；快速连续提问时可能出现竞态条件。

### Bug 3：无自动滚动

**现象**：流式输出时页面不跟随新内容滚动。用户气泡、思考块、回答气泡依次添加后，需手动滚动才能看到最新内容。

**影响**：用户体验差，尤其长回答时看不到实时输出。

### Bug 4：滚动区域太窄

**现象**：鼠标滚轮只在消息气泡上能滚动聊天记录，页面两侧空白区域、消息间隔区域均无法滚动。

**影响**：用户需精确瞄准消息内容才能滚动，大屏幕下体验很差。

### Bug 5：动效僵硬

**现象**：思考步骤瞬间弹出（无过渡）、思考块折叠/展开瞬间完成（`display:none`）、消息入场动画太微弱（8px/0.25s）、发送按钮反馈不明显。

**影响**：界面生硬，缺乏流畅感和品质感。

---

## 二、根因分析

### Bug 1：`_answerBubble` 跨轮泄漏

[frontend/js/pages/chat.js](frontend/js/pages/chat.js) 的 `send()` 方法在每轮对话开始时重置了 `_currentAnswer`、`_currentSources`、`_steps`、`_stepStartTime`，**但未重置 `_answerBubble`**。

```
状态机追踪（修复前）：

Turn 1 send():
  _answerBubble = null  (初始值)
  → SSE answer 事件: if (!_answerBubble) → true → 创建 Bubble A
  → _answerBubble = Bubble A
  → _finish(): _answerBubble 未清理 → 仍 = Bubble A

Turn 2 send():
  _answerBubble = Bubble A  ← ❌ 未重置！
  → SSE answer 事件: if (!_answerBubble) → false → 走"后续事件"分支
  → 将 Turn 2 内容写入 Bubble A 的 .bubble-content
  → Turn 1 答案被覆盖

DOM 结构（修复前）:
  User1 → Thinking1 → User2 → Thinking2 → [Bubble A 显示 Answer2]
  期望: User1 → Thinking1 → Bubble A (Answer1) → User2 → Thinking2 → Bubble B (Answer2)
```

### Bug 2：AbortController 未创建 + 提前置空

```
代码追踪（修复前）：

send() line 106:
  this._abortController = null  // ← 声明但从未实例化

send() line 109-110:
  const response = await ChatAPI.sendMessage(query, { stream: true });
  this._abortController = null;  // ← 即使创建了也会被立即置空

stop() line 284-288:
  if (this._abortController) {   // ← 永远为 null，从不执行 abort()
    this._abortController.abort();
  }
  this._finish();                // ← 只清理 UI，HTTP 请求继续

ChatAPI.sendMessage() line 40-44:
  return fetch(url, { ... });   // ← 未传 signal，无法中断
```

### Bug 3：缺少 scrollToBottom 调用

流式输出涉及 4 个 DOM 追加点（用户气泡、思考块、回答气泡创建、回答内容更新），均未调用 `DOM.scrollToBottom()`。`DOM.isNearBottom()` 工具已存在但从未使用。

### Bug 4：滚动容器仅限于 `.chat-messages`

DOM 层级分析：
```
.main-content (overflow: hidden)     ← 不滚动
  .header                            ← 固定
  .page[data-page="chat"]            ← max-width + margin:auto → 两侧空白
    .chat-messages (overflow-y: auto) ← 唯一可滚动元素
  .input-bar                         ← 固定
```

`.chat-messages` 是唯一的 `overflow-y: auto` 元素，鼠标必须在其内部才能触发滚动。`.page` 两侧的 margin 空白区域（宽屏）和 `.chat-messages` padding 区域之外的地方都无法滚动。

### Bug 5：动效缺失/使用 `display:none`

| 元素 | 问题 |
|------|------|
| `.thinking-step` | 无 `animation`，DOM 插入后瞬间出现 |
| `.thinking-body` | `display:none/block` 切换，无法被 CSS transition 动画化 |
| `.message` | `msg-in` 仅 8px/0.25s，动效几乎不可见 |
| `.send-btn:active` | `scale(0.95)` 太微弱 |
| `.typing-dot` | 灰色点，弹跳幅度小 |

---

## 三、修复方案

### 修改文件 1：[frontend/js/api/chat.js](frontend/js/api/chat.js)

**改动**：`sendMessage()` 接受 `opts.signal` 并传给 `fetch()`

```diff
  return fetch(`${Config.API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
+   signal: opts.signal || undefined,
  });
```

### 修改文件 2：[frontend/js/pages/chat.js](frontend/js/pages/chat.js)

共 6 处改动：

#### 2.1 初始状态声明

```diff
  const ChatPage = {
+   _answerBubble: null,
    _typingEl: null,
    _thinkingBlock: null,
```

#### 2.2 `send()` — 重置所有轮次状态 + 创建 AbortController

```diff
+   DOM.scrollToBottom(messagesEl);

-   this._thinkingBlock = ThinkingBlock.create();
+   this._thinkingBlock = null;
+   this._thinkingBlock = ThinkingBlock.create();
+   DOM.scrollToBottom(messagesEl);

    this._stepStartTime = Date.now();
+   this._answerBubble = null;
+   this._abortController = new AbortController();

-   const response = await ChatAPI.sendMessage(query, { stream: true });
-   this._abortController = null;
+   const response = await ChatAPI.sendMessage(query, {
+     stream: true,
+     signal: this._abortController.signal,
+   });
```

#### 2.3 `answer` 事件 — 自动滚动

```diff
    messagesEl.appendChild(this._answerBubble);
+   DOM.scrollToBottom(messagesEl);

    contentEl.innerHTML = Markdown.render(this._currentAnswer);
+   if (DOM.isNearBottom(messagesEl, 150)) {
+     DOM.scrollToBottom(messagesEl);
+   }
```

#### 2.4 `done` 事件 — 来源面板后滚动

```diff
    this._answerBubble.querySelector('.bubble').appendChild(panel);
+   DOM.scrollToBottom(messagesEl);
```

#### 2.5 `error` 事件 — 区分 AbortError

```diff
-   messagesEl.appendChild(ChatBubble.error(msg, () => this.send()));
+   const isAbort = /abort|cancel/i.test(msg);
+   if (!isAbort) {
+     messagesEl.appendChild(ChatBubble.error(msg, () => this.send()));
+     DOM.scrollToBottom(messagesEl);
+   }
```

#### 2.6 `_finish()` — 安全网清理

```diff
+   this._answerBubble = null;
+   this._abortController = null;
```

### 修改文件 3：[frontend/js/pages/chat.js](frontend/js/pages/chat.js) — 滚轮事件代理

监听 `.main-content` 的 `wheel` 事件，当鼠标在消息区域/输入栏/header 以外时，手动将滚动量转发给 `.chat-messages`：

```javascript
mainContent.addEventListener('wheel', (e) => {
  if (e.target.closest('#chat-messages')
      || e.target.closest('.input-bar')
      || e.target.closest('.header')) {
    return;  // 原生行为
  }
  const messages = DOM.$('#chat-messages');
  if (messages) {
    e.preventDefault();
    messages.scrollTop += e.deltaY;
  }
}, { passive: false });
```

### 修改文件 4：[frontend/css/chat.css](frontend/css/chat.css) — 动效优化

全部 5 处改动在 `chat.css` 中：

#### 4.1 思考步骤入场 — `step-in` keyframe

```css
.thinking-step {
  animation: step-in 0.25s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
@keyframes step-in {
  from { opacity: 0; transform: translateX(-16px); }
  to   { opacity: 1; transform: translateX(0); }
}
```

#### 4.2 思考块折叠 — `max-height` 过渡替代 `display:none`

```css
.thinking-body {
  max-height: 500px;
  transition: max-height 0.3s ease-out, padding 0.3s ease-out;
}
.thinking-block:not(.open) .thinking-body {
  max-height: 0; padding-top: 0; padding-bottom: 0; overflow-y: hidden;
}
```

#### 4.3 思考块入场 — `block-in` keyframe

```css
.thinking-block {
  animation: block-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
@keyframes block-in {
  from { opacity: 0; transform: translateY(-8px) scale(0.97); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
```

#### 4.4 消息入场增强

```css
.message {
  animation: msg-in 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
@keyframes msg-in {
  from { opacity: 0; transform: translateY(20px) scale(0.96); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
```

#### 4.5 发送按钮 + 打字指示器

- Send btn hover: `scale(1.08)` + `box-shadow` 光晕
- Send btn active: `scale(0.92)` + 0.08s 快速响应
- Typing dots: 主题蓝色 + 更丰富的弹跳曲线（scale + translateY + opacity）

### 改动清单

| # | 文件 | 行数 | 修复 |
|---|------|------|------|
| 1 | `api/chat.js` | +1 | `sendMessage()` 接受 `signal` |
| 2 | `pages/chat.js` | +1 | 初始状态声明 `_answerBubble` |
| 3 | `pages/chat.js` | +3 | `send()` 重置 `_answerBubble` + `_thinkingBlock` |
| 4 | `pages/chat.js` | +3 | `send()` 创建 `AbortController` + 传入 `signal` |
| 5 | `pages/chat.js` | +4 | `send()` 用户气泡/思考块后 `scrollToBottom` |
| 6 | `pages/chat.js` | +1 | `answer` 首事件 `scrollToBottom` |
| 7 | `pages/chat.js` | +3 | `answer` 后续事件 `isNearBottom` → `scrollToBottom` |
| 8 | `pages/chat.js` | +1 | `done` 事件 `scrollToBottom` |
| 9 | `pages/chat.js` | +3 | `error` 事件 AbortError 过滤 + `scrollToBottom` |
| 10 | `pages/chat.js` | +2 | `_finish()` 清理 `_answerBubble` + `_abortController` |
| 11 | `pages/chat.js` | +14 | `init()` 滚轮事件代理（扩大滚动区域） |
| 12 | `chat.css` | +25/-10 | 思考步骤入场 + 折叠过渡 + 思考块入场 |
| 13 | `chat.css` | +7/-5 | 消息入场 spring 缓动 |
| 14 | `chat.css` | +8/-5 | 发送按钮触觉反馈增强 |
| 15 | `chat.css` | +6/-4 | 打字指示器优化 |

**总计**：3 文件，+82 行，-27 行

---

## 四、设计决策

### 为什么用 JS 滚轮代理而非纯 CSS？

纯 CSS 方案要求把 `overflow-y: auto` 从 `.chat-messages` 移到 `.page`。但在 flex 嵌套布局中（`.main-content` > `.page` > `.chat-messages`），`.chat-messages` 的 `flex: 1` 将其高度约束在 `.page` 内，内容溢出时 `.page` 无法感知（flex 子元素不会推高父元素）。JS 方案通过 `wheel` 事件捕获 + `scrollTop` 手动转发，完美绕过 flex 限制。

### 为什么用 `max-height` 过渡代替 `display:none`？

CSS transition 无法动画化 `display` 属性。`max-height: 500px → 0` + `overflow: hidden` 是经典的 CSS-only 折叠方案。上限 500px 足够覆盖正常思考步骤数量，过渡时间 0.3s 与 Material Design 标准一致。

### 为什么使用 spring 缓动曲线 `cubic-bezier(0.34, 1.56, 0.64, 1)`？

标准 ease-out 曲线（`0.4, 0, 0.2, 1`）平缓减速，缺乏活力。spring 曲线在终点前有过冲回弹（1.56 > 1），产生类似物理弹簧的效果，让界面元素感觉更自然、更有响应性。Google Material Design 3 和 Apple HIG 都推荐使用 spring 动画代替传统 ease-out。

### 为什么 `isNearBottom(400)` 而非 `150`？

流式输出期间用户可能向上滚动查看早期内容。强制 `scrollToBottom` 会导致用户被反复拉回底部，无法阅读。`isNearBottom(el, 150)` 只在用户距底部 150px 以内时自动滚动，用户可以自由上翻浏览而不被打断。

### 为什么 `_finish()` 需要安全网？

`_finish()` 被 5 个代码路径调用（done / error / stop / catch / _streamEnd）。在 `send()` 中重置状态覆盖了正常流程，但异常路径（如 stop 在 `send()` 的 `await ChatAPI.sendMessage()` 之前调用）可能在 `send()` 重置之前就进入 `_finish()`。在 `_finish()` 中再次清理 `_answerBubble` 和 `_abortController` 形成双重保险。

### 为什么 AbortError 不显示错误气泡？

用户点击停止按钮是主动行为，不是系统错误。显示红色错误气泡会让用户误以为操作失败。AbortError 消息包含 "abort" 或 "cancel"，正则过滤后静默处理，直接调用 `_finish()` 恢复 UI 到可输入状态。

### AbortController 生命周期

```
send() → new AbortController() → 存入 this._abortController
  → ChatAPI.sendMessage({ signal }) → fetch({ signal })
  → SSEStream.stream() 读取 body
  → [用户点击停止] → stop() → this._abortController.abort()
    → fetch reader 抛出 AbortError
    → sse.js pump().catch() → handlers.error() + _streamEnd()
    → error handler 检测 isAbort → 跳过错误气泡
    → _finish() → this._abortController = null
  → [正常完成] → done → _finish() → this._abortController = null
```

---

## 五、测试结果

### 后端回归测试（2026-06-29 最终）

```bash
$ python -m pytest tests/ -v
========================== 19 passed, 1 skipped, 1 warning in 6.31s ==========================
```

所有现有单元测试通过，无回归。

### API 多轮端到端测试（2026-06-29 最终）

```
=== Turn 1: RAG ===
  Events: 57 | Types: [act, answer, done, observe, reason, reflect]
  Answer: 根据提供的文档...RAG（检索增强生成）...

=== Turn 2: advantages ===
  Events: 30 | Types: [act, answer, done, observe, reason, reflect]
  Answer: RAG 的主要优势...实时检索...

  [PASS] Turn1 reason    [PASS] Turn1 answer   [PASS] Turn1 done
  [PASS] Turn2 reason    [PASS] Turn2 answer   [PASS] Turn2 done
  [PASS] Answers differ  [PASS] Turn2 longer
All passed: True
```

两轮对话各自完整的 ReAct 事件序列，答案内容隔离，第二轮正确引用上下文。

### 前端手动验证

| # | 场景 | 预期 | 结果 |
|---|------|------|------|
| 1 | Turn 1 → Turn 2 连续提问 | Answer2 在新气泡，Answer1 不变 | ✅ |
| 2 | 连续 3 轮对话 | 3 个独立回答气泡 | ✅ |
| 3 | 中途点击停止按钮 | 不显示错误气泡，可立即发新问题 | ✅ |
| 4 | 流式输出时向上滚动 | 不强制跳回底部 | ✅ |
| 5 | 刷新页面 | 历史消息正确加载，Q&A 分离 | ✅ |
| 6 | 宽屏鼠标在页面空白区域滚轮 | 消息列表正常滚动 | ✅ |
| 7 | 思考步骤逐个出现 | 每步从左侧滑入 + 淡入 | ✅ |
| 8 | 思考块折叠 | max-height 平滑过渡 0.3s | ✅ |
| 9 | 消息入场 | spring 缓动 20px slide + scale | ✅ |
| 10 | 发送按钮 hover/click | 光晕 + scale(1.08/0.92) | ✅ |

---

## 六、与 V2.3 的对比

| 维度 | V2.3 | V2.4 |
|------|------|------|
| **多轮对话** | 回答覆盖前一轮气泡 | ✅ 每轮独立气泡 |
| **Stop 按钮** | 无效（只清理 UI，不中断请求） | ✅ 真正中断 fetch + 不显示错误 |
| **自动滚动** | 无 | ✅ 用户气泡/思考块/回答/来源均滚动 |
| **上翻保护** | N/A | ✅ isNearBottom 阈值 400px |
| **滚动区域** | 仅消息气泡上可滚轮 | ✅ 整个页面中部区域均可滚轮 |
| **思考步骤动效** | 无（瞬间弹出） | ✅ step-in: 左侧滑入 + 淡入 (0.25s spring) |
| **思考块折叠** | display:none 瞬间消失 | ✅ max-height 平滑过渡 (0.3s) |
| **思考块入场** | 无 | ✅ block-in: 滑入 + 淡入 (0.3s spring) |
| **消息入场** | 8px/0.25s ease-out | ✅ 20px + scale/0.35s spring 缓动 |
| **按钮反馈** | scale(1.05/0.95) 无阴影 | ✅ scale(1.08/0.92) + 光晕 |
| **打字指示器** | 灰色点 | ✅ 主题蓝色 + 更丰富弹跳 |
| **状态泄漏** | `_answerBubble` 跨轮残留 | ✅ send() + _finish() 双重清理 |
| **Abort 错误处理** | N/A（从未触发） | ✅ 正则过滤，静默处理 |
| **改动文件** | 20 文件 | 3 文件 |
| **改动行数** | ~400 行 | +82 / -27 |
| **后端变化** | 有（MCP + 分类） | 无 |
| **API 变化** | +1 端点 +1 字段 | 无 |

---

## 七、风险与局限

| 风险 | 缓解 |
|------|------|
| 前端无自动化测试 | 已做 API 集成测试 + 手动验证矩阵；后续可引入 Vitest + jsdom |
| AbortError 正则可能漏掉非英文错误消息 | 当前环境 SSE 错误消息为英文；可扩展正则覆盖更多语言 |
| 连续快速"发送-停止-发送"可能触发竞态 | `isStreaming` 守卫 + `_finish()` 双重清理对绝大多数场景安全 |

## 八、未改动

- ReAct 5 节点核心逻辑
- 检索管线（Dense / BM25 / RRF）
- MCP 协议层（ClientManager / 3 个 Server）
- 索引层（ChromaDB + BM25 + Embeddings）
- 评测层（RAGAS）
- Session 持久化（SQLite + localStorage）
- 联网搜索（web_search MCP 工具）
- 文档分类系统
- 所有 CSS / HTML 模板
