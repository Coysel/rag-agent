"""
测试配置 — 共享 fixtures
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


@pytest.fixture
def sample_documents():
    """返回示例文档列表"""
    return [
        {
            "id": "doc1",
            "content": "PyTorch 是一个开源的深度学习框架。nn.Conv2d 的默认 stride 为 1。",
            "source": "pytorch.txt",
            "title": "PyTorch 入门",
        },
        {
            "id": "doc2",
            "content": "BM25 是一种基于词频-逆文档频率的检索算法。它擅长精确词匹配。",
            "source": "retrieval.txt",
            "title": "检索算法对比",
        },
    ]


@pytest.fixture
def sample_query():
    return "PyTorch Conv2d 的参数"


@pytest.fixture
def sample_chunks(sample_documents):
    """返回切分好的 child + parent chunks"""
    from src.indexing.loader import chunk_documents

    child, parent, mapping = chunk_documents(
        sample_documents,
        child_size=64,
        parent_size=256,
        overlap=10,
    )
    return child, parent, mapping
