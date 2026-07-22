from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import random
from typing import Any

from .agent import ACTION_SCHEMA, AgentObservation, AgentPolicy, CandidateSummary, HeuristicAgent
from .pareto import Evaluation, evaluate, pareto_frontier
from .search_space import ArchitectureSpec, apply_action, random_spec


@dataclass(frozen=True)
class SearchResult:
    architectures: dict[str, ArchitectureSpec]
    evaluations: dict[str, Evaluation]
    frontier_ids: tuple[str, ...]
    rejected_actions: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluated_count": len(self.evaluations),
            "rejected_actions": self.rejected_actions,
            "pareto_frontier": [
                {
                    "architecture": self.architectures[arch_id].to_dict(),
                    "evaluation": self.evaluations[arch_id].to_dict(),
                }
                for arch_id in self.frontier_ids
            ],
        }


def _observation(
    iteration: int,
    budget: int,
    architectures: dict[str, ArchitectureSpec],
    evaluations: dict[str, Evaluation],
) -> AgentObservation:
    frontier = pareto_frontier(evaluations.values())
    summaries = tuple(
        CandidateSummary(architectures[item.arch_id], item) for item in frontier
    )
    return AgentObservation(
        iteration=iteration,
        evaluated_count=len(evaluations),
        remaining_budget=max(0, budget - len(evaluations)),
        pareto_frontier=summaries,
        allowed_action_schema=ACTION_SCHEMA,
    )


def run_search(
    *,
    policy: AgentPolicy | None = None,
    seed: int = 7,
    initial_population: int = 6,
    iterations: int = 3,
    proposals_per_iteration: int = 4,
    trace_dir: str | Path | None = None,
) -> SearchResult:
    if initial_population < 1 or iterations < 0 or proposals_per_iteration < 1:
        raise ValueError("population/proposal sizes must be positive and iterations non-negative")

    rng = random.Random(seed)
    policy = policy or HeuristicAgent()
    budget = initial_population + iterations * proposals_per_iteration
    architectures: dict[str, ArchitectureSpec] = {}
    evaluations: dict[str, Evaluation] = {}
    rejected_actions = 0
    trace_path = Path(trace_dir) if trace_dir else None
    if trace_path:
        trace_path.mkdir(parents=True, exist_ok=True)

    while len(architectures) < initial_population:
        spec = random_spec(rng)
        if spec.arch_id not in architectures:
            architectures[spec.arch_id] = spec
            evaluations[spec.arch_id] = evaluate(spec)

    for iteration in range(1, iterations + 1):
        observation = _observation(iteration, budget, architectures, evaluations)
        actions = policy.propose(observation, rng, proposals_per_iteration)
        if trace_path:
            (trace_path / f"iteration_{iteration:02d}_observation.json").write_text(
                json.dumps(observation.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (trace_path / f"iteration_{iteration:02d}_actions.json").write_text(
                json.dumps({"actions": [action.to_dict() for action in actions]}, indent=2),
                encoding="utf-8",
            )

        for action in actions:
            parent = architectures.get(action.parent_id)
            try:
                if parent is None:
                    raise ValueError("unknown parent_id")
                child = apply_action(parent, action)
                if child.arch_id in architectures:
                    raise ValueError("duplicate architecture")
            except ValueError:
                rejected_actions += 1
                continue
            architectures[child.arch_id] = child
            evaluations[child.arch_id] = evaluate(child)

    frontier = pareto_frontier(evaluations.values())
    result = SearchResult(
        architectures=architectures,
        evaluations=evaluations,
        frontier_ids=tuple(item.arch_id for item in frontier),
        rejected_actions=rejected_actions,
    )
    if trace_path:
        (trace_path / "search_result.json").write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return result
