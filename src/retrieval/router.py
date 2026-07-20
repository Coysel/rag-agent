"""
语义路由器 — 零样本查询分类

使用 LLM 判断查询类型，指导检索策略:
  - factual（事实查询）→ BM25 权重更高（精确词匹配）
  - conceptual（概念解释）→ Dense 权重更高（语义匹配）
  - multi_hop（多步推理）→ 链式工具调用
"""
from enum import Enum

from src.agent.llm_client import get_llm_client


class QueryType(str, Enum):
    FACTUAL = "factual"        # 事实查询: "Conv2d 参数有哪些？"
    CONCEPTUAL = "conceptual"  # 概念解释: "什么是迁移学习？"
    MULTI_HOP = "multi_hop"    # 多步推理: "A 和 B 在什么场景下各自更优？"


ROUTER_PROMPT = """你是一个查询分类器。分析用户的问题，将其归类为以下三种类型之一:

1. **factual** (事实查询): 问题询问具体的、可精确查找的事实信息。
   - 关键词通常是专有名词、API名、参数名
   - 例如: "Conv2d的参数有哪些？"、"Python的list.append时间复杂度是多少？"

2. **conceptual** (概念解释): 问题要求解释概念、原理或方法。
   - 关键词通常是"什么是"、"如何理解"、"原理"、"区别"
   - 例如: "什么是迁移学习？"、"Transformer的注意力机制如何工作？"

3. **multi_hop** (多步推理): 问题需要综合多个信息源才能回答，涉及比较或推理。
   - 关键词通常是"比较"、"场景"、"为什么"、"如何选择"
   - 例如: "A方法和B方法在什么场景下各自更优？"、"为什么要用RRF融合而不是直接加权？"

请只返回以下三个词之一: factual, conceptual, multi_hop

用户问题: {query}

分类结果:"""


class QueryRouter:
    """语义路由器 — 零样本查询分类"""

    def __init__(self):
        self._llm = get_llm_client()
        self._cache: dict[str, QueryType] = {}

    def classify(self, query: str) -> QueryType:
        """
        对查询进行分类

        Args:
            query: 用户查询

        Returns:
            QueryType: factual | conceptual | multi_hop
        """
        # 简单的关键词预判 (快速路径，无需 API 调用)
        query_lower = query.lower().strip()
        if any(kw in query_lower for kw in ["参数", "配置", "api", "参数列表", "有哪些参数", "用法"]):
            return QueryType.FACTUAL
        if any(kw in query_lower for kw in ["什么是", "概念", "理解", "介绍", "原理", "含义", "定义"]):
            return QueryType.CONCEPTUAL
        if any(kw in query_lower for kw in ["比较", "区别", "对比", "场景", "选择", "为什么", "哪个更", "优劣"]):
            return QueryType.MULTI_HOP

        # 检查缓存
        if query in self._cache:
            return self._cache[query]

        # 调用 LLM 做零样本分类
        try:
            result = self._llm.create_message(
                system="",
                messages=[{"role": "user", "content": ROUTER_PROMPT.format(query=query)}],
                max_tokens=10,
                temperature=0,
            )
            text = result.get("text", "").strip().lower()

            for qtype in QueryType:
                if qtype.value in text:
                    self._cache[query] = qtype
                    return qtype

            # 默认返回 conceptual
            return QueryType.CONCEPTUAL

        except Exception:
            return QueryType.CONCEPTUAL

