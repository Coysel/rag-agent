"""
评测端点 — POST /eval/*
"""
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from src.api.schemas.eval import (
    EvalRetrievalRequest,
    EvalSingleRequest,
    EvalRagasRequest,
    EvalCustomRequest,
)
from src.evaluation.test_set import get_test_questions
from src.evaluation.ragas_eval import (
    compare_retrievers,
    evaluate_single_qa,
)

router = APIRouter(prefix="/eval", tags=["evaluation"])


@router.post("/retrieval")
async def eval_retrieval(req: EvalRetrievalRequest):
    """单条查询检索对比 — BM25 vs Dense vs Hybrid"""
    return compare_retrievers(req.query)


@router.post("/single")
async def eval_single(req: EvalSingleRequest):
    """单条问答评测 — 运行检索+生成流程，计算 4 个 RAGAS 指标"""
    return evaluate_single_qa(req.query)


@router.post("/ragas")
async def eval_ragas(req: EvalRagasRequest):
    """RAGAS 评测 (预设测试集) — SSE 流式返回进度和结果"""
    test_questions = get_test_questions()[:req.count]
    return EventSourceResponse(_stream_evaluation(test_questions))


@router.post("/custom")
async def eval_custom(req: EvalCustomRequest):
    """自定义问题评测 — 用户输入问题，SSE 流式返回 RAGAS 分析结果"""
    questions = list(dict.fromkeys([q.strip() for q in req.questions if q.strip()]))
    if not questions:
        raise HTTPException(status_code=400, detail="没有有效的问题")
    return EventSourceResponse(_stream_custom_evaluation(questions))


# ── SSE 流式评测生成器 ──────────────────────────────────────


async def _stream_evaluation(test_questions) -> AsyncGenerator[str, None]:
    """SSE 流式 RAGAS 评测"""
    total = len(test_questions) * 2  # Dense + Hybrid

    def avg_metrics(results):
        n = len(results) or 1
        return {
            "faithfulness": sum(r.faithfulness for r in results) / n,
            "answer_relevance": sum(r.answer_relevance for r in results) / n,
            "context_precision": sum(r.context_precision for r in results) / n,
            "context_recall": sum(r.context_recall for r in results) / n,
            "avg_latency": sum(r.latency_seconds for r in results) / n,
        }

    try:
        from src.evaluation.ragas_eval import evaluate_single_question as _eval_one

        # Phase 1: Dense
        dense_results = []
        for i, tq in enumerate(test_questions):
            yield {
                "event": "progress",
                "data": json.dumps({
                    "phase": "dense", "current": i + 1, "total": total,
                    "question": tq.question[:60], "method": "纯 Dense",
                }, ensure_ascii=False),
            }
            result = _eval_one(tq.question, tq.ground_truth, retriever_method="dense")
            result.question_id = tq.id
            result.query_type = tq.query_type
            dense_results.append(result)

        # Phase 2: Hybrid
        hybrid_results = []
        for i, tq in enumerate(test_questions):
            yield {
                "event": "progress",
                "data": json.dumps({
                    "phase": "hybrid", "current": len(test_questions) + i + 1, "total": total,
                    "question": tq.question[:60], "method": "混合检索",
                }, ensure_ascii=False),
            }
            result = _eval_one(tq.question, tq.ground_truth, retriever_method="hybrid")
            result.question_id = tq.id
            result.query_type = tq.query_type
            hybrid_results.append(result)

        # 汇总
        dense_avg = avg_metrics(dense_results)
        hybrid_avg = avg_metrics(hybrid_results)

        improvements = {}
        for metric in ["faithfulness", "answer_relevance", "context_precision", "context_recall"]:
            improvements[metric] = {
                "dense": round(dense_avg[metric], 4),
                "hybrid": round(hybrid_avg[metric], 4),
                "improvement_pct": round(
                    (hybrid_avg[metric] - dense_avg[metric]) / max(dense_avg[metric], 0.001) * 100, 1
                ),
            }

        def by_type(results, metric_name):
            groups = {}
            for r in results:
                groups.setdefault(r.query_type, []).append(getattr(r, metric_name))
            return {k: round(sum(v) / len(v), 4) for k, v in groups.items()}

        dense_by_type = {
            "faithfulness": by_type(dense_results, "faithfulness"),
            "answer_relevance": by_type(dense_results, "answer_relevance"),
            "context_precision": by_type(dense_results, "context_precision"),
            "context_recall": by_type(dense_results, "context_recall"),
        }
        hybrid_by_type = {
            "faithfulness": by_type(hybrid_results, "faithfulness"),
            "answer_relevance": by_type(hybrid_results, "answer_relevance"),
            "context_precision": by_type(hybrid_results, "context_precision"),
            "context_recall": by_type(hybrid_results, "context_recall"),
        }

        per_question = []
        for dr, hr in zip(dense_results, hybrid_results):
            per_question.append({
                "id": dr.question_id,
                "question": dr.question[:80],
                "query_type": dr.query_type,
                "dense": {
                    "faithfulness": dr.faithfulness,
                    "answer_relevance": dr.answer_relevance,
                    "context_precision": dr.context_precision,
                    "context_recall": dr.context_recall,
                    "latency": round(dr.latency_seconds, 3),
                },
                "hybrid": {
                    "faithfulness": hr.faithfulness,
                    "answer_relevance": hr.answer_relevance,
                    "context_precision": hr.context_precision,
                    "context_recall": hr.context_recall,
                    "latency": round(hr.latency_seconds, 3),
                },
            })

        yield {
            "event": "done",
            "data": json.dumps({
                "summary": {
                    "dense_avg": dense_avg,
                    "hybrid_avg": hybrid_avg,
                    "improvements": improvements,
                },
                "dense_by_type": dense_by_type,
                "hybrid_by_type": hybrid_by_type,
                "per_question": per_question,
                "total_questions": len(test_questions),
            }, ensure_ascii=False),
        }

    except Exception as e:
        yield {
            "event": "error",
            "data": json.dumps({"message": str(e)}, ensure_ascii=False),
        }


