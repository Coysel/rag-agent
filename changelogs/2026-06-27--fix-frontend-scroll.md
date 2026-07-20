# 修复前端页面无法滚动

**日期**: 2026-06-27
**类型**: bug-fix
**影响范围**: frontend

## 问题描述

前端所有页面（聊天、检索对比、评测、管理、设置）内容超出视口时无法滚动。消息列表、文档表格等超出部分被裁切，无法通过滚动条或触控滑动查看。

## 根因分析

CSS Flexbox 规范中，flex 子元素默认 `min-height: auto`，即 flex 子元素的最小高度不会低于其内容的固有高度。这导致即使设置了 `flex: 1` + `overflow-y: auto`，元素也不会产生滚动条——因为 flex 容器会随内容膨胀，而不是约束子元素高度。

受影响的 flex 链条：

```
.app-container (height: 100vh) → .main-content (flex column) → .page (flex: 1) → .chat-messages / .content-area (flex: 1, overflow-y: auto)
```

链条上每个 flex 子元素都因 `min-height: auto` 而阻止了滚动。

## 修改内容

### [frontend/css/layout.css](frontend/css/layout.css)

1. **`.main-content`** — 新增 `overflow: hidden`，作为最外层保护，防止内容溢出
2. **`.page`** — 新增 `min-height: 0`，允许 flex 容器将页面约束在可用空间内
3. **`.content-area`** — 新增 `min-height: 0`，允许内容区被约束后触发 `overflow-y: auto` 滚动

### [frontend/css/chat.css](frontend/css/chat.css)

4. **`.chat-messages`** — 新增 `min-height: 0`，聊天消息列表可正确滚动

## 技术要点

`min-height: 0` 是 flex 布局中启用滚动的关键 CSS 属性。没有它，flex 子元素的最小高度默认为 `auto`（即内容高度），导致：
- `flex: 1` 无法将元素收缩到内容高度以下
- `overflow-y: auto` 永远不会触发——因为元素总是足够大

这是 CSS Flexbox 最常见但最隐蔽的陷阱之一，官方规范中明确说明了这一行为。

## 影响评估

- ✅ 聊天页面消息列表可正常滚动
- ✅ 评测页面内容区可正常滚动
- ✅ 管理页面文档列表可正常滚动
- ✅ 设置页面内容区可正常滚动
- ✅ 检索对比页面内容区可正常滚动
- ✅ 无视觉变更，不破坏现有布局
- ✅ 移动端触控滑动正常
