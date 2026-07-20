"""
MCP 客户端管理器 — 通过 MCP 协议与 MCP Server 通信

使用 MCP Python SDK 的 ClientSession + call_tool() 执行工具，
使用 list_tools() 动态发现工具，而非直接调用 *_impl() 函数。

架构:
  Agent nodes → MCPClientManager.execute_tool()
    → ClientSession.call_tool()  [MCP JSON-RPC 协议]
      → MCP Server @server.call_tool() handler
        → *_impl() 纯函数 (业务逻辑)

工具发现:
  main.py lifespan → manager.initialize()
    → doc_session.list_tools() + sqlite_session.list_tools()
    → 缓存 Tool 对象 → 动态生成 OpenAI/Anthropic 工具定义
"""
import json
from typing import Any, Dict, List, Tuple

from mcp.client.session import ClientSession
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import Tool


class MCPClientManager:
    """通过 MCP 协议管理文档检索和 SQLite 查询工具"""

    def __init__(self):
        # 创建 MCP Server 实例
        from src.mcp.doc_server import create_doc_search_server
        from src.mcp.sqlite_server import create_sqlite_server
        from src.mcp.web_server import create_web_search_server
        #server对象
        self._doc_server = create_doc_search_server()
        self._sqlite_server = create_sqlite_server()
        self._web_server = create_web_search_server()

        # 异步上下文管理器（延迟进入）
        self._doc_ctx = create_connected_server_and_client_session(self._doc_server)
        self._sqlite_ctx = create_connected_server_and_client_session(self._sqlite_server)
        self._web_ctx = create_connected_server_and_client_session(self._web_server)

        # 初始化后填充
        self._doc_session: ClientSession | None = None
        self._sqlite_session: ClientSession | None = None
        self._web_session: ClientSession | None = None
        self._tool_to_session: Dict[str, ClientSession] = {}#路由映射
        self._all_tools: List[Tool] = []
        self._initialized = False

    # ── 生命周期 ────────────────────────────────────────────

    async def initialize(self):
        """
        启动 MCP Server + 创建 ClientSession + 发现工具。
        在 main.py 的 lifespan 中调用。
        """
        if self._initialized:
            return

        # 进入三个 MCP 上下文管理器 → 启动 Server + 创建并初始化 ClientSession
        self._doc_session = await self._doc_ctx.__aenter__()
        self._sqlite_session = await self._sqlite_ctx.__aenter__()
        self._web_session = await self._web_ctx.__aenter__()

        # 从 doc-server 发现工具
        doc_result = await self._doc_session.list_tools()
        for tool in doc_result.tools:
            self._tool_to_session[tool.name] = self._doc_session
            self._all_tools.append(tool)

        # 从 sqlite-server 发现工具
        sqlite_result = await self._sqlite_session.list_tools()
        for tool in sqlite_result.tools:
            self._tool_to_session[tool.name] = self._sqlite_session
            self._all_tools.append(tool)

        # 从 web-server 发现工具
        web_result = await self._web_session.list_tools()
        for tool in web_result.tools:
            self._tool_to_session[tool.name] = self._web_session
            self._all_tools.append(tool)

        self._initialized = True

    async def close(self):
        """清理 MCP sessions 和 servers。在 main.py 的 lifespan 关闭阶段调用。"""
        if not self._initialized:
            return

        try:
            await self._doc_ctx.__aexit__(None, None, None)
        except Exception:
            pass

        try:
            await self._sqlite_ctx.__aexit__(None, None, None)
        except Exception:
            pass

        try:
            await self._web_ctx.__aexit__(None, None, None)
        except Exception:
            pass

        self._initialized = False
        self._doc_session = None
        self._sqlite_session = None
        self._web_session = None
        self._tool_to_session.clear()
        self._all_tools.clear()

    # ── 工具执行（通过 MCP 协议）────────────────────────────

    async def execute_tool(self, tool_name: str, tool_input: dict) -> Tuple[str, list]:
        """
        通过 MCP call_tool() 执行工具。

        Args:
            tool_name: 工具名称
            tool_input: 工具参数字典

        Returns:
            (result_text, structured_data):
              - result_text: LLM 可读的结果文本
              - structured_data: 原始文档列表（用于 context_docs），非检索类返回空列表
        """
        if not self._initialized:
            return "MCP 服务未初始化，请检查启动日志", []

        session = self._tool_to_session.get(tool_name)#查看工具是哪个server的
        if session is None:
            return f"未知工具: {tool_name}", []

        try:
            # 通过 MCP 协议调用工具
            result = await session.call_tool(tool_name, tool_input)

            # 解析 MCP 返回的 TextContent
            raw_text = ""
            for block in result.content:
                if hasattr(block, "text"):
                    raw_text += block.text

            if result.isError:
                return f"工具执行错误: {raw_text}", []

            # 根据工具类型格式化结果
            return self._format_result(tool_name, tool_input, raw_text)

        except Exception as e:
            return f"工具执行错误: {str(e)}", []

    def _format_result(self, tool_name: str, tool_input: dict, raw_text: str) -> Tuple[str, list]:
        """解析 MCP Server 返回的 JSON 字符串，格式化为 LLM 可读文本 + 结构化数据"""
        # 解析 JSON
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            return raw_text, []

        if "error" in data:
            return f"错误: {data['error']}", []

        if tool_name == "search_documents":
            return self._format_search_result(tool_name, tool_input, data)

        elif tool_name == "get_document":
            return self._format_get_document(data)

        elif tool_name == "execute_query":
            return self._format_sqlite_result(data)

        elif tool_name == "list_tables":
            return self._format_list_tables(data)

        elif tool_name == "web_search":
            return self._format_web_search_result(data)

        return raw_text, []

    def _format_search_result(self, tool_name: str, tool_input: dict, data: dict) -> Tuple[str, list]:
        """格式化检索结果 — data 来自 search_documents_impl 的 JSON 输出"""
        results = data.get("results", [])
        if not results:
            return f"[混合检索] 未找到相关结果", []

        # 从 MCP 返回格式重建文档 dict 列表
        docs = []
        lines = [f"[混合检索] 找到 {len(results)} 条结果:\n"]
        for item in results:
            score_val = item.get("score", 0)
            doc = {
                "id": item.get("id", ""),
                "title": item.get("title", "未知"),
                "source": item.get("source", ""),
                "content": item.get("content_preview", ""),  # MCP impl 只返回 500 字预览
                "score": score_val,
                "rrf_score": score_val,       # 兼容下游: _extract_sources / answer_node 读此字段
                "dense_score": score_val,      # 兼容回退逻辑
                "bm25_score": score_val,
            }
            docs.append(doc)
            lines.append(f"--- 结果 {item.get('rank', '?')} (相关度: {score_val:.4f}) ---")
            lines.append(f"来源: {doc['title']} ({doc['source']})")
            lines.append(f"内容预览: {doc['content'][:300]}...\n")

        return "\n".join(lines), docs

    def _format_sqlite_result(self, data: dict) -> Tuple[str, list]:
        """格式化 SQL 查询结果"""
        columns = data.get("columns", [])
        rows = data.get("rows", [])
        row_count = data.get("row_count", 0)
        truncated = data.get("truncated", False)

        text = f"查询结果 ({row_count} 行):\n"
        if columns:
            text += "| " + " | ".join(columns) + " |\n"
            text += "|" + "|".join("---" for _ in columns) + "|\n"
        for row in rows[:50]:
            text += "| " + " | ".join(str(v) for v in row.values()) + " |\n"
        if truncated:
            text += "\n（结果已截断）"

        return text, []

    def _format_get_document(self, data: dict) -> Tuple[str, list]:
        """格式化 get_document 结果"""
        doc = {
            "id": data.get("id", ""),
            "title": data.get("title", "未知"),
            "source": data.get("source", ""),
            "content": data.get("content", ""),
        }
        text = f"文档: {doc['title']}\n来源: {doc['source']}\n\n{doc['content']}"
        return text, [doc]

    def _format_list_tables(self, data: dict) -> Tuple[str, list]:
        """格式化 list_tables 结果"""
        tables = data.get("tables", [])
        if not tables:
            return "数据库中无表", []
        text = f"数据库中的表 ({len(tables)} 个):\n" + "\n".join(f"- {t}" for t in tables)
        return text, []

    def _format_web_search_result(self, data: dict) -> Tuple[str, list]:
        """格式化 web_search 结果"""
        if "error" in data:
            return f"联网搜索失败: {data['error']}", []

        results = data.get("results", [])
        if not results:
            return data.get("message", "未找到相关网页结果。"), []

        lines = [f"### 联网搜索结果 ({len(results)} 条)\n"]
        docs = []  # 作为 structured data 传给 context_docs
        for i, r in enumerate(results, 1):
            title = r.get("title", "无标题")
            url = r.get("url", "")
            snippet = r.get("snippet", "")
            lines.append(f"{i}. **{title}**")
            if url:
                lines.append(f"   链接: {url}")
            lines.append(f"   {snippet}\n")

            # 构建文档对象供 context_docs 使用
            docs.append({
                "id": url,
                "title": title,
                "source": url,
                "content": snippet,
                "rrf_score": 0.5,
                "dense_score": 0.5,
                "bm25_score": 0.5,
            })

        return "\n".join(lines), docs

    # ── 工具定义生成（从 MCP Tool 对象动态转换）──────────────

    def get_tool_definitions(self, provider: str = "deepseek") -> List[dict]:
        """
        从 MCP list_tools() 发现的 Tool 对象动态生成工具定义。

        Args:
            provider: "deepseek" → OpenAI function-calling 格式
                      "anthropic" → Anthropic tool_use 格式

        Returns:
            工具定义列表，可直接传给 LLM
        """
        if provider == "anthropic":
            return self._to_anthropic_format()
        return self._to_openai_format()

    def _to_openai_format(self) -> List[dict]:
        """MCP Tool → OpenAI function-calling 格式"""
        definitions = []
        for tool in self._all_tools:
            definitions.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                },
            })
        return definitions

    def _to_anthropic_format(self) -> List[dict]:
        """MCP Tool → Anthropic tool_use 格式"""
        definitions = []
        for tool in self._all_tools:
            definitions.append({
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema,
            })
        return definitions


# ── 全局单例 ────────────────────────────────────────────────

_manager: MCPClientManager | None = None


def get_mcp_manager() -> MCPClientManager:
    """获取全局 MCP 客户端管理器实例 (懒初始化)"""
    global _manager
    if _manager is None:
        _manager = MCPClientManager()
    return _manager
