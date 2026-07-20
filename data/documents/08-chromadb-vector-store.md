# ChromaDB 向量数据库

## 概述

ChromaDB 是一个开源的向量数据库，专为 AI 应用设计，尤其适合 RAG 系统。它支持存储文档的 Embedding 向量并进行高效的相似度搜索。

## 安装与初始化

```python
import chromadb

# 持久化模式
client = chromadb.PersistentClient(path="./chroma_db")

# 内存模式（测试用）
client = chromadb.Client()
```

## 距离度量

ChromaDB 支持三种距离度量方式：

| 度量 | hnsw:space 值 | 说明 | 适用场景 |
|------|--------------|------|---------|
| 欧几里得距离 | l2 | 平方距离，默认值 | 通用 |
| 内积 | ip | 点积相似度 | 归一化向量 |
| 余弦距离 | cosine | 1 - 余弦相似度 | 语义搜索（推荐） |

设置方法：
```python
collection = client.create_collection(
    name="docs",
    metadata={"hnsw:space": "cosine"}  # 推荐用于语义搜索
)
```

**默认使用 l2 距离**，但在 RAG 系统中通常推荐使用 cosine，因为 Embedding 模型的语义相似度更适合用余弦距离衡量。

## 基本操作

```python
# 添加文档
collection.add(
    ids=["doc1", "doc2"],
    embeddings=[[0.1, 0.2, ...], [0.3, 0.4, ...]],
    documents=["文本内容1", "文本内容2"],
    metadatas=[{"source": "file1.md"}, {"source": "file2.md"}],
)

# 查询
results = collection.query(
    query_embeddings=[[0.1, 0.2, ...]],
    n_results=5,
    include=["documents", "metadatas", "distances"],
)
```

## ChromaDB 在 RAG 中的角色

1. 存储文档的 Embedding 向量（索引阶段）
2. 根据用户查询的 Embedding 检索最相似的文档（检索阶段）
3. 返回文档内容和元数据给 LLM 用于生成（生成阶段）
