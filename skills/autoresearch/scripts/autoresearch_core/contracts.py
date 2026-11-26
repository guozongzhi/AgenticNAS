from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from typing import Any

from .utils import has_path, is_finite_number, non_negative_number, positive_number


TRACKS = ("architecture", "hpo")
DIRECTIONS = ("maximize", "minimize")
KNOWLEDGE_STATUSES = ("draft", "published", "deprecated")
TRIAL_DECISIONS = ("baseline", "keep", "discard", "proxy_pass", "proxy_discard", "crash", "cancelled")
CAMPAIGN_CLOSED = {"succeeded", "failed", "cancelled"}

FIDELITIES = ("smoke", "proxy", "full")
PROPOSAL_OPERATORS = ("refine", "explore", "recombine", "ablate", "shrink")
RECORD_FAILURE_KINDS = ("oom", "nan_divergence", "timeout", "metric_invalid", "infra_flake", "other")

PATTERN_DIRECTIONS = {
    "gain_up_compute_down",
    "gain_up_compute_neutral",
    "gain_up_compute_up",
    "compute_down_tie",
    "other",
}
FAILURE_TYPES = {
    "compute_budget_exceeded",
    "guardrail_violated",
    "accuracy_regression",
    "training_crash",
    "other",
}
CONFIDENCE_RANK = {"low": 1, "medium": 2, "dev_only": 2, "verified_holdout": 3}


@dataclass(frozen=True)
class Proposal:
    hypothesis: str
    changes: dict[str, Any]
    parent_trial_id: str | None = None
    inspiration_trial_ids: list[str] = field(default_factory=list)
    operator: str = "refine"
    fidelity: str = "full"
    reuse_simulation: bool = False
    expected_primary: float | None = None
    expected_compute_ratio: float | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Proposal:
        if not isinstance(raw, dict):
            raise ValueError("Proposal must be a JSON object")
        hypothesis = raw.get("hypothesis")
        changes = raw.get("changes")
        parent_id = raw.get("parent_trial_id")
        inspirations = raw.get("inspiration_trial_ids") or []
        operator = raw.get("operator", "refine")
        fidelity = raw.get("fidelity", "full")
        reuse_sim = raw.get("reuse_simulation", False)
        exp_primary = raw.get("expected_primary")
        exp_comp_ratio = raw.get("expected_compute_ratio")

        if not isinstance(hypothesis, str) or not hypothesis.strip():
            raise ValueError("proposal.hypothesis must be a non-empty string")
        if not isinstance(changes, dict) or not changes:
            raise ValueError("proposal.changes must be a non-empty JSON object")
        if parent_id is not None and (not isinstance(parent_id, str) or not parent_id.strip()):
            raise ValueError("proposal.parent_trial_id must be a non-empty string or null")
        if not isinstance(inspirations, list) or any(not isinstance(x, str) or not x.strip() for x in inspirations):
            raise ValueError("proposal.inspiration_trial_ids must be a list of trial_id strings")
        if operator not in PROPOSAL_OPERATORS:
            raise ValueError(f"proposal.operator must be one of {PROPOSAL_OPERATORS}")
        if fidelity not in FIDELITIES:
            raise ValueError(f"proposal.fidelity must be one of {FIDELITIES}")
        if not isinstance(reuse_sim, bool):
            raise ValueError("proposal.reuse_simulation must be a boolean")
        if exp_primary is not None and not is_finite_number(exp_primary):
            raise ValueError("proposal.expected_primary must be a finite number")
        if exp_comp_ratio is not None and (not is_finite_number(exp_comp_ratio) or exp_comp_ratio <= 0):
            raise ValueError("proposal.expected_compute_ratio must be a positive finite number")

        return cls(
            hypothesis=hypothesis.strip(),
            changes=changes,
            parent_trial_id=parent_id.strip() if isinstance(parent_id, str) else None,
            inspiration_trial_ids=list(dict.fromkeys(x.strip() for x in inspirations)),
            operator=operator,
            fidelity=fidelity,
            reuse_simulation=reuse_sim,
            expected_primary=float(exp_primary) if exp_primary is not None else None,
            expected_compute_ratio=float(exp_comp_ratio) if exp_comp_ratio is not None else None,
        )


