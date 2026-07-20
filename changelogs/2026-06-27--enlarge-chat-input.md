# 放大聊天输入框

**日期**: 2026-06-27
**类型**: feature
**影响范围**: frontend

## 问题描述

聊天输入框太矮、太贴底边，使用体验差。用户需要低头看屏幕底部边缘才能输入。

## 修改内容

### [frontend/css/tokens.css](frontend/css/tokens.css)
- `--input-bar-height`: `72px` → `88px`，输入栏整体高度增加 16px

### [frontend/css/layout.css](frontend/css/layout.css)
- `.input-bar` padding: `--space-3` → `--space-4`, `--space-4` → `--space-5`（8px→12px 上/下, 16px→20px 左/右）

### [frontend/css/chat.css](frontend/css/chat.css)
- `.chat-input`:
  - `padding`: `--space-2` → `--space-3`, `--space-3` → `--space-4`（4px→8px 上/下, 8px→12px 左/右）
  - `font-size`: `var(--text-sm)` (13px) → `var(--text-base)` (14px)
  - `min-height`: `40px` → `48px`
  - `max-height`: `160px` → `200px`
- `.send-btn`: `40px×40px` → `44px×44px`, 图标 `1.1rem` → `1.2rem`

### [frontend/js/pages/chat.js](frontend/js/pages/chat.js)
- auto-resize 上限 `160px` → `200px`，与 CSS 同步

## 效果对比

| 属性 | 修改前 | 修改后 |
|------|--------|--------|
| 输入栏高度 | 72px | 88px |
| 输入框高度 | 40px | 48px |
| 发送按钮 | 40×40 | 44×44 |
| 输入字体 | 13px | 14px |

## 影响评估
- ✅ 输入框更大，使用体验明显改善
- ✅ 仍保留 auto-resize 多行能力
- ✅ 不破坏页面布局（flex 自动适配）
