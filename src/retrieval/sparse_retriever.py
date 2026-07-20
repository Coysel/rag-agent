"""
BM25 稀疏检索器 — 基于词频-逆文档频率

擅长: 精确词匹配（搜"Conv2d"必须包含该词）
局限: 语义匹配弱（搜"卷积"找不到只写"convolution"的文档）
"""
from typing import List, Tuple

from src.indexing.bm25_index import get_bm25_index
from config import RETRIEVAL_TOP_K


class SparseRetriever:
    """BM25 稀疏检索器"""

    def __init__(self):
        self._bm25 = get_bm25_index()

    def search(self, query: str, top_k: int = RETRIEVAL_TOP_K,
               doc_ids: list[str] | None = None) -> List[Tuple[dict, float]]:
        """
        BM25 关键词检索

        Args:
            query: 查询文本
            top_k: 返回数量
            doc_ids: 限定文档 ID 列表，None 表示搜索全部（BM25 通过后置过滤实现）

        Returns:
            [(doc_dict, bm25_score), ...]
        """
        if not self._bm25.is_built:
            return []

        results = self._bm25.search(query, top_k=top_k)

        # 后置过滤：BM25 不支持原生筛选
        if doc_ids:
            doc_set = set(doc_ids)
            results = [(d, s) for d, s in results if d.get("doc_id", "") in doc_set]

        return results
