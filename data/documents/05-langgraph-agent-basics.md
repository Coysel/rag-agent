# LangGraph Agent 基础

## LangGraph 核心理念

LangGraph 是一个用于构建有状态、多参与者（multi-actor）应用的框架，基于 LangChain 生态系统。它的核心思想是将 Agent 的工作流建模为有向图。

## 三个核心概念

### 1. State（状态）

State 是整个图中流转的数据结构。使用 TypedDict 定义：

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]  # add_messages 是 reducer
    query: str
    answer: str
    step_count: int
```

`Annotated` 中的第二个参数是 **reducer**，控制节点如何合并状态更新。`add_messages` 是 LangGraph 内置的消息列表 reducer。

### 2. Node（节点）

Node 是处理状态的函数。每个 Node 接收当前 State，返回部分 State 更新：

```python
def my_node(state: AgentState) -> dict:
    # 处理逻辑
    return {"answer": "Hello", "step_count": state["step_count"] + 1}
```

### 3. Edge（边）

Edge 定义节点之间的连接关系：

- **普通边 (Normal Edge)**：固定路由，A 完成后总是去 B
- **条件边 (Conditional Edge)**：根据 State 动态决定路由

```python
# 普通边
workflow.add_edge("node_a", "node_b")

# 条件边
workflow.add_conditional_edges(
    "node_a",
    router_function,  # 返回 "path_x" 或 "path_y"
    {"path_x": "node_b", "path_y": "node_c"},
)
```

## Checkpoint 机制

LangGraph 支持在图的每个节点执行后自动保存 State 快照（checkpoint）。作用：

1. **中断恢复**：Agent 运行中断后从最近的 checkpoint 恢复
2. **调试可观测**：回溯查看每一步的 State 变化
3. **人类审批 (Human-in-the-Loop)**：在关键节点暂停，等待人工确认
4. **分支回溯**：回到历史状态尝试不同的执行路径

## 为什么选 LangGraph 而不是 while + if-else

这是面试中的经典问题：

| 维度 | while + if-else | LangGraph |
|------|----------------|-----------|
| 状态管理 | 手动管理，易出错 | TypedDict + Reducer 自动管理 |
| 可观测性 | 需要自己加 log | Checkpoint 自动记录 |
| 可视化 | 代码即文档，难理解 | 图结构可导出为 Mermaid/PNG |
| 流式支持 | 手动实现异步 | 原生支持 astream |
| 中断恢复 | 需要自己实现 | Checkpoint 机制开箱即用 |
| 可组合性 | 难以复用 | 多个 Graph 可组合 |

## ReAct 模式在 LangGraph 中的实现

ReAct (Reasoning + Acting) 是最常用的 Agent 模式：

```
START → reason → act → observe → reflect
                                    ├─ 够了 → answer → END
                                    └─ 不够 → reason (重新检索)
```

- **reason**：分析问题 + 现有信息，决定需要什么
- **act**：调用工具（搜索/数据库/API）
- **observe**：处理工具返回的结果
- **reflect**：判断信息是否足够，决定继续还是回答
- **answer**：基于上下文生成最终回答
