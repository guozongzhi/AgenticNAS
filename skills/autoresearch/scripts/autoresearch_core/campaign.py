from __future__ import annotations

from contextlib import contextmanager
import copy
import fcntl
import json
from pathlib import Path
import time
from typing import Any, Iterator
import uuid

from .contracts import (
    CAMPAIGN_CLOSED,
    CampaignPlan,
    Proposal,
    RECORD_FAILURE_KINDS,
    TRIAL_DECISIONS,
    validate_proposal_bounds,
    validate_proposal_scope,
)
from .knowledge_base import KnowledgeBase
from .reporting import render_campaign_report_markdown, render_results_tsv
from .utils import (
    apply_changes,
    canonical_change_signature,
    canonical_config_id,
    compute_2d_pareto_and_hypervolume,
    compute_gain,
    count_config_diffs,
    derive_mutation_family,
    diff_configs,
    inverse_simpson_diversity,
    is_finite_number,
    meets_holdout_target,
    write_json_atomic,
    write_text_atomic,
)


def _check_guardrails(metrics: dict[str, Any], guardrails: dict[str, Any] | None) -> str | None:
    if not guardrails:
        return None
    for name, max_bound in (guardrails.get("max_metrics") or {}).items():
        if name not in metrics or not is_finite_number(metrics[name]):
            return f"missing guardrail metric: {name}"
        if metrics[name] > max_bound:
            return f"guardrail violated: {name}={metrics[name]} > {max_bound}"
    for name, min_bound in (guardrails.get("min_metrics") or {}).items():
        if name not in metrics or not is_finite_number(metrics[name]):
            return f"missing guardrail metric: {name}"
        if metrics[name] < min_bound:
            return f"guardrail violated: {name}={metrics[name]} < {min_bound}"
    return None


def _check_compute_budget(
    compute_val: float | None,
    compute_ratio: float | None,
    compute_spec: dict[str, Any],
) -> str | None:
    c_name = compute_spec["name"]
    max_val = compute_spec.get("max_value")
    if max_val is not None:
        if compute_val is None:
            return f"missing compute metric {c_name}"
        if compute_val > max_val:
            return f"compute budget exceeded: {c_name}={compute_val} > {max_val}"
    max_ratio = compute_spec.get("max_ratio")
    if max_ratio is not None:
        if compute_ratio is None:
            return f"missing compute_ratio ({c_name})"
        if compute_ratio > max_ratio:
            return f"compute budget exceeded: {c_name}_ratio={compute_ratio} > {max_ratio}"
    return None


def _fold_trial_digest(trial: dict[str, Any]) -> dict[str, Any]:
    """Condense an older attempt into a compact structured digest (MLEvolver Context Folding)."""
    return {
        "trial_id": trial["trial_id"],
        "parent_trial_id": trial.get("parent_trial_id"),
        "fidelity": trial.get("fidelity", "full"),
        "operator": trial.get("operator", "baseline" if trial.get("is_baseline") else "refine"),
        "mutation_family": trial.get("mutation_family", "baseline"),
        "change_signature": canonical_change_signature(trial.get("changes") or {}),
        "decision": trial.get("decision") or trial.get("run_status"),
        "failure_kind": trial.get("failure_kind"),
        "gain_pct": trial.get("gain_pct"),
        "compute_ratio": trial.get("compute_ratio"),
        "outcome_digest": (trial.get("decision_reason") or "")[:120],
    }


