from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


@dataclass
class RouteDecision:
    task_id: str
    route: str
    generator_tier: str
    judge_tier: str
    pairwise_required: bool
    rationale: str


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def route_task(task: dict[str, Any]) -> RouteDecision:
    metadata = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    source_mode = str(metadata.get("source_mode", task.get("source_mode", "")) or "")
    failure_category = str(metadata.get("failure_category", "") or "")
    notes = str(metadata.get("notes", "") or "")

    nuanced_categories = {
        "gap_overclaiming",
        "tone_drift",
        "dual_control_coordination",
    }

    if source_mode == "trace_derived":
        return RouteDecision(
            task_id=str(task.get("task_id", "")),
            route="trace_preserving_rewrite",
            generator_tier="eval",
            judge_tier="eval",
            pairwise_required=False,
            rationale="trace-derived tasks preserve a specific Week 10 failure and should use the higher-fidelity route.",
        )

    if failure_category in nuanced_categories or "subtle" in notes.lower():
        return RouteDecision(
            task_id=str(task.get("task_id", "")),
            route="nuanced_business_framing",
            generator_tier="eval",
            judge_tier="eval",
            pairwise_required=True,
            rationale="framing-sensitive categories need a stronger generator and pairwise tie-break support.",
        )

    return RouteDecision(
        task_id=str(task.get("task_id", "")),
        route="cheap_paraphrase_expansion",
        generator_tier="cheap",
        judge_tier="eval",
        pairwise_required=True,
        rationale="controlled variants can start with the cheaper route but still require eval-tier judging.",
    )


def route_summary(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = [route_task(task) for task in tasks]
    summary = {
        "cheap_generator_count": sum(1 for d in decisions if d.generator_tier == "cheap"),
        "eval_generator_count": sum(1 for d in decisions if d.generator_tier == "eval"),
        "pairwise_required_count": sum(1 for d in decisions if d.pairwise_required),
    }
    return {
        "routing_policy_path": str(ROOT / "routing_policy.md"),
        "implemented_with_live_llm_calls": False,
        "summary": summary,
        "decisions": [asdict(decision) for decision in decisions],
        "note": "Stub routing only; replace route labels with actual model invocations and logs in the final pipeline.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Interim multi-LLM routing scaffold.")
    parser.add_argument("task_file", help="JSONL task file to route")
    args = parser.parse_args()

    task_path = Path(args.task_file).resolve()
    tasks = load_jsonl(task_path)
    payload = {
        "task_file": str(task_path),
        **route_summary(tasks),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
