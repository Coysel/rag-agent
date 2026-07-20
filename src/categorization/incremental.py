"""
增量分类编排器 — 单文档上传后自动摘要 + 归入已有类别或创建新类别

用法:
    from src.categorization.incremental import IncrementalCategorizer

    categorizer = IncrementalCategorizer()
    result = categorizer.categorize_new_document(
        doc_id="abc",
        title="深度学习入门",
        child_chunks=[...],
        parent_chunks=[...],
        child_to_parent={...},
    )
    # result = {"category_id": "xxx", "category_name": "深度学习", "is_new": False, ...}
"""
from typing import List, Dict

from src.categorization.summarizer import Summarizer
from src.categorization.clusterer import Clusterer
from src.categorization.category_store import get_category_store
from src.utils.logging import get_logger


class IncrementalCategorizer:
    """增量分类编排器 — 单文档摘要 + 分类 + 存储更新"""

    def __init__(self):
        self._summarizer = Summarizer()
        self._clusterer = Clusterer()
        self._store = get_category_store()
        self._logger = get_logger()

    def categorize_new_document(
        self,
        doc_id: str,
        title: str,
        child_chunks: List[dict],
        parent_chunks: List[dict],
        child_to_parent: Dict[str, str],
    ) -> dict:
        """
        对新上传的文档进行增量分类。

        Args:
            doc_id: 文档 ID
            title: 文档标题
            child_chunks: 刚索引的 child chunks
            parent_chunks: 刚索引的 parent chunks
            child_to_parent: child_id → parent_id 映射

        Returns:
            {
                "category_id": "xxx",
                "category_name": "...",
                "is_new": bool,
                "reason": "...",
                "skipped": bool,   # 文档过短导致跳过时
            }
        """
        # ── 空文档跳过 ──────────────────────────────────────
        total_content = "".join(c.get("content", "") for c in child_chunks)
        if len(total_content.strip()) < 20:
            self._logger.info(f"文档 {doc_id} 内容过短，跳过分类")
            return {
                "category_id": "",
                "category_name": "",
                "is_new": False,
                "reason": "文档内容过短，跳过分类",
                "skipped": True,
            }

        # ── 构建 docs 字典 ──────────────────────────────────
        docs = {doc_id: {"title": title, "source": ""}}
        parent_to_doc = {}
        for p in parent_chunks:
            parent_to_doc[p.get("id", "")] = doc_id

        # ── 三层摘要 ───────────────────────────────────────
        self._logger.info(f"增量分类: 开始摘要 {len(child_chunks)} 个 child chunks")
        child_summaries = self._summarizer.summarize_child_chunks(child_chunks)

        self._logger.info(f"增量分类: 聚合 {len(parent_chunks)} 个 parent")
        parent_summaries = self._summarizer.aggregate_parents(
            parent_chunks, child_summaries, child_to_parent,
        )

        self._logger.info(f"增量分类: 聚合文档摘要")
        doc_summaries = self._summarizer.aggregate_documents(
            docs, parent_summaries, parent_to_doc,
        )
        doc_summary = doc_summaries.get(doc_id, total_content[:500])

        # ── 分类判断 ───────────────────────────────────────
        existing = self._store.get_all()
        self._logger.info(f"增量分类: 分配类别（已有 {len(existing)} 个类别）")
        decision = self._clusterer.assign_to_category(title, doc_summary, existing)

        category_name = decision.get("category_name", "未分类")
        is_new = decision.get("is_new", False)
        reason = decision.get("reason", "")

        # ── 更新存储 ───────────────────────────────────────
        if is_new:
            # 创建新类别
            cat_id = self._store.create_category(
                name=category_name,
                description=reason,
                doc_ids=[doc_id],
            )
            self._logger.info(f"增量分类: 新建类别「{category_name}」({cat_id})")
        else:
            # 归入已有类别（按名称匹配）
            cat_id = self._find_category_by_name(existing, category_name)
            if cat_id:
                self._store.add_doc_to_category(doc_id, cat_id)
                self._logger.info(f"增量分类: 归入「{category_name}」({cat_id})")
            else:
                # 匹配失败 → 创建新类别
                cat_id = self._store.create_category(
                    name=category_name,
                    description=reason,
                    doc_ids=[doc_id],
                )
                is_new = True
                self._logger.info(f"增量分类: 名称无匹配，新建「{category_name}」({cat_id})")

        return {
            "category_id": cat_id,
            "category_name": category_name,
            "is_new": is_new,
            "reason": reason,
            "skipped": False,
        }

    def _find_category_by_name(self, categories: List[dict], name: str) -> str:
        """按名称模糊匹配已有类别，返回 category_id 或空字符串"""
        # 精确匹配
        for c in categories:
            if c.get("name", "") == name:
                return c["id"]
        # 包含匹配
        for c in categories:
            cat_name = c.get("name", "")
            if name in cat_name or cat_name in name:
                return c["id"]
        return ""
