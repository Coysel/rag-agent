"""
一键运行 RAGAS 评估脚本

流程:
  1. 加载 20 条测试问题
  2. 运行纯 Dense 检索评估
  3. 运行混合检索评估
  4. 输出对比报告

用法:
  python scripts/run_evaluation.py
  python scripts/run_evaluation.py --output report.json
"""
import argparse
import json
import sys
import os
from dataclasses import asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evaluation.test_set import get_test_questions, get_by_type
from src.evaluation.ragas_eval import run_comparison, run_evaluation, EvalResult


def main(output_path: str = None):
    test_questions = get_test_questions()#获取问题

    print(f"加载了 {len(test_questions)} 条测试问题")
    print(f"  - factual: {len(get_by_type('factual'))} 条")
    print(f"  - conceptual: {len(get_by_type('conceptual'))} 条")
    print(f"  - multi_hop: {len(get_by_type('multi_hop'))} 条")
    print()

    # 运行对比实验
    report = run_comparison(test_questions)

    # 输出按类型分组的详细结果
    print("   按查询类型分组 (混合检索)")

    for qtype in ["factual", "conceptual", "multi_hop"]:
        type_results = [r for r in report.results_b if r.query_type == qtype]
        if not type_results:
            continue
        n = len(type_results)
        print(f"\n[{qtype}] ({n} 条问题):")
        print(f"  忠实度:        {sum(r.faithfulness for r in type_results)/n:.4f}")
        print(f"  答案相关性:    {sum(r.answer_relevance for r in type_results)/n:.4f}")
        print(f"  上下文精度:    {sum(r.context_precision for r in type_results)/n:.4f}")
        print(f"  上下文召回:    {sum(r.context_recall for r in type_results)/n:.4f}")
        print(f"  平均延迟:      {sum(r.latency_seconds for r in type_results)/n:.2f}s")

    # 保存到文件
    if output_path:
        output = {
            "summary": report.summary,
            "dense_results": [asdict(r) for r in report.results_a],
            "hybrid_results": [asdict(r) for r in report.results_b],
        }

        # 清理不可序列化的内容
        for results in [output["dense_results"], output["hybrid_results"]]:
            for r in results:
                r["contexts"] = r["contexts"][:2]  # 只保留前2条
                r["answer"] = r["answer"][:200]    # 截断
                r["ground_truth"] = r["ground_truth"][:200]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n报告已保存至: {output_path}")

    print("\n评估完成。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="运行 RAGAS 评估")
    parser.add_argument("--output", "-o", type=str, default=None, help="输出 JSON 报告路径")
    args = parser.parse_args()
    main(args.output)