class CampaignController:
    def __init__(self, runs_dir: Path) -> None:
        self.runs_dir = runs_dir.resolve()
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.latest_file = self.runs_dir / "latest.txt"

    @contextmanager
    def _lock(self, campaign_id: str) -> Iterator[None]:
        c_dir = self.runs_dir / campaign_id
        c_dir.mkdir(parents=True, exist_ok=True)
        lock_file = c_dir / ".campaign.lock"
        with lock_file.open("w", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def resolve_id(self, campaign_id: str) -> str:
        if campaign_id == "latest":
            if not self.latest_file.is_file():
                raise ValueError("No campaigns exist in runs directory yet; run `campaign create` first")
            resolved = self.latest_file.read_text(encoding="utf-8").strip()
            if not resolved:
                raise ValueError("latest.txt is empty")
            return resolved
        if "/" in campaign_id or "\\" in campaign_id or ".." in campaign_id:
            raise ValueError(f"Invalid campaign_id: {campaign_id!r}")
        if not (self.runs_dir / campaign_id / "state.json").is_file():
            raise ValueError(f"Unknown campaign: {campaign_id}")
        return campaign_id

    def _state_path(self, campaign_id: str) -> Path:
        return self.runs_dir / campaign_id / "state.json"

    def _tsv_path(self, campaign_id: str) -> Path:
        return self.runs_dir / campaign_id / "results.tsv"

    def _trace_path(self, campaign_id: str) -> Path:
        return self.runs_dir / campaign_id / "trace.jsonl"

    def _holdout_path(self, campaign_id: str) -> Path:
        return self.runs_dir / campaign_id / "holdout_report.json"

    def _report_md_path(self, campaign_id: str) -> Path:
        return self.runs_dir / campaign_id / "REPORT.md"

    def _append_event(self, campaign_id: str, kind: str, data: dict[str, Any]) -> None:
        trace_file = self._trace_path(campaign_id)
        trace_file.parent.mkdir(parents=True, exist_ok=True)
        record = {"at": round(time.time(), 3), "kind": kind, "data": data}
        with trace_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    @staticmethod
    def _sync_active_ids(state: dict[str, Any]) -> list[str]:
        if "active_trial_ids" in state and isinstance(state["active_trial_ids"], list):
            active_ids = list(state["active_trial_ids"])
        elif state.get("active_trial_id"):
            active_ids = [state["active_trial_id"]]
        else:
            active_ids = []
        state["active_trial_ids"] = active_ids
        state["active_trial_id"] = active_ids[0] if active_ids else None
        return active_ids

    def _save_state(self, state: dict[str, Any]) -> None:
        self._sync_active_ids(state)
        cid = state["campaign_id"]
        write_json_atomic(self._state_path(cid), state)
        write_text_atomic(self._tsv_path(cid), render_results_tsv(state["trials"], state["plan"]))
        if state.get("holdout_report") is not None:
            write_json_atomic(self._holdout_path(cid), state["holdout_report"])

    def status(self, campaign_id: str = "latest") -> dict[str, Any]:
        cid = self.resolve_id(campaign_id)
        state = json.loads(self._state_path(cid).read_text(encoding="utf-8"))
        self._sync_active_ids(state)
        return state

    def events(self, campaign_id: str = "latest") -> list[dict[str, Any]]:
        cid = self.resolve_id(campaign_id)
        path = self._trace_path(cid)
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def create(
        self,
        plan_raw: dict[str, Any],
        *,
        knowledge_base_dir: Path | None = None,
        entry_id: str | None = None,
        entry_revision: str | None = None,
    ) -> dict[str, Any]:
        raw = copy.deepcopy(plan_raw)
        resolved_entry = entry_id or raw.get("knowledge_entry_ref")
        if resolved_entry and knowledge_base_dir is not None and knowledge_base_dir.is_dir():
            knowledge_base = KnowledgeBase(knowledge_base_dir)
            raw["knowledge"] = knowledge_base.freeze_snapshot(resolved_entry, revision=entry_revision)
            raw["knowledge_entry_ref"] = resolved_entry

        plan = CampaignPlan.from_dict(raw).to_dict()
        cid = f"cmp-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        with self._lock(cid):
            state = {
                "campaign_id": cid,
                "status": "running",
                "stop_reason": None,
                "error": None,
                "created_at": round(time.time(), 3),
                "plan": plan,
                "knowledge_sha256": plan["knowledge"].get("content_sha256"),
                "incumbent_trial_id": None,
                "active_trial_id": None,
                "active_trial_ids": [],
                "rejected_proposals_count": 0,
                "baseline_primary_value": None,
                "baseline_compute_value": None,
                "baseline_cost_value": None,
                "total_cost": 0.0,
                "trials": [],
                "holdout_report": None,
            }
            self._save_state(state)
            self._append_event(cid, "campaign_created", {
                "track": plan["track"],
                "model_family": plan["model_family"],
                "knowledge_entry_ref": f"{plan['knowledge_entry_ref']}@{plan['knowledge']['revision']}",
                "max_parallel_trials": plan["budget"].get("max_parallel_trials", 1),
            })
            write_text_atomic(self.latest_file, cid + "\n")
            return state

    def begin_baseline(self, campaign_id: str = "latest") -> dict[str, Any]:
        cid = self.resolve_id(campaign_id)
        with self._lock(cid):
            state = self.status(cid)
            if state["status"] in CAMPAIGN_CLOSED:
                raise ValueError(f"Campaign already closed with status={state['status']}")
            if state["trials"]:
                return state["trials"][0]
            plan = state["plan"]
            base_cfg = copy.deepcopy(plan["base_config"])
            trial = {
                "trial_id": "trial-000",
                "index": 0,
                "parent_trial_id": None,
                "inspiration_trial_ids": [],
                "is_baseline": True,
                "fidelity": "full",
                "operator": "baseline",
                "mutation_family": "baseline",
                "hypothesis": plan["base_hypothesis"],
                "changes": {},
                "candidate_config": base_cfg,
                "config_id": canonical_config_id(base_cfg),
                "frozen_architecture": copy.deepcopy(plan["base_architecture"]) if plan["track"] == "hpo" else None,
                "frozen_training_recipe": copy.deepcopy(plan["base_training_recipe"]) if plan["track"] == "architecture" else None,
                "reuse_simulation": False,
                "complexity_score": 0,
                "expected_primary": None,
                "expected_compute_ratio": None,
                "prediction_calibration": None,
                "run_status": "awaiting_result",
                "decision": None,
                "decision_reason": None,
                "failure_kind": None,
                "guardrail_violated": False,
                "compute_violated": False,
                "audit_warnings": [],
                "primary_value": None,
                "gain": None,
                "gain_pct": None,
                "compute_value": None,
                "compute_ratio": None,
                "cost_value": 0.0,
                "cumulative_cost": 0.0,
                "metrics": {},
                "artifacts": {},
                "external_jobs": [],
                "note": None,
                "started_at": round(time.time(), 3),
                "finished_at": None,
            }
            state["trials"].append(trial)
            state["active_trial_ids"] = ["trial-000"]
            self._save_state(state)
            self._append_event(cid, "baseline_started", {"trial_id": "trial-000", "config_id": trial["config_id"]})
            return trial

    @staticmethod
    def _find_trial(state: dict[str, Any], trial_id: str | None) -> dict[str, Any] | None:
        if not trial_id:
            return None
        for item in state["trials"]:
            if item["trial_id"] == trial_id:
                return item
        return None

    def inspect_trial(self, campaign_id: str, trial_id: str) -> dict[str, Any]:
        """Retrieve complete unfolded record and leaf-level config diffs for any trial."""
        cid = self.resolve_id(campaign_id)
        state = self.status(cid)
        trial = self._find_trial(state, trial_id)
        if trial is None:
            raise ValueError(f"Unknown trial_id {trial_id!r} in campaign {cid}")
        base_cfg = state["plan"]["base_config"]
        parent = self._find_trial(state, trial.get("parent_trial_id"))
        return {
            "campaign_id": cid,
            "trial": trial,
            "diff_vs_baseline": diff_configs(base_cfg, trial["candidate_config"]),
            "diff_vs_parent": diff_configs(parent["candidate_config"], trial["candidate_config"]) if parent else {},
        }

    def get_context(self, campaign_id: str = "latest", *, recent_window: int = 6) -> dict[str, Any]:
        cid = self.resolve_id(campaign_id)
        state = self.status(cid)
        plan = state["plan"]
        incumbent = self._find_trial(state, state["incumbent_trial_id"])
        active_ids = self._sync_active_ids(state)
        active_trials = [self._find_trial(state, tid) for tid in active_ids]
        active_trials = [t for t in active_trials if t is not None]

        max_trials = int(plan["budget"]["max_trials"])
        max_parallel = int(plan["budget"].get("max_parallel_trials", 1))
        cost_spec = plan["budget"]["cost_metric"]
        max_cost = cost_spec.get("max_total")
        used_cost = float(state.get("total_cost", 0.0))
        remaining_trials = max(0, max_trials - len(state["trials"]))
        remaining_cost = round(max(0.0, float(max_cost) - used_cost), 4) if max_cost is not None else None

        # Consecutive non-keep count over decided full-fidelity candidate trials
        consecutive_non_keep = 0
        for trial in reversed(state["trials"]):
            if trial.get("is_baseline") or trial.get("decision") is None or trial.get("fidelity", "full") != "full":
                continue
            if trial.get("failure_kind") == "infra_flake":
                continue
            if trial["decision"] == "keep":
                break
            consecutive_non_keep += 1

        non_cancelled_candidates = [
            t for t in state["trials"]
            if not t.get("is_baseline")
            and t.get("changes")
            and t.get("decision") != "cancelled"
            and t.get("failure_kind") != "infra_flake"
        ]
        evaluated_signatures = [canonical_change_signature(t["changes"]) for t in non_cancelled_candidates]
        eval_sig_set = set(evaluated_signatures)

        # Principle-Level Diversity & Untouched Axes (arXiv:2610.24291)
        family_counts: dict[str, int] = {}
        touched_fields: set[str] = set()
        for t in non_cancelled_candidates:
            fam = t.get("mutation_family") or derive_mutation_family(t["changes"])
            family_counts[fam] = family_counts.get(fam, 0) + 1
            touched_fields.update(t["changes"].keys())
        eff_principles, dom_fam, dom_share = inverse_simpson_diversity(family_counts)
        untouched_fields = [f for f in plan["mutable_fields"] if f not in touched_fields]
        collapse_warning = (
            len(non_cancelled_candidates) >= 4
            and dom_share >= 0.70
            and len(plan["mutable_fields"]) >= 2
            and bool(untouched_fields)
        )

        # Multi-fidelity ready-to-promote proxy winners
        full_evaluated_cfg_ids = {
            t["config_id"] for t in state["trials"]
            if t.get("fidelity", "full") == "full"
            and t.get("decision") != "cancelled"
            and t.get("failure_kind") != "infra_flake"
        }
        ready_proxies = [
            {
                "trial_id": t["trial_id"],
                "config_id": t["config_id"],
                "changes": t["changes"],
                "proxy_primary_value": t["primary_value"],
                "proxy_gain_pct": t["gain_pct"],
                "proxy_compute_ratio": t["compute_ratio"],
            }
            for t in state["trials"]
            if t.get("decision") == "proxy_pass" and t["config_id"] not in full_evaluated_cfg_ids
        ]

        # High-surprise trials from Predict-Then-Verify calibration
        high_surprise = [
            {
                "trial_id": t["trial_id"],
                "changes": t["changes"],
                "calibration": t["prediction_calibration"],
            }
            for t in state["trials"]
            if t.get("prediction_calibration") and t["prediction_calibration"].get("high_surprise")
        ]

        # Aggregate anti-reward-hacking audit warnings
        audit_warnings = [
            {"trial_id": t["trial_id"], "warnings": t["audit_warnings"]}
            for t in state["trials"]
            if t.get("audit_warnings")
        ]

        entry_patterns = plan["knowledge"].get("patterns") or []
        untried_priors = [
            {
                "pattern_id": p.get("pattern_id"),
                "title": p.get("title"),
                "suggested_changes": p.get("suggested_changes"),
                "direction": (p.get("effect") or {}).get("direction"),
                "mean_gain_pct": (p.get("stats") or {}).get("mean_gain_pct"),
                "mean_compute_ratio": (p.get("stats") or {}).get("mean_compute_ratio"),
            }
            for p in entry_patterns
            if p.get("change_signature") not in eval_sig_set
        ]

        p_spec = plan["acceptance"]["primary_metric"]
        c_spec = plan["acceptance"]["compute_metric"]
        pareto_frontier, compute_elites, pareto_hv = compute_2d_pareto_and_hypervolume(
            state["trials"],
            primary_direction=p_spec["direction"],
            compute_direction=c_spec.get("direction", "minimize"),
            baseline_primary=state.get("baseline_primary_value"),
            max_compute_ratio=c_spec.get("max_ratio"),
        )

        # MLEvolver Context Folding: older trials folded into 1-line digests, recent_window kept rich
        win = max(1, int(recent_window))
        older_trials = state["trials"][:-win] if len(state["trials"]) > win else []
        recent_trials = state["trials"][-win:] if state["trials"] else []

        scope = plan["knowledge"].get("scope") or {}
        return {
            "campaign_id": cid,
            "status": state["status"],
            "track": plan["track"],
            "model_family": plan["model_family"],
            "knowledge_entry_ref": plan["knowledge_entry_ref"],
            "active_trial": active_trials[0] if active_trials else None,
            "active_trials": active_trials,
            "incumbent": {
                "trial_id": incumbent["trial_id"],
                "config": incumbent["candidate_config"],
                "config_id": incumbent["config_id"],
                "primary_value": incumbent["primary_value"],
                "compute_value": incumbent["compute_value"],
                "compute_ratio": incumbent["compute_ratio"],
                "complexity_score": incumbent["complexity_score"],
                "model_ref": (incumbent.get("artifacts") or {}).get("model_ref"),
                "dataset_ref": (incumbent.get("artifacts") or {}).get("dataset_ref") or plan["dataset_ref"],
            } if incumbent else None,
            "pareto_frontier": pareto_frontier,
            "compute_elites": compute_elites,
            "pareto_hypervolume": pareto_hv,
            "mutable_fields": plan["mutable_fields"],
            "param_bounds": scope.get("param_bounds") or {},
            "forbidden_ops": scope.get("forbidden_ops") or [],
            "primary_metric": p_spec,
            "compute_metric": c_spec,
            "guardrails": plan["acceptance"].get("guardrails") or {},
            "cost_metric": cost_spec,
            "remaining_budget": {
                "remaining_trials": remaining_trials,
                "remaining_cost": remaining_cost,
                "used_cost": used_cost,
                "max_parallel_trials": max_parallel,
                "open_parallel_slots": max(0, max_parallel - len(active_ids)),
            },
            "folded_history": [_fold_trial_digest(t) for t in older_trials],
            "recent_trials": recent_trials,
            "search_diagnostics": {
                "consecutive_non_keep": consecutive_non_keep,
                "plateau_warning": consecutive_non_keep >= 3,
                "rejected_proposals_count": state.get("rejected_proposals_count", 0),
                "untouched_mutable_fields": untouched_fields,
                "principle_diversity": {
                    "effective_principle_count": eff_principles,
                    "dominant_family": dom_fam,
                    "dominant_family_share": dom_share,
                    "family_counts": family_counts,
                    "principle_collapse_warning": collapse_warning,
                },
                "ready_to_promote_proxies": ready_proxies,
                "high_surprise_trials": high_surprise,
                "audit_warnings": audit_warnings,
                "evaluated_signatures": evaluated_signatures,
                "untried_knowledge_priors": untried_priors,
                "known_anti_patterns": plan["knowledge"].get("anti_patterns") or [],
            },
            "evaluators": {
                "dev_evaluator_ref": plan["dev_evaluator_ref"],
                "holdout_evaluator_ref": plan["holdout_evaluator_ref"],
            },
            "results_tsv": render_results_tsv(state["trials"], plan),
        }

    def propose(
        self,
        campaign_id: str,
        proposal: Proposal,
        *,
        allow_repeat: bool = False,
        force_anti_pattern: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        cid = self.resolve_id(campaign_id)
        with self._lock(cid):
            state = self.status(cid)
            if state["status"] in CAMPAIGN_CLOSED:
                raise ValueError(f"Campaign already closed with status={state['status']}")
            if state["status"] == "awaiting_holdout":
                raise ValueError(
                    "Exploration budget reached (`awaiting_holdout`); no new training proposals allowed. "
                    "Run `campaign finalize` on `incumbent.model_ref`."
                )

            plan = state["plan"]
            active_ids = self._sync_active_ids(state)
            max_parallel = int(plan["budget"].get("max_parallel_trials", 1))
            if not dry_run and len(active_ids) >= max_parallel:
                raise ValueError(
                    f"Parallel active trial limit reached ({len(active_ids)}/{max_parallel}: {active_ids}); "
                    "reconcile remote MCP status and call `campaign record` before proposing more."
                )

            incumbent = self._find_trial(state, state["incumbent_trial_id"])
            if incumbent is None:
                raise ValueError("Baseline trial-000 must succeed before submitting candidate proposals")

            parent_id = proposal.parent_trial_id or incumbent["trial_id"]
            parent = self._find_trial(state, parent_id)
            if parent is None:
                raise ValueError(f"Unknown parent_trial_id: {parent_id!r}")
            if parent.get("run_status") != "succeeded":
                raise ValueError(f"Parent trial {parent_id} did not succeed (status={parent.get('run_status')})")
            for insp_id in proposal.inspiration_trial_ids:
                if self._find_trial(state, insp_id) is None:
                    raise ValueError(f"Unknown inspiration trial_id: {insp_id!r}")

            if not dry_run and len(state["trials"]) >= int(plan["budget"]["max_trials"]):
                state["status"] = "awaiting_holdout"
                state["stop_reason"] = "max_trials_reached"
                self._save_state(state)
                raise ValueError("max_trials reached; run `campaign finalize` on incumbent")

            scope = plan["knowledge"].get("scope") or {}
            try:
                validate_proposal_scope(proposal, plan["mutable_fields"])
                validate_proposal_bounds(
                    proposal,
                    scope.get("param_bounds"),
                    forbidden_ops=scope.get("forbidden_ops"),
                )

                cand_cfg = apply_changes(parent["candidate_config"], proposal.changes)
                cand_id = canonical_config_id(cand_cfg)
                if cand_id == parent["config_id"]:
                    raise ValueError(f"No-op proposal: candidate_config is identical to parent {parent_id}")

                if not allow_repeat:
                    for existing in state["trials"]:
                        if existing.get("decision") == "cancelled" or existing.get("failure_kind") == "infra_flake":
                            continue
                        if existing["config_id"] != cand_id:
                            continue
                        ex_fid = existing.get("fidelity", "full")
                        if ex_fid == proposal.fidelity:
                            raise ValueError(
                                f"Duplicate configuration at fidelity={proposal.fidelity!r}: "
                                f"matches {existing['trial_id']} (config_id={cand_id})"
                            )
                        if ex_fid == "full" and proposal.fidelity in {"smoke", "proxy"}:
                            raise ValueError(
                                f"Configuration {cand_id} was already evaluated at full fidelity in {existing['trial_id']}"
                            )

                # Derive effective changes relative to parent for signature & principle tracking
                effective_changes = {
                    key: val
                    for key, val in proposal.changes.items()
                    if key in diff_configs(parent["candidate_config"], cand_cfg)
                    or diff_configs(parent["candidate_config"], cand_cfg)
                }
                sig = canonical_change_signature(effective_changes)
                if not force_anti_pattern:
                    for anti in plan["knowledge"].get("anti_patterns") or []:
                        if anti.get("change_signature") == sig:
                            raise ValueError(
                                f"Blocked by knowledge_base anti-pattern {anti.get('pattern_id')} "
                                f"({anti.get('failure_type')}): {anti.get('observed_failure')}. "
                                "Pass --force-anti-pattern to override."
                            )
            except ValueError as exc:
                if not dry_run:
                    state["rejected_proposals_count"] = int(state.get("rejected_proposals_count", 0)) + 1
                    self._save_state(state)
                    self._append_event(cid, "proposal_rejected", {
                        "parent_trial_id": parent_id,
                        "operator": proposal.operator,
                        "fidelity": proposal.fidelity,
                        "hypothesis": proposal.hypothesis,
                        "changes": proposal.changes,
                        "error": str(exc),
                    })
                raise

            complexity = count_config_diffs(plan["base_config"], cand_cfg)
            mut_family = derive_mutation_family(proposal.changes)
            if dry_run:
                return {
                    "dry_run": True,
                    "valid": True,
                    "parent_trial_id": parent_id,
                    "fidelity": proposal.fidelity,
                    "operator": proposal.operator,
                    "mutation_family": mut_family,
                    "candidate_config": cand_cfg,
                    "config_id": cand_id,
                    "complexity_score": complexity,
                }

            idx = len(state["trials"])
            trial_id = f"trial-{idx:03d}"
            trial = {
                "trial_id": trial_id,
                "index": idx,
                "parent_trial_id": parent_id,
                "inspiration_trial_ids": list(proposal.inspiration_trial_ids),
                "is_baseline": False,
                "fidelity": proposal.fidelity,
                "operator": proposal.operator,
                "mutation_family": mut_family,
                "hypothesis": proposal.hypothesis,
                "changes": copy.deepcopy(proposal.changes),
                "candidate_config": cand_cfg,
                "config_id": cand_id,
                "frozen_architecture": copy.deepcopy(plan["base_architecture"]) if plan["track"] == "hpo" else None,
                "frozen_training_recipe": copy.deepcopy(plan["base_training_recipe"]) if plan["track"] == "architecture" else None,
                "reuse_simulation": proposal.reuse_simulation,
                "complexity_score": complexity,
                "expected_primary": proposal.expected_primary,
                "expected_compute_ratio": proposal.expected_compute_ratio,
                "prediction_calibration": None,
                "run_status": "awaiting_result",
                "decision": None,
                "decision_reason": None,
                "failure_kind": None,
                "guardrail_violated": False,
                "compute_violated": False,
                "audit_warnings": [],
                "primary_value": None,
                "gain": None,
                "gain_pct": None,
                "compute_value": None,
                "compute_ratio": None,
                "cost_value": 0.0,
                "cumulative_cost": state["total_cost"],
                "metrics": {},
                "artifacts": {},
                "external_jobs": [],
                "note": None,
                "started_at": round(time.time(), 3),
                "finished_at": None,
            }
            state["trials"].append(trial)
            active_ids.append(trial_id)
            state["active_trial_ids"] = active_ids
            self._save_state(state)
            self._append_event(cid, "trial_proposed", {
                "trial_id": trial_id,
                "parent_trial_id": parent_id,
                "inspiration_trial_ids": proposal.inspiration_trial_ids,
                "fidelity": proposal.fidelity,
                "operator": proposal.operator,
                "mutation_family": mut_family,
                "config_id": cand_id,
                "changes": proposal.changes,
                "hypothesis": proposal.hypothesis,
            })
            return trial

    def record(
        self,
        campaign_id: str,
        *,
        trial_id: str | None = None,
        status: str = "succeeded",
        failure_kind: str | None = None,
        metrics: dict[str, Any] | None = None,
        cost: dict[str, Any] | None = None,
        artifacts: dict[str, Any] | None = None,
        external_jobs: list[dict[str, Any]] | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        if status not in {"succeeded", "failed", "timeout", "crash", "cancelled"}:
            raise ValueError(f"Unsupported record status: {status!r}")
        if failure_kind is not None and failure_kind not in RECORD_FAILURE_KINDS:
            raise ValueError(f"Unsupported --failure-kind {failure_kind!r}; expected one of {RECORD_FAILURE_KINDS}")

        cid = self.resolve_id(campaign_id)
        with self._lock(cid):
            state = self.status(cid)
            if state["status"] in CAMPAIGN_CLOSED:
                raise ValueError(f"Campaign already closed with status={state['status']}")
            active_ids = self._sync_active_ids(state)
            if trial_id:
                target_id = trial_id
            elif len(active_ids) == 1:
                target_id = active_ids[0]
            elif len(active_ids) > 1:
                raise ValueError(
                    f"Multiple parallel trials are active ({active_ids}); specify `--trial <trial_id>` explicitly"
                )
            else:
                raise ValueError("No active trial awaiting_result; run `baseline` or `propose` first")

            trial = self._find_trial(state, target_id)
            if trial is None:
                raise ValueError(f"Unknown trial_id: {target_id}")
            if trial["decision"] is not None:
                raise ValueError(f"Trial {target_id} is already decided ({trial['decision']})")

            plan = state["plan"]
            p_spec = plan["acceptance"]["primary_metric"]
            c_spec = plan["acceptance"]["compute_metric"]
            cost_spec = plan["budget"]["cost_metric"]
            cost_name = cost_spec["name"]

            cost_dict = dict(cost or {})
            raw_cost = cost_dict.get(cost_name, 0.0)
            if not is_finite_number(raw_cost) or raw_cost < 0:
                raise ValueError(f"Invalid cost value for {cost_name}: {raw_cost!r}")
            trial["cost_value"] = round(float(raw_cost), 4)
            state["total_cost"] = round(float(state["total_cost"]) + trial["cost_value"], 4)
            trial["cumulative_cost"] = state["total_cost"]

            trial["run_status"] = status
            trial["finished_at"] = round(time.time(), 3)
            trial["artifacts"] = dict(artifacts or {})
            trial["external_jobs"] = list(external_jobs or [])
            trial["note"] = note

            if status == "cancelled":
                trial["decision"] = "cancelled"
                trial["decision_reason"] = note or "trial cancelled"
            elif status != "succeeded":
                resolved_fk = failure_kind or ("timeout" if status == "timeout" else "other")
                trial["failure_kind"] = resolved_fk
                trial["decision"] = "crash"
                trial["decision_reason"] = (
                    f"[{resolved_fk}] {note}" if note else f"[{resolved_fk}] MCP trial ended with status={status}"
                )
                if trial["is_baseline"]:
                    state["status"] = "failed"
                    state["error"] = f"Baseline trial-000 failed: {trial['decision_reason']}"
            else:
                m_dict = dict(metrics or {})
                p_name = p_spec["name"]
                if p_name not in m_dict or not is_finite_number(m_dict[p_name]):
                    raise ValueError(f"Missing or non-finite primary metric {p_name!r} in --metrics")
                p_val = float(m_dict[p_name])

                c_name = c_spec["name"]
                c_val: float | None = None
                if c_name in m_dict and m_dict[c_name] is not None:
                    if not is_finite_number(m_dict[c_name]) or m_dict[c_name] <= 0:
                        raise ValueError(f"Compute metric {c_name!r} must be a positive finite number")
                    c_val = float(m_dict[c_name])

                trial["metrics"] = m_dict
                trial["primary_value"] = p_val
                trial["compute_value"] = c_val

                if trial["is_baseline"]:
                    state["baseline_primary_value"] = p_val
                    state["baseline_compute_value"] = c_val
                    state["baseline_cost_value"] = trial["cost_value"]
                    trial["gain"] = 0.0
                    trial["gain_pct"] = 0.0
                    trial["compute_ratio"] = 1.0 if c_val is not None else None
                    trial["decision"] = "baseline"
                    trial["decision_reason"] = f"established baseline ({p_name}={p_val})"
                    state["incumbent_trial_id"] = trial["trial_id"]
                else:
                    base_p = float(state["baseline_primary_value"])
                    gain, gain_pct = compute_gain(p_val, base_p, p_spec["direction"])
                    trial["gain"] = gain
                    trial["gain_pct"] = gain_pct
                    base_c = state.get("baseline_compute_value")
                    if c_val is not None and base_c:
                        trial["compute_ratio"] = round(c_val / float(base_c), 4)

                    # Predict-Then-Verify calibration (Heuresis Curiosity surprise)
                    if trial.get("expected_primary") is not None or trial.get("expected_compute_ratio") is not None:
                        p_err = (
                            round(abs(p_val - float(trial["expected_primary"])), 6)
                            if trial.get("expected_primary") is not None
                            else None
                        )
                        c_err = (
                            round(abs(float(trial["compute_ratio"]) - float(trial["expected_compute_ratio"])), 4)
                            if (trial.get("expected_compute_ratio") is not None and trial.get("compute_ratio") is not None)
                            else None
                        )
                        denom = max(abs(base_p), 1e-9)
                        high_surp = bool(
                            (p_err is not None and (p_err / denom) > 0.05)
                            or (c_err is not None and c_err > 0.12)
                        )
                        trial["prediction_calibration"] = {
                            "expected_primary": trial.get("expected_primary"),
                            "actual_primary": p_val,
                            "primary_abs_error": p_err,
                            "expected_compute_ratio": trial.get("expected_compute_ratio"),
                            "actual_compute_ratio": trial.get("compute_ratio"),
                            "compute_ratio_abs_error": c_err,
                            "high_surprise": high_surp,
                        }

                    incumbent = self._find_trial(state, state["incumbent_trial_id"])
                    assert incumbent is not None
                    g_viol = _check_guardrails(m_dict, plan["acceptance"].get("guardrails"))
                    c_viol = _check_compute_budget(c_val, trial["compute_ratio"], c_spec)
                    trial["guardrail_violated"] = g_viol is not None
                    trial["compute_violated"] = c_viol is not None

                    fidelity = trial.get("fidelity", "full")
                    if fidelity in {"smoke", "proxy"}:
                        # Low-fidelity screening NEVER overwrites the full-fidelity incumbent!
                        if g_viol is not None or c_viol is not None:
                            trial["decision"] = "proxy_discard"
                            trial["decision_reason"] = f"[{fidelity}] {g_viol or c_viol}"
                        else:
                            delta, _ = compute_gain(p_val, float(incumbent["primary_value"]), p_spec["direction"])
                            tie_tol = float(p_spec.get("tie_tolerance", 0.0))
                            if delta >= -tie_tol:
                                trial["decision"] = "proxy_pass"
                                trial["decision_reason"] = (
                                    f"[{fidelity} screen passed] delta={delta:+.4g}, "
                                    f"{c_spec['name']}_ratio={trial['compute_ratio']}; eligible to promote to --fidelity full"
                                )
                            else:
                                trial["decision"] = "proxy_discard"
                                trial["decision_reason"] = f"[{fidelity} screen weak] delta={delta:+.4g}"
                    else:
                        if g_viol is not None:
                            trial["decision"] = "discard"
                            trial["decision_reason"] = g_viol
                        elif c_viol is not None:
                            trial["decision"] = "discard"
                            trial["decision_reason"] = c_viol
                        else:
                            delta, _ = compute_gain(p_val, float(incumbent["primary_value"]), p_spec["direction"])
                            min_gain = float(p_spec.get("min_gain", 0.0))
                            tie_tol = float(p_spec.get("tie_tolerance", 0.0))
                            inc_c = incumbent.get("compute_value")
                            c_dir = c_spec.get("direction", "minimize")
                            better_compute = (
                                c_val is not None
                                and inc_c is not None
                                and ((c_dir == "minimize" and c_val < inc_c) or (c_dir == "maximize" and c_val > inc_c))
                            )
                            if delta >= min_gain and (min_gain > 0 or delta > tie_tol):
                                trial["decision"] = "keep"
                                trial["decision_reason"] = (
                                    f"gain win: {p_name} improved by {delta:+.4g} (>= {min_gain}), "
                                    f"{c_spec['name']}_ratio={trial['compute_ratio']}"
                                )
                                state["incumbent_trial_id"] = trial["trial_id"]
                            elif abs(delta) <= tie_tol and better_compute:
                                trial["decision"] = "keep"
                                trial["decision_reason"] = (
                                    f"compute win: within tie_tolerance ({delta:+.4g} <= {tie_tol}) "
                                    f"with better {c_spec['name']} ({c_val} vs {inc_c})"
                                )
                                state["incumbent_trial_id"] = trial["trial_id"]
                            elif abs(delta) <= tie_tol and trial["complexity_score"] < incumbent["complexity_score"]:
                                trial["decision"] = "keep"
                                trial["decision_reason"] = (
                                    f"simplicity win: within tie_tolerance ({delta:+.4g} <= {tie_tol}) "
                                    f"with simpler config ({trial['complexity_score']} < {incumbent['complexity_score']})"
                                )
                                state["incumbent_trial_id"] = trial["trial_id"]
                            else:
                                trial["decision"] = "discard"
                                trial["decision_reason"] = (
                                    f"delta={delta:+.4g} < min_gain={min_gain} "
                                    f"({c_spec['name']}={c_val} vs {inc_c})"
                                )

                # Anti-Reward-Hacking Sanity Auditor (Heuresis §5.3)
                warnings: list[str] = []
                if trial.get("fidelity", "full") == "full":
                    if not (trial.get("artifacts") or {}).get("model_ref"):
                        warnings.append("missing_model_ref_on_full_trial")
                    base_cost = state.get("baseline_cost_value") or 0.0
                    if not trial["is_baseline"] and base_cost > 0 and trial["cost_value"] <= 0:
                        warnings.append("zero_cost_reported_on_full_trial")
                    if not trial["is_baseline"] and trial.get("gain_pct") is not None and trial["gain_pct"] > 50.0:
                        warnings.append("extreme_gain_jump_verify_evaluator_and_multiseed")
                trial["audit_warnings"] = warnings

            state["active_trial_ids"] = [tid for tid in active_ids if tid != target_id]

            # Transition to awaiting_holdout only when no parallel trials remain in flight
            if state["status"] == "running" and not state["active_trial_ids"]:
                max_cost = cost_spec.get("max_total")
                if max_cost is not None and state["total_cost"] >= float(max_cost):
                    state["status"] = "awaiting_holdout"
                    state["stop_reason"] = "cost_budget_reached"
                elif len(state["trials"]) >= int(plan["budget"]["max_trials"]):
                    state["status"] = "awaiting_holdout"
                    state["stop_reason"] = "max_trials_reached"

            self._save_state(state)
            self._append_event(cid, "trial_recorded", {
                "trial_id": trial["trial_id"],
                "fidelity": trial.get("fidelity", "full"),
                "decision": trial["decision"],
                "failure_kind": trial.get("failure_kind"),
                "reason": trial["decision_reason"],
                "audit_warnings": trial.get("audit_warnings", []),
                "incumbent_trial_id": state["incumbent_trial_id"],
                "campaign_status": state["status"],
            })
            return trial

    def finalize(
        self,
        campaign_id: str,
        *,
        status: str = "succeeded",
        metrics: dict[str, Any] | None = None,
        cost: dict[str, Any] | None = None,
        artifacts: dict[str, Any] | None = None,
        external_jobs: list[dict[str, Any]] | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        cid = self.resolve_id(campaign_id)
        with self._lock(cid):
            state = self.status(cid)
            if state["status"] in CAMPAIGN_CLOSED:
                return state
            active_ids = self._sync_active_ids(state)
            if active_ids:
                raise ValueError(f"Active trial(s) {active_ids} must be recorded before finalize")
            incumbent = self._find_trial(state, state["incumbent_trial_id"])
            if incumbent is None:
                raise ValueError("Cannot finalize holdout without a succeeded baseline/incumbent")

            plan = state["plan"]
            p_spec = plan["acceptance"]["primary_metric"]
            c_spec = plan["acceptance"]["compute_metric"]
            cost_spec = plan["budget"]["cost_metric"]
            cost_name = cost_spec["name"]

            art_dict = dict(artifacts or {})
            inc_model_ref = (incumbent.get("artifacts") or {}).get("model_ref")
            if inc_model_ref and art_dict.get("model_ref") and art_dict["model_ref"] != inc_model_ref:
                raise ValueError(
                    f"Holdout model_ref mismatch: expected incumbent {inc_model_ref!r}, got {art_dict['model_ref']!r}"
                )

            cost_dict = dict(cost or {})
            eval_cost = float(cost_dict.get(cost_name, 0.0) or 0.0)
            state["total_cost"] = round(float(state["total_cost"]) + eval_cost, 4)

            if status != "succeeded":
                state["status"] = "failed"
                state["error"] = note or f"Holdout evaluation failed with status={status}"
                self._save_state(state)
                return state

            m_dict = dict(metrics or {})
            p_name = p_spec["name"]
            if p_name not in m_dict or not is_finite_number(m_dict[p_name]):
                raise ValueError(f"Missing or non-finite holdout primary metric {p_name!r}")
            cand_p = float(m_dict[p_name])
            base_p_raw = m_dict.get(f"baseline_{p_name}", state.get("baseline_primary_value"))
            base_p = float(base_p_raw) if is_finite_number(base_p_raw) else None
            gain, gain_pct = compute_gain(cand_p, base_p, p_spec["direction"]) if base_p is not None else (None, None)

            c_name = c_spec["name"]
            cand_c_raw = m_dict.get(c_name, incumbent.get("compute_value"))
            cand_c = float(cand_c_raw) if is_finite_number(cand_c_raw) else None
            base_c_raw = m_dict.get(f"baseline_{c_name}", state.get("baseline_compute_value"))
            base_c = float(base_c_raw) if is_finite_number(base_c_raw) else None
            comp_ratio = round(cand_c / base_c, 4) if (cand_c is not None and base_c) else None

            c_viol = _check_compute_budget(cand_c, comp_ratio, c_spec)
            g_viol = _check_guardrails(m_dict, plan["acceptance"].get("guardrails"))
            target_ok = meets_holdout_target(cand_p, base_p, p_spec)
            accepted = target_ok and (c_viol is None) and (g_viol is None)

            total_cost = state["total_cost"]
            gain_per_cost = round(gain_pct / total_cost, 4) if (gain_pct is not None and total_cost > 0) else None
            counts = {
                dec: sum(1 for item in state["trials"] if item.get("decision") == dec)
                for dec in TRIAL_DECISIONS
            }
            _, _, pareto_hv = compute_2d_pareto_and_hypervolume(
                state["trials"],
                primary_direction=p_spec["direction"],
                compute_direction=c_spec.get("direction", "minimize"),
                baseline_primary=state.get("baseline_primary_value"),
                max_compute_ratio=c_spec.get("max_ratio"),
            )

            state["holdout_report"] = {
                "campaign_id": cid,
                "track": plan["track"],
                "model_family": plan["model_family"],
                "knowledge_entry_ref": plan["knowledge_entry_ref"],
                "knowledge_sha256": state["knowledge_sha256"],
                "evaluator_ref": plan["holdout_evaluator_ref"],
                "incumbent_trial_id": incumbent["trial_id"],
                "incumbent_config": copy.deepcopy(incumbent["candidate_config"]),
                "incumbent_complexity": incumbent["complexity_score"],
                "model_ref": art_dict.get("model_ref") or inc_model_ref,
                "primary_metric_name": p_name,
                "primary_direction": p_spec["direction"],
                "baseline_primary_value": base_p,
                "candidate_primary_value": cand_p,
                "gain": gain,
                "gain_pct": gain_pct,
                "compute_metric_name": c_name,
                "baseline_compute_value": base_c,
                "candidate_compute_value": cand_c,
                "compute_ratio": comp_ratio,
                "compute_within_budget": c_viol is None,
                "guardrails_passed": g_viol is None,
                "accepted": accepted,
                "rejection_reason": c_viol or g_viol or (None if target_ok else "holdout target not met"),
                "metrics": m_dict,
                "pareto_hypervolume": pareto_hv,
                "cost_metric_name": cost_name,
                "total_cost": total_cost,
                "cost_unit": cost_spec.get("unit", ""),
                "gain_per_cost": gain_per_cost,
                "total_trials": len(state["trials"]),
                "rejected_proposals_count": state.get("rejected_proposals_count", 0),
                "decision_counts": counts,
                "external_jobs": list(external_jobs or []),
                "note": note,
            }
            state["status"] = "succeeded"
            self._save_state(state)
            self._append_event(cid, "holdout_finalized", {
                "incumbent_trial_id": incumbent["trial_id"],
                "accepted": accepted,
                "gain_pct": gain_pct,
                "compute_ratio": comp_ratio,
            })

        # Auto-write REPORT.md after releasing lock
        self.write_report(cid)
        return self.status(cid)

    def write_report(self, campaign_id: str = "latest") -> tuple[Path, str]:
        cid = self.resolve_id(campaign_id)
        state = self.status(cid)
        ctx = self.get_context(cid)
        md_text = render_campaign_report_markdown(state, ctx)
        report_path = self._report_md_path(cid)
        write_text_atomic(report_path, md_text)
        return report_path, md_text

    def stop(self, campaign_id: str = "latest", reason: str = "user_stopped") -> dict[str, Any]:
        cid = self.resolve_id(campaign_id)
        with self._lock(cid):
            state = self.status(cid)
            if state["status"] in CAMPAIGN_CLOSED:
                return state
            active_ids = self._sync_active_ids(state)
            if state["incumbent_trial_id"] and not active_ids:
                state["status"] = "awaiting_holdout"
                state["stop_reason"] = reason
            else:
                state["status"] = "cancelled"
                state["stop_reason"] = reason
            self._save_state(state)
            self._append_event(cid, "campaign_stopped", {"reason": reason, "status": state["status"]})
            return state
