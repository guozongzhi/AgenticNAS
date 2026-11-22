from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from typing import Any, Protocol

from .spec_utils import DIRECTIONS, has_path, is_finite_number


STAGES = ('simulation', 'training', 'evaluation')
TERMINAL = {'succeeded', 'failed', 'cancelled', 'budget_exhausted'}
EVALUATION_SCOPES = ('dev', 'holdout')
TRIAL_DECISIONS = ('baseline', 'keep', 'discard', 'crash', 'cancelled')
TRACKS = ('architecture', 'hpo', 'data_recipe')
EXECUTION_MODES = ('managed', 'external_mcp')


def positive_number(value: Any, name: str) -> None:
    if not is_finite_number(value) or value <= 0:
        raise ValueError(f'{name} must be a finite positive number')


def non_negative_number(value: Any, name: str) -> None:
    if not is_finite_number(value) or value < 0:
        raise ValueError(f'{name} must be a finite non-negative number')


def validate_knowledge(knowledge: Any) -> None:
    if not isinstance(knowledge, dict):
        raise ValueError('knowledge must be an object')
    for name in ('id', 'revision', 'text'):
        if not isinstance(knowledge.get(name), str) or not knowledge[name].strip():
            raise ValueError(f'knowledge.{name} is required')
    if knowledge.get('status') != 'published':
        raise ValueError('Knowledge must be published')
    uses = knowledge.get('approved_uses')
    if not isinstance(uses, list) or 'training' not in uses:
        raise ValueError('Knowledge must allow training use')


def validate_mock_settings(mock: Any) -> None:
    if mock is None:
        return
    if not isinstance(mock, dict):
        raise ValueError('mock must be an object or null')
    duration = mock['duration_seconds']
    non_negative_number(duration, 'mock.duration_seconds')
    for name in ('fail_stage', 'lose_submit_reply_stage'):
        if mock.get(name) not in (None, *STAGES):
            raise ValueError(f'Invalid mock {name}')
    if 'stop_unsupported' in mock and not isinstance(mock['stop_unsupported'], bool):
        raise ValueError('mock.stop_unsupported must be a boolean')
    for key in ('eval_fixture', 'stage_usage'):
        val = mock.get(key)
        if val is not None and not isinstance(val, dict):
            raise ValueError(f'mock.{key} must be an object')


def validate_compute_acceptance(acceptance: dict[str, Any]) -> None:
    for key in ('max_inference_flops_m', 'max_flops_ratio'):
        if acceptance.get(key) is not None:
            positive_number(acceptance[key], f'acceptance.{key}')
    compute_metric = acceptance.get('compute_metric')
    if compute_metric is not None:
        if not isinstance(compute_metric, dict):
            raise ValueError('acceptance.compute_metric must be an object')
        if not isinstance(compute_metric.get('name'), str) or not compute_metric['name'].strip():
            raise ValueError('acceptance.compute_metric.name is required')
        direction = compute_metric.get('direction', 'minimize')
        if direction not in DIRECTIONS:
            raise ValueError(f'Invalid compute_metric.direction: {direction}')
        for bound_key in ('max_value', 'max_ratio'):
            if compute_metric.get(bound_key) is not None:
                positive_number(compute_metric[bound_key], f'acceptance.compute_metric.{bound_key}')


def validate_primary_metric_spec(primary_metric: Any) -> None:
    if not isinstance(primary_metric, dict):
        raise ValueError('acceptance.primary_metric must be an object')
    if not isinstance(primary_metric.get('name'), str) or not primary_metric['name'].strip():
        raise ValueError('acceptance.primary_metric.name is required')
    direction = primary_metric.get('direction', 'maximize')
    if direction not in DIRECTIONS:
        raise ValueError(f'Invalid primary_metric.direction: {direction}')
    non_negative_number(primary_metric.get('min_gain', 0.0), 'acceptance.primary_metric.min_gain')
    non_negative_number(primary_metric.get('tie_tolerance', 0.0), 'acceptance.primary_metric.tie_tolerance')
    if primary_metric.get('holdout_target') is not None and not is_finite_number(primary_metric['holdout_target']):
        raise ValueError('acceptance.primary_metric.holdout_target must be a finite number')
    if primary_metric.get('holdout_min_gain') is not None:
        non_negative_number(primary_metric['holdout_min_gain'], 'acceptance.primary_metric.holdout_min_gain')


