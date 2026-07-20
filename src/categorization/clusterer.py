"""
文档聚类器 — 基于文档摘要将相似文档分组为类别

使用 LLM 进行语义聚类：将所有文档摘要提交给 LLM，要求输出分组。
"""
import json
from typing import List, Dict

from src.agent.llm_client import get_llm_client
from src.utils.logging import get_logger


CLUSTER_PROMPT = """你是一个文档分类助手。以下是 {doc_count} 篇文档的摘要，请根据内容将它们分为 {max_categories} 个以内的类别。

每个类别应该包含内容高度相关的文档。同一类别的文档应该讨论相似的主题或领域。

请以 JSON 格式输出，格式为:
[
  {{"name": "类别名称（简洁中文，2-6字）", "description": "类别描述（一句话）", "doc_indices": [0, 3, 5]}},
  ...
]

doc_indices 是文档在输入列表中的索引（从 0 开始）。
每篇文档必须且只能属于一个类别。
如果一个文档的内容与所有其他文档都不相关，把它单独归为一个类别。

文档摘要:
{doc_summaries}

只输出 JSON 数组，不要加任何其他内容。"""

ASSIGN_PROMPT = """你是一个文档分类助手。现有以下类别：
{category_list}

新文档「{doc_title}」的摘要：
{doc_summary}

请判断该文档应该归入哪个已有类别。
如果文档内容与某个类别高度相关，输出该类别名；如果文档内容与所有已有类别都不匹配，返回一个合适的新类别名（2-6字，简洁中文）。
此外输出一句简短的理由说明为什么这样归类。

输出 JSON: {{"category": "类别名", "is_new": true或false, "reason": "归类理由（一句话）"}}
只输出 JSON，不要加任何其他内容。"""


class Clusterer:
    """文档聚类器"""

    def __init__(self):
        self._llm = get_llm_client()
        self._logger = get_logger()

    def cluster(
        self,
        docs: Dict[str, dict],
        doc_summaries: Dict[str, str],
        max_categories: int = 8,
    ) -> List[dict]:
        """
        将文档聚类为类别。

        Args:
            docs: {doc_id: {title: ..., source: ...}}
            doc_summaries: {doc_id: summary_text}
            max_categories: 最大类别数

        Returns:
            [{"name": "...", "description": "...", "doc_ids": ["id1", "id2"]}, ...]
        """
        if not doc_summaries:
            return []

        # 构建有序的 doc_id 列表和对应的摘要文本
        doc_ids = list(doc_summaries.keys())
        summary_lines = []
        for i, doc_id in enumerate(doc_ids):
            doc_info = docs.get(doc_id, {})
            title = doc_info.get("title", "未知")
            summary = doc_summaries.get(doc_id, "")
            summary_lines.append(f"[{i}] {title}\n{summary}")

        prompt = CLUSTER_PROMPT.format(
            doc_count=len(doc_ids),
            max_categories=min(max_categories, len(doc_ids)),
            doc_summaries="\n\n---\n\n".join(summary_lines),
        )

        try:
            result = self._llm.create_message(
                system="",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.1,
            )
            text = result.get("text", "").strip()

            # 清理 markdown 包裹
            if text.startswith("```"):
                # 去掉 ```json ... ``` 或 ``` ... ```
                text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            clusters = json.loads(text)
            # 转换 doc_indices → doc_ids
            return self._resolve_doc_ids(clusters, doc_ids)

        except (json.JSONDecodeError, Exception) as e:
            self._logger.warning(f"聚类解析失败: {e}，使用单类别回退")
            # 回退：所有文档归入一个类别
            return [{
                "name": "全部文档",
                "description": "所有已索引的文档",
                "doc_ids": doc_ids,
            }]

    def assign_to_category(
        self,
        doc_title: str,
        doc_summary: str,
        existing_categories: List[dict],
    ) -> dict:
        """
        将单篇文档分配到已有类别或建议新类别。

        Args:
            doc_title: 文档标题
            doc_summary: 文档完整摘要
            existing_categories: [{"id": ..., "name": ..., "description": ...}, ...]

        Returns:
            {"category_name": "...", "is_new": bool, "reason": "..."}
        """
        if not existing_categories:
            # 无已有类别 → 强制创建新类别
            try:
                result = self._llm.create_message(
                    system="",
                    messages=[{"role": "user", "content": (
                        f"以下是一篇文档的摘要，请为它取一个合适的分类名（2-6字，简洁中文）。\n\n"
                        f"文档「{doc_title}」的摘要：\n{doc_summary}\n\n"
                        f"只输出 JSON: {{\"category\": \"类别名\", \"is_new\": true, \"reason\": \"理由\"}}"
                    )}],
                    max_tokens=150,
                    temperature=0.1,
                )
                text = result.get("text", "").strip()
                data = self._parse_assign_json(text)
                return {
                    "category_name": data.get("category", "综合"),
                    "is_new": True,
                    "reason": data.get("reason", "首个类别"),
                }
            except Exception:
                return {"category_name": "综合", "is_new": True, "reason": "自动创建"}

        # 构建类别列表文本
        cat_lines = "\n".join(
            f"- {c['name']}: {c.get('description', '')}"
            for c in existing_categories
        )
        prompt = ASSIGN_PROMPT.format(
            category_list=cat_lines,
            doc_title=doc_title,
            doc_summary=doc_summary,
        )

        try:
            result = self._llm.create_message(
                system="",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1,
            )
            text = result.get("text", "").strip()
            data = self._parse_assign_json(text)
            return {
                "category_name": data.get("category", "未分类"),
                "is_new": data.get("is_new", False),
                "reason": data.get("reason", ""),
            }
        except Exception as e:
            self._logger.warning(f"文档分类判断失败: {e}")
            return {
                "category_name": "未分类",
                "is_new": False,
                "reason": f"LLM 调用失败回退: {e}",
            }

    def _parse_assign_json(self, text: str) -> dict:
        """解析 assign 返回的 JSON，容错处理"""
        import json as _json
        try:
            # 清理 markdown 包裹
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:]) if len(lines) > 1 else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
            return _json.loads(text)
        except (_json.JSONDecodeError, Exception):
            return {}

    def _resolve_doc_ids(self, clusters: List[dict], doc_ids: List[str]) -> List[dict]:
        """将 LLM 返回的 doc_indices 转换为 doc_ids"""
        result = []
        seen_doc_ids = set()
        for c in clusters:
            resolved = []
            for idx in c.get("doc_indices", []):
                if 0 <= idx < len(doc_ids):
                    doc_id = doc_ids[idx]
                    if doc_id not in seen_doc_ids:
                        resolved.append(doc_id)
                        seen_doc_ids.add(doc_id)
            if resolved:
                result.append({
                    "name": c.get("name", "未分类"),
                    "description": c.get("description", ""),
                    "doc_ids": resolved,
                })

        # 确保所有文档都被覆盖（LLM 可能漏掉）
        uncovered = [did for did in doc_ids if did not in seen_doc_ids]
        if uncovered:
            result.append({
                "name": "其他",
                "description": "未归类的文档",
                "doc_ids": uncovered,
            })

        return result
