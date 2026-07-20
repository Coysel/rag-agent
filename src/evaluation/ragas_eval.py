"""
RAGAS 评估框架 — 定量评估 RAG 系统回答质量

四个核心指标:
  - Faithfulness (忠实度): 回答是否有原文依据 (有没有瞎编)
  - Answer Relevance (答案相关性): 回答是否切题 (有没有跑题)
  - Context Precision (上下文精度): 检索到的文档是否相关 (搜到的有没有用)
  - Context Recall (上下文召回): 相关文档是否被检索到 (有用的检没检索到)

对比实验:
  - 纯 Dense 检索 vs 混合检索 (Dense + BM25 + RRF)
"""
import time
from typing import List, Dict, Any
from dataclasses import dataclass

from src.agent.llm_client import get_llm_client
from src.evaluation.test_set import TestQuestion, get_test_questions


@dataclass
class EvalResult:
    """单条评估结果"""
    question_id: str
    question: str
    query_type: str
    answer: str
    ground_truth: str
    contexts: List[str]  # 检索到的文档内容
    faithfulness: float = 0.0
    answer_relevance: float = 0.0
    context_precision: float = 0.0
    context_recall: float = 0.0
    latency_seconds: float = 0.0
    tool_calls_count: int = 0


@dataclass
class ComparisonReport:
    """对比实验报告"""
    method_a_name: str
    method_b_name: str
    results_a: List[EvalResult]
    results_b: List[EvalResult]
    summary: Dict[str, Any]


def _get_llm():
    """获取 LLM 客户端"""
    return get_llm_client()


def _call_llm(prompt: str, max_tokens: int = 10) -> str:
    """调用 LLM 做简单文本评估，返回文本结果"""
    try:
        result = _get_llm().create_message(
            system="",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0,
        )
        return result.get("text", "").strip()
    except Exception:
        return ""


def evaluate_faithfulness(answer: str, contexts: List[str]) -> float:
    """
    评估忠实度 (Faithfulness)

    检测回答中的陈述是否可以在检索到的上下文中找到依据。
    """
    if not contexts or not answer:
        return 0.0

    context_text = "\n\n".join(c[:1000] for c in contexts[:5])
    prompt = f"""评估以下回答是否忠实于提供的上下文。即判断回答中的信息是否都可以在上下文中找到依据。

上下文:
{context_text}

回答:
{answer}

请给出忠实度评分 (0-1):
- 1.0: 回答中的每个关键陈述都可以在上下文中找到明确依据
- 0.7-0.9: 大部分陈述有依据，少量补充是合理推断
- 0.4-0.6: 部分陈述有依据，部分无依据或偏差
- 0.1-0.3: 大部分陈述在上下文中找不到依据
- 0.0: 回答与上下文完全无关或严重矛盾

请只回复一个 0 到 1 之间的数字，保留两位小数。"""

    text = _call_llm(prompt)
    try:
        score = float(text)
        return max(0.0, min(1.0, score))
    except (ValueError, TypeError):
        return 0.5


def evaluate_answer_relevance(question: str, answer: str) -> float:
    """
    评估答案相关性 (Answer Relevance)

    判断回答是否切合用户的问题。
    """
    if not answer:
        return 0.0

    prompt = f"""评估以下回答是否切合用户问题。即判断回答是否直接回应了问题，没有跑题。

用户问题:
{question}

回答:
{answer[:2000]}

请给出相关性评分 (0-1):
- 1.0: 回答完全针对问题，直接回应了所有要点
- 0.7-0.9: 回答基本切题，少量内容稍有偏离
- 0.4-0.6: 部分内容切题，但有明显偏离
- 0.1-0.3: 大部分内容不切题
- 0.0: 完全答非所问

请只回复一个 0 到 1 之间的数字，保留两位小数。"""

    text = _call_llm(prompt)
    try:
        score = float(text)
        return max(0.0, min(1.0, score))
    except (ValueError, TypeError):
        return 0.5


def evaluate_context_precision(question: str, contexts: List[str]) -> float:
    """
    评估上下文精度 (Context Precision)

    检索到的文档中，有多少是与问题真正相关的。
    """
    if not contexts:
        return 0.0

    context_items = "\n\n---\n\n".join(
        f"[文档 {i+1}] {c[:500]}" for i, c in enumerate(contexts[:10])
    )

    prompt = f"""评估以下检索结果中，有多少文档与用户问题真正相关。

用户问题:
{question}

检索到的文档:
{context_items}

请给出上下文精度评分 (0-1):
- 1.0: 所有检索到的文档都与问题高度相关
- 0.7-0.9: 大部分文档相关，少量不相关
- 0.4-0.6: 约一半文档相关
- 0.1-0.3: 大部分文档不相关
- 0.0: 所有文档都与问题无关

请只回复一个 0 到 1 之间的数字，保留两位小数。"""

    text = _call_llm(prompt)
    try:
        score = float(text)
        return max(0.0, min(1.0, score))
    except (ValueError, TypeError):
        return 0.5