def validate_proposal_scope(proposal: Proposal, mutable_fields: list[str]) -> None:
    allowed = set(mutable_fields)
    illegal = sorted(key for key in proposal.changes if key not in allowed)
    if illegal:
        raise ValueError(f"Proposal modifies immutable fields: {', '.join(illegal)}")


def validate_proposal_bounds(
    proposal: Proposal,
    param_bounds: dict[str, Any] | None,
    forbidden_ops: list[str] | None = None,
) -> None:
    banned = {str(op).strip() for op in (forbidden_ops or []) if str(op).strip()}
    bounds = param_bounds or {}
    for key, value in proposal.changes.items():
        if isinstance(value, str) and value.strip() in banned:
            raise ValueError(f"Proposal field {key}={value!r} uses a forbidden operator: {sorted(banned)}")
        spec = bounds.get(key)
        if spec is None and "." in key:
            spec = bounds.get(key.rsplit(".", 1)[-1])
        if not isinstance(spec, dict):
            continue
        expected_type = spec.get("type")
        if expected_type == "int":
            if type(value) is not int:
                raise ValueError(f"Proposal field {key}={value!r} violates param_bounds: expected int")
        elif expected_type == "float":
            if not is_finite_number(value):
                raise ValueError(f"Proposal field {key}={value!r} violates param_bounds: expected finite float")
        elif expected_type == "str":
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Proposal field {key}={value!r} violates param_bounds: expected non-empty str")
        elif expected_type == "bool":
            if not isinstance(value, bool):
                raise ValueError(f"Proposal field {key}={value!r} violates param_bounds: expected bool")
        if "enum" in spec and value not in spec["enum"]:
            raise ValueError(f"Proposal field {key}={value!r} violates param_bounds: allowed={spec['enum']}")
        if "min" in spec and (not is_finite_number(value) or value < spec["min"]):
            raise ValueError(f"Proposal field {key}={value!r} violates param_bounds: min={spec['min']}")
        if "max" in spec and (not is_finite_number(value) or value > spec["max"]):
            raise ValueError(f"Proposal field {key}={value!r} violates param_bounds: max={spec['max']}")


