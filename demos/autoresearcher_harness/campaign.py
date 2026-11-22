from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import time
from typing import Any
import uuid

from .contracts import (
    CampaignPlan,
    CampaignState,
    Proposal,
    Proposer,
    TERMINAL,
    ToolClient,
    TrialRecord,
    validate_proposal_bounds,
    validate_proposal_scope,
)
from .engine import Harness
from .knowledge_base import KnowledgeBase
from .spec_utils import (
    apply_changes,
    compute_gain,
    count_config_diffs,
    is_finite_number,
    meets_holdout_target,
    normalize_compute_metric,
    normalize_cost_metric,
    normalize_primary_metric,
)
from .store import Store, write_json, write_text


CAMPAIGN_TERMINAL = TERMINAL


def _tsv_cell(value: Any) -> str:
    if value is None or value == '':
        return '-'
    return str(value).replace('\t', ' ').replace('\r', ' ').replace('\n', ' ').strip() or '-'


def format_diff(changes: dict[str, Any]) -> str:
    if not changes:
        return '-'
    return ';'.join(f'{key}={json.dumps(changes[key], ensure_ascii=False)}' for key in sorted(changes))


def render_results_tsv(trials: list[dict[str, Any]], plan: dict[str, Any] | None = None) -> str:
    if plan:
        p_spec = normalize_primary_metric(plan['acceptance'])
        c_spec = normalize_compute_metric(plan['acceptance'])
        cost_spec = normalize_cost_metric(plan['budget'])
        header = '\t'.join([
            'trial_id',
            'parent_trial',
            'status',
            f"primary({p_spec['name']})",
            'gain',
            f"compute({c_spec['name']})",
            'compute_ratio',
            f"cost({cost_spec['name']})",
            'cum_cost',
            'complexity',
            'diff',
            'hypothesis',
        ])
        legacy_counts = p_spec.get('legacy_counts', False)
    else:
        header = (
            'trial_id\tparent_trial\tstatus\tprimary\tgain\t'
            'compute\tcompute_ratio\tcost\tcum_cost\tcomplexity\tdiff\thypothesis'
        )
        legacy_counts = False

    lines = [header]
    for trial in trials:
        if trial['decision'] is None:
            continue
        if legacy_counts and trial.get('dev_correct') is not None and trial.get('dev_total') is not None:
            primary_str = f"{trial['dev_correct']}/{trial['dev_total']}"
            gain_val = trial.get('gain_vs_baseline')
            gain_pct = trial.get('gain_pp')
            gain_str = f"{gain_val:+d} ({gain_pct:+.1f}pp)" if gain_val is not None and gain_pct is not None else '-'
        else:
            p_val = trial.get('primary_value')
            primary_str = f'{p_val:.4g}' if is_finite_number(p_val) else '-'
            g_val = trial.get('gain')
            g_pct = trial.get('gain_pct')
            if is_finite_number(g_val):
                gain_str = f'{g_val:+.4g} ({g_pct:+.1f}%)' if is_finite_number(g_pct) else f'{g_val:+.4g}'
            else:
                gain_str = '-'

        comp_val = trial.get('compute_value') if trial.get('compute_value') is not None else trial.get('candidate_inference_flops_m')
        comp_ratio = trial.get('compute_ratio') if trial.get('compute_ratio') is not None else trial.get('flops_ratio')
        cost_val = trial.get('cost_value') if trial.get('cost_value') else trial.get('gpu_seconds', 0.0)
        cum_cost = trial.get('cumulative_cost') if trial.get('cumulative_cost') else trial.get('cumulative_gpu_seconds', 0.0)

        lines.append('\t'.join([
            _tsv_cell(trial['trial_id']),
            _tsv_cell(trial['parent_trial_id']),
            _tsv_cell(trial['decision']),
            _tsv_cell(primary_str),
            _tsv_cell(gain_str),
            f'{comp_val:.2f}' if is_finite_number(comp_val) else '-',
            f'{comp_ratio:.2f}x' if is_finite_number(comp_ratio) else '-',
            f'{cost_val:.2f}' if is_finite_number(cost_val) else '0.00',
            f'{cum_cost:.2f}' if is_finite_number(cum_cost) else '0.00',
            f"{trial['complexity_score']:.1f}",
            _tsv_cell(format_diff(trial['changes'])),
            _tsv_cell(trial['hypothesis']),
        ]))
    return '\n'.join(lines) + '\n'


def compute_complexity(
    base_target: dict[str, Any],
    candidate_target: dict[str, Any],
    parent_complexity: float,
    complexity_delta: float | None,
) -> float:
    if complexity_delta is not None:
        return round(parent_complexity + float(complexity_delta), 4)
    return count_config_diffs(base_target, candidate_target)


def check_guardrails(metrics: dict[str, Any], guardrails: dict[str, Any] | None) -> str | None:
    if not guardrails:
        return None
    for metric_name, max_bound in guardrails.get('max_metrics', {}).items():
        if metric_name not in metrics:
            return f'missing guardrail metric: {metric_name}'
        value = metrics[metric_name]
        if not is_finite_number(value) or value > max_bound:
            return f'guardrail violated: {metric_name}={value} > {max_bound}'
    for metric_name, min_bound in guardrails.get('min_metrics', {}).items():
        if metric_name not in metrics:
            return f'missing guardrail metric: {metric_name}'
        value = metrics[metric_name]
        if not is_finite_number(value) or value < min_bound:
            return f'guardrail violated: {metric_name}={value} < {min_bound}'
    return None


def check_compute_budget(
    compute_value: float | None,
    compute_ratio: float | None,
    compute_spec: dict[str, Any],
) -> str | None:
    name = compute_spec['name']
    max_val = compute_spec.get('max_value')
    if max_val is not None:
        if compute_value is None:
            return f'missing compute metric {name} for compute budget check'
        if compute_value > max_val:
            return f'compute budget exceeded: {name}={compute_value} > {max_val}'
    max_ratio = compute_spec.get('max_ratio')
    if max_ratio is not None:
        if compute_ratio is None:
            return f'missing compute_ratio ({name}) for compute budget check'
        if compute_ratio > max_ratio:
            return f'compute budget exceeded: {name}_ratio={compute_ratio} > {max_ratio}'
    return None


def _base_target_config(plan: dict[str, Any]) -> dict[str, Any]:
    if plan.get('base_config'):
        return copy.deepcopy(plan['base_config'])
    if plan['track'] == 'architecture':
        return copy.deepcopy(plan['base_architecture'] or {})
    return copy.deepcopy(plan['base_training_recipe'] or {})


def _incumbent_target_config(plan: dict[str, Any], incumbent: dict[str, Any]) -> dict[str, Any]:
    if incumbent.get('candidate_config') is not None:
        return copy.deepcopy(incumbent['candidate_config'])
    if plan['track'] == 'architecture':
        return copy.deepcopy(incumbent.get('architecture') or plan.get('base_architecture') or {})
    return copy.deepcopy(incumbent.get('training_recipe') or plan.get('base_training_recipe') or {})


def _trial_mock_settings(
    base_mock: dict[str, Any] | None,
    overrides: dict[str, Any] | None = None,
    eval_fixture_key: str | None = None,
) -> dict[str, Any] | None:
    if base_mock is None and overrides is None:
        return None
    merged = {
        key: value for key, value in (base_mock or {'duration_seconds': 0}).items()
        if key not in {'baseline_eval_fixture', 'holdout_eval_fixture'}
    }
    if eval_fixture_key and base_mock and base_mock.get(eval_fixture_key) is not None:
        merged['eval_fixture'] = base_mock[eval_fixture_key]
    if overrides:
        for key, value in overrides.items():
            if key not in {'baseline_eval_fixture', 'holdout_eval_fixture'}:
                merged[key] = value
    return merged


class ScriptedProposer:
    """Deterministic offline proposer reading proposals from CampaignPlan."""

    def __init__(self, proposals: list[dict[str, Any]]) -> None:
        self.proposals = [Proposal.from_dict(item) for item in proposals]

    def propose(self, context: dict[str, Any]) -> Proposal | None:
        candidate_attempts = sum(1 for item in context['history'] if not item['is_baseline'])
        if candidate_attempts >= len(self.proposals):
            return None
        return self.proposals[candidate_attempts]