def evaluate_context_recall(question: str, contexts: List[str], ground_truth: str) -> float:
    """
    评估上下文召回 (Context Recall)

    标准答案中需要的信息，有多少在检索到的文档中找到了。
    """
    if not contexts:
        return 0.0

    context_text = "\n\n".join(c[:800] for c in contexts[:5])

    prompt = f"""评估检索到的文档是否包含了回答以下问题所需的信息。

用户问题:
{question}

标准答案 (包含了回答问题所需的信息):
{ground_truth[:1000]}

检索到的文档内容:
{context_text[:2000]}

请给出上下文召回评分 (0-1):
- 1.0: 检索文档包含了标准答案所需的全部关键信息
- 0.7-0.9: 包含了大部分关键信息，少量缺失
- 0.4-0.6: 包含了部分关键信息，有较多缺失
- 0.1-0.3: 仅包含少量相关信息
- 0.0: 完全没有包含所需信息

请只回复一个 0 到 1 之间的数字，保留两位小数。"""

    text = _call_llm(prompt)
    try:
        score = float(text)
        return max(0.0, min(1.0, score))
    except (ValueError, TypeError):
        return 0.5


def _retrieve_docs(query: str, retriever_method: str = "hybrid") -> tuple:
    """执行检索，返回 (docs, latency) — 委托给统一管线"""
    from src.retrieval.pipeline import retrieve

    docs, latency = retrieve(query, method=retriever_method, return_latency=True)
    return docs, latency


def _generate_answer(query: str, docs: list) -> str:
    """基于检索到的文档生成回答"""
    if not docs:
        return "（未检索到相关文档）"

    context_text = "\n\n---\n\n".join(
        f"[来源: {d.get('title', '未知')}] {d.get('content', '')[:800]}"
        for d in docs[:5]
    )

    try:
        result = _get_llm().create_message(
            system="你是一个基于文档知识库的问答助手。请基于提供的文档内容回答问题，标注信息来源。如果文档没有相关信息，请诚实说明。",
            messages=[{
                "role": "user",
                "content": f"文档内容:\n{context_text}\n\n问题: {query}",
            }],
            max_tokens=1024,
            temperature=0.3,
        )
        return result.get("text", "")
    except Exception as e:
        return f"生成出错: {str(e)}"


def evaluate_single_question(
    question: str,
    ground_truth: str = "",
    retriever_method: str = "hybrid",
) -> EvalResult:
    """对单条问题进行检索→生成→评估，返回完整 EvalResult"""
    start_time = time.time()

    # 检索
    docs, _ = _retrieve_docs(question, retriever_method)
    contexts = [d.get("content", "") for d in docs[:5]]

    # 生成回答
    answer = _generate_answer(question, docs)
    latency = time.time() - start_time

    # 计算 RAGAS 指标
    faithfulness = evaluate_faithfulness(answer, contexts)
    answer_relevance = evaluate_answer_relevance(question, answer)
    context_precision = evaluate_context_precision(question, contexts)
    context_recall = evaluate_context_recall(question, contexts, ground_truth)

    return EvalResult(
        question_id="",
        question=question,
        query_type="",
        answer=answer,
        ground_truth=ground_truth,
        contexts=[c[:500] for c in contexts],
        faithfulness=faithfulness,
        answer_relevance=answer_relevance,
        context_precision=context_precision,
        context_recall=context_recall,
        latency_seconds=latency,
        tool_calls_count=1,
    )


def run_evaluation(
    test_questions: List[TestQuestion],
    retriever_method: str = "hybrid",
) -> List[EvalResult]:
    """对测试集逐条运行 RAGAS 评估"""
    results = []
    for tq in test_questions:
        result = evaluate_single_question(
            question=tq.question,
            ground_truth=tq.ground_truth,
            retriever_method=retriever_method,
        )
        result.question_id = tq.id
        result.query_type = tq.query_type
        results.append(result)
    return results


