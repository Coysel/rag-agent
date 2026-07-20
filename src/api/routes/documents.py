"""
文档列表端点 — GET /documents, plus shared helper used by admin routes
"""
from fastapi import APIRouter

from src.indexing.vector_store import get_vector_store

router = APIRouter(tags=["documents"])


def _get_document_list(include_doc_id: bool = False) -> dict:
    """从 ChromaDB 提取去重后的文档列表（admin 和 public 端点复用）"""
    vs = get_vector_store()
    try:
        col = vs.get_or_create_collection()
        all_data = col.get(include=["metadatas"])
        if not all_data["metadatas"]:
            return {"documents": [], "total_unique": 0, "total_chunks": 0}

        doc_map = {}
        for m in all_data["metadatas"]:
            if not m:
                continue
            doc_id = m.get("doc_id", "")
            if doc_id not in doc_map:
                entry = {
                    "title": m.get("title", "未知"),
                    "source": m.get("source", ""),
                    "chunk_count": 0,
                }
                if include_doc_id:
                    entry["doc_id"] = doc_id
                doc_map[doc_id] = entry
            doc_map[doc_id]["chunk_count"] += 1

        docs_list = sorted(doc_map.values(), key=lambda d: d["source"])
        return {
            "documents": docs_list,
            "total_unique": len(docs_list),
            "total_chunks": len(all_data["metadatas"]),
        }
    except Exception as e:
        return {"documents": [], "total_unique": 0, "total_chunks": 0, "error": str(e)}


@router.get("/documents")
async def list_documents():
    """列出所有已索引的文档（去重，公开端点）"""
    return _get_document_list(include_doc_id=False)