async def _stream_custom_evaluation(questions: list) -> AsyncGenerator[str, None]:
    """SSE 流式自定义问题评测"""
    total = len(questions)
    results = []

    for i, question in enumerate(questions):
        yield {
            "event": "progress",
            "data": json.dumps({
                "current": i + 1, "total": total,
                "question": question[:80],
            }, ensure_ascii=False),
        }

        try:
            result = evaluate_single_qa(question)
            results.append(result)
            yield {"event": "result", "data": json.dumps(result, ensure_ascii=False)}
        except Exception as e:
            results.append({
                "query": question, "answer": f"评测出错: {str(e)}",
                "sources": [], "steps": 0, "query_type": "",
                "latency_seconds": 0, "faithfulness": 0,
                "answer_relevance": 0, "context_precision": 0,
                "context_recall": 0, "context_docs_count": 0,
            })
            yield {"event": "result", "data": json.dumps(results[-1], ensure_ascii=False)}

    # 汇总
    valid = [r for r in results if r.get("faithfulness", 0) > 0 or r.get("answer_relevance", 0) > 0]
    n = len(valid) or 1
    summary = {
        "avg_faithfulness": round(sum(r.get("faithfulness", 0) for r in results) / n, 4),
        "avg_answer_relevance": round(sum(r.get("answer_relevance", 0) for r in results) / n, 4),
        "avg_context_precision": round(sum(r.get("context_precision", 0) for r in results) / n, 4),
        "avg_context_recall": round(sum(r.get("context_recall", 0) for r in results) / n, 4),
        "avg_latency": round(sum(r.get("latency_seconds", 0) for r in results) / n, 3),
        "avg_docs": round(sum(r.get("context_docs_count", 0) for r in results) / n, 1),
    }

    yield {
        "event": "done",
        "data": json.dumps({"summary": summary, "results": results, "total": total}, ensure_ascii=False),
    }
