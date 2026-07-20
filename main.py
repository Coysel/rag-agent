"""
Agentic RAG 智能问答系统 — FastAPI 入口

启动方式:
    python main.py

    或:
    uvicorn main:app --host 0.0.0.0 --port 8001 --reload

API 端点:
    POST /chat     — 对话接口 (支持 SSE 流式)
    GET  /health   — 健康检查

架构:
    基于 LangGraph 的 ReAct 循环 + MCP 工具层 + 混合检索
"""
import os

from config import API_HOST, API_PORT
from src.api.app import create_app

# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn
    reload = os.getenv("RELOAD", "true").lower() in ("1", "true", "yes")
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=reload,
    )
