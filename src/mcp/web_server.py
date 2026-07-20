"""
MCP 联网搜索 Server — 基于 Bing 的网页搜索工具

提供工具:
  - web_search: 联网搜索网页，返回标题、链接和摘要
"""
import json
import re
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


# ── Bing HTML 解析 ────────────────────────────────────────

_BING_URL = "https://cn.bing.com/search"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

_ALGO_RE = re.compile(r'<li class="b_algo"[^>]*>(.*?)</li>', re.DOTALL)
_TITLE_RE = re.compile(r'<h2[^>]*><a[^>]*href="([^"]*)"[^>]*>(.*?)</a></h2>', re.DOTALL)
_SNIPPET_RE = re.compile(r'<p[^>]*>(.*?)</p>', re.DOTALL)
_TAG_RE = re.compile(r'<[^>]+>')


def _clean_html(text: str) -> str:
    text = _TAG_RE.sub("", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


def _extract_results(html: str, max_results: int) -> list:
    results = []
    for match in _ALGO_RE.finditer(html):
        if len(results) >= max_results:
            break
        block = match.group(1)
        title_match = _TITLE_RE.search(block)
        if not title_match:
            continue
        url = title_match.group(1)
        title = _clean_html(title_match.group(2))
        snippet = ""
        snippet_match = _SNIPPET_RE.search(block)
        if snippet_match:
            snippet = _clean_html(snippet_match.group(1))
        if title and url:
            results.append({"title": title, "url": url, "snippet": snippet[:500]})
    return results


# ── 搜索实现（同步，在线程池中运行）─────────────────────

def _search_sync(query: str, max_results: int) -> str:
    """在单独的线程中执行 HTTP 请求，避免阻塞 asyncio 事件循环"""
    try:
        import httpx
        max_results = min(max(max_results, 1), 10)

        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(_BING_URL, params={"q": query, "count": max_results}, headers=_HEADERS)
            resp.raise_for_status()

        raw_results = _extract_results(resp.text, max_results)

        return json.dumps({
            "results": raw_results,
            "total": len(raw_results),
            "query": query,
        }, ensure_ascii=False)
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
                    "使用 Bing 搜索互联网获取最新信息。"
                    "返回网页标题、URL 和内容摘要。"
                    "适用于: 用户要求联网搜索、查询实时信息、最新新闻、天气、"
                    "最新版本、最新进展等本地知识库不可能包含的内容。"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索查询文本",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "返回结果数量，默认 5，最多 10",
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
                # 在独立线程中运行同步 HTTP 请求，避免阻塞 asyncio
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
