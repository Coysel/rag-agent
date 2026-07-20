"""
检索模块单元测试
"""
import pytest


class TestParentRetriever:
    """Parent-Document Retriever 测试"""

    def test_build_from_chunks(self, sample_chunks):
        from src.retrieval.parent_retriever import ParentDocumentRetriever

        child, parent, mapping = sample_chunks
        pr = ParentDocumentRetriever()
        pr.build_from_chunks(child, parent, mapping)

        assert len(pr._child_to_parent) > 0
        assert len(pr._parents) > 0

    def test_expand_deduplicates_same_parent(self, sample_chunks):
        from src.retrieval.parent_retriever import ParentDocumentRetriever

        child, parent, mapping = sample_chunks
        pr = ParentDocumentRetriever()
        pr.build_from_chunks(child, parent, mapping)

        # 找两个属于同一 parent 的 child
        parent_groups = {}
        for c in child:
            pid = c.get("parent_id", "")
            parent_groups.setdefault(pid, []).append(c)

        # 取第一组（至少 2 个 child 的 parent）
        multi_child = [g for g in parent_groups.values() if len(g) >= 2]
        if not multi_child:
            pytest.skip("没有 multi-child parent 组")

        children = [dict(multi_child[0][0]), dict(multi_child[0][1])]
        children[0]["rrf_score"] = 0.5
        children[1]["rrf_score"] = 0.3

        results = pr.expand_to_parents(children)
        # 两个 child 属于同一 parent，应去重为 1 条
        assert len(results) == 1
        # 分数来自第一个 child
        assert results[0]["rrf_score"] == 0.5

    def test_empty_results(self):
        from src.retrieval.parent_retriever import ParentDocumentRetriever

        pr = ParentDocumentRetriever()
        assert pr.expand_to_parents([]) == []


class TestHybridRetriever:
    """混合检索器测试（注意：需要已构建的索引）"""

    def test_search_returns_results(self):
        """跳过条件：索引未构建时返回空列表（不抛异常）"""
        from src.retrieval.hybrid_retriever import HybridRetriever

        hr = HybridRetriever()
        results = hr.search("测试查询")
        # 索引不存在时应返回空列表而非抛异常
        assert isinstance(results, list)


class TestRRF:
    """RRF 融合算法测试"""

    def test_fusion_basic(self):
        from src.retrieval.hybrid_retriever import reciprocal_rank_fusion

        dense = [({"id": "a", "parent_id": "p1"}, 0.9)]  # rank 1
        sparse = [({"id": "a", "parent_id": "p1"}, 8.0)]  # rank 1

        results = reciprocal_rank_fusion(dense, sparse, k=60, top_k=5)
        assert len(results) == 1
        assert results[0]["rrf_score"] > 0

    def test_fusion_deduplication(self):
        from src.retrieval.hybrid_retriever import reciprocal_rank_fusion

        dense = [
            ({"id": "a", "parent_id": "p1"}, 0.9),
            ({"id": "b", "parent_id": "p2"}, 0.8),
        ]
        sparse = [
            ({"id": "b", "parent_id": "p2"}, 7.0),
            ({"id": "c", "parent_id": "p3"}, 5.0),
        ]

        results = reciprocal_rank_fusion(dense, sparse, k=60, top_k=5)
        # 应去重：a, b, c 三个独特文档
        assert len(results) == 3

    def test_weighted_fusion(self):
        from src.retrieval.hybrid_retriever import reciprocal_rank_fusion

        dense = [({"id": "a", "parent_id": "p1"}, 0.9)]
        sparse = [({"id": "b", "parent_id": "p2"}, 9.0)]

        # 等权重下 a 和 b 都出现
        equal = reciprocal_rank_fusion(dense, sparse, top_k=5, dense_weight=1.0, sparse_weight=1.0)
        assert len(equal) == 2

        # sparse 权重为 0 时，b 的得分为 0，但仍在结果中（只是得分最低）
        sparse_zero = reciprocal_rank_fusion(dense, sparse, top_k=5, dense_weight=1.0, sparse_weight=0.0)
        # b 得分应为 0，a 得分 > 0
        b_doc = [d for d in sparse_zero if d["id"] == "b"][0]
        assert b_doc["rrf_score"] == 0.0
        a_doc = [d for d in sparse_zero if d["id"] == "a"][0]
        assert a_doc["rrf_score"] > 0.0
