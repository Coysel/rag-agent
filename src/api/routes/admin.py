"""
Admin API — 文档管理端点（需 API Key 鉴权）

端点:
  GET    /admin/documents          — 列出所有文档
  POST   /admin/documents          — 上传/索引新文档（支持自动分类）
  DELETE /admin/documents/{doc_id} — 删除文档及所有 chunks
  POST   /admin/rebuild            — 全量重建索引
"""
from fastapi import APIRouter, HTTPException, Depends

from src.core.security import verify_admin_key
from src.core.exceptions import NotFoundError, ValidationError
from src.indexing.index_manager import get_index_manager
from src.api.routes.documents import _get_document_list
from src.api.schemas.common import AddDocumentRequest
from src.utils.logging import get_logger

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/documents")
async def list_documents_admin(_=Depends(verify_admin_key)):
    """列出所有已索引文档的详细信息（含 doc_id，供管理操作使用）"""
    return _get_document_list(include_doc_id=True)


@router.post("/documents")
async def add_document(request: AddDocumentRequest, _=Depends(verify_admin_key)):
    """
    添加文档（JSON 格式）

    Body:
        {"content": "文档正文", "title": "标题", "source": "来源路径（可选）"}

    如果 AUTO_CATEGORIZE_ON_UPLOAD=true（默认），上传后自动进行
    增量摘要+分类，归入已有类别或创建新类别。
    """
    from config import AUTO_CATEGORIZE_ON_UPLOAD

    manager = get_index_manager()
    logger = get_logger()

    source = request.source or request.title

    try:
        result = manager.add_document(request.content, request.title, source)
        doc_id = result["doc_id"]
        logger.info(f"Admin: 添加文档 '{request.title}' → {doc_id}")

        response = {"status": "ok", "doc_id": doc_id, "title": request.title}

        # ── 自动增量分类 ──────────────────────────────────
        if AUTO_CATEGORIZE_ON_UPLOAD:
            try:
                from src.categorization.incremental import IncrementalCategorizer
                categorizer = IncrementalCategorizer()
                cat_result = categorizer.categorize_new_document(
                    doc_id=doc_id,
                    title=request.title,
                    child_chunks=result["child_chunks"],
                    parent_chunks=result["parent_chunks"],
                    child_to_parent=result["child_to_parent"],
                )
                response["auto_categorized"] = cat_result
                if not cat_result.get("skipped"):
                    verb = "新类别" if cat_result.get("is_new") else "归入"
                    logger.info(
                        f"Admin: 自动分类 → {verb}「{cat_result['category_name']}」"
                        f"（{cat_result.get('reason', '')}）"
                    )
            except Exception as cat_err:
                logger.warning(f"Admin: 自动分类失败（不影响上传）: {cat_err}")

        return response

    except Exception as e:
        logger.error(f"Admin: 添加文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, _=Depends(verify_admin_key)):
    """删除文档及所有 chunks"""
    manager = get_index_manager()
    logger = get_logger()
    try:
        success = manager.remove_document(doc_id)
        if success:
            logger.info(f"Admin: 删除文档 {doc_id}")
            return {"status": "ok", "doc_id": doc_id}
        raise NotFoundError("文档", doc_id)
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Admin: 删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rebuild")
async def rebuild_index(_=Depends(verify_admin_key)):
    """全量重建索引"""
    manager = get_index_manager()
    logger = get_logger()
    try:
        result = manager.rebuild_all()
        logger.info(f"Admin: 全量重建完成 → {result}")
        return {"status": "ok", **result}
    except Exception as e:
        logger.error(f"Admin: 重建失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
