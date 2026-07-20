"""
统一检索管线 — 项目中所有检索的唯一入口

消除了三套并行检索代码:
  - doc_server.py:_search_documents()
  - ragas_eval.py:_retrieve_docs()
  - 各处的 ad-hoc 检索调用

所有调用方都走这个函数，保证检索行为一致。
"""
import time
from typing import List, Tuple

from config import HYBRID_TOP_K, RETRIEVAL_TOP_K
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.dense_retriever import DenseRetriever
from src.retrieval.sparse_retriever import SparseRetriever
from src.retrieval.parent_retriever import get_parent_retriever


def retrieve(
    query: str,
    method: str = "hybrid",
    top_k: int = HYBRID_TOP_K,
    return_latency: bool = False,
    doc_ids: list[str] | None = None,
) -> List[dict] | Tuple[List[dict], float]:
    """
    统一检索入口 — 项目中所有检索调用的唯一路径

    Args:
        query: 检索查询文本
        method: "hybrid" | "bm25" | "dense"
        top_k: 返回文档数量（仅 hybrid 模式的 RRF 融合阶段生效）
        return_latency: 是否返回耗时
        doc_ids: 限定文档 ID 列表，None 表示搜索全部

    Returns:
        若 return_latency=False: [doc_dict, ...] 已完成 parent 展开 + 去重
        若 return_latency=True:  ([doc_dict, ...], latency_seconds)
    """
    t0 = time.time()

    parent_retriever = get_parent_retriever()

    if method == "bm25":
        retriever = SparseRetriever()
        raw = retriever.search(query, top_k=RETRIEVAL_TOP_K, doc_ids=doc_ids)
        docs = [r[0] for r in raw]
    elif method == "dense":
        retriever = DenseRetriever()
        raw = retriever.search(query, top_k=RETRIEVAL_TOP_K, doc_ids=doc_ids)
        docs = [r[0] for r in raw]
    else:  # hybrid
        retriever = HybridRetriever()
        docs = retriever.search(query, top_k=top_k, doc_ids=doc_ids)

    # Parent-Document 展开 + 去重
    docs = parent_retriever.expand_to_parents(docs)

    latency = time.time() - t0

    if return_latency:
        return docs, latency
    return docs
