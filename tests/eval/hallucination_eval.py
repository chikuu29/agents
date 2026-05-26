# tests/eval/hallucination_eval.py
"""
Hallucination rate evaluation framework.

Measures how often the agent produces claims not grounded
in the provided context (faithfulness) and how accurately
it reproduces expected facts (factual accuracy).

Metrics:
- faithfulness_score:  % of response claims grounded in context
- hallucination_rate:  1 - faithfulness_score
- factual_accuracy:    % of expected facts present in response
- relevance_score:     How well the response addresses the input

Uses an LLM-as-judge approach for evaluation.
"""

import json
import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from core.llm.base import BaseLLM

logger = structlog.get_logger(__name__)


@dataclass
class EvalSample:
    """A single evaluation sample."""
    id: str
    input_text: str
    context: str                    # Ground-truth context provided to the agent
    expected_facts: list[str]       # Facts the response should contain
    response: str = ""              # Agent's actual response (filled during eval)


@dataclass
class EvalScore:
    """Evaluation scores for a single sample."""
    sample_id: str
    faithfulness_score: float       # 0.0 - 1.0
    hallucination_rate: float       # 1 - faithfulness
    factual_accuracy: float         # 0.0 - 1.0
    relevance_score: float          # 0.0 - 1.0
    claims_total: int = 0
    claims_grounded: int = 0
    facts_found: int = 0
    facts_expected: int = 0
    details: str = ""


@dataclass
class EvalReport:
    """Aggregate evaluation report."""
    scores: list[EvalScore] = field(default_factory=list)
    avg_faithfulness: float = 0.0
    avg_hallucination_rate: float = 0.0
    avg_factual_accuracy: float = 0.0
    avg_relevance: float = 0.0
    total_samples: int = 0
    duration_seconds: float = 0.0


class HallucinationEvaluator:
    """
    Evaluates agent responses for hallucination using LLM-as-judge.

    The evaluator sends a structured prompt to a judge LLM asking it
    to analyze each claim in the response against the provided context.
    """

    def __init__(self, judge_llm: BaseLLM):
        self.judge = judge_llm

    async def evaluate_sample(
        self, sample: EvalSample
    ) -> EvalScore:
        """Evaluate a single sample for hallucination and accuracy."""

        judge_prompt = f"""You are an impartial evaluation judge. Analyze the following response for hallucination and factual accuracy.

## Context (ground truth):
{sample.context}

## User Input:
{sample.input_text}

## Agent Response:
{sample.response}

## Expected Facts:
{json.dumps(sample.expected_facts)}

Evaluate and respond with ONLY valid JSON (no markdown fences):
{{
    "claims": [
        {{"claim": "<extracted claim>", "grounded": true/false, "reason": "<why>"}}
    ],
    "facts_found": ["<which expected facts are present in the response>"],
    "relevance_score": 0.0-1.0,
    "reasoning": "<overall assessment>"
}}
"""

        try:
            response = await self.judge.chat(
                messages=[{"role": "user", "content": judge_prompt}],
                max_tokens=1500,
                temperature=0.1,  # Low temperature for consistent evaluation
            )

            raw_text = response.text or ""
            # Strip markdown fences
            raw_text = raw_text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[-1]
            if raw_text.endswith("```"):
                raw_text = raw_text.rsplit("```", 1)[0]

            data = json.loads(raw_text.strip())

            claims = data.get("claims", [])
            grounded_count = sum(1 for c in claims if c.get("grounded", False))
            total_claims = len(claims) if claims else 1

            facts_found = data.get("facts_found", [])
            facts_expected = len(sample.expected_facts)

            faithfulness = grounded_count / total_claims if total_claims > 0 else 1.0
            factual_accuracy = len(facts_found) / facts_expected if facts_expected > 0 else 1.0
            relevance = data.get("relevance_score", 0.0)

            return EvalScore(
                sample_id=sample.id,
                faithfulness_score=round(faithfulness, 3),
                hallucination_rate=round(1 - faithfulness, 3),
                factual_accuracy=round(min(factual_accuracy, 1.0), 3),
                relevance_score=round(relevance, 3),
                claims_total=total_claims,
                claims_grounded=grounded_count,
                facts_found=len(facts_found),
                facts_expected=facts_expected,
                details=data.get("reasoning", ""),
            )

        except Exception as e:
            logger.error("eval.judge_error", sample_id=sample.id, error=str(e))
            return EvalScore(
                sample_id=sample.id,
                faithfulness_score=0.0,
                hallucination_rate=1.0,
                factual_accuracy=0.0,
                relevance_score=0.0,
                details=f"Evaluation error: {e}",
            )

    async def evaluate_dataset(
        self, samples: list[EvalSample], concurrency: int = 3
    ) -> EvalReport:
        """Evaluate a dataset of samples with controlled concurrency."""
        start_time = time.perf_counter()

        semaphore = asyncio.Semaphore(concurrency)

        async def eval_with_limit(sample: EvalSample) -> EvalScore:
            async with semaphore:
                return await self.evaluate_sample(sample)

        scores = await asyncio.gather(
            *[eval_with_limit(s) for s in samples]
        )

        duration = time.perf_counter() - start_time

        # Aggregate
        report = EvalReport(
            scores=list(scores),
            total_samples=len(scores),
            duration_seconds=round(duration, 2),
        )

        if scores:
            report.avg_faithfulness = round(
                sum(s.faithfulness_score for s in scores) / len(scores), 3
            )
            report.avg_hallucination_rate = round(
                sum(s.hallucination_rate for s in scores) / len(scores), 3
            )
            report.avg_factual_accuracy = round(
                sum(s.factual_accuracy for s in scores) / len(scores), 3
            )
            report.avg_relevance = round(
                sum(s.relevance_score for s in scores) / len(scores), 3
            )

        return report


def load_eval_dataset(path: str) -> list[EvalSample]:
    """Load evaluation dataset from a JSONL file."""
    samples = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            samples.append(EvalSample(
                id=data["id"],
                input_text=data["input"],
                context=data["context"],
                expected_facts=data["expected_facts"],
                response=data.get("response", ""),
            ))
    return samples


def print_report(report: EvalReport) -> None:
    """Pretty-print an evaluation report to the console."""
    print("\n" + "=" * 70)
    print("  HALLUCINATION EVALUATION REPORT")
    print("=" * 70)
    print(f"  Samples evaluated:     {report.total_samples}")
    print(f"  Duration:              {report.duration_seconds}s")
    print("-" * 70)
    print(f"  Avg Faithfulness:      {report.avg_faithfulness:.1%}")
    print(f"  Avg Hallucination Rate:{report.avg_hallucination_rate:.1%}")
    print(f"  Avg Factual Accuracy:  {report.avg_factual_accuracy:.1%}")
    print(f"  Avg Relevance:         {report.avg_relevance:.1%}")
    print("-" * 70)

    for score in report.scores:
        status = "✅" if score.hallucination_rate < 0.2 else "⚠️" if score.hallucination_rate < 0.5 else "❌"
        print(f"  {status} [{score.sample_id}]  "
              f"Faith={score.faithfulness_score:.0%}  "
              f"Halluc={score.hallucination_rate:.0%}  "
              f"Facts={score.facts_found}/{score.facts_expected}  "
              f"Rel={score.relevance_score:.0%}")
        if score.details:
            print(f"     └─ {score.details[:120]}")

    print("=" * 70 + "\n")
