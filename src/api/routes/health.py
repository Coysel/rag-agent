"""
健康检查端点 — GET /health, /health/deep, /llm-test
"""
import time
from fastapi import APIRouter

from src.api.schemas.common import HealthResponse
from src.api.routes.documents import _get_document_list
from src.indexing.bm25_index import get_bm25_index
from src.indexing.vector_store import get_vector_store
from src.agent.llm_client import get_llm_client
from src.indexing.embeddings import get_embedding_model

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查 — 返回索引状态、LLM 配置等"""
    bm25 = get_bm25_index()
    vs = get_vector_store()

    doc_info = _get_document_list(include_doc_id=False)
    unique_doc_count = doc_info.get("total_unique", 0)
    chunk_count = doc_info.get("total_chunks", vs.count)

    llm_info = get_llm_client().get_info()
    emb = get_embedding_model()

    return HealthResponse(
        status="ok",
        index_ready=bm25.is_built and vs.count > 0,
        document_count=unique_doc_count,
        chunk_count=vs.count,
        llm_provider=llm_info["provider"],
        llm_model=llm_info["model"],
        embedding_provider=emb.provider,
        embedding_model=emb.model_name,
    )


@router.get("/health/deep")
async def health_check_deep():
    """深度健康检查 — 验证 LLM 连通性 + 检索功能"""
    result = {"status": "ok", "checks": {}}

    # LLM 连通性
    t0 = time.time()
    try:
        client = get_llm_client()
        client.create_message(
            system="", messages=[{"role": "user", "content": "ping"}],
            max_tokens=5, temperature=0,
        )
        result["checks"]["llm"] = {
            "status": "ok",
            "latency_ms": round((time.time() - t0) * 1000),
        }
    except Exception as e:
        result["checks"]["llm"] = {"status": "error", "message": str(e)}

    # 检索功能
    t0 = time.time()
    try:
        from src.retrieval.pipeline import retrieve
        docs = retrieve("ping", method="hybrid")
        result["checks"]["retrieval"] = {
            "status": "ok",
            "doc_count": len(docs),
            "latency_ms": round((time.time() - t0) * 1000),
        }
    except Exception as e:
        result["checks"]["retrieval"] = {"status": "error", "message": str(e)}

    if any(c.get("status") == "error" for c in result["checks"].values()):
        result["status"] = "degraded"

    return result


@router.get("/llm-test")
async def llm_test():
    """LLM 连接测试 — 调用 API 验证连通性和返回 token 用量"""
    client = get_llm_client()
    info = client.get_info()

    t0 = time.time()
    try:
        result = client.create_message(
            system="你是一个有用的助手。",
            messages=[{"role": "user", "content": "请用一句话介绍你自己"}],
            max_tokens=64,
            temperature=0,
        )
        latency = round(time.time() - t0, 3)
        return {
            "status": "ok",
            "llm": info,
            "response": result.get("text", ""),
            "usage": result.get("usage", {}),
            "latency_seconds": latency,
        }
    except Exception as e:
        return {
            "status": "error",
            "llm": info,
            "error": str(e),
            "hint": "请检查 .env 中的 DEEPSEEK_API_KEY 是否有效，以及网络是否能访问 api.deepseek.com",
        }
