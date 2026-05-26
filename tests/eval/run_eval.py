# tests/eval/run_eval.py
"""
CLI entrypoint for running hallucination evaluation.

Usage:
    python -m tests.eval.run_eval --dataset tests/eval/eval_dataset.jsonl
    python -m tests.eval.run_eval --dataset tests/eval/eval_dataset.jsonl --provider gemini
    python -m tests.eval.run_eval --dataset tests/eval/eval_dataset.jsonl --output results.json
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from dataclasses import asdict

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import Settings
from core.llm.factory import get_llm_client
from core.logging_config import setup_logging
from tests.eval.hallucination_eval import (
    HallucinationEvaluator,
    load_eval_dataset,
    print_report,
)


async def run_evaluation(args):
    """Run the hallucination evaluation pipeline."""
    # Load settings (can override provider via CLI args)
    settings = Settings()
    if args.provider:
        settings = settings.model_copy(update={"llm_provider": args.provider})
    if args.model:
        settings = settings.model_copy(update={"llm_model": args.model})

    setup_logging(settings)

    # Create judge LLM
    judge_llm = get_llm_client(settings)
    print(f"\n📊 Evaluation Judge: {judge_llm.provider_name} ({settings.llm_model})")

    # Load dataset
    dataset = load_eval_dataset(args.dataset)
    print(f"📄 Dataset: {args.dataset} ({len(dataset)} samples)")

    # Run evaluation
    evaluator = HallucinationEvaluator(judge_llm)
    report = await evaluator.evaluate_dataset(
        dataset, concurrency=args.concurrency
    )

    # Print report
    print_report(report)

    # Save results
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, default=str)
        print(f"💾 Results saved to: {output_path}")

    # Return exit code based on hallucination threshold
    if report.avg_hallucination_rate > args.threshold:
        print(
            f"\n❌ FAIL: Hallucination rate {report.avg_hallucination_rate:.1%} "
            f"exceeds threshold {args.threshold:.1%}"
        )
        return 1
    else:
        print(
            f"\n✅ PASS: Hallucination rate {report.avg_hallucination_rate:.1%} "
            f"within threshold {args.threshold:.1%}"
        )
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Run hallucination rate evaluation on an agent system",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="tests/eval/eval_dataset.jsonl",
        help="Path to JSONL evaluation dataset",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="",
        help="Override LLM provider for the judge (e.g., anthropic, gemini, ollama)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="",
        help="Override model for the judge",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Output path for JSON results file",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Max concurrent evaluation requests (default: 3)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.3,
        help="Max acceptable hallucination rate (default: 0.3 = 30%%)",
    )

    args = parser.parse_args()
    exit_code = asyncio.run(run_evaluation(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