def validate_cost_metric_spec(budget: dict[str, Any]) -> None:
    if budget.get('max_gpu_seconds') is not None:
        positive_number(budget['max_gpu_seconds'], 'budget.max_gpu_seconds')
    cost_metric = budget.get('cost_metric')
    if cost_metric is not None:
        if not isinstance(cost_metric, dict):
            raise ValueError('budget.cost_metric must be an object')
        if not isinstance(cost_metric.get('name'), str) or not cost_metric['name'].strip():
            raise ValueError('budget.cost_metric.name is required')
        if cost_metric.get('max_total') is not None:
            positive_number(cost_metric['max_total'], 'budget.cost_metric.max_total')


@dataclass(frozen=True)
class Plan:
    schema_version: int
    knowledge: dict[str, Any]
    hypothesis: str
    baseline_model_ref: str
    dataset_ref: str
    evaluator_ref: str
    training_recipe: dict[str, Any]
    budget: dict[str, Any]
    acceptance: dict[str, Any]
    mock: dict[str, Any] | None = None
    architecture: dict[str, Any] | None = None
    evaluation_scope: str = 'holdout'
    reuse_dataset_ref: str | None = None
    reuse_model_ref: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Plan:
        try:
            plan = cls(**json.loads(json.dumps(value, allow_nan=False)))
            if type(plan.schema_version) is not int or plan.schema_version != 1:
                raise ValueError('Unsupported plan schema_version')
            for name in ('hypothesis', 'baseline_model_ref', 'dataset_ref', 'evaluator_ref'):
                if not isinstance(getattr(plan, name), str) or not getattr(plan, name).strip():
                    raise ValueError(f'{name} is required')
            validate_knowledge(plan.knowledge)
            if not isinstance(plan.training_recipe, dict) or not plan.training_recipe:
                raise ValueError('training_recipe must be a non-empty object')
            if plan.architecture is not None and (not isinstance(plan.architecture, dict) or not plan.architecture):
                raise ValueError('architecture must be a non-empty object or null')
            limit = plan.budget['max_tasks']
            if type(limit) is not int or limit < 1:
                raise ValueError('max_tasks must be a positive integer')
            positive_number(plan.budget['wall_seconds'], 'wall_seconds')
            validate_cost_metric_spec(plan.budget)
            cases, minimum = plan.acceptance['total_cases'], plan.acceptance['min_correct']
            if type(cases) is not int or type(minimum) is not int or not 0 <= minimum <= cases or cases < 1:
                raise ValueError('Invalid acceptance counts')
            validate_compute_acceptance(plan.acceptance)
            if plan.evaluation_scope not in EVALUATION_SCOPES:
                raise ValueError(f'Invalid evaluation_scope: {plan.evaluation_scope}')
            for ref_name in ('reuse_dataset_ref', 'reuse_model_ref'):
                ref_value = getattr(plan, ref_name)
                if ref_value is not None and (not isinstance(ref_value, str) or not ref_value.strip()):
                    raise ValueError(f'{ref_name} must be a non-empty string or null')
            validate_mock_settings(plan.mock)
            return plan
        except (KeyError, TypeError) as error:
            raise ValueError(f'Invalid plan fields: {error}') from error

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Proposal:
    hypothesis: str
    changes: dict[str, Any]
    reuse_simulation: bool = False
    complexity_delta: float | None = None
    mock_overrides: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Proposal:
        try:
            proposal = cls(**json.loads(json.dumps(value, allow_nan=False)))
        except (KeyError, TypeError) as error:
            raise ValueError(f'Invalid proposal fields: {error}') from error
        if not isinstance(proposal.hypothesis, str) or not proposal.hypothesis.strip():
            raise ValueError('proposal.hypothesis is required')
        if not isinstance(proposal.changes, dict) or not proposal.changes:
            raise ValueError('proposal.changes must be a non-empty object')
        if not isinstance(proposal.reuse_simulation, bool):
            raise ValueError('proposal.reuse_simulation must be a boolean')
        if proposal.complexity_delta is not None and not is_finite_number(proposal.complexity_delta):
            raise ValueError('proposal.complexity_delta must be a finite number')
        if proposal.mock_overrides is not None and not isinstance(proposal.mock_overrides, dict):
            raise ValueError('proposal.mock_overrides must be an object or null')
        return proposal

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_proposal_scope(proposal: Proposal, mutable_fields: list[str]) -> None:
    allowed = set(mutable_fields)
    disallowed = sorted(key for key in proposal.changes if key not in allowed)
    if disallowed:
        raise ValueError(f'Proposal modifies immutable fields: {", ".join(disallowed)}')