class CampaignRunner:
    def __init__(
        self,
        output: Path,
        client: ToolClient | None = None,
        proposer: Proposer | None = None,
        stop_retry_seconds: float = 5.0,
    ) -> None:
        self.harness = Harness(output, client=client, stop_retry_seconds=stop_retry_seconds)
        self.store: Store = self.harness.store
        self.root = self.store.root
        self.proposer = proposer

    def create(
        self,
        value: dict[str, Any],
        plan_dir: Path | None = None,
        kb_root: Path | None = None,
        kb_id: str | None = None,
        kb_revision: str | None = None,
    ) -> str:
        raw = json.loads(json.dumps(value, allow_nan=False))
        resolved_kb_id = kb_id or raw.get('kb_ref')
        if resolved_kb_id and kb_root is not None:
            kb = KnowledgeBase(kb_root)
            raw['knowledge'] = kb.freeze_snapshot(resolved_kb_id, revision=kb_revision)
            raw['kb_ref'] = resolved_kb_id
        if raw.get('program_text') is None and isinstance(raw.get('program_ref'), str) and plan_dir is not None:
            candidate_path = (plan_dir / raw['program_ref']).resolve()
            if candidate_path.is_file():
                raw['program_text'] = candidate_path.read_text(encoding='utf-8')
        plan = CampaignPlan.from_dict(raw).to_dict()
        campaign_id = 'cmp-' + uuid.uuid4().hex
        knowledge_bytes = json.dumps(plan['knowledge'], ensure_ascii=False, sort_keys=True).encode('utf-8')
        knowledge_sha256 = hashlib.sha256(knowledge_bytes).hexdigest()
        program_sha256 = None
        if plan.get('program_text'):
            program_sha256 = hashlib.sha256(plan['program_text'].encode('utf-8')).hexdigest()
        state = CampaignState(
            campaign_id=campaign_id,
            plan=plan,
            knowledge_sha256=knowledge_sha256,
            program_sha256=program_sha256,
            created_at=time.time(),
        ).to_dict()
        self.store.create_campaign(state)
        self.store.event(campaign_id, 'campaign_created', {
            'track': plan['track'],
            'execution_mode': plan['execution_mode'],
            'model_family': plan.get('model_family') or (plan['knowledge'].get('scope') or {}).get('model_family'),
            'kb_ref': plan.get('kb_ref'),
            'knowledge_sha256': knowledge_sha256,
            'program_sha256': program_sha256,
            'mutable_fields': plan['mutable_fields'],
            'max_trials': plan['budget']['max_trials'],
            'primary_metric': normalize_primary_metric(plan['acceptance'])['name'],
            'compute_metric': normalize_compute_metric(plan['acceptance'])['name'],
            'cost_metric': normalize_cost_metric(plan['budget'])['name'],
        })
        return campaign_id

    def status(self, campaign_id: str) -> dict[str, Any]:
        return self.store.load_campaign(campaign_id)

    def events(self, campaign_id: str) -> list[dict[str, Any]]:
        return self.store.events(self.status(campaign_id)['campaign_id'])

    def request_stop(self, campaign_id: str) -> None:
        campaign = self.status(campaign_id)
        if campaign['status'] in CAMPAIGN_TERMINAL:
            return
        self.store.request_campaign_stop(campaign['campaign_id'])
        self.store.event(campaign['campaign_id'], 'campaign_stop_requested', {})

    def _proposer_for(self, campaign: dict[str, Any]) -> Proposer:
        if self.proposer is not None:
            return self.proposer
        return ScriptedProposer(campaign['plan'].get('proposals', []))

    @staticmethod
    def _find_trial(campaign: dict[str, Any], trial_id: str | None) -> dict[str, Any] | None:
        if trial_id is None:
            return None
        return next((item for item in campaign['trials'] if item['trial_id'] == trial_id), None)

    def _build_context(self, campaign: dict[str, Any]) -> dict[str, Any]:
        plan = campaign['plan']
        p_spec = normalize_primary_metric(plan['acceptance'])
        c_spec = normalize_compute_metric(plan['acceptance'])
        cost_spec = normalize_cost_metric(plan['budget'])
        incumbent = self._find_trial(campaign, campaign['incumbent_trial_id'])

        max_cost = cost_spec.get('max_total')
        used_cost = round(float(campaign.get('total_cost') or campaign.get('total_gpu_seconds', 0.0)), 4)
        remaining_cost = max(0.0, round(max_cost - used_cost, 4)) if max_cost is not None else None
        total_wall = plan['budget'].get('total_wall_seconds')
        remaining_wall = max(0.0, round(total_wall - (time.time() - campaign['created_at']), 2)) if total_wall else None

        frozen_fields = (
            {'training_recipe': dict(plan['base_training_recipe'])}
            if plan['track'] == 'architecture'
            else ({'architecture': dict(plan['base_architecture'])} if plan.get('base_architecture') else {})
        )
        return {
            'campaign_id': campaign['campaign_id'],
            'status': campaign['status'],
            'execution_mode': plan.get('execution_mode', 'managed'),
            'track': plan['track'],
            'model_family': plan.get('model_family') or (plan['knowledge'].get('scope') or {}).get('model_family'),
            'stages': plan.get('stages'),
            'kb_ref': plan.get('kb_ref'),
            'program_ref': plan.get('program_ref'),
            'mcp_tools_ref': plan.get('mcp_tools_ref'),
            'program_text': plan.get('program_text'),
            'knowledge': plan['knowledge'],
            'mutable_fields': list(plan['mutable_fields']),
            'param_bounds': dict((plan['knowledge'].get('scope') or {}).get('param_bounds') or {}),
            'frozen_fields': frozen_fields,
            'base_config': _base_target_config(plan),
            'base_architecture': dict(plan['base_architecture']) if plan.get('base_architecture') else None,
            'base_training_recipe': dict(plan['base_training_recipe']),
            'dev_evaluator_ref': plan['dev_evaluator_ref'],
            'holdout_evaluator_ref': plan['holdout_evaluator_ref'],
            'primary_metric': p_spec,
            'compute_metric': c_spec,
            'cost_metric': cost_spec,
            'compute_limits': {
                'compute_metric': c_spec['name'],
                'max_value': c_spec.get('max_value'),
                'max_ratio': c_spec.get('max_ratio'),
                'max_inference_flops_m': plan['acceptance'].get('max_inference_flops_m'),
                'max_flops_ratio': plan['acceptance'].get('max_flops_ratio'),
                'guardrails': plan['acceptance'].get('guardrails'),
            },
            'remaining_budget': {
                'remaining_trials': max(0, plan['budget']['max_trials'] - len(campaign['trials'])),
                'cost_metric': cost_spec['name'],
                'cost_used': used_cost,
                'remaining_cost': remaining_cost,
                'remaining_gpu_seconds': remaining_cost if cost_spec['name'] == 'gpu_seconds' else None,
                'remaining_wall_seconds': remaining_wall,
                'total_gpu_seconds_used': round(campaign.get('total_gpu_seconds', 0.0), 3),
                'total_train_tflops_used': round(campaign.get('total_train_tflops', 0.0), 3),
            },
            'active_trial_id': campaign['active_trial_id'],
            'incumbent': {
                'trial_id': incumbent['trial_id'],
                'primary_value': incumbent.get('primary_value'),
                'gain': incumbent.get('gain'),
                'gain_pct': incumbent.get('gain_pct'),
                'compute_value': incumbent.get('compute_value'),
                'compute_ratio': incumbent.get('compute_ratio'),
                'dev_correct': incumbent['dev_correct'],
                'dev_total': incumbent['dev_total'],
                'gain_vs_baseline': incumbent.get('gain_vs_baseline'),
                'gain_pp': incumbent.get('gain_pp'),
                'candidate_inference_flops_m': incumbent.get('candidate_inference_flops_m'),
                'flops_ratio': incumbent.get('flops_ratio'),
                'dev_metrics': incumbent['dev_metrics'],
                'complexity_score': incumbent['complexity_score'],
                'candidate_config': _incumbent_target_config(plan, incumbent),
                'architecture': dict(incumbent['architecture']) if incumbent.get('architecture') else None,
                'training_recipe': dict(incumbent['training_recipe']),
                'artifacts': dict(incumbent.get('artifacts') or {}),
                'dataset_ref': incumbent['dataset_ref'],
                'model_ref': incumbent['model_ref'],
            } if incumbent else None,
            'history': [dict(item) for item in campaign['trials']],
            'results_tsv': render_results_tsv(campaign['trials'], plan),
            'remaining_trials': max(0, plan['budget']['max_trials'] - len(campaign['trials'])),
        }

    def get_context(self, campaign_id: str) -> dict[str, Any]:
        """Return compact state, KB priors/anti-patterns, bounds, limits, and results.tsv for an external Agent."""
        return self._build_context(self.status(campaign_id))

    def begin_external_baseline(self, campaign_id: str) -> dict[str, Any]:
        """Create trial-000 baseline ticket for an Agent using its own MCP tools."""
        campaign_id = self.status(campaign_id)['campaign_id']
        with self.store.campaign_lock(campaign_id):
            campaign = self.status(campaign_id)
            if campaign['status'] in CAMPAIGN_TERMINAL:
                raise ValueError(f"Campaign already terminated with status={campaign['status']}")
            if campaign['trials']:
                return campaign['trials'][0]
            plan = campaign['plan']
            base_cfg = _base_target_config(plan)
            base_arch = copy.deepcopy(base_cfg) if plan['track'] == 'architecture' else (
                copy.deepcopy(plan['base_architecture']) if plan.get('base_architecture') else None
            )
            base_recipe = copy.deepcopy(plan['base_training_recipe']) if plan['track'] == 'architecture' else copy.deepcopy(base_cfg)
            trial = TrialRecord(
                trial_id='trial-000',
                index=0,
                parent_trial_id=None,
                is_baseline=True,
                hypothesis=plan['base_hypothesis'],
                changes={},
                architecture=base_arch,
                candidate_config=base_cfg,
                training_recipe=base_recipe,
                reuse_simulation=False,
                complexity_score=0.0,
                run_id=None,
                run_status='awaiting_result',
                started_at=time.time(),
            ).to_dict()
            campaign['trials'].append(trial)
            campaign['active_trial_id'] = trial['trial_id']
            self.store.save_campaign(campaign)
            self.store.event(campaign_id, 'trial_started', {
                'trial_id': trial['trial_id'],
                'execution_mode': 'external_mcp',
                'is_baseline': True,
                'hypothesis': trial['hypothesis'],
            })
            return trial

    def submit_proposal(self, campaign_id: str, proposal: Proposal | dict[str, Any]) -> dict[str, Any]:
        """Validate a single declarative proposal (whitelist + param_bounds) and create a trial."""
        campaign_id = self.status(campaign_id)['campaign_id']
        if isinstance(proposal, dict):
            proposal = Proposal.from_dict(proposal)
        with self.store.campaign_lock(campaign_id):
            campaign = self.status(campaign_id)
            if campaign['status'] in CAMPAIGN_TERMINAL:
                raise ValueError(f"Campaign already terminated with status={campaign['status']}")
            if campaign['status'] == 'evaluating_holdout':
                raise ValueError('Campaign is already in holdout evaluation')
            if campaign['active_trial_id'] is not None:
                raise ValueError(f"Trial {campaign['active_trial_id']} is still active; record or finish it first")
            plan = campaign['plan']
            self._check_campaign_limits(campaign)
            if campaign['stop_reason']:
                campaign['status'] = campaign['stop_reason']
                self.store.save_campaign(campaign)
                raise ValueError(f"Campaign budget/stop reached: {campaign['stop_reason']}")
            if not campaign['trials']:
                raise ValueError('Baseline trial-000 has not run yet; run baseline first')
            if len(campaign['trials']) >= plan['budget']['max_trials']:
                raise ValueError('Campaign max_trials budget reached; run finalize for holdout evaluation')
            incumbent = self._find_trial(campaign, campaign['incumbent_trial_id'])
            if incumbent is None:
                raise ValueError('No valid incumbent available')
            try:
                validate_proposal_scope(proposal, plan['mutable_fields'])
                validate_proposal_bounds(proposal, (plan['knowledge'].get('scope') or {}).get('param_bounds'))
            except ValueError as error:
                self.store.event(campaign_id, 'proposal_rejected', {
                    'hypothesis': proposal.hypothesis,
                    'changes': proposal.changes,
                    'error': str(error),
                })
                raise
            campaign['status'], campaign['error'] = 'running', None
            if plan.get('execution_mode') == 'external_mcp':
                self._start_external_candidate(campaign, incumbent, proposal)
            else:
                self._start_candidate(campaign, incumbent, proposal)
            self.store.save_campaign(campaign)
            return campaign['trials'][-1]

    def _start_external_candidate(self, campaign: dict[str, Any], incumbent: dict[str, Any], proposal: Proposal) -> None:
        plan = campaign['plan']
        index = len(campaign['trials'])
        trial_id = f'trial-{index:03d}'
        base_cfg = _base_target_config(plan)
        inc_cfg = _incumbent_target_config(plan, incumbent)
        candidate_cfg = apply_changes(inc_cfg, proposal.changes)
        complexity = compute_complexity(base_cfg, candidate_cfg, incumbent['complexity_score'], proposal.complexity_delta)
        cand_arch = copy.deepcopy(candidate_cfg) if plan['track'] == 'architecture' else (
            copy.deepcopy(plan['base_architecture']) if plan.get('base_architecture') else None
        )
        cand_recipe = copy.deepcopy(plan['base_training_recipe']) if plan['track'] == 'architecture' else copy.deepcopy(candidate_cfg)
        trial = TrialRecord(
            trial_id=trial_id,
            index=index,
            parent_trial_id=incumbent['trial_id'],
            is_baseline=False,
            hypothesis=proposal.hypothesis,
            changes=dict(proposal.changes),
            architecture=cand_arch,
            candidate_config=candidate_cfg,
            training_recipe=cand_recipe,
            reuse_simulation=proposal.reuse_simulation,
            complexity_score=complexity,
            run_id=None,
            run_status='awaiting_result',
            started_at=time.time(),
        ).to_dict()
        campaign['trials'].append(trial)
        campaign['active_trial_id'] = trial_id
        self.store.event(campaign['campaign_id'], 'trial_started', {
            'trial_id': trial_id,
            'parent_trial_id': incumbent['trial_id'],
            'execution_mode': 'external_mcp',
            'track': plan['track'],
            'hypothesis': proposal.hypothesis,
            'changes': dict(proposal.changes),
            'complexity_score': complexity,
        })

    def record_trial(
        self,
        campaign_id: str,
        trial_id: str | None = None,
        status: str = 'succeeded',
        metrics: dict[str, Any] | None = None,
        cost: dict[str, Any] | None = None,
        artifacts: dict[str, Any] | None = None,
        external_jobs: list[dict[str, Any]] | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        """BYO-MCP entry: record results produced by the Agent's own MCP tools and run ratchet decision."""
        if status not in {'succeeded', 'failed', 'timeout', 'crash', 'cancelled'}:
            raise ValueError(f'Unsupported trial record status: {status}')
        campaign_id = self.status(campaign_id)['campaign_id']
        with self.store.campaign_lock(campaign_id):
            campaign = self.status(campaign_id)
            if campaign['status'] in CAMPAIGN_TERMINAL:
                raise ValueError(f"Campaign already terminated with status={campaign['status']}")
            target_id = trial_id or campaign['active_trial_id']
            if not target_id:
                raise ValueError('No active trial to record; run baseline or propose first')
            trial = self._find_trial(campaign, target_id)
            if trial is None:
                raise ValueError(f'Unknown trial_id: {target_id}')
            if trial['decision'] is not None:
                raise ValueError(f'Trial {target_id} is already decided ({trial["decision"]})')

            plan = campaign['plan']
            p_spec = normalize_primary_metric(plan['acceptance'])
            c_spec = normalize_compute_metric(plan['acceptance'])
            cost_spec = normalize_cost_metric(plan['budget'])

            now = time.time()
            trial['finished_at'] = now
            trial['duration_seconds'] = max(0.0, round(now - trial['started_at'], 3))
            trial['run_status'] = status
            trial['artifacts'] = dict(artifacts or {})
            trial['external_jobs'] = list(external_jobs or [])
            if trial['artifacts'].get('dataset_ref'):
                trial['dataset_ref'] = str(trial['artifacts']['dataset_ref'])
            if trial['artifacts'].get('model_ref'):
                trial['model_ref'] = str(trial['artifacts']['model_ref'])

            cost_dict = dict(cost or {})
            cost_name = cost_spec['name']
            raw_cost = cost_dict.get(cost_name, cost_dict.get('gpu_seconds', 0.0))
            if not is_finite_number(raw_cost) or raw_cost < 0:
                raise ValueError(f'Invalid cost value for {cost_name}: {raw_cost!r}')
            trial['cost_value'] = round(float(raw_cost), 4)
            campaign['total_cost'] = round(float(campaign.get('total_cost', 0.0)) + trial['cost_value'], 4)
            trial['cumulative_cost'] = campaign['total_cost']
            if cost_name == 'gpu_seconds' or 'gpu_seconds' in cost_dict:
                gpu_s = float(cost_dict.get('gpu_seconds', trial['cost_value']))
                trial['gpu_seconds'] = round(gpu_s, 3)
                campaign['total_gpu_seconds'] = round(campaign.get('total_gpu_seconds', 0.0) + trial['gpu_seconds'], 3)
                trial['cumulative_gpu_seconds'] = campaign['total_gpu_seconds']
            if 'train_tflops' in cost_dict and is_finite_number(cost_dict['train_tflops']):
                trial['train_tflops'] = round(float(cost_dict['train_tflops']), 3)
                campaign['total_train_tflops'] = round(campaign.get('total_train_tflops', 0.0) + trial['train_tflops'], 3)

            if status == 'cancelled':
                trial['decision'] = 'cancelled'
                trial['decision_reason'] = note or 'trial cancelled'
            elif status != 'succeeded':
                trial['decision'] = 'crash'
                trial['decision_reason'] = note or f'external MCP trial ended with status={status}'
                if trial['is_baseline']:
                    campaign['status'] = 'failed'
                    campaign['error'] = f'Baseline trial failed: {trial["decision_reason"]}'
            else:
                metrics_dict = dict(metrics or {})
                p_name = p_spec['name']
                if p_name not in metrics_dict or not is_finite_number(metrics_dict[p_name]):
                    raise ValueError(f'Missing or invalid primary metric "{p_name}" in recorded metrics')
                primary_val = float(metrics_dict[p_name])
                c_name = c_spec['name']
                compute_val = None
                if c_name in metrics_dict and metrics_dict[c_name] is not None:
                    if not is_finite_number(metrics_dict[c_name]) or metrics_dict[c_name] <= 0:
                        raise ValueError(f'Invalid compute metric "{c_name}": {metrics_dict[c_name]!r}')
                    compute_val = float(metrics_dict[c_name])
                self._apply_generic_decision(
                    campaign=campaign,
                    trial=trial,
                    primary_val=primary_val,
                    compute_val=compute_val,
                    metrics_dict=metrics_dict,
                    p_spec=p_spec,
                    c_spec=c_spec,
                )

            campaign['active_trial_id'] = None
            self.store.event(campaign['campaign_id'], 'trial_decided', {
                'trial_id': trial['trial_id'],
                'execution_mode': 'external_mcp',
                'decision': trial['decision'],
                'reason': trial['decision_reason'],
                'primary_metric': p_spec['name'],
                'primary_value': trial['primary_value'],
                'gain': trial['gain'],
                'gain_pct': trial['gain_pct'],
                'compute_metric': c_spec['name'],
                'compute_value': trial['compute_value'],
                'compute_ratio': trial['compute_ratio'],
                'cost_value': trial['cost_value'],
                'incumbent_trial_id': campaign['incumbent_trial_id'],
            })
            self._write_results_tsv(campaign)
            self._check_campaign_limits(campaign)
            if campaign['stop_reason'] and campaign['status'] not in CAMPAIGN_TERMINAL:
                campaign['status'] = campaign['stop_reason']
                self.store.event(campaign['campaign_id'], 'campaign_stopped', {'reason': campaign['stop_reason']})
            self.store.save_campaign(campaign)
            return trial

    def finalize_external_holdout(
        self,
        campaign_id: str,
        metrics: dict[str, Any] | None = None,
        cost: dict[str, Any] | None = None,
        artifacts: dict[str, Any] | None = None,
        external_jobs: list[dict[str, Any]] | None = None,
        status: str = 'succeeded',
        note: str | None = None,
    ) -> dict[str, Any]:
        """BYO-MCP entry: record the single independent holdout evaluation for the locked incumbent."""
        campaign_id = self.status(campaign_id)['campaign_id']
        with self.store.campaign_lock(campaign_id):
            campaign = self.status(campaign_id)
            if campaign['status'] in CAMPAIGN_TERMINAL:
                return campaign
            if campaign['active_trial_id'] is not None:
                raise ValueError(f"Active trial {campaign['active_trial_id']} must be recorded before finalize")
            incumbent = self._find_trial(campaign, campaign['incumbent_trial_id'])
            if incumbent is None:
                raise ValueError('Cannot finalize holdout without a valid incumbent trial')
            plan = campaign['plan']
            p_spec = normalize_primary_metric(plan['acceptance'])
            c_spec = normalize_compute_metric(plan['acceptance'])
            cost_spec = normalize_cost_metric(plan['budget'])
            artifacts_dict = dict(artifacts or {})
            if incumbent.get('model_ref') and artifacts_dict.get('model_ref'):
                if artifacts_dict['model_ref'] != incumbent['model_ref']:
                    raise ValueError(
                        f"Holdout model_ref mismatch: expected incumbent {incumbent['model_ref']}, "
                        f"got {artifacts_dict['model_ref']}"
                    )

            cost_dict = dict(cost or {})
            cost_name = cost_spec['name']
            holdout_cost = float(cost_dict.get(cost_name, cost_dict.get('gpu_seconds', 0.0)) or 0.0)
            campaign['total_cost'] = round(float(campaign.get('total_cost', 0.0)) + holdout_cost, 4)
            if cost_name == 'gpu_seconds' or 'gpu_seconds' in cost_dict:
                campaign['total_gpu_seconds'] = round(
                    campaign.get('total_gpu_seconds', 0.0) + float(cost_dict.get('gpu_seconds', holdout_cost)), 3
                )
            if 'train_tflops' in cost_dict and is_finite_number(cost_dict['train_tflops']):
                campaign['total_train_tflops'] = round(
                    campaign.get('total_train_tflops', 0.0) + float(cost_dict['train_tflops']), 3
                )

            if status != 'succeeded':
                campaign['status'] = 'failed'
                campaign['error'] = note or f'Holdout evaluation ended with status={status}'
                self.store.save_campaign(campaign)
                return campaign

            metrics_dict = dict(metrics or {})
            p_name = p_spec['name']
            if p_name not in metrics_dict or not is_finite_number(metrics_dict[p_name]):
                raise ValueError(f'Missing or invalid holdout primary metric "{p_name}"')
            cand_primary = float(metrics_dict[p_name])
            base_primary = metrics_dict.get(f'baseline_{p_name}', campaign.get('baseline_primary_value'))
            if base_primary is not None:
                base_primary = float(base_primary)
                gain, gain_pct = compute_gain(cand_primary, base_primary, p_spec['direction'])
            else:
                gain, gain_pct = None, None

            c_name = c_spec['name']
            cand_compute = metrics_dict.get(c_name, incumbent.get('compute_value'))
            cand_compute = float(cand_compute) if is_finite_number(cand_compute) else None
            base_compute = metrics_dict.get(f'baseline_{c_name}', campaign.get('baseline_compute_value'))
            base_compute = float(base_compute) if is_finite_number(base_compute) else None
            compute_ratio = round(cand_compute / base_compute, 4) if (cand_compute is not None and base_compute) else None

            compute_violation = check_compute_budget(cand_compute, compute_ratio, c_spec)
            guardrail_violation = check_guardrails(metrics_dict, plan['acceptance'].get('guardrails'))
            target_ok = meets_holdout_target(cand_primary, base_primary, p_spec)
            accepted = target_ok and (compute_violation is None) and (guardrail_violation is None)

            total_cost = campaign['total_cost']
            gain_per_cost = round(gain_pct / total_cost, 4) if (gain_pct is not None and total_cost > 0) else None
            counts = {
                name: sum(1 for item in campaign['trials'] if item['decision'] == name)
                for name in ('baseline', 'keep', 'discard', 'crash', 'cancelled')
            }
            campaign['holdout_report'] = {
                'mode': 'external_mcp',
                'evaluation_scope': 'holdout',
                'campaign_id': campaign['campaign_id'],
                'track': plan['track'],
                'model_family': plan.get('model_family') or (plan['knowledge'].get('scope') or {}).get('model_family'),
                'kb_ref': plan.get('kb_ref'),
                'knowledge_sha256': campaign['knowledge_sha256'],
                'program_sha256': campaign['program_sha256'],
                'evaluator_ref': plan['holdout_evaluator_ref'],
                'incumbent_trial_id': incumbent['trial_id'],
                'incumbent_config': _incumbent_target_config(plan, incumbent),
                'incumbent_complexity': incumbent['complexity_score'],
                'model_ref': artifacts_dict.get('model_ref') or incumbent.get('model_ref'),
                'artifacts': artifacts_dict,
                'external_jobs': list(external_jobs or []),
                'primary_metric_name': p_name,
                'primary_direction': p_spec['direction'],
                'baseline_primary_value': base_primary,
                'candidate_primary_value': cand_primary,
                'gain': gain,
                'gain_pct': gain_pct,
                'compute_metric_name': c_name,
                'baseline_compute_value': base_compute,
                'candidate_compute_value': cand_compute,
                'compute_ratio': compute_ratio,
                'flops_ratio': compute_ratio,
                'compute_within_budget': compute_violation is None,
                'guardrails_passed': guardrail_violation is None,
                'accepted': accepted,
                'rejection_reason': compute_violation or guardrail_violation or (None if target_ok else 'holdout target not met'),
                'metrics': metrics_dict,
                'cost_metric_name': cost_name,
                'campaign_compute_usage': {
                    'total_cost': total_cost,
                    'cost_unit': cost_spec.get('unit', ''),
                    'total_gpu_seconds': campaign['total_gpu_seconds'],
                    'total_train_tflops': campaign['total_train_tflops'],
                },
                'gain_per_cost': gain_per_cost,
                'total_trials': len(campaign['trials']),
                'decision_counts': counts,
                'note': note,
            }
            campaign['status'] = 'succeeded'
            self.store.event(campaign['campaign_id'], 'campaign_succeeded', {
                'execution_mode': 'external_mcp',
                'incumbent_trial_id': incumbent['trial_id'],
                'accepted': accepted,
                'primary_metric': p_name,
                'gain': gain,
                'compute_ratio': compute_ratio,
                'total_cost': total_cost,
            })
            self.store.save_campaign(campaign)
            return campaign

    def _apply_generic_decision(
        self,
        campaign: dict[str, Any],
        trial: dict[str, Any],
        primary_val: float,
        compute_val: float | None,
        metrics_dict: dict[str, Any],
        p_spec: dict[str, Any],
        c_spec: dict[str, Any],
        denom_override: float | None = None,
    ) -> None:
        trial['primary_value'] = primary_val
        trial['compute_value'] = compute_val
        trial['dev_metrics'] = dict(metrics_dict)
        if trial['is_baseline']:
            campaign['baseline_primary_value'] = primary_val
            if compute_val is not None:
                campaign['baseline_compute_value'] = compute_val
            trial['gain'] = 0.0
            trial['gain_pct'] = 0.0
            trial['compute_ratio'] = 1.0 if compute_val is not None else None
            trial['decision'] = 'baseline'
            trial['decision_reason'] = f"established baseline incumbent ({p_spec['name']}={primary_val})"
            campaign['incumbent_trial_id'] = trial['trial_id']
            return

        base_primary = campaign.get('baseline_primary_value')
        if base_primary is not None:
            gain, gain_pct = compute_gain(primary_val, base_primary, p_spec['direction'], denominator_override=denom_override)
            trial['gain'] = gain
            trial['gain_pct'] = gain_pct
        base_compute = campaign.get('baseline_compute_value')
        if compute_val is not None and base_compute:
            trial['compute_ratio'] = round(compute_val / base_compute, 4)

        incumbent = self._find_trial(campaign, campaign['incumbent_trial_id'])
        acceptance = campaign['plan']['acceptance']
        violation = check_guardrails(metrics_dict, acceptance.get('guardrails'))
        compute_violation = check_compute_budget(compute_val, trial['compute_ratio'], c_spec)
        if violation is not None:
            trial['decision'] = 'discard'
            trial['decision_reason'] = violation
            return
        if compute_violation is not None:
            trial['decision'] = 'discard'
            trial['decision_reason'] = compute_violation
            return

        inc_primary = incumbent.get('primary_value')
        delta, _ = compute_gain(primary_val, float(inc_primary), p_spec['direction'])
        min_gain = float(p_spec.get('min_gain', 0.0))
        tie_tol = float(p_spec.get('tie_tolerance', 0.0))
        inc_compute = incumbent.get('compute_value')
        better_compute = (
            compute_val is not None
            and inc_compute is not None
            and (
                (c_spec['direction'] == 'minimize' and compute_val < inc_compute)
                or (c_spec['direction'] == 'maximize' and compute_val > inc_compute)
            )
        )
        if delta >= min_gain and (min_gain > 0 or delta > tie_tol):
            trial['decision'] = 'keep'
            trial['decision_reason'] = (
                f"gain win: {p_spec['name']} improved by {delta:+.4g} (>= {min_gain}), "
                f"{c_spec['name']}_ratio={trial['compute_ratio']}"
            )
            campaign['incumbent_trial_id'] = trial['trial_id']
        elif abs(delta) <= tie_tol and better_compute:
            trial['decision'] = 'keep'
            trial['decision_reason'] = (
                f"compute win: tied delta={delta:+.4g} with better {c_spec['name']} "
                f'{compute_val} vs {inc_compute}'
            )
            campaign['incumbent_trial_id'] = trial['trial_id']
        elif abs(delta) <= tie_tol and trial['complexity_score'] < incumbent['complexity_score']:
            trial['decision'] = 'keep'
            trial['decision_reason'] = (
                f'simplicity win: tied delta={delta:+.4g} with lower complexity '
                f"{trial['complexity_score']} < {incumbent['complexity_score']}"
            )
            campaign['incumbent_trial_id'] = trial['trial_id']
        else:
            trial['decision'] = 'discard'
            trial['decision_reason'] = (
                f'delta={delta:+.4g} did not beat min_gain={min_gain} '
                f"({c_spec['name']}={compute_val} vs {inc_compute}, "
                f"complexity={trial['complexity_score']} vs {incumbent['complexity_score']})"
            )

    def run_baseline(self, campaign_id: str, poll_seconds: float = 0.05) -> dict[str, Any]:
        """Ensure trial-000 baseline is created (and completed automatically in managed mode)."""
        campaign_id = self.status(campaign_id)['campaign_id']
        if self.status(campaign_id)['plan'].get('execution_mode') == 'external_mcp':
            return self.begin_external_baseline(campaign_id)
        with self.store.campaign_lock(campaign_id):
            campaign = self.status(campaign_id)
            if campaign['status'] in CAMPAIGN_TERMINAL:
                raise ValueError(f"Campaign already terminated with status={campaign['status']}")
            if not campaign['trials']:
                self._start_baseline(campaign)
                self.store.save_campaign(campaign)
        return self.run_active_trial(campaign_id, poll_seconds=poll_seconds)

    def run_active_trial(self, campaign_id: str, poll_seconds: float = 0.05) -> dict[str, Any]:
        """Advance only the currently active managed trial until it reaches a decision."""
        campaign_id = self.status(campaign_id)['campaign_id']
        initial = self.status(campaign_id)
        if initial['plan'].get('execution_mode') == 'external_mcp':
            raise ValueError('In external_mcp mode, run your own MCP tools and call `campaign record` to report results')
        target_trial_id = initial['active_trial_id']
        if target_trial_id is None:
            if not initial['trials']:
                raise ValueError('No active trial; run baseline or submit a proposal first')
            return initial['trials'][-1]
        while True:
            with self.store.campaign_lock(campaign_id):
                campaign = self.status(campaign_id)
                if campaign['status'] in CAMPAIGN_TERMINAL or campaign['active_trial_id'] != target_trial_id:
                    trial = self._find_trial(campaign, target_trial_id)
                    return trial if trial is not None else campaign['trials'][-1]
                campaign['error'] = None
                try:
                    self._check_campaign_limits(campaign)
                    self._advance_active_trial(campaign)
                except Exception as error:
                    campaign['status'], campaign['error'] = 'paused', str(error)
                    self.store.event(campaign_id, 'campaign_paused', {'error': str(error)})
                self.store.save_campaign(campaign)
                trial = self._find_trial(campaign, target_trial_id)
                if campaign['status'] == 'paused' or campaign['active_trial_id'] != target_trial_id:
                    return trial if trial is not None else campaign['trials'][-1]
            time.sleep(poll_seconds)

    def finalize_holdout(self, campaign_id: str, poll_seconds: float = 0.05) -> dict[str, Any]:
        """Lock current incumbent and execute the single independent holdout evaluation (managed mode)."""
        campaign_id = self.status(campaign_id)['campaign_id']
        if self.status(campaign_id)['plan'].get('execution_mode') == 'external_mcp':
            raise ValueError('In external_mcp mode, pass holdout --metrics to `campaign finalize`')
        while True:
            with self.store.campaign_lock(campaign_id):
                campaign = self.status(campaign_id)
                if campaign['status'] in CAMPAIGN_TERMINAL:
                    return campaign
                if campaign['active_trial_id'] is not None:
                    raise ValueError(f"Active trial {campaign['active_trial_id']} must finish before finalize")
                campaign['error'] = None
                try:
                    if campaign['status'] != 'evaluating_holdout':
                        self._begin_holdout(campaign, reason='explicit_finalize')
                    else:
                        self._advance_holdout(campaign)
                except Exception as error:
                    campaign['status'], campaign['error'] = 'paused', str(error)
                    self.store.event(campaign_id, 'campaign_paused', {'error': str(error)})
                self.store.save_campaign(campaign)
                if campaign['status'] in CAMPAIGN_TERMINAL or campaign['status'] == 'paused':
                    return campaign
            time.sleep(poll_seconds)

    def _check_campaign_limits(self, campaign: dict[str, Any]) -> None:
        plan = campaign['plan']
        if self.store.campaign_cancel_requested(campaign['campaign_id']):
            campaign['stop_reason'] = campaign['stop_reason'] or 'cancelled'
        total_wall = plan['budget'].get('total_wall_seconds')
        if total_wall is not None and time.time() - campaign['created_at'] >= total_wall:
            campaign['stop_reason'] = campaign['stop_reason'] or 'budget_exhausted'
        cost_spec = normalize_cost_metric(plan['budget'])
        max_total = cost_spec.get('max_total')
        used_cost = campaign.get('total_cost') or campaign.get('total_gpu_seconds', 0.0)
        if max_total is not None and used_cost >= max_total:
            campaign['stop_reason'] = campaign['stop_reason'] or 'budget_exhausted'

    def step(self, campaign_id: str) -> dict[str, Any]:
        campaign_id = self.status(campaign_id)['campaign_id']
        with self.store.campaign_lock(campaign_id):
            campaign = self.status(campaign_id)
            if campaign['status'] in CAMPAIGN_TERMINAL:
                return campaign
            if campaign['plan'].get('execution_mode') == 'external_mcp':
                raise ValueError('external_mcp campaigns are driven by `baseline / propose / record / finalize`, not `step`')
            if campaign['status'] == 'paused':
                campaign['status'] = 'evaluating_holdout' if campaign['holdout_run_id'] else 'running'
            campaign['error'] = None
            try:
                self._advance(campaign)
            except Exception as error:
                campaign['status'], campaign['error'] = 'paused', str(error)
                self.store.event(campaign_id, 'campaign_paused', {'error': str(error)})
            self.store.save_campaign(campaign)
            return campaign

    def _advance(self, campaign: dict[str, Any]) -> None:
        plan = campaign['plan']
        self._check_campaign_limits(campaign)

        if campaign['status'] == 'evaluating_holdout':
            self._advance_holdout(campaign)
            return

        if campaign['active_trial_id'] is not None:
            self._advance_active_trial(campaign)
            return

        if campaign['stop_reason']:
            campaign['status'] = campaign['stop_reason']
            self.store.event(campaign['campaign_id'], 'campaign_stopped', {'reason': campaign['stop_reason']})
            return

        if not campaign['trials']:
            self._start_baseline(campaign)
            return

        if len(campaign['trials']) >= plan['budget']['max_trials']:
            self._begin_holdout(campaign, reason='max_trials_reached')
            return

        incumbent = self._find_trial(campaign, campaign['incumbent_trial_id'])
        if incumbent is None:
            campaign['status'] = 'failed'
            campaign['error'] = 'No incumbent available for candidate exploration'
            return

        context = self._build_context(campaign)
        proposal = self._proposer_for(campaign).propose(context)
        if proposal is None:
            self._begin_holdout(campaign, reason='proposer_exhausted')
            return
        if isinstance(proposal, dict):
            proposal = Proposal.from_dict(proposal)
        try:
            validate_proposal_scope(proposal, plan['mutable_fields'])
            validate_proposal_bounds(proposal, (plan['knowledge'].get('scope') or {}).get('param_bounds'))
        except ValueError as error:
            self.store.event(campaign['campaign_id'], 'proposal_rejected', {
                'hypothesis': proposal.hypothesis,
                'changes': proposal.changes,
                'error': str(error),
            })
            raise
        self._start_candidate(campaign, incumbent, proposal)

    def _start_baseline(self, campaign: dict[str, Any]) -> None:
        plan = campaign['plan']
        base_cfg = _base_target_config(plan)
        base_arch = copy.deepcopy(base_cfg) if plan['track'] == 'architecture' else (
            copy.deepcopy(plan['base_architecture']) if plan.get('base_architecture') else None
        )
        base_recipe = copy.deepcopy(plan['base_training_recipe']) if plan['track'] == 'architecture' else copy.deepcopy(base_cfg)
        run_plan: dict[str, Any] = {
            'schema_version': 1,
            'knowledge': plan['knowledge'],
            'hypothesis': plan['base_hypothesis'],
            'baseline_model_ref': plan['baseline_model_ref'],
            'dataset_ref': plan['dataset_ref'],
            'evaluator_ref': plan['dev_evaluator_ref'],
            'evaluation_scope': 'dev',
            'architecture': base_arch,
            'training_recipe': base_recipe,
            'budget': {
                'max_tasks': plan['budget'].get('max_tasks_per_trial', 3),
                'wall_seconds': plan['budget']['per_trial_wall_seconds'],
            },
            'acceptance': {
                'total_cases': plan['acceptance'].get('dev_total_cases', 24),
                'min_correct': 0,
            },
            'mock': _trial_mock_settings(plan.get('mock'), eval_fixture_key='baseline_eval_fixture'),
        }
        run_id = self.harness.create(run_plan)
        trial = TrialRecord(
            trial_id='trial-000',
            index=0,
            parent_trial_id=None,
            is_baseline=True,
            hypothesis=plan['base_hypothesis'],
            changes={},
            architecture=base_arch,
            candidate_config=base_cfg,
            training_recipe=base_recipe,
            reuse_simulation=False,
            complexity_score=0.0,
            run_id=run_id,
            started_at=time.time(),
        ).to_dict()
        campaign['trials'].append(trial)
        campaign['active_trial_id'] = trial['trial_id']
        self.store.event(campaign['campaign_id'], 'trial_started', {
            'trial_id': trial['trial_id'],
            'run_id': run_id,
            'is_baseline': True,
            'hypothesis': trial['hypothesis'],
        })

    def _start_candidate(self, campaign: dict[str, Any], incumbent: dict[str, Any], proposal: Proposal) -> None:
        plan = campaign['plan']
        index = len(campaign['trials'])
        trial_id = f'trial-{index:03d}'
        base_cfg = _base_target_config(plan)
        inc_cfg = _incumbent_target_config(plan, incumbent)
        candidate_cfg = apply_changes(inc_cfg, proposal.changes)
        complexity = compute_complexity(base_cfg, candidate_cfg, incumbent['complexity_score'], proposal.complexity_delta)
        if plan['track'] == 'architecture':
            candidate_arch = copy.deepcopy(candidate_cfg)
            candidate_recipe = copy.deepcopy(plan['base_training_recipe'])
        else:
            candidate_arch = copy.deepcopy(plan['base_architecture']) if plan.get('base_architecture') else None
            candidate_recipe = copy.deepcopy(candidate_cfg)
        reuse_dataset = incumbent['dataset_ref'] if proposal.reuse_simulation else None
        run_plan: dict[str, Any] = {
            'schema_version': 1,
            'knowledge': plan['knowledge'],
            'hypothesis': proposal.hypothesis,
            'baseline_model_ref': plan['baseline_model_ref'],
            'dataset_ref': plan['dataset_ref'],
            'evaluator_ref': plan['dev_evaluator_ref'],
            'evaluation_scope': 'dev',
            'reuse_dataset_ref': reuse_dataset,
            'architecture': candidate_arch,
            'training_recipe': candidate_recipe,
            'budget': {
                'max_tasks': plan['budget'].get('max_tasks_per_trial', 3),
                'wall_seconds': plan['budget']['per_trial_wall_seconds'],
            },
            'acceptance': {
                'total_cases': plan['acceptance'].get('dev_total_cases', 24),
                'min_correct': 0,
            },
            'mock': _trial_mock_settings(plan.get('mock'), overrides=proposal.mock_overrides),
        }
        run_id = self.harness.create(run_plan)
        trial = TrialRecord(
            trial_id=trial_id,
            index=index,
            parent_trial_id=incumbent['trial_id'],
            is_baseline=False,
            hypothesis=proposal.hypothesis,
            changes=dict(proposal.changes),
            architecture=candidate_arch,
            candidate_config=candidate_cfg,
            training_recipe=candidate_recipe,
            reuse_simulation=bool(reuse_dataset),
            complexity_score=complexity,
            run_id=run_id,
            started_at=time.time(),
        ).to_dict()
        campaign['trials'].append(trial)
        campaign['active_trial_id'] = trial_id
        self.store.event(campaign['campaign_id'], 'trial_started', {
            'trial_id': trial_id,
            'parent_trial_id': incumbent['trial_id'],
            'run_id': run_id,
            'is_baseline': False,
            'track': plan['track'],
            'hypothesis': proposal.hypothesis,
            'changes': dict(proposal.changes),
            'reuse_simulation': bool(reuse_dataset),
            'complexity_score': complexity,
        })

    def _advance_active_trial(self, campaign: dict[str, Any]) -> None:
        trial = self._find_trial(campaign, campaign['active_trial_id'])
        if trial is None:
            raise ValueError(f"Unknown active trial: {campaign['active_trial_id']}")
        if campaign['stop_reason']:
            self.harness.request_stop(trial['run_id'])
        run = self.harness.step(trial['run_id'])
        trial['run_status'] = run['status']
        if run['status'] == 'running':
            return
        if run['status'] == 'paused':
            campaign['status'] = 'paused'
            campaign['error'] = f"Trial {trial['trial_id']} paused: {run['error']}"
            self.store.event(campaign['campaign_id'], 'campaign_paused', {
                'trial_id': trial['trial_id'],
                'run_id': run['run_id'],
                'error': run['error'],
            })
            return

        now = time.time()
        trial['finished_at'] = now
        trial['duration_seconds'] = max(0.0, now - trial['started_at'])
        trial['dev_total'] = campaign['plan']['acceptance'].get('dev_total_cases', 24)
        usage = run.get('compute_usage') or {'gpu_seconds': 0.0, 'train_tflops': 0.0}
        trial['gpu_seconds'] = round(float(usage.get('gpu_seconds', 0.0)), 3)
        trial['train_tflops'] = round(float(usage.get('train_tflops', 0.0)), 3)
        trial['cost_value'] = trial['gpu_seconds']
        campaign['total_gpu_seconds'] = round(campaign.get('total_gpu_seconds', 0.0) + trial['gpu_seconds'], 3)
        campaign['total_train_tflops'] = round(campaign.get('total_train_tflops', 0.0) + trial['train_tflops'], 3)
        campaign['total_cost'] = campaign['total_gpu_seconds']
        trial['cumulative_gpu_seconds'] = campaign['total_gpu_seconds']
        trial['cumulative_cost'] = campaign['total_cost']

        if run['tasks'][0]['result'].get('dataset_ref'):
            trial['dataset_ref'] = run['tasks'][0]['result']['dataset_ref']
            trial['artifacts']['dataset_ref'] = trial['dataset_ref']
        if run['tasks'][1]['result'].get('model_ref'):
            trial['model_ref'] = run['tasks'][1]['result']['model_ref']
            trial['artifacts']['model_ref'] = trial['model_ref']

        self._decide_managed_trial(campaign, trial, run)
        campaign['active_trial_id'] = None
        self._write_results_tsv(campaign)

        self._check_campaign_limits(campaign)
        if campaign['stop_reason'] and campaign['status'] not in CAMPAIGN_TERMINAL:
            campaign['status'] = campaign['stop_reason']
            self.store.event(campaign['campaign_id'], 'campaign_stopped', {'reason': campaign['stop_reason']})

    def _decide_managed_trial(self, campaign: dict[str, Any], trial: dict[str, Any], run: dict[str, Any]) -> None:
        if campaign['stop_reason'] == 'cancelled' and run['status'] == 'cancelled':
            trial['decision'] = 'cancelled'
            trial['decision_reason'] = 'campaign cancelled by user'
        elif run['status'] != 'succeeded' or run['report'] is None:
            trial['decision'] = 'crash'
            trial['decision_reason'] = f"trial run ended with status={run['status']}"
            if trial['is_baseline'] and not campaign['stop_reason']:
                campaign['status'] = 'failed'
                campaign['error'] = f"Baseline trial failed with status={run['status']}"
        else:
            report = run['report']
            plan = campaign['plan']
            p_spec = normalize_primary_metric(plan['acceptance'])
            c_spec = normalize_compute_metric(plan['acceptance'])
            trial['dev_correct'] = report['candidate_correct']
            trial['dev_total'] = report['total_cases']
            trial['gain_vs_baseline'] = report.get('gain_correct', report['candidate_correct'] - report['baseline_correct'])
            trial['gain_pp'] = report.get('gain_pp', round(trial['gain_vs_baseline'] * 100.0 / report['total_cases'], 2))
            trial['baseline_inference_flops_m'] = report.get('baseline_inference_flops_m')
            trial['candidate_inference_flops_m'] = report.get('candidate_inference_flops_m')
            trial['flops_ratio'] = report.get('flops_ratio')
            self._apply_generic_decision(
                campaign=campaign,
                trial=trial,
                primary_val=float(report['candidate_correct']),
                compute_val=report.get('candidate_inference_flops_m'),
                metrics_dict=dict(report.get('metrics') or {}),
                p_spec=p_spec,
                c_spec=c_spec,
                denom_override=float(report['total_cases']),
            )
            if report.get('flops_ratio') is not None:
                trial['compute_ratio'] = report['flops_ratio']

        self.store.event(campaign['campaign_id'], 'trial_decided', {
            'trial_id': trial['trial_id'],
            'run_id': trial['run_id'],
            'decision': trial['decision'],
            'reason': trial['decision_reason'],
            'dev_correct': trial['dev_correct'],
            'gain_vs_baseline': trial['gain_vs_baseline'],
            'candidate_inference_flops_m': trial['candidate_inference_flops_m'],
            'flops_ratio': trial['flops_ratio'],
            'gpu_seconds': trial['gpu_seconds'],
            'complexity_score': trial['complexity_score'],
            'incumbent_trial_id': campaign['incumbent_trial_id'],
        })

    def _begin_holdout(self, campaign: dict[str, Any], reason: str) -> None:
        incumbent = self._find_trial(campaign, campaign['incumbent_trial_id'])
        if incumbent is None or not incumbent.get('model_ref'):
            campaign['status'] = 'failed'
            campaign['error'] = 'Cannot run holdout evaluation without a valid incumbent model_ref'
            return
        campaign['status'] = 'evaluating_holdout'
        self.store.event(campaign['campaign_id'], 'holdout_locked', {
            'reason': reason,
            'incumbent_trial_id': incumbent['trial_id'],
            'model_ref': incumbent['model_ref'],
            'holdout_evaluator_ref': campaign['plan']['holdout_evaluator_ref'],
        })
        self._advance_holdout(campaign)

    def _advance_holdout(self, campaign: dict[str, Any]) -> None:
        plan = campaign['plan']
        incumbent = self._find_trial(campaign, campaign['incumbent_trial_id'])
        if incumbent is None:
            raise ValueError('Incumbent trial missing during holdout evaluation')
        if campaign['holdout_run_id'] is None:
            if campaign['stop_reason']:
                campaign['status'] = campaign['stop_reason']
                return
            holdout_acceptance: dict[str, Any] = {
                'total_cases': plan['acceptance'].get('holdout_total_cases', 24),
                'min_correct': plan['acceptance'].get('holdout_min_correct', 0),
            }
            for key in ('max_inference_flops_m', 'max_flops_ratio'):
                if plan['acceptance'].get(key) is not None:
                    holdout_acceptance[key] = plan['acceptance'][key]
            holdout_plan: dict[str, Any] = {
                'schema_version': 1,
                'knowledge': plan['knowledge'],
                'hypothesis': f"[holdout:{incumbent['trial_id']}] {incumbent['hypothesis']}",
                'baseline_model_ref': plan['baseline_model_ref'],
                'dataset_ref': plan['dataset_ref'],
                'evaluator_ref': plan['holdout_evaluator_ref'],
                'evaluation_scope': 'holdout',
                'reuse_dataset_ref': incumbent['dataset_ref'],
                'reuse_model_ref': incumbent['model_ref'],
                'architecture': dict(incumbent['architecture']) if incumbent.get('architecture') else None,
                'training_recipe': dict(incumbent['training_recipe']),
                'budget': {
                    'max_tasks': 1,
                    'wall_seconds': plan['budget']['per_trial_wall_seconds'],
                },
                'acceptance': holdout_acceptance,
                'mock': _trial_mock_settings(plan.get('mock'), eval_fixture_key='holdout_eval_fixture'),
            }
            holdout_run_id = self.harness.create(holdout_plan)
            campaign['holdout_run_id'] = holdout_run_id
            self.store.save_campaign(campaign)
            self.store.event(campaign['campaign_id'], 'holdout_started', {
                'holdout_run_id': holdout_run_id,
                'incumbent_trial_id': incumbent['trial_id'],
                'model_ref': incumbent['model_ref'],
            })

        if campaign['stop_reason']:
            self.harness.request_stop(campaign['holdout_run_id'])
        run = self.harness.step(campaign['holdout_run_id'])
        if run['status'] == 'running':
            return
        if run['status'] == 'paused':
            campaign['status'] = 'paused'
            campaign['error'] = f"Holdout evaluation paused: {run['error']}"
            self.store.event(campaign['campaign_id'], 'campaign_paused', {
                'holdout_run_id': run['run_id'],
                'error': run['error'],
            })
            return
        if run['status'] != 'succeeded' or run['report'] is None:
            campaign['status'] = campaign['stop_reason'] or run['status']
            campaign['error'] = run['error']
            self.store.event(campaign['campaign_id'], 'holdout_ended', {
                'holdout_run_id': run['run_id'],
                'status': campaign['status'],
            })
            return

        holdout_usage = run.get('compute_usage') or {'gpu_seconds': 0.0, 'train_tflops': 0.0}
        campaign['total_gpu_seconds'] = round(
            campaign.get('total_gpu_seconds', 0.0) + float(holdout_usage.get('gpu_seconds', 0.0)), 3
        )
        campaign['total_train_tflops'] = round(
            campaign.get('total_train_tflops', 0.0) + float(holdout_usage.get('train_tflops', 0.0)), 3
        )
        campaign['total_cost'] = campaign['total_gpu_seconds']
        counts = {
            name: sum(1 for item in campaign['trials'] if item['decision'] == name)
            for name in ('baseline', 'keep', 'discard', 'crash', 'cancelled')
        }
        total_gpu_s = campaign['total_gpu_seconds']
        gain_pp = run['report'].get('gain_pp', 0.0)
        campaign_gain_per_gpu_hour = round(gain_pp / (total_gpu_s / 3600.0), 4) if total_gpu_s > 0 else None
        campaign['holdout_report'] = {
            **run['report'],
            'campaign_id': campaign['campaign_id'],
            'track': plan['track'],
            'model_family': plan.get('model_family') or (plan['knowledge'].get('scope') or {}).get('model_family'),
            'kb_ref': plan.get('kb_ref'),
            'program_sha256': campaign['program_sha256'],
            'incumbent_trial_id': incumbent['trial_id'],
            'incumbent_architecture': incumbent.get('architecture'),
            'incumbent_config': _incumbent_target_config(plan, incumbent),
            'incumbent_dev_correct': incumbent['dev_correct'],
            'incumbent_dev_total': incumbent['dev_total'],
            'incumbent_complexity': incumbent['complexity_score'],
            'total_trials': len(campaign['trials']),
            'decision_counts': counts,
            'campaign_compute_usage': {
                'total_cost': total_gpu_s,
                'total_gpu_seconds': total_gpu_s,
                'total_train_tflops': campaign['total_train_tflops'],
            },
            'gain_per_gpu_hour': campaign_gain_per_gpu_hour,
        }
        campaign['status'] = 'succeeded'
        self.store.event(campaign['campaign_id'], 'campaign_succeeded', {
            'incumbent_trial_id': incumbent['trial_id'],
            'accepted': campaign['holdout_report']['accepted'],
            'holdout_gain_correct': campaign['holdout_report']['gain_correct'],
            'flops_ratio': campaign['holdout_report']['flops_ratio'],
            'total_gpu_seconds': total_gpu_s,
        })

    def _write_results_tsv(self, campaign: dict[str, Any]) -> Path:
        path = self.root / campaign['campaign_id'] / 'results.tsv'
        write_text(path, render_results_tsv(campaign['trials'], campaign['plan']))
        return path

    def export(self, campaign_id: str) -> Path:
        campaign_id = self.status(campaign_id)['campaign_id']
        with self.store.campaign_lock(campaign_id):
            campaign = self.status(campaign_id)
            directory = self.root / campaign_id
            write_json(directory / 'campaign.json', campaign)
            write_json(directory / 'holdout_report.json', campaign['holdout_report'])
            write_text(directory / 'results.tsv', render_results_tsv(campaign['trials'], campaign['plan']))
            events = ''.join(json.dumps(event, ensure_ascii=False) + '\n' for event in self.events(campaign_id))
            write_text(directory / 'trace.jsonl', events)
            return directory
