"""
层次摘要生成器 — chunk → parent → document

复用 src/agent/llm_client.py 的 LLMClient。
"""
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict

from src.agent.llm_client import get_llm_client
from src.utils.logging import get_logger

PROGRESS_FILE = Path("data/category_progress.json")


class Summarizer:
    """层次摘要生成器"""

    # Prompt 模板
    CHILD_SUMMARY_PROMPT = (
        "你是一个文档摘要助手。请用1-2句简洁的中文概括以下文本片段的核心内容。"
        "只输出摘要，不要加前缀或解释。\n\n文本:\n{chunk_text}"
    )

    PARENT_AGGREGATE_PROMPT = (
        "你是一个文档摘要助手。以下是文档「{doc_title}」中一个章节的不同片段的摘要，"
        "请将这些片段摘要整合为一段连贯的章节摘要（3-5句）。只输出摘要，不要加前缀或解释。\n\n"
        "片段摘要:\n{child_summaries}"
    )

    DOC_AGGREGATE_PROMPT = (
        "你是一个文档摘要助手。以下是文档「{doc_title}」各章节的摘要，"
        "请整合为一段完整的文档摘要（5-8句），涵盖文档的主要主题和内容。"
        "只输出摘要，不要加前缀或解释。\n\n章节摘要:\n{parent_summaries}"
    )

    def __init__(self):
        self._llm = get_llm_client()
        self._logger = get_logger()
        self._started_at: str = ""

    # ── 进度文件（跨进程可读）──────────────────────────────

    def init_progress(self, stage: str, total: int):
        """初始化进度文件（每次生成开始时调用）"""
        self._started_at = datetime.now(timezone.utc).isoformat()
        PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._write_progress(stage, 0, total, "开始...")

    def _write_progress(self, stage: str, current: int, total: int, message: str = ""):
        """写入进度到 JSON 文件（原子写入）"""
        try:
            data = {
                "stage": stage,
                "current": current,
                "total": total,
                "percent": round(current / total * 100, 1) if total > 0 else 0,
                "message": message or f"{stage}: {current}/{total}",
                "started_at": self._started_at,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            tmp = PROGRESS_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(PROGRESS_FILE)
        except Exception:
            pass  # 进度文件写入失败不影响主流程

    def summarize_child_chunks(self, chunks: List[dict]) -> Dict[str, str]:
        """
        对每个 child chunk 生成摘要。

        Args:
            chunks: child chunk 列表，每个含 "id" 和 "content"

        Returns:
            {chunk_id: summary_text} 映射
        """
        summaries = {}
        total = len(chunks)
        for i, chunk in enumerate(chunks):
            content = chunk.get("content", "")
            chunk_id = chunk.get("id", "")
            if not content or len(content.strip()) < 20:
                summaries[chunk_id] = content.strip()[:100] if content.strip() else "（空内容）"
                continue

            prompt = self.CHILD_SUMMARY_PROMPT.format(chunk_text=content[:800])
            try:
                result = self._llm.create_message(
                    system="",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150,
                    temperature=0.2,
                )
                summaries[chunk_id] = result.get("text", "").strip()
            except Exception as e:
                self._logger.warning(f"Chunk {chunk_id} 摘要失败: {e}")
                summaries[chunk_id] = content[:100].replace("\n", " ") + "..."

            if (i + 1) % 5 == 0 or i + 1 == total:
                self._logger.info(f"Child 摘要进度: {i+1}/{total}")
                self._write_progress("child_summaries", i + 1, total)

        return summaries

    def aggregate_parents(
        self,
        parent_chunks: List[dict],
        child_summaries: Dict[str, str],
        child_to_parent: Dict[str, str],
    ) -> Dict[str, str]:
        """
        将 child 摘要聚合为 parent 级摘要。

        Args:
            parent_chunks: parent chunk 列表
            child_summaries: {child_id: summary} 映射
            child_to_parent: {child_id: parent_id} 映射

        Returns:
            {parent_id: summary_text} 映射
        """
        # 按 parent 分组 child 摘要
        parent_groups: Dict[str, List[str]] = {}
        for child_id, summary in child_summaries.items():
            parent_id = child_to_parent.get(child_id, "")
            if parent_id:
                parent_groups.setdefault(parent_id, []).append(summary)

        summaries = {}
        total = len(parent_chunks)
        for i, p in enumerate(parent_chunks):
            pid = p.get("id", "")
            child_sums = parent_groups.get(pid, [])
            if not child_sums:
                summaries[pid] = p.get("content", "")[:200] + "..."
                continue

            # 如果只有 1 个 child，直接使用
            if len(child_sums) == 1:
                summaries[pid] = child_sums[0]
                continue

            title = p.get("title", "未知")
            joined = "\n---\n".join(f"- {s}" for s in child_sums)
            prompt = self.PARENT_AGGREGATE_PROMPT.format(
                doc_title=title, child_summaries=joined,
            )
            try:
                result = self._llm.create_message(
                    system="",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                    temperature=0.2,
                )
                summaries[pid] = result.get("text", "").strip()
            except Exception as e:
                self._logger.warning(f"Parent {pid} 聚合失败: {e}")
                summaries[pid] = " ".join(child_sums)[:300]

            if (i + 1) % 3 == 0 or i + 1 == total:
                self._logger.info(f"Parent 聚合进度: {i+1}/{total}")
                self._write_progress("parent_aggregation", i + 1, total)

        return summaries

    def aggregate_documents(
        self,
        docs: Dict[str, dict],
        parent_summaries: Dict[str, str],
        parent_to_doc: Dict[str, str],
    ) -> Dict[str, str]:
        """
        将 parent 摘要聚合为文档级摘要。

        Args:
            docs: {doc_id: {title: ..., ...}}
            parent_summaries: {parent_id: summary}
            parent_to_doc: {parent_id: doc_id}

        Returns:
            {doc_id: doc_summary_text}
        """
        # 按文档分组 parent 摘要
        doc_groups: Dict[str, List[str]] = {}
        for pid, summary in parent_summaries.items():
            doc_id = parent_to_doc.get(pid, "")
            if doc_id:
                doc_groups.setdefault(doc_id, []).append(summary)

        summaries = {}
        total = len(docs)
        for i, (doc_id, doc_info) in enumerate(docs.items()):
            parent_sums = doc_groups.get(doc_id, [])
            if not parent_sums:
                summaries[doc_id] = f"文档: {doc_info.get('title', '未知')}"
                continue

            if len(parent_sums) == 1:
                summaries[doc_id] = parent_sums[0]
                continue

            title = doc_info.get("title", "未知")
            joined = "\n---\n".join(f"- {s}" for s in parent_sums)
            prompt = self.DOC_AGGREGATE_PROMPT.format(
                doc_title=title, parent_summaries=joined,
            )
            try:
                result = self._llm.create_message(
                    system="",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500,
                    temperature=0.2,
                )
                summaries[doc_id] = result.get("text", "").strip()
            except Exception as e:
                self._logger.warning(f"Document {doc_id} 聚合失败: {e}")
                summaries[doc_id] = " ".join(parent_sums)[:500]

            if (i + 1) % 3 == 0 or i + 1 == total:
                self._logger.info(f"Document 聚合进度: {i+1}/{total}")
                self._write_progress("doc_aggregation", i + 1, total)

        return summaries
