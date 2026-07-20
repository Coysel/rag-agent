"""
Dense 语义检索器 — 基于 ChromaDB 向量相似度

擅长: 语义匹配（搜"卷积"能找到"convolution"）
局限: 精确词匹配弱（搜"Conv2d"可能漏掉）
"""
from typing import List, Tuple

from src.indexing.embeddings import get_embedding_model
from src.indexing.vector_store import get_vector_store
from config import RETRIEVAL_TOP_K


class DenseRetriever:
    """Dense (向量) 检索器"""

    def __init__(self):
        self._embedding_model = get_embedding_model()
        self._vector_store = get_vector_store()

    def search(self, query: str, top_k: int = RETRIEVAL_TOP_K,
               doc_ids: list[str] | None = None) -> List[Tuple[dict, float]]:
        """
        语义检索

        Args:
            query: 查询文本
            top_k: 返回数量
            doc_ids: 限定文档 ID 列表，None 表示搜索全部

        Returns:
            [(doc_dict, similarity_score), ...]
            doc_dict 包含: id, content, parent_id, title, source, doc_id, dense_score
        """
        if self._vector_store.count == 0:
            return []

        where = None
        if doc_ids:
            where = {"doc_id": {"$in": list(doc_ids)}}

        query_embedding = self._embedding_model.embed_single(query)
        return self._vector_store.search(query_embedding, top_k=top_k, where_filter=where)