def validate_proposal_bounds(proposal: Proposal, param_bounds: dict[str, Any] | None) -> None:
    if not param_bounds:
        return
    for key, value in proposal.changes.items():
        spec = param_bounds.get(key)
        if spec is None and '.' in key:
            spec = param_bounds.get(key.rsplit('.', 1)[-1])
        if not isinstance(spec, dict):
            continue
        expected_type = spec.get('type')
        if expected_type == 'int':
            if type(value) is not int:
                raise ValueError(f'Proposal field {key}={value!r} violates param_bounds: expected int')
        elif expected_type == 'float':
            if not is_finite_number(value):
                raise ValueError(f'Proposal field {key}={value!r} violates param_bounds: expected finite float')
        elif expected_type == 'str':
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'Proposal field {key}={value!r} violates param_bounds: expected non-empty str')
        elif expected_type == 'bool':
            if not isinstance(value, bool):
                raise ValueError(f'Proposal field {key}={value!r} violates param_bounds: expected bool')
        if 'enum' in spec and value not in spec['enum']:
            raise ValueError(f'Proposal field {key}={value!r} violates param_bounds: allowed={spec["enum"]}')
        if 'min' in spec and (not is_finite_number(value) or value < spec['min']):
            raise ValueError(f'Proposal field {key}={value!r} violates param_bounds: min={spec["min"]}')
        if 'max' in spec and (not is_finite_number(value) or value > spec['max']):
            raise ValueError(f'Proposal field {key}={value!r} violates param_bounds: max={spec["max"]}')


