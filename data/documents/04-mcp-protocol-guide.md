# MCP (Model Context Protocol) 协议指南

## MCP 是什么

MCP (Model Context Protocol) 是 Anthropic 提出的开放协议，旨在标准化 AI 模型与外部工具和数据源之间的交互方式。它是 AI 应用的 "USB-C 接口"——提供统一的连接标准。

## MCP 的核心概念

### 架构

```
┌─────────────┐     MCP Protocol     ┌─────────────┐
│  MCP Client  │ ◄──────────────────► │  MCP Server  │
│  (LLM App)   │    (JSON-RPC)        │  (Tool/API)  │
└─────────────┘                      └─────────────┘
```

- **MCP Client**：嵌入在 LLM 应用中，负责与 Server 通信
- **MCP Server**：提供工具/资源的具体实现，独立运行
- **Transport**：通信方式，支持 stdio（本地）和 SSE（远程）

### Server 提供的能力

1. **Tools**：可执行的函数，LLM 可以调用（如搜索文档、查询数据库）
2. **Resources**：可读取的数据（如文件内容、API 响应）
3. **Prompts**：预定义的提示模板

## MCP vs Function Calling

这是面试中的高频追问点。两者的本质区别：

| 维度 | Function Calling | MCP |
|------|-----------------|-----|
| 耦合度 | 工具定义耦合在 API 请求中 | 工具定义与模型解耦 |
| 复用性 | 切换模型需要重写工具定义 | 同一 Server 跨模型通用 |
| 可发现性 | 需要预先知道工具列表 | 动态发现 (list_tools) |
| 生命周期 | 无状态，随 API 调用结束 | Server 独立运行，有状态 |
| 标准化 | 各厂商自定义格式 | 开放协议，社区标准 |

**类比**: Function Calling 是每次点菜手写菜单，MCP 是固定菜单本（标准化、可复用）。

## MCP vs A2A (Agent-to-Agent)

- **MCP** = Agent ↔ Tool（纵向关系）：Agent 调用工具获取信息或执行操作
- **A2A** = Agent ↔ Agent（横向关系）：Agent 之间相互协作、委派任务

两者不是竞争关系，而是互补关系。一个 Agent 可以同时使用 MCP 调用工具和 A2A 与其他 Agent 通信。

## MCP Server 生命周期

1. **初始化**：Client 连接 Server，交换能力信息
2. **发现**：Client 通过 `list_tools` / `list_resources` 了解 Server 能力
3. **调用**：Client 通过 `call_tool` / `read_resource` 使用 Server 功能
4. **关闭**：连接断开，Server 清理资源

## 为什么 MCP 是未来的趋势

- 工具生态标准化，避免每个 LLM 框架都自己发明一套工具定义
- 工具开发者只需写一个 MCP Server，所有 LLM 应用都能用
- 支持工具的独立更新和版本管理
- 社区正在快速发展，已有大量现成的 MCP Server 可用
