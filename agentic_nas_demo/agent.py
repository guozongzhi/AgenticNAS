from __future__ import annotations

from dataclasses import dataclass
import json
import random
from typing import Any, Callable, Protocol

from .pareto import Evaluation
from .search_space import ArchitectureSpec, MutationAction, random_action


@dataclass(frozen=True)
class CandidateSummary:
    architecture: ArchitectureSpec
    evaluation: Evaluation

    def to_dict(self) -> dict[str, Any]:
        return {
            "architecture": self.architecture.to_dict(),
            "evaluation": self.evaluation.to_dict(),
        }


@dataclass(frozen=True)
class AgentObservation:
    iteration: int
    evaluated_count: int
    remaining_budget: int
    pareto_frontier: tuple[CandidateSummary, ...]
    allowed_action_schema: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "evaluated_count": self.evaluated_count,
            "remaining_budget": self.remaining_budget,
            "pareto_frontier": [candidate.to_dict() for candidate in self.pareto_frontier],
            "allowed_action_schema": self.allowed_action_schema,
        }


class AgentPolicy(Protocol):
    def propose(
        self,
        observation: AgentObservation,
        rng: random.Random,
        count: int,
    ) -> list[MutationAction]: ...


class HeuristicAgent:
    """Provider-free baseline that exercises the same contract as an LLM Agent."""

    def propose(
        self,
        observation: AgentObservation,
        rng: random.Random,
        count: int,
    ) -> list[MutationAction]:
        parents = [candidate.architecture for candidate in observation.pareto_frontier]
        if not parents:
            return []
        return [random_action(rng.choice(parents), rng) for _ in range(count)]


class CallableJsonAgent:
    """Adapter for an internal GLM/MiniMax/Claude completion function."""

    def __init__(self, completion: Callable[[dict[str, Any]], str]) -> None:
        self.completion = completion

    def propose(
        self,
        observation: AgentObservation,
        rng: random.Random,
        count: int,
    ) -> list[MutationAction]:
        del rng
        request = observation.to_dict()
        request["requested_action_count"] = count
        response = json.loads(self.completion(request))
        actions = [MutationAction.from_dict(item) for item in response["actions"]]
        if len(actions) != count:
            raise ValueError(f"Agent must return exactly {count} actions")
        return actions


ACTION_SCHEMA: dict[str, Any] = {
    "response": {"actions": "array"},
    "action": {
        "parent_id": "string from pareto_frontier",
        "level": ["block", "cell", "op"],
        "target_index": "null for block; integer for cell/op",
        "field": {
            "block": ["depth"],
            "cell": ["num_heads", "ffn_ratio"],
            "op": ["ffn_kernel_size", "activation"],
        },
        "value": "a different value allowed by the architecture description",
    },
}
