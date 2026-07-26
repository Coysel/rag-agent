"""
MCP 联网搜索 Server — 基于百度搜索 API (千帆 AppBuilder)

提供工具:
  - web_search: 联网搜索网页，返回标题、链接和摘要

API 文档: https://ai.baidu.com/ai-doc/AppBuilder/pmaxd1hvy
免费额度: 每日 100 次
"""
import json
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False


# ── 百度搜索 API 配置 ────────────────────────────────────

_BAIDU_SEARCH_URL = "https://qianfan.baidubce.com/v2/ai_search/web_search"


def _get_api_key() -> str:
    """从 config 获取百度 API Key"""
    from config import BAIDU_API_KEY
    return BAIDU_API_KEY


# ── 搜索实现（同步，在线程池中运行）─────────────────────

def _search_sync(query: str, max_results: int) -> str:
    """在单独的线程中执行 HTTP 请求，避免阻塞 asyncio 事件循环"""
    import httpx

    api_key = _get_api_key()
    if not api_key:
        return json.dumps({
            "error": "百度 API Key 未配置。请在 .env 中设置 BAIDU_API_KEY。"
            "申请地址: https://qianfan.cloud.baidu.com/appbuilder",
        }, ensure_ascii=False)

    max_results = min(max(max_results, 1), 20)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    body = {
        "messages": [{"role": "user", "content": query}],
        "search_source": "baidu_search_v2",
        "resource_type_filter": [{"type": "web", "top_k": max_results}],
    }

    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.post(_BAIDU_SEARCH_URL, headers=headers, json=body)
            resp.raise_for_status()

        data = resp.json()

        # 检查业务层错误码（401 等 HTTP 错误由 raise_for_status 处理，
        # 这里处理 HTTP 200 但业务失败的情况）
        error_code = data.get("code")
        if error_code:
            return json.dumps({
                "error": f"百度 API 错误 (code={error_code}): {data.get('message', '未知错误')}",
            }, ensure_ascii=False)

        references = data.get("references", [])

        # 完整传递百度 API 返回的字段，不做截断
        results = []
        for ref in references:
            # content 和 snippet 通常相同（均为摘要），content 可能更长
            full_content = ref.get("content") or ref.get("snippet", "")
            results.append({
                "title": ref.get("title", "无标题"),
                "url": ref.get("url", ""),
                "content": full_content,
                "snippet": ref.get("snippet", ""),
                "website": ref.get("website", ""),
                "date": ref.get("date", ""),
                "rerank_score": ref.get("rerank_score", 0.5),
                "authority_score": ref.get("authority_score", 0.5),
            })

        return json.dumps({
            "results": results,
            "total": len(results),
            "query": query,
        }, ensure_ascii=False)

    except httpx.HTTPStatusError as e:
        # HTTP 4xx/5xx → 尝试解析 body 中的错误信息
        detail = ""
        try:
            err_data = e.response.json()
            detail = err_data.get("message", e.response.text[:200])
        except Exception:
            detail = e.response.text[:200]
        return json.dumps({
            "error": f"百度 API HTTP {e.response.status_code}: {detail}",
        }, ensure_ascii=False)
    except httpx.TimeoutException:
        return json.dumps({"error": "搜索请求超时（15s），请稍后重试"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"搜索失败: {str(e)}"}, ensure_ascii=False)


# ── MCP Server 工厂函数 ───────────────────────────────────

def create_web_search_server() -> "Server":
    if not HAS_MCP:
        raise ImportError("mcp package not installed. Run: pip install mcp")

    server = Server("web-search-server")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="web_search",
                description=(
                    "使用百度搜索引擎获取互联网最新信息。"
                    "返回网页标题、URL、内容摘要、发布日期和来源网站。"
                    "适用于: 用户要求联网搜索、查询实时信息、最新新闻、天气、"
                    "最新版本、最新进展等本地知识库不可能包含的内容。"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索查询文本。建议使用简洁的关键词组合，例如 '北京今天天气' 而非 '帮我查一下北京今天的天气怎么样'",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "返回结果数量，默认 5，最多 20",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "web_search":
            query = arguments.get("query", "")
            max_results = arguments.get("max_results", 5)
            if not query.strip():
                result = json.dumps({"error": "搜索查询不能为空"}, ensure_ascii=False)
            else:
                result = await asyncio.to_thread(_search_sync, query, max_results)
        else:
            result = json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)
        return [TextContent(type="text", text=result)]

    return server


# ── 独立运行入口 ──────────────────────────────────────────

async def run_web_server():
    server = create_web_search_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(run_web_server())
