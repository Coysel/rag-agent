"""
MCP SQLite 查询 Server — 基于 MCP Python SDK 实现的数据库查询工具

提供工具:
  - execute_query: 执行 SELECT 查询
  - list_tables: 列出数据库中的所有表

使用场景: 当知识库中包含结构化数据（如性能对比表、配置参数表）时，
Agent 可以通过 SQL 查询精确获取数据。
"""
import json
import sqlite3
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

# 默认数据库路径 (优先使用 config 配置)
try:
    from config import SQLITE_DB_PATH as DEFAULT_DB_PATH
except ImportError:
    DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "knowledge.db"


# ── 工具实现 ──────────────────────────────────────────────

def _get_connection(db_path: str = None) -> sqlite3.Connection:
    """获取数据库连接"""
    if db_path is None:
        db_path = str(DEFAULT_DB_PATH)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def execute_query_impl(sql: str, db_path: str = None) -> str:
    """
    执行 SELECT 查询 (只读安全限制)

    Args:
        sql: SELECT SQL 语句
        db_path: 数据库路径

    Returns:
        JSON 格式的查询结果
    """
    sql = sql.strip()

    # 安全检查：只允许 SELECT 语句
    if not sql.upper().startswith("SELECT"):
        return json.dumps({
            "error": "仅允许 SELECT 查询，不支持修改操作",
            "sql": sql,
        }, ensure_ascii=False)

    # 禁止危险操作
    dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "ATTACH"]
    upper_sql = sql.upper()
    for kw in dangerous_keywords:
        if kw in upper_sql:
            return json.dumps({
                "error": f"不允许包含 {kw} 语句",
            }, ensure_ascii=False)

    try:
        conn = _get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(sql)

        columns = [d[0] for d in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        conn.close()

        result = {
            "columns": columns,
            "row_count": len(rows),
            "rows": [dict(zip(columns, row)) for row in rows[:100]],  # 最多返回 100 行
            "truncated": len(rows) > 100,
        }
        return json.dumps(result, ensure_ascii=False, default=str)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def list_tables_impl(db_path: str = None) -> str:
    """列出所有表"""
    try:
        conn = _get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        result = {"tables": tables, "count": len(tables)}
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e), "tables": []}, ensure_ascii=False)


# ── MCP Server 定义 ───────────────────────────────────────

def create_sqlite_server(db_path: str = None) -> "Server":
    """创建 MCP SQLite 查询 Server"""
    if not HAS_MCP:
        raise ImportError("mcp package not installed. Run: pip install mcp")

    server = Server("sqlite-query-server")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="execute_query",
                description=(
                    "执行 SQLite SELECT 查询，获取结构化数据。"
                    "适用于: 需要统计数据、查询表格数据的问题。"
                    "注意: 仅支持只读 SELECT 查询。"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "要执行的 SELECT 查询语句，例如: SELECT * FROM models WHERE accuracy > 0.9",
                        },
                    },
                    "required": ["sql"],
                },
            ),
            Tool(
                name="list_tables",
                description="列出数据库中的所有表及其结构信息",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "execute_query":
            sql = arguments.get("sql", "")
            result = execute_query_impl(sql, db_path)
        elif name == "list_tables":
            result = list_tables_impl(db_path)
        else:
            result = json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)

        return [TextContent(type="text", text=result)]

    return server


async def run_sqlite_server():
    """启动 MCP SQLite 查询 Server (stdio 模式)"""
    server = create_sqlite_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


# ── 直接入口 ──────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_sqlite_server())
