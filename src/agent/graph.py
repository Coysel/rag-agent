"""
LangGraph 图构建 — 组装 ReAct 循环

图结构:
    START → reason → act → observe → reflect
                                      ├─ "continue" → reason
                                      ├─ "answer" → answer → END
                                      └─ "max_steps" → answer → END

使用 LangGraph StateGraph，条件边在 reflect 节点分流。
"""
from typing import Literal

from langgraph.graph import StateGraph, END

from src.agent.state import AgentState
from src.agent.nodes import (
    reason_node,
    act_node,
    observe_node,
    reflect_node,
    answer_node,
)
from config import MAX_STEPS

#react

def route_after_reflect(state: AgentState) -> Literal["reason", "answer"]:
    """reflect 之后的路由决策"""
    status = state.get("status", "continue")
    if status in ("answer", "max_steps"):
        return "answer"
    return "reason"


def route_after_reason(state: AgentState) -> Literal["act", "answer"]:
    """reason 之后的路由决策"""
    status = state.get("status", "continue")
    if status == "answer":
        return "answer"
    return "act"


def build_graph() -> StateGraph:
    """
    构建并编译 ReAct 循环的 LangGraph

    Returns:
        编译好的 StateGraph (Runnable)
    """
    # 创建 StateGraph
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("reason", reason_node)
    workflow.add_node("act", act_node)
    workflow.add_node("observe", observe_node)
    workflow.add_node("reflect", reflect_node)
    workflow.add_node("answer", answer_node)

    # 设置入口
    workflow.set_entry_point("reason")

    # 添加边
    # reason → act 或 answer (条件边)
    workflow.add_conditional_edges(
        "reason",
        route_after_reason,
        {"act": "act", "answer": "answer"},
    )

    # act → observe (固定边)
    workflow.add_edge("act", "observe")

    # observe → reflect (固定边)
    workflow.add_edge("observe", "reflect")

    # reflect → reason 或 answer (条件边)
    workflow.add_conditional_edges(
        "reflect",
        route_after_reflect,
        {"reason": "reason", "answer": "answer"},
    )

    # answer → END (固定边)
    workflow.add_edge("answer", END)

    # 编译
    graph = workflow.compile()
    return graph


def get_initial_state(
    query: str,
    max_steps: int = MAX_STEPS,
    conversation_history: list = None,
    session_id: str = "",
    doc_ids: list[str] | None = None,
    web_search: bool = False,
) -> dict:
    """
    创建初始 State

    Args:
        query: 用户查询
        max_steps: 最大循环轮数
        conversation_history: 历史对话（多轮对话上下文）
        session_id: 会话 ID
        doc_ids: 限定搜索的文档 ID 列表，None/空=全部
        web_search: 是否允许联网搜索
    """
    return {
        "query": query,
        "messages": [],
        "conversation_history": conversation_history or [],
        "session_id": session_id,
        "query_type": "",
        "tool_calls": [],
        "tool_results": [],
        "context_docs": [],
        "answer": "",
        "step_count": 0,
        "max_steps": max_steps,
        "status": "continue",
        "stream_buffer": [],
        "stream_tokens": [],
        "doc_ids": doc_ids or [],
        "web_search": web_search,
    }
