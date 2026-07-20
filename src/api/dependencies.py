"""
FastAPI 依赖注入 — 统一管理全局单例的获取

用法:
    @router.post("/chat")
    async def chat(request: ChatRequest, graph=Depends(get_graph)):
        ...
"""
from functools import lru_cache

from src.agent.graph import build_graph
from src.retrieval.router import QueryRouter
from src.storage.session_store import get_session_store, SessionStore


@lru_cache()
def _get_graph_cached():
    """LangGraph ReAct 循环（编译一次，全局复用）"""
    return build_graph()


@lru_cache()
def _get_query_router_cached():
    """查询分类路由器（初始化一次）"""
    return QueryRouter()


def get_graph():
    """获取编译好的 LangGraph"""
    return _get_graph_cached()


def get_query_router():
    """获取查询分类路由器"""
    return _get_query_router_cached()


def get_session() -> SessionStore:
    """获取 Session 持久化存储"""
    return get_session_store()