@dataclass(frozen=True)
class CampaignPlan:
    schema_version: int
    knowledge: dict[str, Any]
    base_hypothesis: str
    dev_evaluator_ref: str
    holdout_evaluator_ref: str
    mutable_fields: list[str]
    budget: dict[str, Any]
    acceptance: dict[str, Any]
    baseline_model_ref: str = 'baseline-model'
    dataset_ref: str = 'default-dataset'
    base_training_recipe: dict[str, Any] = field(default_factory=dict)
    base_architecture: dict[str, Any] | None = None
    base_config: dict[str, Any] | None = None
    track: str = 'data_recipe'
    execution_mode: str = 'managed'
    model_family: str | None = None
    stages: list[str] | None = None
    kb_ref: str | None = None
    program_ref: str | None = None
    program_text: str | None = None
    mcp_tools_ref: str | None = None
    mock: dict[str, Any] | None = None
    proposals: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CampaignPlan:
        try:
            plan = cls(**json.loads(json.dumps(value, allow_nan=False)))
            if type(plan.schema_version) is not int or plan.schema_version != 1:
                raise ValueError('Unsupported campaign schema_version')
            if plan.track not in TRACKS:
                raise ValueError(f'Unsupported track: {plan.track}')
            if plan.execution_mode not in EXECUTION_MODES:
                raise ValueError(f'Unsupported execution_mode: {plan.execution_mode}')
            for name in ('base_hypothesis', 'dev_evaluator_ref', 'holdout_evaluator_ref',
                         'baseline_model_ref', 'dataset_ref'):
                if not isinstance(getattr(plan, name), str) or not getattr(plan, name).strip():
                    raise ValueError(f'{name} is required')
            if plan.dev_evaluator_ref == plan.holdout_evaluator_ref:
                raise ValueError('holdout_evaluator_ref must be isolated from dev_evaluator_ref')
            validate_knowledge(plan.knowledge)
            kb_track = plan.knowledge.get('track')
            if kb_track is not None and kb_track != plan.track:
                raise ValueError(f'Knowledge track ({kb_track}) does not match campaign track ({plan.track})')

            has_generic_config = isinstance(plan.base_config, dict) and bool(plan.base_config)
            if plan.base_config is not None and not has_generic_config:
                raise ValueError('base_config must be a non-empty object or null')
            if plan.track == 'architecture':
                arch_src = plan.base_config if has_generic_config else plan.base_architecture
                if not isinstance(arch_src, dict) or not arch_src:
                    raise ValueError('base_architecture or base_config is required for architecture track')
                if plan.execution_mode == 'managed' and (not isinstance(plan.base_training_recipe, dict) or not plan.base_training_recipe):
                    raise ValueError('base_training_recipe must be a non-empty object in managed mode')
            else:
                recipe_src = plan.base_config if has_generic_config else plan.base_training_recipe
                if not isinstance(recipe_src, dict) or not recipe_src:
                    raise ValueError('base_training_recipe or base_config must be a non-empty object')

            if (not isinstance(plan.mutable_fields, list) or not plan.mutable_fields
                    or any(not isinstance(item, str) or not item.strip() for item in plan.mutable_fields)):
                raise ValueError('mutable_fields must be a non-empty list of field names')
            if len(set(plan.mutable_fields)) != len(plan.mutable_fields):
                raise ValueError('mutable_fields must not contain duplicates')

            if plan.track == 'architecture' and plan.base_training_recipe:
                overlap = sorted(f for f in plan.mutable_fields if has_path(plan.base_training_recipe, f))
                if overlap:
                    raise ValueError(f'Architecture track cannot mutate training recipe fields: {", ".join(overlap)}')
            elif plan.track != 'architecture' and plan.base_architecture:
                overlap = sorted(f for f in plan.mutable_fields if has_path(plan.base_architecture, f))
                if overlap:
                    raise ValueError(f'{plan.track} track cannot mutate architecture fields: {", ".join(overlap)}')

            max_trials = plan.budget['max_trials']
            if type(max_trials) is not int or max_trials < 1:
                raise ValueError('budget.max_trials must be a positive integer')
            max_tasks_per_trial = plan.budget.get('max_tasks_per_trial', 3)
            if type(max_tasks_per_trial) is not int or max_tasks_per_trial < 1:
                raise ValueError('budget.max_tasks_per_trial must be a positive integer')
            if plan.execution_mode == 'managed' or plan.budget.get('per_trial_wall_seconds') is not None:
                positive_number(plan.budget['per_trial_wall_seconds'], 'budget.per_trial_wall_seconds')
            if plan.execution_mode == 'managed' or plan.budget.get('total_wall_seconds') is not None:
                positive_number(plan.budget['total_wall_seconds'], 'budget.total_wall_seconds')
            validate_cost_metric_spec(plan.budget)

            if 'primary_metric' in plan.acceptance:
                validate_primary_metric_spec(plan.acceptance['primary_metric'])
            else:
                dev_cases = plan.acceptance['dev_total_cases']
                holdout_cases = plan.acceptance['holdout_total_cases']
                holdout_min = plan.acceptance['holdout_min_correct']
                if type(dev_cases) is not int or dev_cases < 1:
                    raise ValueError('acceptance.dev_total_cases must be a positive integer')
                if type(holdout_cases) is not int or type(holdout_min) is not int or not 0 <= holdout_min <= holdout_cases or holdout_cases < 1:
                    raise ValueError('Invalid holdout acceptance counts')
                non_negative_number(plan.acceptance.get('min_delta', 1), 'acceptance.min_delta')
                non_negative_number(plan.acceptance.get('tie_tolerance', 0.0), 'acceptance.tie_tolerance')

            validate_compute_acceptance(plan.acceptance)
            guardrails = plan.acceptance.get('guardrails')
            if guardrails is not None:
                if not isinstance(guardrails, dict):
                    raise ValueError('acceptance.guardrails must be an object')
                for direction in ('max_metrics', 'min_metrics'):
                    if direction in guardrails:
                        bounds = guardrails[direction]
                        if not isinstance(bounds, dict):
                            raise ValueError(f'acceptance.guardrails.{direction} must be an object')
                        for metric_name, bound in bounds.items():
                            if not is_finite_number(bound):
                                raise ValueError(f'Invalid guardrail bound for {metric_name}')

            if plan.stages is not None:
                if not isinstance(plan.stages, list) or not plan.stages or any(not isinstance(s, str) or not s.strip() for s in plan.stages):
                    raise ValueError('stages must be a non-empty list of stage names')
            for opt_str in ('kb_ref', 'program_ref', 'mcp_tools_ref', 'model_family'):
                val = getattr(plan, opt_str)
                if val is not None and (not isinstance(val, str) or not val.strip()):
                    raise ValueError(f'{opt_str} must be a non-empty string or null')
            if plan.program_text is not None and not isinstance(plan.program_text, str):
                raise ValueError('program_text must be a string or null')
            validate_mock_settings(plan.mock)
            if not isinstance(plan.proposals, list):
                raise ValueError('proposals must be a list')
            for raw in plan.proposals:
                if not isinstance(raw, dict):
                    raise ValueError('Each proposal must be an object')
                Proposal.from_dict(raw)
            return plan
        except (KeyError, TypeError) as error:
            raise ValueError(f'Invalid campaign plan fields: {error}') from error

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskState:
    stage: str
    request_id: str
    status: str = 'pending'
    job_id: str | None = None
    remote_status: str | None = None
    result: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, float] = field(default_factory=dict)
    log_path: str | None = None
    stop_sent_at: float | None = None
    stop_unsupported: bool = False


