"""
统一检索管线测试 — 三种检索方式的调度与 parent 展开

retrieve() 是项目所有检索调用的唯一入口（MCP doc_server、RAGAS 评测、
各 route 都走它），这里用 mock 替换三个 Retriever 与 parent_retriever，
验证调度分支和参数传递。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from src.retrieval.pipeline import retrieve


@pytest.fixture
def parent_stub(mocker):
    """parent_retriever mock：expand_to_parents 原样返回并打标"""
    mock_pr = mocker.patch("src.retrieval.pipeline.get_parent_retriever")
    mock_pr.return_value.expand_to_parents.side_effect = \
        lambda docs: [{**d, "expanded": True} for d in docs]
    return mock_pr.return_value


class TestMethodDispatch:

    def test_hybrid_is_default(self, mocker, parent_stub):
        """不传 method：走 HybridRetriever"""
        mock_cls = mocker.patch("src.retrieval.pipeline.HybridRetriever")
        mock_cls.return_value.search.return_value = [{"id": "h1"}]

        docs = retrieve("查询")

        mock_cls.assert_called_once_with()
        assert docs == [{"id": "h1", "expanded": True}]

    def test_bm25_uses_sparse_retriever(self, mocker, parent_stub):
        """method=bm25：走 SparseRetriever 并拆掉 (doc, score) 元组"""
        mock_cls = mocker.patch("src.retrieval.pipeline.SparseRetriever")
        mock_cls.return_value.search.return_value = [({"id": "s1"}, 1.2)]

        docs = retrieve("查询", method="bm25")

        assert docs[0]["id"] == "s1"
        assert docs[0]["expanded"] is True

    def test_dense_uses_dense_retriever(self, mocker, parent_stub):
        """method=dense：走 DenseRetriever"""
        mock_cls = mocker.patch("src.retrieval.pipeline.DenseRetriever")
        mock_cls.return_value.search.return_value = [({"id": "d1"}, 0.8)]

        docs = retrieve("查询", method="dense")

        assert docs[0]["id"] == "d1"

    def test_unknown_method_falls_back_to_hybrid(self, mocker, parent_stub):
        """未知 method：兜底到 hybrid 分支"""
        mock_cls = mocker.patch("src.retrieval.pipeline.HybridRetriever")
        mock_cls.return_value.search.return_value = []

        retrieve("查询", method="bogus")

        mock_cls.assert_called_once_with()


class TestParameters:

    def test_top_k_passed_to_hybrid(self, mocker, parent_stub):
        """top_k 透传给 hybrid 的 RRF 融合阶段"""
        mock_cls = mocker.patch("src.retrieval.pipeline.HybridRetriever")
        mock_cls.return_value.search.return_value = []

        retrieve("查询", top_k=7)

        assert mock_cls.return_value.search.call_args.kwargs["top_k"] == 7

    def test_doc_ids_passed_through(self, mocker, parent_stub):
        """doc_ids 过滤条件透传到检索器"""
        mock_cls = mocker.patch("src.retrieval.pipeline.HybridRetriever")
        mock_cls.return_value.search.return_value = []

        retrieve("查询", doc_ids=["doc-1", "doc-2"])

        assert mock_cls.return_value.search.call_args.kwargs["doc_ids"] == \
            ["doc-1", "doc-2"]

    def test_return_latency_returns_tuple(self, mocker, parent_stub):
        """return_latency=True：返回 (docs, latency) 二元组"""
        mocker.patch("src.retrieval.pipeline.HybridRetriever")

        result = retrieve("查询", return_latency=True)

        assert isinstance(result, tuple) and len(result) == 2
        docs, latency = result
        assert docs == []
        assert isinstance(latency, float) and latency >= 0

    def test_parent_expansion_applied_in_bm25_path(self, mocker, parent_stub):
        """parent 展开对所有 method 生效"""
        mock_cls = mocker.patch("src.retrieval.pipeline.SparseRetriever")
        mock_cls.return_value.search.return_value = [({"id": "s1"}, 1.0)]

        retrieve("查询", method="bm25")

        parent_stub.expand_to_parents.assert_called_once()
