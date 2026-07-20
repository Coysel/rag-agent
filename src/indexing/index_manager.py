"""
索引管理器 — 增量索引 & 文档生命周期管理

支持:
  - 增量添加: 新文档自动分块 → 向量化 → 写入 ChromaDB + BM25
  - 按 ID 删除: 从 ChromaDB 和 BM25 中移除文档所有 chunks
  - 全量重建: 保留 CLI 脚本兼容
"""
import uuid
from pathlib import Path
from typing import List, Dict

from config import CHILD_CHUNK_SIZE, PARENT_CHUNK_SIZE, CHUNK_OVERLAP
from src.indexing.loader import chunk_documents
from src.indexing.embeddings import get_embedding_model
from src.indexing.bm25_index import get_bm25_index
from src.indexing.vector_store import get_vector_store
from src.retrieval.parent_retriever import get_parent_retriever
from src.utils.logging import get_logger


class IndexManager:
    """增量索引管理器"""

    def __init__(self):
        self._emb = get_embedding_model()
        self._vs = get_vector_store()
        self._bm25 = get_bm25_index()
        self._parent = get_parent_retriever()
        self._logger = get_logger()

    def add_document(self, content: str, title: str, source: str = "") -> dict:
        """
        增量添加一篇文档（纯文本方式）

        Args:
            content: 文档正文
            title: 文档标题
            source: 文件来源标识

        Returns:
            {"doc_id": str, "child_chunks": [...], "parent_chunks": [...], "child_to_parent": {...}}
        """
        doc_id = str(uuid.uuid4())
        documents = [{"id": doc_id, "content": content, "source": source or title, "title": title}]
        result = self._index_documents(documents)
        result["doc_id"] = doc_id
        return result

    def add_file(self, file_path: Path) -> dict:
        """
        增量添加一个文件

        Args:
            file_path: 文件路径

        Returns:
            {"doc_id": str, "child_chunks": [...], "parent_chunks": [...], "child_to_parent": {...}}
        """
        file_path = Path(file_path)
        content = file_path.read_text(encoding="utf-8", errors="replace")
        title = file_path.stem.replace("_", " ").replace("-", " ")
        source = file_path.name
        return self.add_document(content, title, source)

    def _index_documents(self, documents: List[dict]) -> dict:
        """
        将文档列表索引化（内部分块 → 向量化 → 写入）

        Returns:
            {"doc_ids": [...], "child_chunks": [...], "parent_chunks": [...], "child_to_parent": {...}}
        """
        child_chunks, parent_chunks, child_to_parent = chunk_documents(
            documents, CHILD_CHUNK_SIZE, PARENT_CHUNK_SIZE, CHUNK_OVERLAP,
        )

        if not child_chunks:
            return {"doc_ids": [], "child_chunks": [], "parent_chunks": [], "child_to_parent": {}}

        # 向量化
        texts = [c["content"] for c in child_chunks]
        embeddings = self._emb.embed(texts)

        # 写入 ChromaDB
        child_ids = [c["id"] for c in child_chunks]
        child_metadatas = [
            {"doc_id": c["doc_id"], "parent_id": c["parent_id"],
             "title": c["title"], "source": c["source"]}
            for c in child_chunks
        ]
        self._vs.add_documents(
            ids=child_ids, embeddings=embeddings,
            documents=texts, metadatas=child_metadatas,
        )

        # 更新 BM25（追加式重建 — BM25 无增量 API）
        self._bm25.add_documents(child_chunks)

        # 更新 Parent-Document 映射
        self._parent._child_to_parent.update(child_to_parent)
        for p in parent_chunks:
            self._parent._parents[p["id"]] = p

        doc_ids = list({c["doc_id"] for c in child_chunks})
        self._logger.info(f"索引完成: {len(doc_ids)} 篇文档 → {len(child_chunks)} chunks")
        return {
            "doc_ids": doc_ids,
            "child_chunks": child_chunks,
            "parent_chunks": parent_chunks,
            "child_to_parent": child_to_parent,
        }

    def remove_document(self, doc_id: str) -> bool:
        """
        移除一篇文档及其所有 chunks

        Args:
            doc_id: 文档 ID

        Returns:
            是否删除成功
        """
        # 从 ChromaDB 删除（按 doc_id 元数据过滤）
        self._vs.delete_by_doc_id(doc_id)

        # 从 BM25 移除
        self._bm25.remove_by_doc_id(doc_id)

        # 从 parent 映射中清理
        parent_ids_to_remove = []
        for pid, parent in list(self._parent._parents.items()):
            if parent.get("doc_id") == doc_id:
                parent_ids_to_remove.append(pid)
        for pid in parent_ids_to_remove:
            del self._parent._parents[pid]

        child_ids_to_remove = [
            cid for cid, pid in self._parent._child_to_parent.items()
            if pid in parent_ids_to_remove
        ]
        for cid in child_ids_to_remove:
            del self._parent._child_to_parent[cid]

        self._logger.info(f"已移除文档: {doc_id} ({len(parent_ids_to_remove)} parents, {len(child_ids_to_remove)} children)")
        return True

    def rebuild_all(self, docs_dir: Path = None) -> dict:
        """
        全量重建索引（保留 CLI 脚本兼容）

        Returns:
            {"documents": int, "child_chunks": int, "parent_chunks": int}
        """
        from config import DOCUMENTS_DIR
        from src.indexing.loader import load_documents

        if docs_dir is None:
            docs_dir = DOCUMENTS_DIR

        self._vs.delete_collection()
        documents = load_documents(docs_dir)
        child_chunks, parent_chunks, child_to_parent = chunk_documents(
            documents, CHILD_CHUNK_SIZE, PARENT_CHUNK_SIZE, CHUNK_OVERLAP,
        )

        # 向量化 + 写入 ChromaDB
        texts = [c["content"] for c in child_chunks]
        batch_size = 50
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            all_embeddings.extend(self._emb.embed(batch))

        self._vs.add_documents(
            ids=[c["id"] for c in child_chunks],
            embeddings=all_embeddings,
            documents=texts,
            metadatas=[{
                "doc_id": c["doc_id"], "parent_id": c["parent_id"],
                "title": c["title"], "source": c["source"],
            } for c in child_chunks],
        )

        # BM25 + Parent 映射
        self._bm25.build(child_chunks)
        self._bm25.save()
        self._parent.build_from_chunks(child_chunks, parent_chunks, child_to_parent)

        return {
            "documents": len(documents),
            "child_chunks": len(child_chunks),
            "parent_chunks": len(parent_chunks),
        }


# 全局单例
_index_manager: IndexManager | None = None


def get_index_manager() -> IndexManager:
    global _index_manager
    if _index_manager is None:
        _index_manager = IndexManager()
    return _index_manager
