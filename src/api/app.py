"""
FastAPI 应用工厂 — create_app()

将 app 创建从 main.py 中分离，便于测试和配置注入。

用法:
    from src.api.app import create_app
    app = create_app()
"""
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import API_HOST, API_PORT, DOCUMENTS_DIR
from src.core.exceptions import AppException, app_exception_handler, general_exception_handler
from src.api.middleware import setup_middleware
from src.api.routes import register_routes
from src.utils.logging import setup_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    setup_logging()
    logger = get_logger()
    logger.info("Agentic RAG 智能问答系统 v2.0 启动中...")

    # ── BM25 索引 ──────────────────────────────────────────
    try:
        from src.indexing.bm25_index import get_bm25_index
        bm25 = get_bm25_index()
        bm25.load()
        logger.info(f"BM25 索引已加载 ({bm25.document_count} 篇文档)")
    except FileNotFoundError:
        logger.warning("BM25 索引未找到，请先运行: python scripts/index_documents.py")
    except Exception as e:
        logger.warning(f"BM25 索引加载失败: {e}")

    # ── ChromaDB ───────────────────────────────────────────
    try:
        from src.indexing.vector_store import get_vector_store
        from src.api.routes.documents import _get_document_list
        vs = get_vector_store()
        doc_info = _get_document_list(include_doc_id=False)
        unique_docs = doc_info.get("total_unique", 0)
        logger.info(f"ChromaDB 已连接 ({vs.count} 条向量, {unique_docs} 篇唯一文档)")
    except Exception as e:
        logger.warning(f"ChromaDB 连接失败: {e}")

    # ── LLM ────────────────────────────────────────────────
    try:
        from src.agent.llm_client import get_llm_client
        llm_info = get_llm_client().get_info()
        key_prefix = os.getenv("DEEPSEEK_API_KEY", "")[:10] if llm_info["provider"] == "deepseek" else ""
        key_status = f"{key_prefix}... (已配置)" if key_prefix else "未配置"
        logger.info(f"LLM: {llm_info['provider']} / {llm_info['model']} @ {llm_info['base_url']} | Key: {key_status}")
    except Exception as e:
        logger.warning(f"LLM 初始化失败: {e}")

    # ── Embedding ──────────────────────────────────────────
    try:
        from src.indexing.embeddings import get_embedding_model
        emb = get_embedding_model()
        logger.info(f"Embedding: {emb.provider} / {emb.model_name}")
    except Exception as e:
        logger.warning(f"Embedding 初始化失败: {e}")

    # ── MCP 服务 ───────────────────────────────────────────
    try:
        from src.mcp.client_manager import get_mcp_manager
        mcp = get_mcp_manager()
        await mcp.initialize()
        tool_names = [t.name for t in mcp._all_tools]
        logger.info(f"MCP 服务已连接, 发现 {len(tool_names)} 个工具: {tool_names}")
    except Exception as e:
        logger.warning(f"MCP 服务初始化失败: {e}")

    # ── Session 存储清理 ───────────────────────────────────
    try:
        from src.storage.session_store import get_session_store
        store = get_session_store()
        cleaned = store.cleanup()
        if cleaned > 0:
            logger.info(f"Session 清理: {cleaned} 条过期会话已删除")
    except Exception:
        pass

    logger.info(f"服务就绪: http://{API_HOST}:{API_PORT}")
    logger.info("=" * 60)

    yield

    # 关闭时清理
    try:
        from src.mcp.client_manager import get_mcp_manager
        mcp = get_mcp_manager()
        await mcp.close()
        logger.info("MCP 服务已关闭")
    except Exception:
        pass

    logger.info("服务关闭")


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例

    Returns:
        配置好的 FastAPI app，可直接传给 uvicorn
    """
    app = FastAPI(
        title="Agentic RAG 智能问答系统",
        description="基于 LangGraph + MCP + 混合检索的 Agentic RAG 系统",
        version="2.0.0",
        lifespan=lifespan,
    )

    # 中间件
    setup_middleware(app)

    # 异常处理
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # 路由注册
    register_routes(app)

    return app
