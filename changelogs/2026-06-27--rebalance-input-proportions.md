# 调整输入框比例 — 更宽更扁

**日期**: 2026-06-27
**类型**: feature
**影响范围**: frontend

## 问题描述

上轮放大后输入框重心仍然偏下，比例不佳——太高、不够宽。

## 修改内容

| 属性 | 修改前 | 修改后 | 说明 |
|------|--------|--------|------|
| `--input-bar-height` | 88px | **64px** | 输入栏整体压扁 |
| `--max-content-width` | 900px | **960px** | 内容区更宽 |
| `.input-bar` padding | 16px 20px | **8px 20px** | 上下收紧 |
| `.input-bar` align-items | flex-end | **center** | 垂直居中 |
| `.chat-input` min-height | 48px | **42px** | 输入框稍矮 |
| `.chat-input` max-height | 200px | **160px** | 多行上限回收 |
| `.chat-input` padding | 12px 16px | **8px 16px** | 上下收紧 |
| `.chat-input` border-radius | 10px | **16px** | 更圆润 |
| `.send-btn` | 44×44px | **38×38px** | 按钮缩小 |
| `.send-btn` border-radius | 10px | **16px** | 更圆润 |

## 比例变化

```
修改前: 输入栏高 88px, 内容宽 900px, 输入框 48px高  → 高扁比 ≈ 1:19
修改后: 输入栏高 64px, 内容宽 960px, 输入框 42px高  → 高扁比 ≈ 1:23
```

## 影响评估
- ✅ 视觉重心上移，不再贴底边
- ✅ 内容区加宽 60px，输入更从容
- ✅ 输入栏高度降低 27%，聊天区获得更多空间
