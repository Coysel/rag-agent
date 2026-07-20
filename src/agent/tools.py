"""
Agent 工具定义 — 从 MCP Server 动态获取

工具定义完全由 MCP list_tools() 协议动态发现，不再维护硬编码副本。
MCP 未初始化时直接抛异常（而非静默回退到不一致的硬编码定义）。
"""
from typing import List


def get_tool_definitions(provider: str = "deepseek") -> List[dict]:
    """
    从 MCP Server 动态获取工具定义（通过 list_tools() 协议发现）。

    Args:
        provider: "deepseek" → OpenAI function-calling 格式
                  "anthropic" → Anthropic tool_use 格式

    Returns:
        工具定义列表，可直接传给 LLM

    Raises:
        RuntimeError: MCP 未初始化
    """
    from src.mcp.client_manager import get_mcp_manager
    manager = get_mcp_manager()
    if not manager._all_tools:
        raise RuntimeError(
            "MCP 服务未初始化，无法获取工具定义。请检查应用启动日志。"
        )
    return manager.get_tool_definitions(provider)


# 保持向后兼容的别名
get_dynamic_tool_definitions = get_tool_definitions
