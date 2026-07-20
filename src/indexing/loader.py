"""
文档加载器 — 加载技术文档并切分为父子块

Parent-Document Retriever 策略:
  - 小块 (child, ~256 tokens): 用于向量检索，精度高
  - 大块 (parent, ~1024 tokens): 用于上下文生成，信息完整
  - 每个 child 记录其 parent 的索引，检索时从小块定位到大块
"""
import uuid
from pathlib import Path
from typing import List, Tuple

from config import DOCUMENTS_DIR, CHILD_CHUNK_SIZE, PARENT_CHUNK_SIZE, CHUNK_OVERLAP


def _split_by_tokens(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    按 token 数切分文本 (粗略近似: 用字符数按比例估算)

    更精确的做法是用 tiktoken 逐 token 切分，但粗略近似在大多数场景足够。
    中文大约 1 token ≈ 1.5 字符，英文大约 1 token ≈ 4 字符。
    这里采用保守估计: 1 token ≈ 3 字符。
    """
    char_ratio = 3.0
    chunk_chars = int(chunk_size * char_ratio)
    overlap_chars = int(overlap * char_ratio)

    chunks = []
    start = 0
    text_len = len(text)
    #滑动窗口切割
    while start < text_len:
        end = min(start + chunk_chars, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_len:
            break
        start = end - overlap_chars

    return chunks


def load_documents(directory: Path = None) -> List[dict]:
    """
    加载目录下的所有文档 (支持 .txt, .md, .py)

    返回: [{"id": str, "content": str, "source": str, "title": str}, ...]
    """
    if directory is None:
        directory = DOCUMENTS_DIR

    directory = Path(directory)
    documents = []

    for file_path in directory.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in {".txt", ".md", ".py", ".rst", ".html", ".css", ".js", ".yaml", ".yml", ".json", ".toml", ".cfg", ".ini"}:
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        if not content.strip():
            continue

        # 用文件名作为标题 (去除后缀)
        title = file_path.stem.replace("_", " ").replace("-", " ")

        documents.append({
            "id": str(uuid.uuid4()),
            "content": content,
            "source": str(file_path.relative_to(directory)),
            "title": title,
        })

    return documents


def chunk_documents(
    documents: List[dict],
    child_size: int = CHILD_CHUNK_SIZE,
    parent_size: int = PARENT_CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> Tuple[List[dict], List[dict], dict]:
    """
    将文档切分为 child chunks 和 parent chunks

    Args:
        documents: 原始文档列表
        child_size: 小块 token 数
        parent_size: 大块 token 数
        overlap: 重叠 token 数

    Returns:
        (child_chunks, parent_chunks, child_to_parent_map)

        child_chunks: [{"id": str, "content": str, "doc_id": str, "parent_id": str, ...}, ...]
        parent_chunks: [{"id": str, "content": str, "doc_id": str, "title": str, ...}, ...]
        child_to_parent_map: {child_id: parent_id}
    """
    child_chunks = []
    parent_chunks = []
    child_to_parent = {}

    for doc in documents:
        doc_id = doc["id"]
        title = doc["title"]
        source = doc["source"]
        content = doc["content"]

        # 1. 先切分为 parent chunks (大块)
        doc_parents = _split_by_tokens(content, parent_size, overlap)

        for i, parent_text in enumerate(doc_parents):
            parent_id = f"{doc_id}_p{i}"
            parent_chunks.append({
                "id": parent_id,
                "content": parent_text,
                "doc_id": doc_id,
                "title": title,
                "source": source,
                "chunk_index": i,
            })

            # 2. 再将每个 parent 切分为 child chunks (小块)
            doc_children = _split_by_tokens(parent_text, child_size, overlap // 2)

            for j, child_text in enumerate(doc_children):
                child_id = f"{parent_id}_c{j}"
                child_chunks.append({
                    "id": child_id,
                    "content": child_text,
                    "doc_id": doc_id,
                    "parent_id": parent_id,
                    "source": source,
                    "title": title,
                    "chunk_index": j,
                })
                child_to_parent[child_id] = parent_id

    return child_chunks, parent_chunks, child_to_parent
