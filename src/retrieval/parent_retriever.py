"""
Parent-Document Retriever — 小块检索 + 大块上下文策略

策略:
  1. 检索时用小块 (child, ~256 tokens): 向量匹配更精准
  2. 生成时用大块 (parent, ~1024 tokens): 保留完整上下文，避免信息碎片化

这样既保证了检索精度，又确保了生成时能看到完整的上下文。
"""
from typing import List, Dict


class ParentDocumentRetriever:
    """
    Parent-Document Retriever

    维护 child → parent 的映射关系。
    检索返回 child chunks，生成时自动替换为对应的 parent chunks。
    """

    def __init__(self):
        self._child_to_parent: Dict[str, str] = {}# child_id → parent_id
        self._parents: Dict[str, dict] = {}# parent_id → parent 完整 dict

    def build_from_chunks(
        self,
        child_chunks: List[dict],
        parent_chunks: List[dict],
        child_to_parent: Dict[str, str],
    ) -> None:
        """从已切分好的 chunks 构建映射"""
        self._child_to_parent = dict(child_to_parent)
        self._parents = {p["id"]: p for p in parent_chunks}

    def get_parent_doc(self, child_id: str) -> dict | None:
        """根据 child ID 获取对应的 parent 完整信息"""
        parent_id = self._child_to_parent.get(child_id)
        if parent_id and parent_id in self._parents:
            return dict(self._parents[parent_id])
        return None

    def expand_to_parents(self, child_results: List[dict]) -> List[dict]:
        """
        将 child 检索结果扩展为 parent 文档

        去除重复 (多个 child 可能属于同一个 parent)，
        返回去重后的 parent 文档列表。

        Args:
            child_results: 检索返回的 child chunks 列表

        Returns:
            去重后的 parent chunks 列表
        """
        seen_parents: set = set()
        parent_results = []

        for child_doc in child_results:
            child_id = child_doc.get("id", "")
            parent_id = child_doc.get("parent_id") or self._child_to_parent.get(child_id)

            if not parent_id or parent_id in seen_parents:#去重
                continue

            seen_parents.add(parent_id)
            parent_doc = self._parents.get(parent_id)

            if parent_doc:
                result = dict(parent_doc)
                # 保留 child 的检索分数
                result["rrf_score"] = child_doc.get("rrf_score", 0)
                result["dense_score"] = child_doc.get("dense_score", 0)
                result["bm25_score"] = child_doc.get("bm25_score", 0)
                parent_results.append(result)
            else:
                # parent 不在缓存中，直接用 child 内容
                parent_results.append(dict(child_doc))

        return parent_results


# 全局单例
_parent_retriever: ParentDocumentRetriever | None = None


def get_parent_retriever() -> ParentDocumentRetriever:
    """获取全局 Parent-Document Retriever 实例"""
    global _parent_retriever
    if _parent_retriever is None:
        _parent_retriever = ParentDocumentRetriever()
    return _parent_retriever
