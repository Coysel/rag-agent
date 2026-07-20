"""
文档加载 & 分块测试
"""
import pytest


class TestSplitByTokens:
    def test_splits_long_text(self):
        from src.indexing.loader import _split_by_tokens

        text = "测试" * 200  # 400 字符
        chunks = _split_by_tokens(text, chunk_size=50, overlap=10)
        assert len(chunks) > 1
        assert all(len(c) > 0 for c in chunks)

    def test_short_text_single_chunk(self):
        from src.indexing.loader import _split_by_tokens

        text = "短文本"
        chunks = _split_by_tokens(text, chunk_size=256, overlap=50)
        assert len(chunks) == 1
        assert chunks[0] == "短文本"

    def test_empty_text(self):
        from src.indexing.loader import _split_by_tokens

        chunks = _split_by_tokens("", chunk_size=256, overlap=50)
        assert chunks == []


class TestChunkDocuments:
    def test_chunks_have_required_fields(self, sample_documents):
        from src.indexing.loader import chunk_documents

        child, parent, mapping = chunk_documents(
            sample_documents, child_size=64, parent_size=256, overlap=10,
        )

        for c in child:
            assert "id" in c
            assert "content" in c
            assert "parent_id" in c
            assert "doc_id" in c

        for p in parent:
            assert "id" in p
            assert "content" in p
            assert "doc_id" in p

        # mapping 的 key 是 child id，value 是 parent id
        for child_id, parent_id in mapping.items():
            assert child_id in {c["id"] for c in child}
            assert parent_id in {p["id"] for p in parent}

    def test_parents_larger_than_children(self, sample_documents):
        from src.indexing.loader import chunk_documents

        child, parent, mapping = chunk_documents(
            sample_documents, child_size=64, parent_size=256, overlap=10,
        )

        # parent 数量应 ≤ child 数量
        assert len(parent) <= len(child)

    def test_child_to_parent_ratio(self, sample_documents):
        from src.indexing.loader import chunk_documents

        child, parent, mapping = chunk_documents(
            sample_documents, child_size=64, parent_size=256, overlap=10,
        )

        # 每个 parent 至少有一个 child
        parent_ids_in_children = {c["parent_id"] for c in child}
        parent_ids = {p["id"] for p in parent}
        assert parent_ids_in_children == parent_ids
