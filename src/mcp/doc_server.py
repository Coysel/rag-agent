"""
MCP 文档检索 Server — 基于 MCP Python SDK 实现的文档搜索工具

提供工具:
  - search_documents: 混合检索文档 (BM25 + Dense + RRF)
  - get_document: 根据 ID 获取完整文档

设计要点 (面试高频追问):
  MCP vs Function Calling:
  - FC = 每次请求把工具列表塞进 API 参数，换模型要重写
  - MCP = 工具抽象成独立 Server，复用、可发现、跨模型通用
  类比: FC 是每次点菜手写菜单，MCP 是固定菜单本

  MCP Server 生命周期:
  1. 启动 → 注册 tools/resources/prompts
  2. 等待 Client 连接 (stdio/SSE)
  3. 响应 Client 的 tool 调用请求
  4. 关闭 → 清理资源

  MCP vs A2A:
  - MCP = Agent ↔ Tool (纵向，Agent 调用工具)
  - A2A = Agent ↔ Agent (横向，Agent 之间协作)
"""
import json
import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False


# ── 工具实现 (纯函数，可独立使用) ──────────────────────────

def _search_documents(query: str, method: str = "hybrid", doc_ids: list[str] | None = None) -> list:
    """
    核心检索逻辑 — 委托给统一的检索管线

    Args:
        query: 检索查询文本
        method: "hybrid" | "bm25" | "dense"
        doc_ids: 限定文档 ID 列表，None 表示全部

    Returns:
        文档 dict 列表（已完成 parent 展开 + 去重）
    """
    from src.retrieval.pipeline import retrieve
    return retrieve(query, method=method, doc_ids=doc_ids)


def search_documents_impl(query: str, method: str = "hybrid", doc_ids: list[str] | None = None) -> str:
    """
    文档检索实现 — 返回 JSON 字符串（供 MCP Server call_tool 使用）

    Args:
        query: 检索查询文本
        method: "hybrid" | "bm25" | "dense"
        doc_ids: 限定文档 ID 列表

    Returns:
        JSON 格式的检索结果
    """
    try:
        docs = _search_documents(query, method, doc_ids=doc_ids)

        if not docs:
            return json.dumps({"results": [], "message": "未找到相关结果"}, ensure_ascii=False)

        formatted = []
        for i, doc in enumerate(docs, 1):
            formatted.append({
                "rank": i,
                "id": doc.get("id", ""),
                "title": doc.get("title", "未知"),
                "source": doc.get("source", ""),
                "content_preview": doc.get("content", "")[:500],
                "score": doc.get("rrf_score", doc.get("dense_score", doc.get("bm25_score", 0))),
            })

        return json.dumps({"results": formatted, "total": len(formatted)}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def get_document_impl(doc_id: str) -> str:
    """获取完整文档实现"""
    try:
        from src.retrieval.parent_retriever import get_parent_retriever
        parent_retriever = get_parent_retriever()
        doc = parent_retriever.get_parent_doc(doc_id)
        if doc:
            return json.dumps({
                "id": doc["id"],
                "title": doc.get("title", ""),
                "source": doc.get("source", ""),
                "content": doc.get("content", ""),
            }, ensure_ascii=False)
        return json.dumps({"error": "文档不存在"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ── MCP Server 定义 ───────────────────────────────────────

def create_doc_search_server() -> "Server":
    """创建 MCP 文档检索 Server"""
    if not HAS_MCP:
        raise ImportError("mcp package not installed. Run: pip install mcp")

    server = Server("doc-search-server")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="search_documents",
                description="混合检索文档知识库 (BM25 + Dense Embedding + RRF 融合排序)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "检索查询文本",
                        },
                        "method": {
                            "type": "string",
                            "enum": ["hybrid", "bm25", "dense"],
                            "description": "检索方法: hybrid(混合,默认), bm25(关键词), dense(语义)",
                            "default": "hybrid",
                        },
                        "doc_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "限定搜索的文档 ID 列表，不传则搜索全部文档",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="get_document",
                description="根据文档 ID 获取完整文档内容",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "doc_id": {
                            "type": "string",
                            "description": "文档 ID (从 search_documents 结果中获取)",
                        },
                    },
                    "required": ["doc_id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "search_documents":
            query = arguments.get("query", "")
            method = arguments.get("method", "hybrid")
            doc_ids = arguments.get("doc_ids")
            result = search_documents_impl(query, method, doc_ids=doc_ids)
        elif name == "get_document":
            doc_id = arguments.get("doc_id", "")
            result = get_document_impl(doc_id)
        else:
            result = json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)

        return [TextContent(type="text", text=result)]

    return server


async def run_doc_server():
    """启动 MCP 文档检索 Server (stdio 模式)"""
    server = create_doc_search_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


# ── 直接入口 ──────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_doc_server())