@dataclass
class RunState:
    run_id: str
    plan: dict[str, Any]
    knowledge_sha256: str
    created_at: float
    tasks: list[dict[str, Any]]
    status: str = 'running'
    attempted_tasks: int = 0
    stop_reason: str | None = None
    error: str | None = None
    compute_usage: dict[str, float] = field(default_factory=lambda: {'gpu_seconds': 0.0, 'train_tflops': 0.0})
    report: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrialRecord:
    trial_id: str
    index: int
    parent_trial_id: str | None
    is_baseline: bool
    hypothesis: str
    changes: dict[str, Any]
    training_recipe: dict[str, Any]
    reuse_simulation: bool
    complexity_score: float
    run_id: str | None
    started_at: float
    architecture: dict[str, Any] | None = None
    candidate_config: dict[str, Any] | None = None
    run_status: str = 'running'
    decision: str | None = None
    decision_reason: str | None = None
    primary_value: float | None = None
    gain: float | None = None
    gain_pct: float | None = None
    compute_value: float | None = None
    compute_ratio: float | None = None
    cost_value: float = 0.0
    cumulative_cost: float = 0.0
    dev_correct: int | None = None
    dev_total: int | None = None
    gain_vs_baseline: int | None = None
    gain_pp: float | None = None
    baseline_inference_flops_m: float | None = None
    candidate_inference_flops_m: float | None = None
    flops_ratio: float | None = None
    gpu_seconds: float = 0.0
    train_tflops: float = 0.0
    cumulative_gpu_seconds: float = 0.0
    dev_metrics: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    external_jobs: list[dict[str, Any]] = field(default_factory=list)
    dataset_ref: str | None = None
    model_ref: str | None = None
    finished_at: float | None = None
    duration_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CampaignState:
    campaign_id: str
    plan: dict[str, Any]
    knowledge_sha256: str
    program_sha256: str | None
    created_at: float
    status: str = 'running'
    stop_reason: str | None = None
    error: str | None = None
    incumbent_trial_id: str | None = None
    active_trial_id: str | None = None
    holdout_run_id: str | None = None
    holdout_report: dict[str, Any] | None = None
    baseline_primary_value: float | None = None
    baseline_compute_value: float | None = None
    total_cost: float = 0.0
    total_gpu_seconds: float = 0.0
    total_train_tflops: float = 0.0
    trials: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ToolClient(Protocol):
    """Replace this client with a real MCP SDK client or ConfigurableMCPAdapter."""

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]: ...


class Proposer(Protocol):
    """Pluggable hypothesis proposer (scripted, classical HPO, or external Coding Agent)."""

    def propose(self, context: dict[str, Any]) -> Proposal | None: ...
