"""
一键构建索引脚本

流程:
  1. 加载 data/documents/ 下的所有文档
  2. 切分为 child chunks (256 token) 和 parent chunks (1024 token)
  3. 生成 Embedding (text-embedding-3-small / voyage-2)
  4. 存入 ChromaDB (child chunks)
  5. 构建 BM25 索引 (child chunks)
  6. 构建 Parent-Document 映射

用法:
  python scripts/index_documents.py
  python scripts/index_documents.py --docs-dir ./my_docs/
"""
import argparse
import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DOCUMENTS_DIR, CHILD_CHUNK_SIZE, PARENT_CHUNK_SIZE, CHUNK_OVERLAP
from src.indexing.loader import load_documents, chunk_documents
from src.indexing.embeddings import get_embedding_model
from src.indexing.bm25_index import get_bm25_index
from src.indexing.vector_store import get_vector_store
from src.retrieval.parent_retriever import get_parent_retriever


def main(docs_dir: str = None):
    if docs_dir is None:
        docs_dir = str(DOCUMENTS_DIR)

    print("  Agentic RAG — 文档索引构建")
    # 1. 加载文档
    print(f"\n[1/6] 加载文档: {docs_dir}")
    documents = load_documents(docs_dir if docs_dir else None)#递归扫描

    if not documents:
        print("[ERROR] 未找到任何文档！")
        print(f"请将 .txt/.md/.py 文件放入 {docs_dir} 目录")
        sys.exit(1)

    print(f"  已加载 {len(documents)} 篇文档")
    for doc in documents[:5]:#预览确认
        print(f"    - {doc['title']} ({len(doc['content'])} 字符)")
    if len(documents) > 5:
        print(f"    ... 及其他 {len(documents) - 5} 篇")

    # 2. 切分文档，生成列表
    print(f"\n[2/6] 切分文档 (child={CHILD_CHUNK_SIZE} tokens, parent={PARENT_CHUNK_SIZE} tokens)")
    child_chunks, parent_chunks, child_to_parent = chunk_documents(
        documents,
        child_size=CHILD_CHUNK_SIZE,
        parent_size=PARENT_CHUNK_SIZE,
        overlap=CHUNK_OVERLAP,
    )
    print(f"  Child chunks: {len(child_chunks)}")
    print(f"  Parent chunks: {len(parent_chunks)}")

    # 3. 调用Embedding
    print(f"\n[3/6] 生成 Embedding (这将调用 API)...")
    embedding_model = get_embedding_model()
    print(f"  Provider: {embedding_model.provider}")
    print(f"  Model: {embedding_model.model}")

    child_texts = [c["content"] for c in child_chunks]

    # 批量生成向量 (分批，避免 API 限制)
    batch_size = 50
    all_embeddings = []
    for i in range(0, len(child_texts), batch_size):
        batch = child_texts[i:i + batch_size]
        print(f"  处理 {i+1}-{min(i+batch_size, len(child_texts))}/{len(child_texts)}...")
        embeddings = embedding_model.embed(batch)
        all_embeddings.extend(embeddings)

    print(f"  共生成 {len(all_embeddings)} 条向量, 维度: {len(all_embeddings[0]) if all_embeddings else 0}")

    # 4. 存入 ChromaDB (先生成向量再清空旧数据，避免中途失败丢失索引)
    print(f"\n[4/6] 存入 ChromaDB...")
    vector_store = get_vector_store()
    vector_store.delete_collection()  # 向量已生成完毕，安全清空旧数据

    child_ids = [c["id"] for c in child_chunks]#提取id
    child_metadatas = [
        {
            "doc_id": c["doc_id"],
            "parent_id": c["parent_id"],
            "title": c["title"],
            "source": c["source"],
        }
        for c in child_chunks
    ]

    vector_store.add_documents(
        ids=child_ids,
        embeddings=all_embeddings,
        documents=child_texts,
        metadatas=child_metadatas,
    )
    print(f"  已存入 {vector_store.count} 条记录")

    # 5. 构建 BM25 索引
    print(f"\n[5/6] 构建 BM25 索引...")
    bm25 = get_bm25_index()
    bm25.build(child_chunks)
    bm25.save()
    print(f"  已构建 ({bm25.document_count} 篇文档)")
    print(f"  索引保存至: data/bm25_index.pkl")

    # 6. 构建 Parent-Document 映射
    print(f"\n[6/6] 构建 Parent-Document 映射...")
    parent_retriever = get_parent_retriever()
    parent_retriever.build_from_chunks(child_chunks, parent_chunks, child_to_parent)
    print(f"  已建立 {len(child_to_parent)} 条 child→parent 映射")

    print("  索引构建完成!")
    print(f"  文档数: {len(documents)}")
    print(f"  Child chunks: {len(child_chunks)}")
    print(f"  Parent chunks: {len(parent_chunks)}")
    print(f"  现在可以启动服务: python main.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="构建 RAG 文档索引")
    parser.add_argument("--docs-dir", type=str, default=None, help="文档目录路径")
    args = parser.parse_args()
    main(args.docs_dir)
