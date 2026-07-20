"""
LangGraph Agent State — ReAct 循环的状态定义

State 在 ReAct 各节点间流转，记录每一步的中间结果。
"""
from typing import TypedDict, Annotated, Sequence, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """Agentic RAG 的 ReAct 循环状态"""

    # 原始输入
    query: str

    # 消息历史 (LangGraph 标准格式, add_messages reducer 自动合并)
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # 对话历史（多轮对话上下文，最多保留 N 轮）
    conversation_history: list[dict]  # [{"role": "user/assistant", "content": "..."}, ...]

    # 会话 ID
    session_id: str

    # 查询分类结果
    query_type: str  # "factual" | "conceptual" | "multi_hop"

    # 工具调用相关
    tool_calls: list[dict]   # 待执行的工具调用
    tool_results: list[dict] # 已执行的工具结果

    # 检索到的上下文文档
    context_docs: list[dict]  # [{"content": str, "title": str, "source": str, ...}, ...]

    # 最终回答
    answer: str

    # 流程控制
    step_count: int     # 当前步数
    max_steps: int      # 最大步数限制
    status: str         # "continue" | "answer" | "max_steps"

    # 文档过滤（按类别限定检索范围）
    doc_ids: list[str]  # 限定搜索的文档 ID 列表，空列表=全部

    # 联网搜索
    web_search: bool    # 是否允许使用 web_search 工具

    # 流式输出缓冲
    stream_buffer: list[str]

    # 答案逐句流式 tokens（answer_node 输出）
    stream_tokens: list[str]
