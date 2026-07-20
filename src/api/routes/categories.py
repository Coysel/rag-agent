"""
类别管理端点 — GET /categories, POST /admin/categories/generate, GET /admin/categories/progress
"""
import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException

from src.core.security import verify_admin_key
from src.core.exceptions import ServiceUnavailableError
from src.categorization.category_store import get_category_store, CategoryStore
from src.utils.logging import get_logger

PROGRESS_FILE = Path("data/category_progress.json")

router = APIRouter(tags=["categories"])


@router.get("/categories")
async def list_categories():
    """获取所有文档类别"""
    store = get_category_store()
    categories = store.get_all()
    return {
        "categories": categories,
        "last_generated": store.get_last_generated(),
    }


@router.post("/admin/categories/generate")
async def generate_categories(_=Depends(verify_admin_key)):
    """
    生成文档类别 — 对已索引文档进行层次摘要 + 聚类

    需要 Admin API Key。
    这是一个耗时操作，可能需要数分钟。
    """
    logger = get_logger()
    store = get_category_store()

    # 获取所有已索引文档的信息
    from src.indexing.vector_store import get_vector_store
    from src.indexing.bm25_index import get_bm25_index
    from src.retrieval.parent_retriever import get_parent_retriever

    vs = get_vector_store()
    bm25 = get_bm25_index()
    parent = get_parent_retriever()

    if vs.count == 0:
        raise HTTPException(status_code=400, detail="索引为空，请先索引文档后再生成类别")

    # 获取所有 child chunks（从 ChromaDB）
    try:
        collection = vs.get_or_create_collection()
        all_data = collection.get(include=["documents", "metadatas"])
    except Exception as e:
        raise ServiceUnavailableError("无法读取向量存储", str(e))

    if not all_data["ids"]:
        raise HTTPException(status_code=400, detail="索引中无数据")

    # 构建 chunks 列表
    child_chunks = []
    for i, cid in enumerate(all_data["ids"]):
        meta = all_data["metadatas"][i] if all_data["metadatas"] else {}
        child_chunks.append({
            "id": cid,
            "content": all_data["documents"][i] if all_data["documents"] else "",
            "doc_id": meta.get("doc_id", ""),
            "parent_id": meta.get("parent_id", ""),
            "title": meta.get("title", "未知"),
        })

    # 构建文档字典 {doc_id: {title, source}}
    docs = {}
    parent_to_doc = {}
    child_to_parent = {}
    for cc in child_chunks:
        doc_id = cc["doc_id"]
        if doc_id and doc_id not in docs:
            docs[doc_id] = {"title": cc["title"], "source": meta.get("source", "") if not docs.get(doc_id) else docs[doc_id].get("source", "")}

    # 构建 child_to_parent 映射和 parent_to_doc 映射
    for cc in child_chunks:
        child_to_parent[cc["id"]] = cc["parent_id"]
        parent_to_doc[cc["parent_id"]] = cc["doc_id"]

    # 从 parent_retriever 获取 parent chunks
    parent_chunks = list(parent._parents.values())

    logger.info(f"开始生成类别: {len(docs)} 篇文档, {len(child_chunks)} chunks, {len(parent_chunks)} parents")

    # ── 层次摘要生成 ────────────────────────────────────
    from src.categorization.summarizer import Summarizer
    from src.categorization.clusterer import Clusterer

    summarizer = Summarizer()
    summarizer.init_progress("child_summaries", len(child_chunks))

    # Step 1: Child chunk 摘要
    logger.info("Step 1/3: 生成 child chunk 摘要...")
    child_summaries = summarizer.summarize_child_chunks(child_chunks)

    # Step 2: Parent 聚合
    logger.info("Step 2/3: 聚合 parent 摘要...")
    summarizer.init_progress("parent_aggregation", len(parent_chunks))
    parent_summaries = summarizer.aggregate_parents(
        parent_chunks, child_summaries, child_to_parent,
    )

    # Step 3: Document 聚合
    logger.info("Step 3/3: 聚合文档摘要...")
    summarizer.init_progress("doc_aggregation", len(docs))
    doc_summaries = summarizer.aggregate_documents(
        docs, parent_summaries, parent_to_doc,
    )

    # ── 聚类 ────────────────────────────────────────────
    logger.info("聚类中...")
    summarizer._write_progress("clustering", 0, 1, "LLM 聚类中...")
    clusterer = Clusterer()
    categories = clusterer.cluster(docs, doc_summaries)

    # ── 保存 ────────────────────────────────────────────
    store.save_categories(categories)
    logger.info(f"类别生成完毕: {len(categories)} 个类别")
    summarizer._write_progress("done", 1, 1, f"完成 — {len(categories)} 个类别")

    return {
        "status": "ok",
        "categories": store.get_all(),
        "last_generated": store.get_last_generated(),
    }


@router.get("/admin/categories/progress")
async def get_progress():
    """
    查询类别生成进度（不需要 Admin Key，公开可查）

    返回:
        {stage, current, total, percent, message, started_at, updated_at}
        如果从未生成过则返回 {stage: "none"}
    """
    try:
        if not PROGRESS_FILE.exists():
            return {"stage": "none", "message": "尚未生成过类别"}
        data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        return data
    except Exception:
        return {"stage": "error", "message": "无法读取进度文件"}
