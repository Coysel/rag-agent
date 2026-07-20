# 迭代改进文档

> 本项目每次修改均需在此目录下生成对应的迭代改进解析文档。

## 目录结构

```
docs/
├── README.md                           # 本文件 — 文档索引与规范
├── backend-iterations/                 # 后端迭代文档
│   └── ITERATION_REPORT.md             # 第一轮后端优化（2026-06-26）
├── frontend-iterations/               # 前端迭代文档
│   └── FRONTEND_V1_REPORT.md           # 第一轮前端优化（2026-06-27）
├── fullstack-iterations/              # 全栈迭代文档
│   └── FULLSTACK_V2_REPORT.md          # V2.0 全栈重构（2026-06-27）
└── ...                                 # 未来迭代文档将按分类存放
```

## 文档规范

每次迭代必须输出一个 Markdown 文档，放在对应分类目录下，遵循以下结构：

```markdown
# [标题] — 迭代改进详细解析文档

> 本次迭代日期：YYYY-MM-DD
> 改动范围：[文件列表]
> 相关约束：[如"后端不动"、"API 不变"等]

---

## 改动概览

| 指标 | 数值 |
|------|------|
| 改动文件 | N 个 |
| 新增文件 | N 个 |
| 删除代码行 | ~N |
| 新增代码行 | ~N |

---

## 逐项优化详解

### X1. [优化项标题]

**问题根因：** [为什么要改 — 现状的痛点]

**优化方案：** [改了什么 — 最好附关键代码片段]

**作用：** [这么改的价值]

**目的达成：** ✅/❌ [是否达到预期效果]

---

### X2. ...

---

## 前后对比

[表格或结构化对比]

## 未改动

[明确哪些部分没动，避免混淆]

## 验证记录

[如何验证改动正确性]
```

## 命名规范

- 后端迭代：`docs/backend-iterations/BACKEND_V{N}_REPORT.md`
- 前端迭代：`docs/frontend-iterations/FRONTEND_V{N}_REPORT.md`
- 全栈迭代：`docs/fullstack-iterations/FULLSTACK_V{N}_REPORT.md`

## 已有迭代索引

| 日期 | 分类 | 文档 | 主题 |
|------|------|------|------|
| 2026-06-26 | 后端 | [ITERATION_REPORT.md](backend-iterations/ITERATION_REPORT.md) | 统一检索管道 + 日志 + 多轮对话 + 增量索引 + 测试体系 |
| 2026-06-27 | 前端 | [FRONTEND_V1_REPORT.md](frontend-iterations/FRONTEND_V1_REPORT.md) | SSE 解析复用 + 打字指示器 + ReAct 折叠 + Copy 按钮等 10 项优化 |
| 2026-06-27 | 全栈 | [FULLSTACK_V2_REPORT.md](fullstack-iterations/FULLSTACK_V2_REPORT.md) | 企业级全栈重构：后端分层架构 + 前端 32 文件模块化 + SQLite Session + Design Tokens |
