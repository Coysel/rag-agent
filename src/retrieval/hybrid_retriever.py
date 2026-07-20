"""
RRF (Reciprocal Rank Fusion) 混合检索融合

核心算法 — 用排名而非原始分数融合，因为:
  - BM25 分数无界
  - 余弦相似度在 [-1, 1]
  - 直接加权需要归一化，用排名巧妙绕过

加权 RRF 公式: score(d) = Σ w_i × 1/(k + rank_i(d))  对每个检索器 i

参考: Cormack et al., "Reciprocal Rank Fusion outperforms Condorcet and
individual rank learning methods", SIGIR 2009.
"""
from typing import List, Tuple, Dict

from config import RETRIEVAL_TOP_K, HYBRID_TOP_K, RRF_K, DENSE_WEIGHT, SPARSE_WEIGHT


def reciprocal_rank_fusion(
    dense_results: List[Tuple[dict, float]],
    sparse_results: List[Tuple[dict, float]],
    k: int = RRF_K,
    top_k: int = HYBRID_TOP_K,
    dense_weight: float = DENSE_WEIGHT,
    sparse_weight: float = SPARSE_WEIGHT,
) -> List[dict]:
    """
    加权 RRF 混合检索融合

    融合逻辑:
      1. 对每个检索器的结果按排名打分: w_i × 1/(k + rank)
      2. 同一文档在不同检索器中的分数求和
      3. 按 RRF 总分降序排列，返回 top_k

    Args:
        dense_results: [(doc_dict, similarity_score), ...]
        sparse_results: [(doc_dict, bm25_score), ...]
        k: RRF 平滑常数 (默认 60)
        top_k: 最终返回数量
        dense_weight: Dense 检索器权重（>1 偏语义）
        sparse_weight: BM25 检索器权重（>1 偏关键词）

    Returns:
        [doc_dict, ...] 按 RRF 分数降序排列，doc_dict 包含 rrf_score 字段
    """
    rrf_scores: Dict[str, float] = {}
    merged_docs: Dict[str, dict] = {}

    # 处理 dense 结果
    for rank, (doc, _) in enumerate(dense_results, start=1):
        key = doc.get("parent_id") or doc.get("id", "")
        rrf = dense_weight / (k + rank)
        rrf_scores[key] = rrf_scores.get(key, 0) + rrf
        if key not in merged_docs:
            merged_docs[key] = dict(doc)

    # 处理 sparse 结果
    for rank, (doc, _) in enumerate(sparse_results, start=1):
        key = doc.get("parent_id") or doc.get("id", "")
        rrf = sparse_weight / (k + rank)
        rrf_scores[key] = rrf_scores.get(key, 0) + rrf
        if key not in merged_docs:
            merged_docs[key] = dict(doc)

    # 按 RRF 总分降序排列
    ranked_keys = sorted(rrf_scores, key=rrf_scores.get, reverse=True)

    # 返回 top_k
    results = []
    for key in ranked_keys[:top_k]:
        doc = merged_docs[key]
        doc["rrf_score"] = rrf_scores[key]
        results.append(doc)

    return results


class HybridRetriever:
    """混合检索器 — Dense + BM25 + 加权 RRF"""

    def __init__(self, dense_weight: float = DENSE_WEIGHT, sparse_weight: float = SPARSE_WEIGHT):
        from src.retrieval.dense_retriever import DenseRetriever
        from src.retrieval.sparse_retriever import SparseRetriever

        self._dense = DenseRetriever()
        self._sparse = SparseRetriever()
        self._dense_weight = dense_weight
        self._sparse_weight = sparse_weight

    def search(self, query: str, top_k: int = HYBRID_TOP_K,
               doc_ids: list[str] | None = None) -> List[dict]:
        """加权 RRF 混合检索"""
        dense_results = self._dense.search(query, top_k=RETRIEVAL_TOP_K, doc_ids=doc_ids)
        sparse_results = self._sparse.search(query, top_k=RETRIEVAL_TOP_K, doc_ids=doc_ids)
        return reciprocal_rank_fusion(
            dense_results, sparse_results, top_k=top_k,
            dense_weight=self._dense_weight,
            sparse_weight=self._sparse_weight,
        )