@dataclass(frozen=True)
class CampaignPlan:
    schema_version: int
    track: str
    model_family: str
    knowledge_entry_ref: str
    knowledge: dict[str, Any]
    base_hypothesis: str
    baseline_model_ref: str
    dataset_ref: str
    dev_evaluator_ref: str
    holdout_evaluator_ref: str
    base_config: dict[str, Any]
    mutable_fields: list[str]
    budget: dict[str, Any]
    acceptance: dict[str, Any]
    stages: list[str] = field(default_factory=lambda: ["training", "evaluation"])
    base_architecture: dict[str, Any] | None = None
    base_training_recipe: dict[str, Any] = field(default_factory=dict)
    program_ref: str | None = "program.md"
    mcp_tools_ref: str | None = "mcp_tools.md"

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CampaignPlan:
        try:
            raw = json.loads(json.dumps(value, allow_nan=False))
            plan = cls(**raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid campaign.json fields: {exc}") from exc

        if type(plan.schema_version) is not int or plan.schema_version != 1:
            raise ValueError("campaign.json schema_version must be 1")
        if plan.track not in TRACKS:
            raise ValueError(f"Unsupported track {plan.track!r}; expected one of {TRACKS}")
        for req in (
            "model_family",
            "knowledge_entry_ref",
            "base_hypothesis",
            "baseline_model_ref",
            "dataset_ref",
            "dev_evaluator_ref",
            "holdout_evaluator_ref",
        ):
            val = getattr(plan, req)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"{req} must be a non-empty string")
        if plan.dev_evaluator_ref == plan.holdout_evaluator_ref:
            raise ValueError("holdout_evaluator_ref must be isolated from dev_evaluator_ref")

        if not isinstance(plan.knowledge, dict) or plan.knowledge.get("status") != "published":
            raise ValueError("Frozen knowledge snapshot must be a published knowledge_base entry")
        entry_track = plan.knowledge.get("track")
        if entry_track != plan.track:
            raise ValueError(f"Knowledge entry track ({entry_track}) does not match campaign track ({plan.track})")

        if not isinstance(plan.base_config, dict) or not plan.base_config:
            raise ValueError("base_config must be a non-empty JSON object")
        if (
            not isinstance(plan.mutable_fields, list)
            or not plan.mutable_fields
            or any(not isinstance(f, str) or not f.strip() for f in plan.mutable_fields)
        ):
            raise ValueError("mutable_fields must be a non-empty list of dot-path field names")
        if len(set(plan.mutable_fields)) != len(plan.mutable_fields):
            raise ValueError("mutable_fields must not contain duplicates")

        if plan.track == "architecture":
            if not isinstance(plan.base_training_recipe, dict) or not plan.base_training_recipe:
                raise ValueError("architecture track requires a non-empty frozen base_training_recipe")
            overlap = sorted(f for f in plan.mutable_fields if has_path(plan.base_training_recipe, f))
            if overlap:
                raise ValueError(f"architecture track cannot mutate training recipe fields: {', '.join(overlap)}")
        elif plan.track == "hpo":
            if not isinstance(plan.base_architecture, dict) or not plan.base_architecture:
                raise ValueError("hpo track requires a non-empty frozen base_architecture")
            overlap = sorted(f for f in plan.mutable_fields if has_path(plan.base_architecture, f))
            if overlap:
                raise ValueError(f"hpo track cannot mutate architecture fields: {', '.join(overlap)}")

        if not isinstance(plan.stages, list) or not plan.stages:
            raise ValueError("stages must be a non-empty list")

        max_trials = plan.budget.get("max_trials")
        if type(max_trials) is not int or max_trials < 2:
            raise ValueError("budget.max_trials must be an integer >= 2 (trial-000 baseline + >=1 candidate)")
        max_parallel = plan.budget.get("max_parallel_trials", 1)
        if type(max_parallel) is not int or max_parallel < 1:
            raise ValueError("budget.max_parallel_trials must be a positive integer")
        cost_spec = plan.budget.get("cost_metric")
        if not isinstance(cost_spec, dict) or not isinstance(cost_spec.get("name"), str) or not cost_spec["name"].strip():
            raise ValueError("budget.cost_metric.name is required")
        if cost_spec.get("max_total") is not None:
            positive_number(cost_spec["max_total"], "budget.cost_metric.max_total")

        p_spec = plan.acceptance.get("primary_metric")
        if not isinstance(p_spec, dict) or not isinstance(p_spec.get("name"), str) or not p_spec["name"].strip():
            raise ValueError("acceptance.primary_metric.name is required")
        if p_spec.get("direction") not in DIRECTIONS:
            raise ValueError(f"acceptance.primary_metric.direction must be one of {DIRECTIONS}")
        non_negative_number(p_spec.get("min_gain", 0.0), "acceptance.primary_metric.min_gain")
        non_negative_number(p_spec.get("tie_tolerance", 0.0), "acceptance.primary_metric.tie_tolerance")
        if p_spec.get("holdout_target") is not None and not is_finite_number(p_spec["holdout_target"]):
            raise ValueError("acceptance.primary_metric.holdout_target must be a finite number")

        c_spec = plan.acceptance.get("compute_metric")
        if not isinstance(c_spec, dict) or not isinstance(c_spec.get("name"), str) or not c_spec["name"].strip():
            raise ValueError("acceptance.compute_metric.name is required")
        if c_spec.get("direction", "minimize") not in DIRECTIONS:
            raise ValueError(f"acceptance.compute_metric.direction must be one of {DIRECTIONS}")
        for b_key in ("max_value", "max_ratio"):
            if c_spec.get(b_key) is not None:
                positive_number(c_spec[b_key], f"acceptance.compute_metric.{b_key}")

        guardrails = plan.acceptance.get("guardrails")
        if guardrails is not None:
            if not isinstance(guardrails, dict):
                raise ValueError("acceptance.guardrails must be an object")
            for g_dir in ("max_metrics", "min_metrics"):
                bounds = guardrails.get(g_dir, {})
                if not isinstance(bounds, dict):
                    raise ValueError(f"acceptance.guardrails.{g_dir} must be an object")
                for m_name, bound in bounds.items():
                    if not is_finite_number(bound):
                        raise ValueError(f"Guardrail bound for {m_name} must be a finite number")
        return plan

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
