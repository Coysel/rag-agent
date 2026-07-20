"""
ChromaDB 向量存储 — Dense 语义检索

管理 ChromaDB collection 的增删查操作。
存储 child chunks 的向量，检索时返回对应的 parent chunks。
"""
from pathlib import Path
from typing import List, Tuple

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import CHROMA_DIR, RETRIEVAL_TOP_K


class VectorStore:
    """ChromaDB 向量存储管理器"""

    COLLECTION_NAME = "rag_documents"
    #初始化
    def __init__(self, persist_dir: Path = None):
        if persist_dir is None:
            persist_dir = CHROMA_DIR
        persist_dir = Path(persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    def get_or_create_collection(self):
        """获取或创建 collection"""
        return self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},#向量方向为主
        )

    def delete_collection(self) -> None:
        """删除 collection (用于重建索引)"""
        try:
            self._client.delete_collection(self.COLLECTION_NAME)
        except Exception:
            pass

    def delete_by_doc_id(self, doc_id: str) -> int:
        """
        按 doc_id 删除文档的所有 chunks

        通过 ChromaDB metadata 过滤找到所有 chunk 后逐一删除。
        注意: ChromaDB 没有 "delete by metadata filter" 的原生 API，
        需要先 get 再 delete。
        """
        try:
            collection = self.get_or_create_collection()
            # 获取所有 chunks 的 metadata
            all_data = collection.get(include=["metadatas"])
            ids_to_delete = []
            if all_data["ids"] and all_data["metadatas"]:
                for i, meta in enumerate(all_data["metadatas"]):
                    if meta and meta.get("doc_id") == doc_id:
                        ids_to_delete.append(all_data["ids"][i])
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
            return len(ids_to_delete)
        except Exception:
            return 0

    def add_documents(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[dict],
    ) -> None:
        """
        批量添加文档到向量库

        Args:
            ids: 文档唯一 ID (child chunk id)
            embeddings: 对应的向量
            documents: 文档内容 (child chunk content)
            metadatas: 元数据 (至少包含 parent_id, title, source)
        """
        collection = self.get_or_create_collection()
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def search(
        self,
        query_embedding: List[float],
        top_k: int = RETRIEVAL_TOP_K,
        where_filter: dict | None = None,
    ) -> List[Tuple[dict, float]]:
        """
        语义检索

        Args:
            query_embedding: 查询向量
            top_k: 返回数量
            where_filter: ChromaDB where 过滤条件（如 {"doc_id": {"$in": ["id1","id2"]}}）

        Returns:
            [(metadata_dict, distance_score), ...]
        """
        try:
            collection = self.get_or_create_collection()
        except Exception:
            return []

        query_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where_filter:
            query_kwargs["where"] = where_filter

        results = collection.query(**query_kwargs)

        output = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                metadata = results["metadatas"][0][i] if results["metadatas"][0] else {}
                doc_content = results["documents"][0][i] if results["documents"][0] else ""
                distance = results["distances"][0][i] if results["distances"][0] else 1.0

                # ChromaDB 用 cosine distance: 1 - cosine_similarity
                # 转换为相似度分数
                similarity = 1.0 - float(distance)

                output.append(({
                    "id": results["ids"][0][i],
                    "content": doc_content,
                    "parent_id": metadata.get("parent_id", ""),
                    "title": metadata.get("title", ""),
                    "source": metadata.get("source", ""),
                    "doc_id": metadata.get("doc_id", ""),
                    "dense_score": similarity,
                }, similarity))

        return output

    @property
    def count(self) -> int:
        """返回存储的文档数"""
        try:
            collection = self.get_or_create_collection()
            return collection.count()
        except Exception:
            return 0


# 全局单例
_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """获取全局向量存储实例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