def run_comparison(
    test_questions: List[TestQuestion] = None,
) -> ComparisonReport:
    """
    对比实验: 纯 Dense vs 混合检索
    """
    if test_questions is None:
        test_questions = get_test_questions()

    # 纯 Dense
    results_dense = run_evaluation(test_questions, retriever_method="dense")

    # 混合检索
    results_hybrid = run_evaluation(test_questions, retriever_method="hybrid")

    # 计算均值
    def avg_metrics(results: List[EvalResult]) -> Dict[str, float]:
        n = len(results) or 1
        return {
            "faithfulness": sum(r.faithfulness for r in results) / n,
            "answer_relevance": sum(r.answer_relevance for r in results) / n,
            "context_precision": sum(r.context_precision for r in results) / n,
            "context_recall": sum(r.context_recall for r in results) / n,
            "avg_latency": sum(r.latency_seconds for r in results) / n,
        }

    dense_avg = avg_metrics(results_dense)
    hybrid_avg = avg_metrics(results_hybrid)

    # 改进幅度
    improvements = {
        metric: {
            "dense": round(dense_avg[metric], 4),
            "hybrid": round(hybrid_avg[metric], 4),
            "improvement_pct": round(
                (hybrid_avg[metric] - dense_avg[metric]) / max(dense_avg[metric], 0.001) * 100, 1
            ),
        }
        for metric in ["faithfulness", "answer_relevance", "context_precision", "context_recall"]
    }

    # 按查询类型分组统计
    def by_type(results: List[EvalResult], metric: str) -> Dict[str, float]:
        groups: Dict[str, List[float]] = {}
        for r in results:
            groups.setdefault(r.query_type, []).append(getattr(r, metric))
        return {k: sum(v) / len(v) for k, v in groups.items()}

    return ComparisonReport(
        method_a_name="纯 Dense",
        method_b_name="混合检索 (BM25 + Dense + RRF)",
        results_a=results_dense,
        results_b=results_hybrid,
        summary={
            "dense_avg": dense_avg,
            "hybrid_avg": hybrid_avg,
            "improvements": improvements,
        },
    )


# ── 新增: 检索对比 & 单条评测 ─────────────────────────────


def compare_retrievers(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    对比三种检索器对单条查询的检索结果

    Returns:
        {
            "query": str,
            "bm25": {"docs": [...], "latency": float, "count": int},
            "dense": {"docs": [...], "latency": float, "count": int},
            "hybrid": {"docs": [...], "latency": float, "count": int},
        }
    """
    result = {"query": query}

    for method in ["bm25", "dense", "hybrid"]:
        docs, latency = _retrieve_docs(query, method)
        result[method] = {
            "docs": [
                {
                    "title": d.get("title", "未知"),
                    "source": d.get("source", ""),
                    "content": d.get("content", ""),
                    "score": d.get("rrf_score", d.get("dense_score", d.get("bm25_score", 0))),
                }
                for d in docs[:top_k]
            ],
            "latency": round(latency, 4),
            "count": len(docs),
        }

    return result


def evaluate_single_qa(query: str) -> Dict[str, Any]:
    """
    单条问答评测 — 运行检索 + 生成流程后计算 4 个 RAGAS 指标

    Returns:
        {
            "query": str,
            "answer": str,
            "sources": [...],
            "steps": int,
            "query_type": str,
            "latency_seconds": float,
            "faithfulness": float,
            "answer_relevance": float,
            "context_precision": float,
            "context_recall": float,
            "context_docs_count": int,
        }
    """
    from src.retrieval.router import QueryRouter

    t0 = time.time()

    # 查询分类
    router = QueryRouter()
    query_type = router.classify(query)

    # 检索（混合检索）
    docs, _ = _retrieve_docs(query, "hybrid")
    contexts = [d.get("content", "") for d in docs]

    # 生成回答
    answer = _generate_answer(query, docs)
    latency = time.time() - t0

    # 计算 RAGAS 指标
    faithfulness = evaluate_faithfulness(answer, contexts)
    answer_relevance = evaluate_answer_relevance(query, answer)
    context_precision = evaluate_context_precision(query, contexts)
    context_recall = evaluate_context_recall(query, contexts, answer)

    # 提取来源
    sources = []
    seen = set()
    for doc in docs:
        title = doc.get("title", "未知")
        if title not in seen:
            seen.add(title)
            sources.append({
                "title": title,
                "source": doc.get("source", ""),
                "score": doc.get("rrf_score", doc.get("dense_score", doc.get("bm25_score", 0))),
                "content": doc.get("content", "")[:800],
            })

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
        "steps": 1,
        "query_type": query_type.value if hasattr(query_type, 'value') else str(query_type),
        "latency_seconds": round(latency, 3),
        "faithfulness": faithfulness,
        "answer_relevance": answer_relevance,
        "context_precision": context_precision,
        "context_recall": context_recall,
        "context_docs_count": len(docs),
    }
