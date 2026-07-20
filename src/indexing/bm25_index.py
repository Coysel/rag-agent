"""
BM25 稀疏索引 — 关键词检索，擅长精确词匹配

BM25 擅长: 精确词匹配（搜"Conv2d"必须出现"Conv2d"）
Dense 擅长: 语义匹配（搜"卷积"能找到"convolution"）
"""
import pickle
import re
from pathlib import Path
from typing import List, Tuple

from rank_bm25 import BM25Okapi as _BM25Okapi

from config import BM25_INDEX_PATH, RETRIEVAL_TOP_K


def _tokenize(text: str) -> List[str]:
    """简单分词: 英文按空格 + 中文按字符"""
    # 保留中英文字符和数字，其余作分隔
    text = text.lower()
    # 拆分英文单词和中文单字
    tokens = re.findall(r"[a-zA-Z0-9]+|[一-鿿]", text)
    return tokens


class BM25Index:
    """BM25 索引管理器"""

    def __init__(self):
        self._index: _BM25Okapi | None = None
        self._documents: List[dict] = []
        self._corpus: List[List[str]] = []

    def build(self, documents: List[dict]) -> None:
        """
        构建 BM25 索引

        Args:
            documents: 文档列表，每项至少包含 "content" 和 "id"
        """
        self._documents = list(documents)
        self._corpus = [_tokenize(d["content"]) for d in documents]
        self._index = _BM25Okapi(self._corpus)

    def search(self, query: str, top_k: int = RETRIEVAL_TOP_K) -> List[Tuple[dict, float]]:
        """
        检索 top_k 篇文档

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            [(document_dict, score), ...] 按分数降序排列
        """
        if self._index is None:
            return []

        tokenized = _tokenize(query)
        scores = self._index.get_scores(tokenized)

        # 按分数排序
        ranked = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        results = []
        for idx, score in ranked:
            doc = dict(self._documents[idx])
            doc["bm25_score"] = float(score)
            results.append((doc, float(score)))

        return results

    def save(self, path: Path = None) -> None:
        """持久化 BM25 索引到磁盘"""
        if path is None:
            path = BM25_INDEX_PATH
        data = {
            "documents": self._documents,
            "corpus": self._corpus,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)

    def load(self, path: Path = None) -> None:
        """从磁盘加载 BM25 索引"""
        if path is None:
            path = BM25_INDEX_PATH
        if not path.exists():
            raise FileNotFoundError(f"BM25 index not found at {path}")

        with open(path, "rb") as f:
            data = pickle.load(f)

        self._documents = data["documents"]
        self._corpus = data["corpus"]
        self._index = _BM25Okapi(self._corpus)

    def add_documents(self, documents: List[dict]) -> None:
        """增量追加文档到已有索引"""
        if self._index is None:
            self.build(documents)
            return
        new_docs = [d for d in documents if d["id"] not in {x["id"] for x in self._documents}]
        if not new_docs:
            return
        self._documents.extend(new_docs)
        self._corpus.extend(_tokenize(d["content"]) for d in new_docs)
        self._index = _BM25Okapi(self._corpus)

    def remove_by_doc_id(self, doc_id: str) -> int:
        """按 doc_id 移除文档的所有 chunks"""
        keep_idx = [i for i, d in enumerate(self._documents) if d.get("doc_id") != doc_id]
        removed = len(self._documents) - len(keep_idx)
        if removed == 0:
            return 0
        self._documents = [self._documents[i] for i in keep_idx]
        self._corpus = [self._corpus[i] for i in keep_idx]
        self._index = _BM25Okapi(self._corpus) if self._corpus else None
        return removed

    @property
    def is_built(self) -> bool:
        return self._index is not None

    @property
    def document_count(self) -> int:
        return len(self._documents)


# 全局单例
_bm25_index: BM25Index | None = None


def get_bm25_index() -> BM25Index:
    """获取全局 BM25 索引实例"""
    global _bm25_index
    if _bm25_index is None:
        _bm25_index = BM25Index()
    return _bm25_index
