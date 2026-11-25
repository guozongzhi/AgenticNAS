#!/usr/bin/env python3
"""Self-contained control-plane CLI for the AutoResearch Agent Skill.

Zero third-party dependencies (Python 3.10+ standard library only).
Provides pure-file-backed governance for BYO-MCP autonomous model optimization:
  1. Workspace scaffolding (`init`), safe seed customization & NAS->HPO handoff (`configure`),
     and pre-flight contract/integrity diagnostics (`doctor`);
  2. Pure-Markdown layered immutable architecture/HPO knowledge base (`knowledge-base`);
  3. Gain + compute ratchet campaign controller with duplicate/anti-pattern/bounds guards
     and strict dev/holdout isolation (`campaign`).
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import copy
from dataclasses import asdict, dataclass, field
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Iterator
import uuid


SKILL_ROOT = Path(os.path.realpath(__file__)).parent.parent
PRESETS_PATH = SKILL_ROOT / "assets" / "presets.json"
SEED_KNOWLEDGE_BASE_DIR = SKILL_ROOT / "assets" / "knowledge_base"

TRACKS = ("architecture", "hpo")
DIRECTIONS = ("maximize", "minimize")
KNOWLEDGE_STATUSES = ("draft", "published", "deprecated")
TRIAL_DECISIONS = ("baseline", "keep", "discard", "crash", "cancelled")
CAMPAIGN_CLOSED = {"succeeded", "failed", "cancelled"}

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

RECORD_START = "<!-- knowledge_base:record:start -->"
RECORD_END = "<!-- knowledge_base:record:end -->"
EVIDENCE_START = "<!-- knowledge_base:evidence:start -->"
EVIDENCE_END = "<!-- knowledge_base:evidence:end -->"


# ---------------------------------------------------------------------------
# Atomic File & Path Utilities
# ---------------------------------------------------------------------------


def is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def positive_number(value: Any, name: str) -> None:
    if not is_finite_number(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")


def non_negative_number(value: Any, name: str) -> None:
    if not is_finite_number(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative number")


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def write_json_atomic(path: Path, payload: Any) -> None:
    write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def canonical_config_id(config: dict[str, Any]) -> str:
    raw = json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def canonical_change_signature(changes: dict[str, Any]) -> str:
    if not changes:
        return "-"
    return ";".join(
        f"{key}={json.dumps(changes[key], sort_keys=True, ensure_ascii=False)}"
        for key in sorted(changes)
    )


def has_path(mapping: dict[str, Any], dotted_path: str) -> bool:
    cur: Any = mapping
    for part in dotted_path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return True


def get_by_path(mapping: dict[str, Any], dotted_path: str) -> Any:
    cur: Any = mapping
    for part in dotted_path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(dotted_path)
        cur = cur[part]
    return cur


def set_by_path(mapping: dict[str, Any], dotted_path: str, value: Any) -> None:
    parts = dotted_path.split(".")
    cur = mapping
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


def apply_changes(base: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in changes.items():
        if "." in key:
            set_by_path(out, key, copy.deepcopy(value))
        else:
            out[key] = copy.deepcopy(value)
    return out


def flatten_leaf_paths(mapping: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    items: dict[str, Any] = {}
    for key, value in mapping.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict) and value:
            items.update(flatten_leaf_paths(value, path))
        else:
            items[path] = value
    return items


def count_config_diffs(base: dict[str, Any], candidate: dict[str, Any]) -> int:
    left = flatten_leaf_paths(base)
    right = flatten_leaf_paths(candidate)
    all_keys = set(left) | set(right)
    return sum(1 for key in all_keys if left.get(key) != right.get(key))


def compute_gain(candidate: float, reference: float, direction: str) -> tuple[float, float]:
    raw_delta = (candidate - reference) if direction == "maximize" else (reference - candidate)
    denom = abs(reference) if abs(reference) > 1e-12 else 1.0
    return round(raw_delta, 6), round((raw_delta / denom) * 100.0, 4)


def meets_holdout_target(candidate: float, baseline: float | None, primary_spec: dict[str, Any]) -> bool:
    direction = primary_spec["direction"]
    target = primary_spec.get("holdout_target")
    if target is not None:
        return candidate >= target if direction == "maximize" else candidate <= target
    min_gain = float(primary_spec.get("holdout_min_gain", primary_spec.get("min_gain", 0.0)))
    if baseline is None:
        return True
    delta, _ = compute_gain(candidate, baseline, direction)
    return delta >= min_gain


# ---------------------------------------------------------------------------
# Contracts & Validation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Proposal:
    hypothesis: str
    changes: dict[str, Any]
    reuse_simulation: bool = False

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Proposal:
        if not isinstance(raw, dict):
            raise ValueError("Proposal must be a JSON object")
        hypothesis = raw.get("hypothesis")
        changes = raw.get("changes")
        reuse_sim = raw.get("reuse_simulation", False)
        if not isinstance(hypothesis, str) or not hypothesis.strip():
            raise ValueError("proposal.hypothesis must be a non-empty string")
        if not isinstance(changes, dict) or not changes:
            raise ValueError("proposal.changes must be a non-empty JSON object")
        if not isinstance(reuse_sim, bool):
            raise ValueError("proposal.reuse_simulation must be a boolean")
        return cls(hypothesis=hypothesis.strip(), changes=changes, reuse_simulation=reuse_sim)


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


# ---------------------------------------------------------------------------
# Pure-Markdown Layered Immutable Knowledge Base
# ---------------------------------------------------------------------------


def _compute_entry_sha256(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "content_sha256"}
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _next_revision_label(current: str, draft: bool = True) -> str:
    prefix = current.split("-", 1)[0]
    number = int(prefix[1:]) + 1 if (prefix.startswith("v") and prefix[1:].isdigit()) else 2
    return f"v{number}-draft" if draft else f"v{number}"


def _infer_pattern_direction(gain_pct: float | None, compute_ratio: float | None) -> str:
    gain = gain_pct or 0.0
    ratio = compute_ratio if compute_ratio is not None else 1.0
    if gain > 0 and ratio < 0.99:
        return "gain_up_compute_down"
    if gain > 0 and ratio <= 1.02:
        return "gain_up_compute_neutral"
    if gain > 0:
        return "gain_up_compute_up"
    if abs(gain) <= 1e-6 and ratio < 0.99:
        return "compute_down_tie"
    return "other"


def _infer_failure_type(decision: str, reason: str | None) -> str:
    text = (reason or "").lower()
    if decision == "crash":
        return "training_crash"
    if "compute budget exceeded" in text:
        return "compute_budget_exceeded"
    if "guardrail violated" in text:
        return "guardrail_violated"
    if "delta=" in text:
        return "accuracy_regression"
    return "other"


def _md_cell(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return str(value).replace("|", "\\|").replace("\n", " ").strip() or "-"


def _extract_json_block(markdown: str, start_marker: str, end_marker: str) -> Any:
    start = markdown.find(start_marker)
    end = markdown.find(end_marker)
    if start < 0 or end < 0 or end <= start:
        raise ValueError(f"Missing structured block ({start_marker}) in Markdown knowledge_base file")
    section = markdown[start + len(start_marker):end]
    fence_start = section.find("```json")
    if fence_start < 0:
        raise ValueError("Missing ```json fenced block inside structured knowledge_base section")
    body = section[fence_start + len("```json"):]
    fence_end = body.find("```")
    if fence_end < 0:
        raise ValueError("Unterminated ```json fenced block inside structured knowledge_base section")
    return json.loads(body[:fence_end].strip())


def _normalize_pattern(pattern: dict[str, Any]) -> dict[str, Any]:
    item = copy.deepcopy(pattern)
    changes = item.get("suggested_changes") or {}
    if not isinstance(changes, dict) or not changes:
        raise ValueError("pattern.suggested_changes must be a non-empty object")
    item["change_signature"] = item.get("change_signature") or canonical_change_signature(changes)
    item["target_fields"] = sorted(set(item.get("target_fields") or list(changes.keys())))
    effect = item.get("effect") if isinstance(item.get("effect"), dict) else {}
    direction = effect.get("direction", "other")
    if direction not in PATTERN_DIRECTIONS:
        raise ValueError(f"Unsupported pattern effect.direction: {direction}")
    item["effect"] = {
        "direction": direction,
        "notes": str(effect.get("notes", "")),
    }
    stats = item.get("stats") if isinstance(item.get("stats"), dict) else {}
    gain_pct = stats.get("mean_gain_pct")
    comp_ratio = stats.get("mean_compute_ratio")
    mean_cost = stats.get("mean_cost")
    item["stats"] = {
        "observations": int(stats.get("observations", 1)),
        "wins": int(stats.get("wins", 1)),
        "mean_gain_pct": round(float(gain_pct), 4) if gain_pct is not None else None,
        "mean_compute_ratio": round(float(comp_ratio), 4) if comp_ratio is not None else None,
        "mean_cost": round(float(mean_cost), 4) if mean_cost is not None else None,
    }
    item["confidence"] = item.get("confidence", "medium")
    item["evidence_refs"] = list(dict.fromkeys(item.get("evidence_refs") or []))
    return item


def _normalize_anti_pattern(anti: dict[str, Any]) -> dict[str, Any]:
    item = copy.deepcopy(anti)
    changes = item.get("avoid_changes") or {}
    if not isinstance(changes, dict) or not changes:
        raise ValueError("anti_pattern.avoid_changes must be a non-empty object")
    item["change_signature"] = item.get("change_signature") or canonical_change_signature(changes)
    item["target_fields"] = sorted(set(item.get("target_fields") or list(changes.keys())))
    failure_type = item.get("failure_type", "other")
    if failure_type not in FAILURE_TYPES:
        raise ValueError(f"Unsupported anti_pattern.failure_type: {failure_type}")
    item["failure_type"] = failure_type
    item["observed_compute_ratio"] = item.get("observed_compute_ratio")
    item["observed_gain_pct"] = item.get("observed_gain_pct")
    item["observed_failure"] = str(item.get("observed_failure", ""))
    item["occurrences"] = int(item.get("occurrences", 1))
    item["evidence_refs"] = list(dict.fromkeys(item.get("evidence_refs") or []))
    return item


def _weighted_avg(old_val: float | None, old_n: int, new_val: float | None, new_n: int) -> float | None:
    if old_val is None and new_val is None:
        return None
    if old_val is None or old_n <= 0:
        return round(float(new_val), 4)  # type: ignore[arg-type]
    if new_val is None or new_n <= 0:
        return round(float(old_val), 4)
    return round((old_val * old_n + new_val * new_n) / (old_n + new_n), 4)


def render_entry_markdown(doc: dict[str, Any]) -> str:
    scope = doc.get("scope") or {}
    bounds = scope.get("param_bounds") or {}
    lines = [
        f"# {doc['entry_id']} · {doc['title']}",
        "",
        "| 字段 | 值 |",
        "| --- | --- |",
        f"| 经验条目编号 | `{doc['entry_id']}` |",
        f"| 修订版本 | `{doc['revision']}`（父版本：`{doc.get('parent_revision') or '-'}`） |",
        f"| 研究轨道 | `{doc['track']}` |",
        f"| 发布状态 | `{doc['status']}` |",
        f"| 适用模型族 | `{_md_cell(scope.get('model_family'))}` |",
        f"| 审核人 | `{_md_cell(doc.get('reviewed_by'))}` |",
        f"| 内容指纹 | `{doc.get('content_sha256', '')[:16]}...` |",
        "",
        "## 摘要",
        "",
        doc["summary"],
        "",
        "## 适用边界与算量红线",
        "",
        f"- **目标算量上限**：`{_md_cell(scope.get('max_compute_value'))}` / 倍率 `<= {_md_cell(scope.get('max_compute_ratio'))}x`",
        f"- **禁用算子**：{', '.join(f'`{op}`' for op in scope.get('forbidden_ops', [])) or '-'}",
        "",
    ]
    if bounds:
        lines.extend([
            "### 参数合法域（`param_bounds`）",
            "",
            "| 字段 | 类型 | 范围 / 枚举 |",
            "| --- | --- | --- |",
        ])
        for field_name, spec in bounds.items():
            constraint = (
                f"enum: `{spec['enum']}`"
                if "enum" in spec
                else f"min=`{spec.get('min', '-')}`, max=`{spec.get('max', '-')}`"
            )
            lines.append(f"| `{field_name}` | `{spec.get('type', 'any')}` | {constraint} |")
        lines.append("")

    lines.extend([
        "## 推荐有效模式（Patterns）",
        "",
        "| ID | 说明 | 声明式变更 | 方向 | 均值增益(%) | 均值算量比 | 观测/胜出 | 置信度 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for pat in doc.get("patterns", []):
        st = pat.get("stats") or {}
        gain_txt = f"{st['mean_gain_pct']:+.2f}%" if st.get("mean_gain_pct") is not None else "-"
        ratio_txt = f"{st['mean_compute_ratio']:.3f}x" if st.get("mean_compute_ratio") is not None else "-"
        lines.append(
            f"| `{pat.get('pattern_id', '-')}` | {_md_cell(pat.get('title'))} | `{pat['change_signature']}` "
            f"| `{pat['effect']['direction']}` | {gain_txt} | {ratio_txt} "
            f"| {st.get('observations', 0)}/{st.get('wins', 0)} | `{pat.get('confidence', 'medium')}` |"
        )
    if not doc.get("patterns"):
        lines.append("| - | 暂无已验证模式 | - | - | - | - | - | - |")

    lines.extend([
        "",
        "## 已知反例与失效边界（Anti-Patterns）",
        "",
        "| ID | 反例说明 | 避坑变更 | 失败类型 | 实测算量比 | 次数 |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for anti in doc.get("anti_patterns", []):
        ratio_txt = f"{anti['observed_compute_ratio']:.3f}x" if anti.get("observed_compute_ratio") is not None else "-"
        lines.append(
            f"| `{anti.get('pattern_id', '-')}` | {_md_cell(anti.get('title'))} | `{anti['change_signature']}` "
            f"| `{anti['failure_type']}` | {ratio_txt} | {anti.get('occurrences', 1)} |"
        )
    if not doc.get("anti_patterns"):
        lines.append("| - | 暂无记录反例 | - | - | - | - |")

    lines.extend([
        "",
        "---",
        "",
        "<!-- 机器精确解析块：请通过 autoresearch.py configure / knowledge-base distill / knowledge-base publish 维护，勿手改导致 SHA-256 校验失败 -->",
        RECORD_START,
        "```json",
        json.dumps(doc, ensure_ascii=False, indent=2),
        "```",
        RECORD_END,
        "",
    ])
    return "\n".join(lines)


def render_evidence_markdown(entry_id: str, records: list[dict[str, Any]]) -> str:
    lines = [
        f"# {entry_id} · 实证账本（Evidence Ledger）",
        "",
        "| Campaign | 修订 | 胜出 Trial | Holdout 通过 | 增益(%) | 算量比 | 总成本 | 审核人 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for rec in records:
        lines.append(
            f"| `{_md_cell(rec.get('campaign_id'))}` | `{_md_cell(rec.get('revision'))}` "
            f"| `{_md_cell(rec.get('incumbent_trial_id'))}` | `{_md_cell(rec.get('holdout_accepted'))}` "
            f"| `{_md_cell(rec.get('gain_pct'))}` | `{_md_cell(rec.get('compute_ratio'))}` "
            f"| `{_md_cell(rec.get('total_cost'))}` | `{_md_cell(rec.get('reviewed_by'))}` |"
        )
    if not records:
        lines.append("| - | - | - | - | - | - | - | - |")
    lines.extend([
        "",
        EVIDENCE_START,
        "```json",
        json.dumps(records, ensure_ascii=False, indent=2),
        "```",
        EVIDENCE_END,
        "",
    ])
    return "\n".join(lines)


def render_index_markdown(entries: list[dict[str, Any]]) -> str:
    lines = [
        "# 模型优化经验知识库总索引（Knowledge Base Index）",
        "",
        "| 条目编号 | 当前版本 | 轨道 | 状态 | 模型族 | 模式 / 反例 / 实证 / 待审草案 | 入口 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in entries:
        scope = item.get("scope") or {}
        counts = (
            f"{len(item.get('patterns', []))} / {len(item.get('anti_patterns', []))} / "
            f"{len(item.get('evidence', []))} / {len(item.get('draft_revisions', []))}"
        )
        lines.append(
            f"| `{item['entry_id']}` | `{item['revision']}` | `{item['track']}` | `{item['status']}` "
            f"| `{_md_cell(scope.get('model_family'))}` | {counts} | [CURRENT.md](entries/{item['entry_id']}/CURRENT.md) |"
        )
    if not entries:
        lines.append("| - | - | - | - | - | - | - |")
    lines.append("")
    return "\n".join(lines)


class KnowledgeBase:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.entries_dir = self.root / "entries"
        self.entries_dir.mkdir(parents=True, exist_ok=True)
        self.index_md_path = self.root / "INDEX.md"

    @staticmethod
    def _safe_id(identifier: str) -> str:
        clean = identifier.strip()
        if not clean or "/" in clean or "\\" in clean or ".." in clean:
            raise ValueError(f"Invalid knowledge_base entry_id: {identifier!r}")
        return clean

    def _entry_dir(self, entry_id: str) -> Path:
        return self.entries_dir / self._safe_id(entry_id)

    def _current_path(self, entry_id: str) -> Path:
        return self._entry_dir(entry_id) / "CURRENT.md"

    def _revisions_dir(self, entry_id: str) -> Path:
        return self._entry_dir(entry_id) / "revisions"

    def _revision_path(self, entry_id: str, revision: str) -> Path:
        return self._revisions_dir(entry_id) / f"{self._safe_id(revision)}.md"

    def _drafts_dir(self, entry_id: str) -> Path:
        return self._entry_dir(entry_id) / "drafts"

    def _evidence_path(self, entry_id: str) -> Path:
        return self._entry_dir(entry_id) / "EVIDENCE.md"

    @staticmethod
    def validate_doc(raw: dict[str, Any]) -> dict[str, Any]:
        doc = copy.deepcopy(raw)
        if doc.get("schema_version") not in (1, 2):
            raise ValueError("Unsupported knowledge_base schema_version")
        for key in ("entry_id", "revision", "title", "summary"):
            if not isinstance(doc.get(key), str) or not doc[key].strip():
                raise ValueError(f"Knowledge entry {key} is required")
        if doc.get("track") not in TRACKS:
            raise ValueError(f"Unsupported knowledge_base track: {doc.get('track')}")
        if doc.get("status") not in KNOWLEDGE_STATUSES:
            raise ValueError(f"Unsupported knowledge_base status: {doc.get('status')}")
        if not isinstance(doc.get("scope"), dict):
            raise ValueError("Knowledge entry scope must be an object")
        doc["patterns"] = [_normalize_pattern(p) for p in doc.get("patterns", [])]
        doc["anti_patterns"] = [_normalize_anti_pattern(a) for a in doc.get("anti_patterns", [])]
        return doc

    def _read_evidence(self, entry_id: str) -> list[dict[str, Any]]:
        path = self._evidence_path(entry_id)
        if not path.is_file():
            return []
        data = _extract_json_block(path.read_text(encoding="utf-8"), EVIDENCE_START, EVIDENCE_END)
        if not isinstance(data, list):
            raise ValueError(f"Corrupted EVIDENCE.md in {path}")
        return data

    def list_drafts(self, entry_id: str | None = None) -> list[dict[str, Any]]:
        ids = [self._safe_id(entry_id)] if entry_id else sorted(
            p.name for p in self.entries_dir.iterdir() if p.is_dir() and (p / "CURRENT.md").is_file()
        )
        out: list[dict[str, Any]] = []
        for item_id in ids:
            d_dir = self._drafts_dir(item_id)
            if not d_dir.is_dir():
                continue
            for path in sorted(d_dir.glob("*.md")):
                out.append(_extract_json_block(path.read_text(encoding="utf-8"), RECORD_START, RECORD_END))
        return out

    def load(self, entry_id: str, revision: str | None = None) -> dict[str, Any]:
        safe_id = self._safe_id(entry_id)
        cur_path = self._current_path(safe_id)
        if not cur_path.is_file():
            raise ValueError(f"Unknown knowledge_base entry: {entry_id}")
        cur_doc = _extract_json_block(cur_path.read_text(encoding="utf-8"), RECORD_START, RECORD_END)
        target_path = self._revision_path(safe_id, revision) if revision else cur_path
        if not target_path.is_file():
            raise ValueError(f"Unknown revision {revision!r} for knowledge_base entry {entry_id}")
        raw_doc = _extract_json_block(target_path.read_text(encoding="utf-8"), RECORD_START, RECORD_END)
        doc = self.validate_doc(raw_doc)
        expected_sha = doc.get("content_sha256")
        actual_sha = _compute_entry_sha256(doc)
        if expected_sha and expected_sha != actual_sha:
            raise ValueError(
                f"Revision integrity check failed for {safe_id}@{doc['revision']}: "
                "do not hand-edit CURRENT.md; use `configure` (for v1 seed) or "
                "`knowledge-base distill` + `knowledge-base publish`."
            )
        doc["content_sha256"] = actual_sha
        doc["active_revision"] = cur_doc["revision"]
        rev_dir = self._revisions_dir(safe_id)
        doc["revisions"] = [
            _extract_json_block(p.read_text(encoding="utf-8"), RECORD_START, RECORD_END)["revision"]
            for p in sorted(rev_dir.glob("*.md"))
        ] if rev_dir.is_dir() else []
        doc["evidence"] = self._read_evidence(safe_id)
        doc["draft_revisions"] = self.list_drafts(safe_id)
        return doc

    def save(self, entry: dict[str, Any], allow_overwrite_revision: bool = False) -> Path:
        safe_id = self._safe_id(entry["entry_id"])
        revision = self._safe_id(entry["revision"])
        rev_path = self._revision_path(safe_id, revision)
        if rev_path.is_file() and not allow_overwrite_revision:
            raise ValueError(f"Revision {safe_id}@{revision} is immutable and already exists")

        doc = self.validate_doc({
            "schema_version": 2,
            "entry_id": safe_id,
            "revision": revision,
            "parent_revision": entry.get("parent_revision"),
            "track": entry["track"],
            "status": entry["status"],
            "tags": list(entry.get("tags") or []),
            "title": entry["title"],
            "summary": entry["summary"],
            "scope": entry["scope"],
            "patterns": entry.get("patterns", []),
            "anti_patterns": entry.get("anti_patterns", []),
            "reviewed_by": entry.get("reviewed_by", "seed"),
            "published_at": entry.get("published_at", 0),
        })
        doc["content_sha256"] = _compute_entry_sha256(doc)
        markdown = render_entry_markdown(doc)
        write_text_atomic(rev_path, markdown)
        write_text_atomic(self._current_path(safe_id), markdown)
        self._drafts_dir(safe_id).mkdir(parents=True, exist_ok=True)
        if "evidence" in entry and entry["evidence"] is not None:
            write_text_atomic(self._evidence_path(safe_id), render_evidence_markdown(safe_id, list(entry["evidence"])))
        elif not self._evidence_path(safe_id).is_file():
            write_text_atomic(self._evidence_path(safe_id), render_evidence_markdown(safe_id, []))
        self.reindex()
        return rev_path

    def freeze_snapshot(self, entry_id: str, revision: str | None = None) -> dict[str, Any]:
        doc = self.load(entry_id, revision=revision)
        if doc["status"] != "published":
            raise ValueError(f"Knowledge entry {entry_id}@{doc['revision']} is not published")
        return {
            "entry_id": doc["entry_id"],
            "revision": doc["revision"],
            "track": doc["track"],
            "status": doc["status"],
            "title": doc["title"],
            "summary": doc["summary"],
            "scope": copy.deepcopy(doc["scope"]),
            "patterns": copy.deepcopy(doc["patterns"]),
            "anti_patterns": copy.deepcopy(doc["anti_patterns"]),
            "content_sha256": doc["content_sha256"],
        }

    def reindex(self) -> Path:
        entries = self.list_entries()
        write_text_atomic(self.index_md_path, render_index_markdown(entries))
        return self.index_md_path

    def list_entries(self, track: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for entry_dir in sorted(self.entries_dir.iterdir()):
            if not entry_dir.is_dir() or not (entry_dir / "CURRENT.md").is_file():
                continue
            doc = self.load(entry_dir.name)
            if track and doc["track"] != track:
                continue
            if status and doc["status"] != status:
                continue
            out.append(doc)
        return out

    def search(
        self,
        *,
        query: str = "",
        track: str | None = None,
        model_family: str | None = None,
        field_name: str | None = None,
        direction: str | None = None,
        max_compute_ratio: float | None = None,
        min_gain_pct: float | None = None,
        failure_type: str | None = None,
        status: str | None = "published",
    ) -> list[dict[str, Any]]:
        needle = query.strip().lower()
        fam_needle = (model_family or "").strip().lower()
        results: list[dict[str, Any]] = []
        for doc in self.list_entries(track=track, status=status):
            scope = doc.get("scope") or {}
            if fam_needle and fam_needle not in str(scope.get("model_family") or "").lower():
                continue
            patterns = list(doc.get("patterns", []))
            if direction:
                patterns = [p for p in patterns if p["effect"]["direction"] == direction]
            if min_gain_pct is not None:
                patterns = [
                    p for p in patterns
                    if p["stats"].get("mean_gain_pct") is not None and p["stats"]["mean_gain_pct"] >= min_gain_pct
                ]
            if max_compute_ratio is not None:
                patterns = [
                    p for p in patterns
                    if p["stats"].get("mean_compute_ratio") is not None
                    and p["stats"]["mean_compute_ratio"] <= max_compute_ratio
                ]
            if field_name:
                patterns = [p for p in patterns if field_name in p.get("target_fields", [])]

            antis = list(doc.get("anti_patterns", []))
            if failure_type:
                antis = [a for a in antis if a["failure_type"] == failure_type]
            if field_name:
                antis = [a for a in antis if field_name in a.get("target_fields", [])]

            if needle:
                blob = json.dumps(
                    {"title": doc["title"], "summary": doc["summary"], "patterns": patterns, "anti": antis},
                    ensure_ascii=False,
                ).lower()
                if needle not in blob:
                    continue
            if (direction or min_gain_pct is not None or max_compute_ratio is not None) and not patterns:
                continue
            if failure_type and not antis:
                continue

            results.append({
                "entry_id": doc["entry_id"],
                "revision": doc["revision"],
                "track": doc["track"],
                "title": doc["title"],
                "scope": scope,
                "matched_patterns": patterns,
                "matched_anti_patterns": antis,
            })
        return results

    def import_seed_library(self, preset_filter: str | None = None, overwrite: bool = False) -> list[str]:
        presets = _load_presets()
        imported: list[str] = []
        for name, preset in presets.items():
            if preset_filter and name != preset_filter:
                continue
            seed_id = preset.get("seed_entry_id")
            if not seed_id:
                continue
            if self._current_path(seed_id).is_file() and not overwrite:
                continue
            self.save({
                "entry_id": seed_id,
                "revision": "v1",
                "parent_revision": None,
                "track": preset["track"],
                "status": "published",
                "tags": [preset.get("model_family", name), preset["track"], "seed-library"],
                "title": preset["title"],
                "summary": preset["summary"],
                "reviewed_by": "seed-library",
                "published_at": 0,
                "scope": {
                    "model_family": preset.get("model_family", name),
                    "forbidden_ops": preset.get("forbidden_ops", []),
                    "max_compute_value": None,
                    "max_compute_ratio": preset.get("max_compute_ratio", 1.10),
                    "param_bounds": preset["param_bounds"],
                },
                "patterns": preset.get("patterns", []),
                "anti_patterns": preset.get("anti_patterns", []),
                "evidence": [],
            }, allow_overwrite_revision=overwrite)
            imported.append(seed_id)
        return imported

    def distill_from_campaign(self, campaign: dict[str, Any], entry_id: str | None = None) -> dict[str, Any]:
        target_id = self._safe_id(entry_id or campaign["plan"]["knowledge_entry_ref"])
        cur = self.load(target_id)
        holdout = campaign.get("holdout_report")
        holdout_ok = bool(holdout and holdout.get("accepted"))
        confidence = "verified_holdout" if holdout_ok else "dev_only"
        cid = campaign["campaign_id"]

        new_patterns: list[dict[str, Any]] = []
        new_antis: list[dict[str, Any]] = []
        for idx, trial in enumerate(campaign.get("trials", []), start=1):
            if trial.get("is_baseline") or not trial.get("changes"):
                continue
            sig = canonical_change_signature(trial["changes"])
            decision = trial.get("decision")
            if decision == "keep":
                new_patterns.append(_normalize_pattern({
                    "pattern_id": f"P-{cid[-6:].upper()}-{idx:02d}",
                    "title": trial["hypothesis"],
                    "suggested_changes": trial["changes"],
                    "effect": {
                        "direction": _infer_pattern_direction(trial.get("gain_pct"), trial.get("compute_ratio")),
                        "notes": trial.get("decision_reason") or "",
                    },
                    "stats": {
                        "observations": 1,
                        "wins": 1,
                        "mean_gain_pct": trial.get("gain_pct"),
                        "mean_compute_ratio": trial.get("compute_ratio"),
                        "mean_cost": trial.get("cost_value"),
                    },
                    "confidence": confidence,
                    "evidence_refs": [f"{cid}:{trial['trial_id']}"],
                    "change_signature": sig,
                }))
            elif decision in {"discard", "crash"}:
                ftype = _infer_failure_type(decision, trial.get("decision_reason"))
                if ftype in {"compute_budget_exceeded", "guardrail_violated", "training_crash"} or (
                    trial.get("gain_pct") is not None and trial["gain_pct"] < -1.0
                ):
                    new_antis.append(_normalize_anti_pattern({
                        "pattern_id": f"AP-{cid[-6:].upper()}-{idx:02d}",
                        "title": trial["hypothesis"],
                        "avoid_changes": trial["changes"],
                        "failure_type": ftype,
                        "observed_compute_ratio": trial.get("compute_ratio"),
                        "observed_gain_pct": trial.get("gain_pct"),
                        "observed_failure": trial.get("decision_reason") or decision,
                        "occurrences": 1,
                        "evidence_refs": [f"{cid}:{trial['trial_id']}"],
                        "change_signature": sig,
                    }))

        draft_rev = f"{_next_revision_label(cur['revision'], draft=True)}-{cid[-6:]}"
        draft_doc = {
            "schema_version": 2,
            "entry_id": target_id,
            "revision": draft_rev,
            "parent_revision": cur["revision"],
            "track": cur["track"],
            "status": "draft",
            "tags": cur.get("tags", []),
            "title": cur["title"],
            "summary": cur["summary"],
            "scope": cur["scope"],
            "patterns": new_patterns,
            "anti_patterns": new_antis,
            "source_campaign": {
                "campaign_id": cid,
                "incumbent_trial_id": campaign.get("incumbent_trial_id"),
                "holdout_accepted": holdout_ok if holdout else None,
                "gain_pct": holdout.get("gain_pct") if holdout else None,
                "compute_ratio": holdout.get("compute_ratio") if holdout else None,
                "total_cost": campaign.get("total_cost", 0.0),
            },
            "reviewed_by": None,
            "published_at": round(time.time(), 3),
        }
        draft_doc["content_sha256"] = _compute_entry_sha256(draft_doc)
        draft_path = self._drafts_dir(target_id) / f"{draft_rev}.md"
        write_text_atomic(draft_path, render_entry_markdown(draft_doc))
        self.reindex()
        return {"draft_path": str(draft_path), "draft": draft_doc}

    def publish(self, entry_id: str, draft_revision: str | None = None, reviewer: str = "human") -> dict[str, Any]:
        safe_id = self._safe_id(entry_id)
        cur = self.load(safe_id)
        drafts = self.list_drafts(safe_id)
        if not drafts:
            raise ValueError(f"No pending drafts found for {safe_id}; run `knowledge-base distill` first")
        selected = None
        if draft_revision:
            for item in drafts:
                if item["revision"] == draft_revision:
                    selected = item
                    break
            if selected is None:
                raise ValueError(f"Draft revision {draft_revision!r} not found for {safe_id}")
        else:
            selected = drafts[-1]

        merged_patterns = [_normalize_pattern(p) for p in cur.get("patterns", [])]
        pat_by_sig = {p["change_signature"]: idx for idx, p in enumerate(merged_patterns)}
        for incoming in selected.get("patterns", []):
            cand = _normalize_pattern(incoming)
            sig = cand["change_signature"]
            if sig in pat_by_sig:
                existing = merged_patterns[pat_by_sig[sig]]
                o_s, n_s = existing["stats"], cand["stats"]
                o_n, n_n = o_s["observations"], max(1, n_s["observations"])
                existing["stats"] = {
                    "observations": o_n + n_n,
                    "wins": o_s["wins"] + n_s["wins"],
                    "mean_gain_pct": _weighted_avg(o_s["mean_gain_pct"], o_n, n_s["mean_gain_pct"], n_n),
                    "mean_compute_ratio": _weighted_avg(o_s["mean_compute_ratio"], o_n, n_s["mean_compute_ratio"], n_n),
                    "mean_cost": _weighted_avg(o_s["mean_cost"], o_n, n_s["mean_cost"], n_n),
                }
                if CONFIDENCE_RANK.get(cand["confidence"], 0) > CONFIDENCE_RANK.get(existing["confidence"], 0):
                    existing["confidence"] = cand["confidence"]
                existing["evidence_refs"] = list(dict.fromkeys([*existing["evidence_refs"], *cand["evidence_refs"]]))
                existing["effect"]["direction"] = _infer_pattern_direction(
                    existing["stats"]["mean_gain_pct"], existing["stats"]["mean_compute_ratio"]
                )
            else:
                pat_by_sig[sig] = len(merged_patterns)
                merged_patterns.append(cand)

        merged_antis = [_normalize_anti_pattern(a) for a in cur.get("anti_patterns", [])]
        anti_by_sig = {a["change_signature"]: idx for idx, a in enumerate(merged_antis)}
        for incoming in selected.get("anti_patterns", []):
            cand = _normalize_anti_pattern(incoming)
            sig = cand["change_signature"]
            if sig in anti_by_sig:
                existing = merged_antis[anti_by_sig[sig]]
                existing["occurrences"] += max(1, cand["occurrences"])
                existing["evidence_refs"] = list(dict.fromkeys([*existing["evidence_refs"], *cand["evidence_refs"]]))
                if cand.get("observed_compute_ratio") is not None:
                    existing["observed_compute_ratio"] = cand["observed_compute_ratio"]
            else:
                anti_by_sig[sig] = len(merged_antis)
                merged_antis.append(cand)

        new_rev = _next_revision_label(cur["revision"], draft=False)
        evidence = list(cur.get("evidence", []))
        src_cmp = selected.get("source_campaign") or {}
        if src_cmp.get("campaign_id"):
            evidence.append({
                **src_cmp,
                "revision": new_rev,
                "reviewed_by": reviewer,
                "published_at": round(time.time(), 3),
            })

        self.save({
            "entry_id": safe_id,
            "revision": new_rev,
            "parent_revision": cur["revision"],
            "track": cur["track"],
            "status": "published",
            "tags": cur.get("tags", []),
            "title": cur["title"],
            "summary": cur["summary"],
            "scope": cur["scope"],
            "patterns": merged_patterns,
            "anti_patterns": merged_antis,
            "reviewed_by": reviewer,
            "published_at": round(time.time(), 3),
            "evidence": evidence,
        })
        draft_file = self._drafts_dir(safe_id) / f"{selected['revision']}.md"
        if draft_file.is_file():
            draft_file.unlink()
        self.reindex()
        return self.load(safe_id)


# ---------------------------------------------------------------------------
# Pure-File Ratchet Campaign Controller
# ---------------------------------------------------------------------------


def _tsv_cell(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ").strip() or "-"


def render_results_tsv(trials: list[dict[str, Any]], plan: dict[str, Any]) -> str:
    p_name = plan["acceptance"]["primary_metric"]["name"]
    c_name = plan["acceptance"]["compute_metric"]["name"]
    cost_name = plan["budget"]["cost_metric"]["name"]
    lines = ["\t".join([
        "trial_id",
        "parent_trial",
        "decision",
        f"primary({p_name})",
        "gain",
        "gain_pct",
        f"compute({c_name})",
        "compute_ratio",
        f"cost({cost_name})",
        "cum_cost",
        "complexity",
        "config_id",
        "diff",
        "hypothesis",
    ])]
    for trial in trials:
        status_cell = trial.get("decision") or trial.get("run_status") or "pending"
        lines.append("\t".join([
            _tsv_cell(trial.get("trial_id")),
            _tsv_cell(trial.get("parent_trial_id")),
            _tsv_cell(status_cell),
            _tsv_cell(trial.get("primary_value")),
            _tsv_cell(trial.get("gain")),
            _tsv_cell(f"{trial['gain_pct']:+.2f}%" if trial.get("gain_pct") is not None else None),
            _tsv_cell(trial.get("compute_value")),
            _tsv_cell(trial.get("compute_ratio")),
            _tsv_cell(trial.get("cost_value")),
            _tsv_cell(trial.get("cumulative_cost")),
            _tsv_cell(trial.get("complexity_score")),
            _tsv_cell(trial.get("config_id")),
            _tsv_cell(canonical_change_signature(trial.get("changes") or {})),
            _tsv_cell(trial.get("hypothesis")),
        ]))
    return "\n".join(lines) + "\n"


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

    def _append_event(self, campaign_id: str, kind: str, data: dict[str, Any]) -> None:
        trace_file = self._trace_path(campaign_id)
        trace_file.parent.mkdir(parents=True, exist_ok=True)
        record = {"at": round(time.time(), 3), "kind": kind, "data": data}
        with trace_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _save_state(self, state: dict[str, Any]) -> None:
        cid = state["campaign_id"]
        write_json_atomic(self._state_path(cid), state)
        write_text_atomic(self._tsv_path(cid), render_results_tsv(state["trials"], state["plan"]))
        if state.get("holdout_report") is not None:
            write_json_atomic(self._holdout_path(cid), state["holdout_report"])

    def status(self, campaign_id: str = "latest") -> dict[str, Any]:
        cid = self.resolve_id(campaign_id)
        return json.loads(self._state_path(cid).read_text(encoding="utf-8"))

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
                "baseline_primary_value": None,
                "baseline_compute_value": None,
                "total_cost": 0.0,
                "trials": [],
                "holdout_report": None,
            }
            self._save_state(state)
            self._append_event(cid, "campaign_created", {
                "track": plan["track"],
                "model_family": plan["model_family"],
                "knowledge_entry_ref": f"{plan['knowledge_entry_ref']}@{plan['knowledge']['revision']}",
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
                "is_baseline": True,
                "hypothesis": plan["base_hypothesis"],
                "changes": {},
                "candidate_config": base_cfg,
                "config_id": canonical_config_id(base_cfg),
                "frozen_architecture": copy.deepcopy(plan["base_architecture"]) if plan["track"] == "hpo" else None,
                "frozen_training_recipe": copy.deepcopy(plan["base_training_recipe"]) if plan["track"] == "architecture" else None,
                "reuse_simulation": False,
                "complexity_score": 0,
                "run_status": "awaiting_result",
                "decision": None,
                "decision_reason": None,
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
                "started_at": round(time.time(), 3),
                "finished_at": None,
            }
            state["trials"].append(trial)
            state["active_trial_id"] = "trial-000"
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

    def get_context(self, campaign_id: str = "latest") -> dict[str, Any]:
        cid = self.resolve_id(campaign_id)
        state = self.status(cid)
        plan = state["plan"]
        incumbent = self._find_trial(state, state["incumbent_trial_id"])
        active_trial = self._find_trial(state, state["active_trial_id"])

        max_trials = int(plan["budget"]["max_trials"])
        cost_spec = plan["budget"]["cost_metric"]
        max_cost = cost_spec.get("max_total")
        used_cost = float(state.get("total_cost", 0.0))
        remaining_trials = max(0, max_trials - len(state["trials"]))
        remaining_cost = round(max(0.0, float(max_cost) - used_cost), 4) if max_cost is not None else None

        consecutive_non_keep = 0
        for trial in reversed(state["trials"]):
            if trial.get("is_baseline") or trial.get("decision") is None:
                continue
            if trial["decision"] == "keep":
                break
            consecutive_non_keep += 1

        evaluated_signatures = [
            canonical_change_signature(t["changes"])
            for t in state["trials"]
            if not t.get("is_baseline") and t.get("changes") and t.get("decision") != "cancelled"
        ]
        eval_sig_set = set(evaluated_signatures)
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

        scope = plan["knowledge"].get("scope") or {}
        return {
            "campaign_id": cid,
            "status": state["status"],
            "track": plan["track"],
            "model_family": plan["model_family"],
            "knowledge_entry_ref": plan["knowledge_entry_ref"],
            "active_trial": active_trial,
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
            "mutable_fields": plan["mutable_fields"],
            "param_bounds": scope.get("param_bounds") or {},
            "forbidden_ops": scope.get("forbidden_ops") or [],
            "primary_metric": plan["acceptance"]["primary_metric"],
            "compute_metric": plan["acceptance"]["compute_metric"],
            "guardrails": plan["acceptance"].get("guardrails") or {},
            "cost_metric": cost_spec,
            "remaining_budget": {
                "remaining_trials": remaining_trials,
                "remaining_cost": remaining_cost,
                "used_cost": used_cost,
            },
            "search_diagnostics": {
                "consecutive_non_keep": consecutive_non_keep,
                "plateau_warning": consecutive_non_keep >= 3,
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
            if state["active_trial_id"] is not None:
                raise ValueError(
                    f"Active trial {state['active_trial_id']} is still awaiting_result; "
                    "reconcile remote MCP status and call `campaign record` before proposing."
                )
            incumbent = self._find_trial(state, state["incumbent_trial_id"])
            if incumbent is None:
                raise ValueError("Baseline trial-000 must succeed before submitting candidate proposals")

            plan = state["plan"]
            if len(state["trials"]) >= int(plan["budget"]["max_trials"]):
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

                inc_cfg = incumbent["candidate_config"]
                cand_cfg = apply_changes(inc_cfg, proposal.changes)
                cand_id = canonical_config_id(cand_cfg)
                if cand_id == incumbent["config_id"]:
                    raise ValueError("No-op proposal: candidate_config is identical to current incumbent")

                if not allow_repeat:
                    seen_ids = {
                        t["config_id"]: t["trial_id"]
                        for t in state["trials"]
                        if t.get("decision") != "cancelled"
                    }
                    if cand_id in seen_ids:
                        raise ValueError(
                            f"Duplicate configuration: matches already-evaluated {seen_ids[cand_id]} "
                            f"(config_id={cand_id})"
                        )

                sig = canonical_change_signature(proposal.changes)
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
                    self._append_event(cid, "proposal_rejected", {
                        "hypothesis": proposal.hypothesis,
                        "changes": proposal.changes,
                        "error": str(exc),
                    })
                raise

            complexity = count_config_diffs(plan["base_config"], cand_cfg)
            if dry_run:
                return {
                    "dry_run": True,
                    "valid": True,
                    "parent_trial_id": incumbent["trial_id"],
                    "candidate_config": cand_cfg,
                    "config_id": cand_id,
                    "complexity_score": complexity,
                }

            idx = len(state["trials"])
            trial_id = f"trial-{idx:03d}"
            trial = {
                "trial_id": trial_id,
                "index": idx,
                "parent_trial_id": incumbent["trial_id"],
                "is_baseline": False,
                "hypothesis": proposal.hypothesis,
                "changes": copy.deepcopy(proposal.changes),
                "candidate_config": cand_cfg,
                "config_id": cand_id,
                "frozen_architecture": copy.deepcopy(plan["base_architecture"]) if plan["track"] == "hpo" else None,
                "frozen_training_recipe": copy.deepcopy(plan["base_training_recipe"]) if plan["track"] == "architecture" else None,
                "reuse_simulation": proposal.reuse_simulation,
                "complexity_score": complexity,
                "run_status": "awaiting_result",
                "decision": None,
                "decision_reason": None,
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
                "started_at": round(time.time(), 3),
                "finished_at": None,
            }
            state["trials"].append(trial)
            state["active_trial_id"] = trial_id
            self._save_state(state)
            self._append_event(cid, "trial_proposed", {
                "trial_id": trial_id,
                "parent_trial_id": incumbent["trial_id"],
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
        metrics: dict[str, Any] | None = None,
        cost: dict[str, Any] | None = None,
        artifacts: dict[str, Any] | None = None,
        external_jobs: list[dict[str, Any]] | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        if status not in {"succeeded", "failed", "timeout", "crash", "cancelled"}:
            raise ValueError(f"Unsupported record status: {status!r}")
        cid = self.resolve_id(campaign_id)
        with self._lock(cid):
            state = self.status(cid)
            if state["status"] in CAMPAIGN_CLOSED:
                raise ValueError(f"Campaign already closed with status={state['status']}")
            target_id = trial_id or state["active_trial_id"]
            if not target_id:
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

            if status == "cancelled":
                trial["decision"] = "cancelled"
                trial["decision_reason"] = note or "trial cancelled"
            elif status != "succeeded":
                trial["decision"] = "crash"
                trial["decision_reason"] = note or f"MCP trial ended with status={status}"
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

                    incumbent = self._find_trial(state, state["incumbent_trial_id"])
                    assert incumbent is not None
                    g_viol = _check_guardrails(m_dict, plan["acceptance"].get("guardrails"))
                    c_viol = _check_compute_budget(c_val, trial["compute_ratio"], c_spec)
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

            state["active_trial_id"] = None

            if state["status"] == "running":
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
                "decision": trial["decision"],
                "reason": trial["decision_reason"],
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
            if state["active_trial_id"] is not None:
                raise ValueError(f"Active trial {state['active_trial_id']} must be recorded before finalize")
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
                "cost_metric_name": cost_name,
                "total_cost": total_cost,
                "cost_unit": cost_spec.get("unit", ""),
                "gain_per_cost": gain_per_cost,
                "total_trials": len(state["trials"]),
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
            return state

    def stop(self, campaign_id: str = "latest", reason: str = "user_stopped") -> dict[str, Any]:
        cid = self.resolve_id(campaign_id)
        with self._lock(cid):
            state = self.status(cid)
            if state["status"] in CAMPAIGN_CLOSED:
                return state
            if state["incumbent_trial_id"] and state["active_trial_id"] is None:
                state["status"] = "awaiting_holdout"
                state["stop_reason"] = reason
            else:
                state["status"] = "cancelled"
                state["stop_reason"] = reason
            self._save_state(state)
            self._append_event(cid, "campaign_stopped", {"reason": reason, "status": state["status"]})
            return state


# ---------------------------------------------------------------------------
# Workspace Scaffolding, Safe Configurator & Doctor
# ---------------------------------------------------------------------------


def _load_presets() -> dict[str, Any]:
    if PRESETS_PATH.is_file():
        return json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
    return {}


def init_workspace(
    *,
    workspace: Path,
    model_family: str,
    entry_id: str,
    primary_metric: str,
    direction: str = "maximize",
    min_gain: float = 0.5,
    tie_tolerance: float = 0.0,
    holdout_target: float | None = None,
    compute_metric: str = "flops_m",
    compute_unit: str = "MFLOPs",
    max_compute_value: float | None = None,
    max_compute_ratio: float = 1.10,
    cost_metric: str = "gpu_seconds",
    cost_unit: str = "s",
    max_cost: float = 3600.0,
    max_trials: int = 6,
    track: str = "architecture",
    stages: list[str] | None = None,
    preset_name: str | None = None,
) -> dict[str, Any]:
    root = workspace.resolve()
    root.mkdir(parents=True, exist_ok=True)
    presets = _load_presets()
    chosen_preset_key = preset_name or ("generic_arch" if track == "architecture" else "hpo_recipe")
    if chosen_preset_key not in presets:
        raise ValueError(f"Unknown --preset {chosen_preset_key!r}; available: {sorted(presets)}")
    preset = copy.deepcopy(presets[chosen_preset_key])
    if preset["track"] != track:
        raise ValueError(f"Preset {chosen_preset_key!r} belongs to track={preset['track']!r}, not {track!r}")

    knowledge_base_dir = root / "knowledge_base"
    runs_dir = root / "runs"
    knowledge_base = KnowledgeBase(knowledge_base_dir)
    knowledge_base.save({
        "entry_id": entry_id,
        "revision": "v1",
        "parent_revision": None,
        "track": track,
        "status": "published",
        "tags": [model_family, track, "gain-compute"],
        "title": preset.get("title") or f"{model_family} {'结构优化增益与算量' if track == 'architecture' else '固定架构超参调优'}经验知识库",
        "summary": (
            f"面向 {model_family}（{track} 轨道）的实证经验知识库。"
            f"主指标：{primary_metric}（{direction}）；算量约束：{compute_metric} <= {max_compute_ratio}x；"
            f"总成本上限：{max_cost} {cost_unit}。"
        ),
        "reviewed_by": "init-seed",
        "published_at": 0,
        "scope": {
            "model_family": model_family,
            "forbidden_ops": preset.get("forbidden_ops", []),
            "max_compute_value": max_compute_value,
            "max_compute_ratio": max_compute_ratio,
            "param_bounds": preset["param_bounds"],
        },
        "patterns": preset.get("patterns", []),
        "anti_patterns": preset.get("anti_patterns", []),
        "evidence": [],
    }, allow_overwrite_revision=True)

    stage_list = stages or ["training", "evaluation"]
    plan = CampaignPlan.from_dict({
        "schema_version": 1,
        "track": track,
        "model_family": model_family,
        "knowledge_entry_ref": entry_id,
        "knowledge": knowledge_base.freeze_snapshot(entry_id),
        "base_hypothesis": f"建立 {model_family} 在 {primary_metric} 与 {compute_metric} 上的参照基线（trial-000）。",
        "baseline_model_ref": f"uri://models/{model_family}-baseline",
        "dataset_ref": f"uri://datasets/{model_family}-train",
        "dev_evaluator_ref": f"uri://evaluators/{model_family}-dev",
        "holdout_evaluator_ref": f"uri://evaluators/{model_family}-holdout",
        "base_config": preset["base_config"],
        "base_architecture": preset.get("base_architecture") or (
            copy.deepcopy(preset["base_config"]) if track == "architecture" else None
        ),
        "base_training_recipe": preset.get("base_training_recipe") or (
            copy.deepcopy(preset["base_config"]) if track == "hpo" else {}
        ),
        "mutable_fields": preset["mutable_fields"],
        "stages": stage_list,
        "budget": {
            "max_trials": max_trials,
            "cost_metric": {
                "name": cost_metric,
                "unit": cost_unit,
                "max_total": max_cost,
            },
        },
        "acceptance": {
            "primary_metric": {
                "name": primary_metric,
                "direction": direction,
                "min_gain": min_gain,
                "tie_tolerance": tie_tolerance,
                "holdout_target": holdout_target,
            },
            "compute_metric": {
                "name": compute_metric,
                "unit": compute_unit,
                "direction": "minimize",
                "max_value": max_compute_value,
                "max_ratio": max_compute_ratio,
            },
            "guardrails": {
                "max_metrics": {},
                "min_metrics": {},
            },
        },
    })
    plan_path = root / "campaign.json"
    write_json_atomic(plan_path, plan.to_dict())

    mcp_lines = [
        f"# {model_family} · 环境已有 MCP 工具映射表",
        "",
        "请将下方 `<your_*_mcp_tool>` 替换为当前环境中实际可用的 MCP 工具名及参数映射：",
        "",
        "| 阶段 | MCP 工具名 | 输入来源 | 必须提取并回填的字段 |",
        "| --- | --- | --- | --- |",
        *[
            f"| `{st}` | `<your_{st}_mcp_tool>` | `candidate_config` + 冻结项 | "
            + (
                f"`{primary_metric}`, `{compute_metric}`, 护栏指标, `cost.{cost_metric}`"
                if st == "evaluation"
                else f"`artifacts.model_ref`, `cost.{cost_metric}`, 远端 `job_id`"
            )
            + " |"
            for st in stage_list
        ],
        "",
        "## 异常与留出隔离约定",
        f"- 训练 OOM / NaN / 超时：先取消远端任务，再执行 `campaign record latest --status crash --cost '{{\"{cost_metric}\": <已消耗>}}' --note \"<原因>\"`。",
        "- 开发迭代期只准调用 `dev_evaluator_ref`；仅在收束后对 `incumbent.model_ref` 调用唯一一次 `holdout_evaluator_ref`。",
        "",
    ]
    mcp_path = root / "mcp_tools.md"
    write_text_atomic(mcp_path, "\n".join(mcp_lines))

    cli_self = Path(os.path.realpath(__file__))
    ar_cmd = f'python3 "{cli_self}" --workspace "{root}"'
    prog_lines = [
        f"# Research Program · {model_family}（{track} 轨道）",
        "",
        f"- **主指标**：`{primary_metric}`（`{direction}`，`min_gain={min_gain}`，`holdout_target={holdout_target}`）",
        f"- **算量红线**：`{compute_metric}`（`<= {max_compute_ratio}x` 基线，上限 `{max_compute_value}` {compute_unit}）",
        f"- **总预算**：`max_trials={max_trials}`（含 `trial-000` 基线 + `{max_trials - 1}` 轮候选），`{cost_metric} <= {max_cost} {cost_unit}`",
        "",
        "## 标准命令流",
        "```bash",
        f"{ar_cmd} doctor",
        f"{ar_cmd} knowledge-base search --model-family {model_family} --track {track}",
        f"{ar_cmd} campaign create",
        f"{ar_cmd} campaign baseline latest",
        "# 调 MCP 跑基线后回填：",
        f"{ar_cmd} campaign record latest --status succeeded --metrics '{{\"{primary_metric}\": <val>, \"{compute_metric}\": <val>}}' --cost '{{\"{cost_metric}\": <val>}}' --artifacts '{{\"model_ref\": \"<uri>\"}}'",
        "# 多轮棘轮（重复至目标达成或预算收束）：",
        f"{ar_cmd} campaign context latest",
        f"{ar_cmd} campaign propose latest --hypothesis \"<单一清晰可归因假设>\" --changes '{{\"<field>\": <val>}}'",
        "# 唯一一次 Holdout 盲评与知识库蒸馏：",
        f"{ar_cmd} campaign finalize latest --metrics '{{\"{primary_metric}\": <val>, \"{compute_metric}\": <val>}}' --cost '{{\"{cost_metric}\": <val>}}' --artifacts '{{\"model_ref\": \"<incumbent_uri>\"}}'",
        f"{ar_cmd} knowledge-base distill latest",
        "```",
        "",
    ]
    prog_path = root / "program.md"
    write_text_atomic(prog_path, "\n".join(prog_lines))
    runs_dir.mkdir(parents=True, exist_ok=True)

    return {
        "workspace": str(root),
        "preset": chosen_preset_key,
        "track": track,
        "entry_id": entry_id,
        "campaign_plan": str(plan_path),
        "program_md": str(prog_path),
        "mcp_tools_md": str(mcp_path),
        "knowledge_base_dir": str(knowledge_base_dir),
        "knowledge_base_index": str(knowledge_base.index_md_path),
        "candidate_slots": max_trials - 1,
    }


def _load_json_or_file(raw: str | None) -> Any:
    if raw is None:
        return None
    stripped = raw.strip()
    if stripped.startswith(("{", "[")):
        return json.loads(stripped)
    try:
        candidate = Path(stripped)
        if candidate.is_file():
            return json.loads(candidate.read_text(encoding="utf-8"))
    except OSError:
        pass
    return json.loads(stripped)


def _parse_str_list(raw: Any) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    text = str(raw).strip()
    if text.startswith("["):
        arr = json.loads(text)
        if not isinstance(arr, list):
            raise ValueError("Expected JSON array")
        return [str(x).strip() for x in arr if str(x).strip()]
    return [part.strip() for part in text.split(",") if part.strip()]


def _resolve_holdout_report(source: Path) -> dict[str, Any]:
    src = source.resolve()
    if src.is_file():
        return json.loads(src.read_text(encoding="utf-8"))
    if src.is_dir():
        if (src / "holdout_report.json").is_file():
            return json.loads((src / "holdout_report.json").read_text(encoding="utf-8"))
        runs_candidate = src / "runs" if (src / "runs" / "latest.txt").is_file() else src
        if (runs_candidate / "latest.txt").is_file():
            ctrl = CampaignController(runs_candidate)
            report = ctrl.status("latest").get("holdout_report")
            if isinstance(report, dict):
                return report
    raise ValueError(f"Could not locate a completed holdout_report.json from {source}")


def configure_workspace(args: argparse.Namespace, workspace: Path) -> dict[str, Any]:
    ws = workspace.resolve()
    plan_path = ws / "campaign.json"
    knowledge_base_dir = ws / "knowledge_base"
    if not plan_path.is_file():
        raise ValueError(f"Missing campaign.json in {ws}; run `init` first")

    spec = _load_json_or_file(args.spec) or {}
    if not isinstance(spec, dict):
        raise ValueError("--spec must resolve to a JSON object")

    plan_raw = json.loads(plan_path.read_text(encoding="utf-8"))
    knowledge_base = KnowledgeBase(knowledge_base_dir)
    entry_id = args.entry_id or spec.get("entry_id") or plan_raw.get("knowledge_entry_ref")
    entry_doc = knowledge_base.load(entry_id)
    if entry_doc["revision"] != "v1" or len(entry_doc.get("revisions", [])) > 1 or entry_doc.get("evidence"):
        raise ValueError(
            f"Knowledge entry {entry_id} already has empirical history ({entry_doc['revision']}); "
            "use `knowledge-base distill` + `knowledge-base publish` instead of overwriting v1 seed."
        )

    handoff_src = args.from_holdout or (Path(spec["from_holdout"]) if spec.get("from_holdout") else None)
    if handoff_src is not None:
        holdout = _resolve_holdout_report(Path(handoff_src))
        if holdout.get("track") != "architecture":
            raise ValueError("--from-holdout requires a holdout_report from an 'architecture' campaign")
        if plan_raw.get("track") != "hpo":
            raise ValueError("--from-holdout can only be applied to a workspace initialized with --track hpo")
        inc_cfg = holdout.get("incumbent_config")
        if not isinstance(inc_cfg, dict) or not inc_cfg:
            raise ValueError("Source holdout_report does not contain a valid incumbent_config")
        plan_raw["base_architecture"] = copy.deepcopy(inc_cfg)
        if holdout.get("model_ref"):
            plan_raw["baseline_model_ref"] = str(holdout["model_ref"])
        plan_raw["base_hypothesis"] = (
            f"锁定已验收胜出结构（{holdout.get('campaign_id')} {holdout.get('incumbent_trial_id')}），"
            "建立固定架构训练超参基线（trial-000）。"
        )

    base_cfg = _load_json_or_file(args.base_config) if args.base_config is not None else spec.get("base_config")
    base_arch = (
        _load_json_or_file(args.base_architecture)
        if args.base_architecture is not None
        else spec.get("base_architecture")
    )
    base_recipe = _load_json_or_file(args.base_recipe) if args.base_recipe is not None else spec.get("base_training_recipe")
    mut_fields = (
        _parse_str_list(args.mutable_fields)
        if args.mutable_fields is not None
        else _parse_str_list(spec.get("mutable_fields"))
    )
    p_bounds = _load_json_or_file(args.param_bounds) if args.param_bounds is not None else spec.get("param_bounds")
    f_ops = (
        _parse_str_list(args.forbidden_ops)
        if args.forbidden_ops is not None
        else _parse_str_list(spec.get("forbidden_ops"))
    )
    guardrails = _load_json_or_file(args.guardrails) if args.guardrails is not None else spec.get("guardrails")
    patterns = _load_json_or_file(args.patterns) if args.patterns is not None else spec.get("patterns")
    anti_patterns = (
        _load_json_or_file(args.anti_patterns) if args.anti_patterns is not None else spec.get("anti_patterns")
    )

    if base_cfg is not None:
        if not isinstance(base_cfg, dict) or not base_cfg:
            raise ValueError("base_config must be a non-empty JSON object")
        plan_raw["base_config"] = base_cfg
        if plan_raw["track"] == "architecture" and base_arch is None:
            plan_raw["base_architecture"] = copy.deepcopy(base_cfg)
        elif plan_raw["track"] == "hpo" and base_recipe is None:
            plan_raw["base_training_recipe"] = copy.deepcopy(base_cfg)
    if base_arch is not None:
        plan_raw["base_architecture"] = base_arch
    if base_recipe is not None:
        plan_raw["base_training_recipe"] = base_recipe
    if mut_fields is not None:
        plan_raw["mutable_fields"] = mut_fields

    for ref_key in ("baseline_model_ref", "dataset_ref", "dev_evaluator_ref", "holdout_evaluator_ref", "base_hypothesis"):
        if ref_key in spec and spec[ref_key] is not None:
            plan_raw[ref_key] = spec[ref_key]

    if guardrails is not None:
        plan_raw.setdefault("acceptance", {})["guardrails"] = guardrails
    if args.tie_tolerance is not None or "tie_tolerance" in spec:
        val = args.tie_tolerance if args.tie_tolerance is not None else spec["tie_tolerance"]
        plan_raw["acceptance"]["primary_metric"]["tie_tolerance"] = float(val)
    if args.min_gain is not None or "min_gain" in spec:
        val = args.min_gain if args.min_gain is not None else spec["min_gain"]
        plan_raw["acceptance"]["primary_metric"]["min_gain"] = float(val)
    if args.holdout_target is not None or "holdout_target" in spec:
        val = args.holdout_target if args.holdout_target is not None else spec["holdout_target"]
        plan_raw["acceptance"]["primary_metric"]["holdout_target"] = val
    if args.max_trials is not None or "max_trials" in spec:
        val = args.max_trials if args.max_trials is not None else spec["max_trials"]
        plan_raw["budget"]["max_trials"] = int(val)

    scope = copy.deepcopy(entry_doc.get("scope") or {})
    if p_bounds is not None:
        if not isinstance(p_bounds, dict):
            raise ValueError("param_bounds must be a JSON object")
        scope["param_bounds"] = p_bounds
    if f_ops is not None:
        scope["forbidden_ops"] = f_ops

    active_bounds = scope.get("param_bounds") or {}
    seed_vals = {
        field_key: get_by_path(plan_raw["base_config"], field_key)
        for field_key in plan_raw["mutable_fields"]
        if has_path(plan_raw["base_config"], field_key)
    }
    if seed_vals:
        validate_proposal_bounds(
            Proposal(hypothesis="validate-seed-config", changes=seed_vals),
            active_bounds,
            forbidden_ops=scope.get("forbidden_ops"),
        )

    knowledge_base.save({
        "entry_id": entry_id,
        "revision": "v1",
        "parent_revision": None,
        "track": entry_doc["track"],
        "status": "published",
        "tags": spec.get("tags", entry_doc.get("tags", [])),
        "title": spec.get("title", entry_doc["title"]),
        "summary": spec.get("summary", entry_doc["summary"]),
        "scope": scope,
        "patterns": patterns if patterns is not None else entry_doc.get("patterns", []),
        "anti_patterns": anti_patterns if anti_patterns is not None else entry_doc.get("anti_patterns", []),
        "reviewed_by": spec.get("reviewed_by", entry_doc.get("reviewed_by", "engineer")),
        "published_at": entry_doc.get("published_at", 0),
        "evidence": [],
    }, allow_overwrite_revision=True)

    plan_raw["knowledge_entry_ref"] = entry_id
    plan_raw["knowledge"] = knowledge_base.freeze_snapshot(entry_id)
    validated = CampaignPlan.from_dict(plan_raw)
    write_json_atomic(plan_path, validated.to_dict())
    refreshed = knowledge_base.load(entry_id)

    return {
        "ok": True,
        "workspace": str(ws),
        "entry_id": entry_id,
        "revision": refreshed["revision"],
        "content_sha256": refreshed["content_sha256"],
        "track": validated.track,
        "mutable_fields": validated.mutable_fields,
        "param_bounds_fields": sorted((refreshed.get("scope") or {}).get("param_bounds") or {}),
        "patterns": len(refreshed.get("patterns", [])),
        "anti_patterns": len(refreshed.get("anti_patterns", [])),
        "max_trials": validated.budget["max_trials"],
        "candidate_slots": validated.budget["max_trials"] - 1,
    }


def run_doctor(workspace: Path | None) -> dict[str, Any]:
    report: dict[str, Any] = {
        "ok": sys.version_info >= (3, 10),
        "python_version": sys.version.split()[0],
        "skill_root": str(SKILL_ROOT),
        "seed_knowledge_base_dir": str(SEED_KNOWLEDGE_BASE_DIR),
        "available_presets": sorted(_load_presets()),
        "checks": ["self_contained_engine_ready"],
        "warnings": [],
        "errors": [] if sys.version_info >= (3, 10) else ["Python >= 3.10 is required"],
    }
    if SEED_KNOWLEDGE_BASE_DIR.is_dir():
        try:
            seed_entries = KnowledgeBase(SEED_KNOWLEDGE_BASE_DIR).list_entries()
            report["bundled_seed_entries"] = [e["entry_id"] for e in seed_entries]
            report["checks"].append("bundled_seed_knowledge_base_verified")
        except Exception as exc:
            report["ok"] = False
            report["errors"].append(f"Bundled seed knowledge_base integrity check failed: {exc}")

    if workspace is None:
        return report

    ws = workspace.resolve()
    report["workspace"] = str(ws)
    if not ws.is_dir():
        report["ok"] = False
        report["errors"].append(f"Workspace directory does not exist: {ws}")
        return report

    knowledge_base_dir = ws / "knowledge_base"
    if knowledge_base_dir.is_dir():
        try:
            knowledge_base = KnowledgeBase(knowledge_base_dir)
            entries = knowledge_base.list_entries()
            report["knowledge_base_entries"] = [
                {
                    "entry_id": e["entry_id"],
                    "revision": e["revision"],
                    "track": e["track"],
                    "patterns": len(e.get("patterns", [])),
                    "anti_patterns": len(e.get("anti_patterns", [])),
                    "drafts": len(e.get("draft_revisions", [])),
                }
                for e in entries
            ]
            report["checks"].append("knowledge_base_sha256_integrity_verified")
        except Exception as exc:
            report["ok"] = False
            report["errors"].append(f"Knowledge base integrity check failed: {exc}")
    else:
        report["ok"] = False
        report["errors"].append(f"Missing knowledge_base directory: {knowledge_base_dir}")

    plan_path = ws / "campaign.json"
    if plan_path.is_file():
        try:
            raw_plan = json.loads(plan_path.read_text(encoding="utf-8"))
            plan = CampaignPlan.from_dict(raw_plan)
            report["checks"].append("campaign_plan_valid")
            report["plan_summary"] = {
                "track": plan.track,
                "model_family": plan.model_family,
                "knowledge_entry_ref": plan.knowledge_entry_ref,
                "mutable_fields": plan.mutable_fields,
                "max_trials": plan.budget["max_trials"],
                "candidate_slots": plan.budget["max_trials"] - 1,
            }
            bounds = ((plan.knowledge.get("scope") or {}).get("param_bounds") or {})
            unbounded = [
                f for f in plan.mutable_fields
                if f not in bounds and (f.rsplit(".", 1)[-1] not in bounds)
            ]
            if unbounded:
                report["warnings"].append(f"mutable_fields missing param_bounds: {unbounded}")
        except Exception as exc:
            report["ok"] = False
            report["errors"].append(f"campaign.json validation failed: {exc}")
    else:
        report["ok"] = False
        report["errors"].append(f"Missing campaign.json: {plan_path}")

    mcp_path = ws / "mcp_tools.md"
    if mcp_path.is_file():
        placeholders = sorted(set(re.findall(r"<your_[a-z0-9_]+_mcp_tool>", mcp_path.read_text(encoding="utf-8"))))
        if placeholders:
            report["warnings"].append(f"mcp_tools.md contains unedited placeholders: {placeholders}")
        else:
            report["checks"].append("mcp_tools_customized")

    runs_dir = ws / "runs"
    if (runs_dir / "latest.txt").is_file():
        try:
            ctrl = CampaignController(runs_dir)
            ctx = ctrl.get_context("latest")
            report["latest_campaign"] = {
                "campaign_id": ctx["campaign_id"],
                "status": ctx["status"],
                "active_trial_id": ctx["active_trial"]["trial_id"] if ctx["active_trial"] else None,
                "incumbent_trial_id": ctx["incumbent"]["trial_id"] if ctx["incumbent"] else None,
                "remaining_budget": ctx["remaining_budget"],
            }
        except Exception as exc:
            report["warnings"].append(f"Failed to inspect latest campaign: {exc}")
    return report


# ---------------------------------------------------------------------------
# CLI Parser & Entrypoint
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="AutoResearch · 自包含零依赖模型自主优化控制面（BYO-MCP + 纯 Markdown 经验知识库 + 增益/算量棘轮）"
    )
    p.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="工作区根目录（自动推断 <ws>/knowledge_base、<ws>/runs 与 <ws>/campaign.json）",
    )
    p.add_argument("--runs-dir", type=Path, default=None, help="显式指定运行状态目录（默认 <workspace>/runs）")
    p.add_argument(
        "--knowledge-base-dir",
        type=Path,
        default=None,
        help="显式指定纯 Markdown 经验知识库目录（默认 <workspace>/knowledge_base；未传 --workspace 时回退技能内置预置知识库）",
    )
    sub = p.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init", help="初始化专属 AutoResearch 工作区（内置模型族与 HPO 预置知识库）")
    init_p.add_argument("--workspace", dest="init_workspace", type=Path, default=None, help="目标工作区目录")
    init_p.add_argument("--preset", default=None, help="可选预设：generic_arch | conv1d_transformer | edge_vit | cnn_csi | hpo_recipe")
    init_p.add_argument("--model-family", required=True, help="模型族标识，如 conv1d_transformer / edge_vit / cnn_csi_feedback")
    init_p.add_argument("--entry-id", required=True, help="经验知识库条目编号，如 CONV1D-ARCH-001")
    init_p.add_argument("--track", choices=TRACKS, default="architecture")
    init_p.add_argument("--metric", required=True, help="主指标名，如 accuracy / map50 / nmse_db / val_bpb")
    init_p.add_argument("--direction", choices=DIRECTIONS, default="maximize")
    init_p.add_argument("--min-gain", type=float, default=0.5)
    init_p.add_argument("--tie-tolerance", type=float, default=0.0)
    init_p.add_argument("--holdout-target", type=float, default=None)
    init_p.add_argument("--compute", default="flops_m", help="推理/模型算量指标名，如 flops_m / macs_m / latency_ms / params_m")
    init_p.add_argument("--compute-unit", default="MFLOPs")
    init_p.add_argument("--max-compute", type=float, default=None)
    init_p.add_argument("--max-compute-ratio", type=float, default=1.10)
    init_p.add_argument("--cost", default="gpu_seconds", help="搜索/训练成本指标名，如 gpu_seconds / gpu_hours")
    init_p.add_argument("--cost-unit", default="s")
    init_p.add_argument("--max-cost", type=float, default=3600.0)
    init_p.add_argument("--max-trials", type=int, default=6, help="总试验数（含 trial-000 基线）")
    init_p.add_argument("--stages", default="training,evaluation")

    cfg_p = sub.add_parser("configure", help="安全更新初始 v1 配置、param_bounds 与 NAS->HPO 胜出结构交接")
    cfg_p.add_argument("--workspace", dest="cfg_workspace", type=Path, default=None)
    cfg_p.add_argument("--spec", default=None, help="完整覆盖 JSON 字符串或文件路径")
    cfg_p.add_argument("--entry-id", default=None)
    cfg_p.add_argument("--base-config", default=None)
    cfg_p.add_argument("--base-architecture", default=None)
    cfg_p.add_argument("--base-recipe", default=None)
    cfg_p.add_argument("--mutable-fields", default=None)
    cfg_p.add_argument("--param-bounds", default=None)
    cfg_p.add_argument("--forbidden-ops", default=None)
    cfg_p.add_argument("--guardrails", default=None)
    cfg_p.add_argument("--tie-tolerance", type=float, default=None)
    cfg_p.add_argument("--min-gain", type=float, default=None)
    cfg_p.add_argument("--holdout-target", type=float, default=None)
    cfg_p.add_argument("--max-trials", type=int, default=None)
    cfg_p.add_argument("--patterns", default=None)
    cfg_p.add_argument("--anti-patterns", default=None)
    cfg_p.add_argument("--from-holdout", type=Path, default=None, help="已完成 architecture 工作区目录或 holdout_report.json")

    doc_p = sub.add_parser("doctor", help="检查引擎环境、知识库 SHA-256 完整性、campaign.json 契约与活跃运行状态")
    doc_p.add_argument("--workspace", dest="doc_workspace", type=Path, default=None)

    kb_p = sub.add_parser("knowledge-base", help="纯 Markdown 分层不可变经验知识库管理")
    kb_sub = kb_p.add_subparsers(dest="knowledge_base_command", required=True)
    kb_list = kb_sub.add_parser("list")
    kb_list.add_argument("--track", choices=TRACKS)
    kb_list.add_argument("--status", choices=KNOWLEDGE_STATUSES)
    kb_search = kb_sub.add_parser("search")
    kb_search.add_argument("--query", default="")
    kb_search.add_argument("--track", choices=TRACKS)
    kb_search.add_argument("--model-family", default=None)
    kb_search.add_argument("--field", default=None)
    kb_search.add_argument("--direction", choices=sorted(PATTERN_DIRECTIONS), default=None)
    kb_search.add_argument("--max-compute-ratio", type=float, default=None)
    kb_search.add_argument("--min-gain-pct", type=float, default=None)
    kb_search.add_argument("--failure-type", choices=sorted(FAILURE_TYPES), default=None)
    kb_search.add_argument("--status", choices=KNOWLEDGE_STATUSES, default="published")
    kb_show = kb_sub.add_parser("show")
    kb_show.add_argument("entry_id")
    kb_show.add_argument("--revision", default=None)
    kb_drafts = kb_sub.add_parser("drafts")
    kb_drafts.add_argument("entry_id", nargs="?", default=None)
    kb_distill = kb_sub.add_parser("distill")
    kb_distill.add_argument("campaign_id", nargs="?", default="latest")
    kb_distill.add_argument("--entry-id", default=None)
    kb_pub = kb_sub.add_parser("publish")
    kb_pub.add_argument("entry_id")
    kb_pub.add_argument("--revision", default=None)
    kb_pub.add_argument("--reviewer", default="human")
    kb_seed = kb_sub.add_parser("import-presets", help="将技能内置预置知识库条目导入目标 knowledge_base 目录")
    kb_seed.add_argument("--preset", default=None, help="仅导入指定预设，默认导入全部预置条目")
    kb_seed.add_argument("--overwrite", action="store_true", help="覆盖同名 v1 种子条目")
    kb_sub.add_parser("reindex")

    cmp_p = sub.add_parser("campaign", help="增益 + 算量棘轮研究闭环控制器")
    cmp_sub = cmp_p.add_subparsers(dest="campaign_command", required=True)
    c_create = cmp_sub.add_parser("create")
    c_create.add_argument("--plan", type=Path, default=None, help="默认读取 <workspace>/campaign.json")
    c_create.add_argument("--knowledge-entry", default=None, help="覆盖 plan.knowledge_entry_ref")
    c_create.add_argument("--knowledge-revision", default=None)

    c_base = cmp_sub.add_parser("baseline")
    c_base.add_argument("campaign_id", nargs="?", default="latest")

    c_ctx = cmp_sub.add_parser("context")
    c_ctx.add_argument("campaign_id", nargs="?", default="latest")

    c_prop = cmp_sub.add_parser("propose")
    c_prop.add_argument("campaign_id", nargs="?", default="latest")
    c_prop.add_argument("--hypothesis", default=None)
    c_prop.add_argument("--changes", default=None)
    c_prop.add_argument("--proposal-file", type=Path, default=None)
    c_prop.add_argument("--reuse-simulation", action="store_true")
    c_prop.add_argument("--allow-repeat", action="store_true", help="允许重复已有配置（仅用于多随机种子复核）")
    c_prop.add_argument("--force-anti-pattern", action="store_true", help="强制放行命中已知反例签名的提案")
    c_prop.add_argument("--dry-run", action="store_true", help="仅预校验白名单、合法域、去重与反例，不创建活跃 trial")

    c_rec = cmp_sub.add_parser("record")
    c_rec.add_argument("campaign_id", nargs="?", default="latest")
    c_rec.add_argument("--trial", default=None)
    c_rec.add_argument("--status", choices=("succeeded", "failed", "timeout", "crash", "cancelled"), default="succeeded")
    c_rec.add_argument("--metrics", default=None)
    c_rec.add_argument("--metrics-file", type=Path, default=None)
    c_rec.add_argument("--cost", default=None)
    c_rec.add_argument("--artifacts", default=None)
    c_rec.add_argument("--external-jobs", default=None)
    c_rec.add_argument("--note", default=None)

    c_fin = cmp_sub.add_parser("finalize")
    c_fin.add_argument("campaign_id", nargs="?", default="latest")
    c_fin.add_argument("--status", choices=("succeeded", "failed"), default="succeeded")
    c_fin.add_argument("--metrics", default=None)
    c_fin.add_argument("--metrics-file", type=Path, default=None)
    c_fin.add_argument("--cost", default=None)
    c_fin.add_argument("--artifacts", default=None)
    c_fin.add_argument("--external-jobs", default=None)
    c_fin.add_argument("--note", default=None)

    for simple_cmd in ("status", "events", "stop"):
        sc = cmp_sub.add_parser(simple_cmd)
        sc.add_argument("campaign_id", nargs="?", default="latest")

    return p


def _resolve_dirs(args: argparse.Namespace) -> tuple[Path | None, Path, Path]:
    ws: Path | None = args.workspace
    if ws is not None:
        ws = ws.resolve()
    runs_dir = (args.runs_dir or (ws / "runs" if ws else Path.cwd() / "runs")).resolve()
    if args.knowledge_base_dir is not None:
        knowledge_base_dir = args.knowledge_base_dir.resolve()
    elif ws is not None:
        knowledge_base_dir = (ws / "knowledge_base").resolve()
    elif (Path.cwd() / "knowledge_base").is_dir():
        knowledge_base_dir = (Path.cwd() / "knowledge_base").resolve()
    else:
        knowledge_base_dir = SEED_KNOWLEDGE_BASE_DIR.resolve()
    return ws, runs_dir, knowledge_base_dir


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "init":
            target_ws = args.init_workspace or args.workspace
            if target_ws is None:
                raise ValueError("Pass --workspace <dir> to `init`")
            stages = [s.strip() for s in args.stages.split(",") if s.strip()]
            _print_json(init_workspace(
                workspace=target_ws,
                model_family=args.model_family,
                entry_id=args.entry_id,
                primary_metric=args.metric,
                direction=args.direction,
                min_gain=args.min_gain,
                tie_tolerance=args.tie_tolerance,
                holdout_target=args.holdout_target,
                compute_metric=args.compute,
                compute_unit=args.compute_unit,
                max_compute_value=args.max_compute,
                max_compute_ratio=args.max_compute_ratio,
                cost_metric=args.cost,
                cost_unit=args.cost_unit,
                max_cost=args.max_cost,
                max_trials=args.max_trials,
                track=args.track,
                stages=stages,
                preset_name=args.preset,
            ))
            return 0

        if args.command == "configure":
            target_ws = args.cfg_workspace or args.workspace
            if target_ws is None:
                raise ValueError("Pass --workspace <dir> to `configure`")
            _print_json(configure_workspace(args, target_ws))
            return 0

        if args.command == "doctor":
            target_ws = args.doc_workspace or args.workspace
            rep = run_doctor(target_ws)
            _print_json(rep)
            return 0 if rep["ok"] else 2

        ws, runs_dir, knowledge_base_dir = _resolve_dirs(args)

        if args.command == "knowledge-base":
            knowledge_base = KnowledgeBase(knowledge_base_dir)
            cmd = args.knowledge_base_command
            if cmd == "list":
                _print_json([
                    {
                        "entry_id": e["entry_id"],
                        "revision": e["revision"],
                        "track": e["track"],
                        "status": e["status"],
                        "model_family": (e.get("scope") or {}).get("model_family"),
                        "patterns": len(e.get("patterns", [])),
                        "anti_patterns": len(e.get("anti_patterns", [])),
                        "evidence": len(e.get("evidence", [])),
                        "drafts": len(e.get("draft_revisions", [])),
                    }
                    for e in knowledge_base.list_entries(track=args.track, status=args.status)
                ])
                return 0
            if cmd == "search":
                _print_json(knowledge_base.search(
                    query=args.query,
                    track=args.track,
                    model_family=args.model_family,
                    field_name=args.field,
                    direction=args.direction,
                    max_compute_ratio=args.max_compute_ratio,
                    min_gain_pct=args.min_gain_pct,
                    failure_type=args.failure_type,
                    status=args.status,
                ))
                return 0
            if cmd == "show":
                _print_json(knowledge_base.load(args.entry_id, revision=args.revision))
                return 0
            if cmd == "drafts":
                _print_json(knowledge_base.list_drafts(args.entry_id))
                return 0
            if cmd == "distill":
                ctrl = CampaignController(runs_dir)
                cmp_state = ctrl.status(args.campaign_id)
                _print_json(knowledge_base.distill_from_campaign(cmp_state, entry_id=args.entry_id))
                return 0
            if cmd == "publish":
                pub = knowledge_base.publish(args.entry_id, draft_revision=args.revision, reviewer=args.reviewer)
                _print_json({
                    "entry_id": pub["entry_id"],
                    "revision": pub["revision"],
                    "status": pub["status"],
                    "reviewed_by": pub.get("reviewed_by"),
                    "patterns": len(pub.get("patterns", [])),
                    "anti_patterns": len(pub.get("anti_patterns", [])),
                    "evidence": len(pub.get("evidence", [])),
                    "content_sha256": pub["content_sha256"],
                })
                return 0
            if cmd == "import-presets":
                imported = knowledge_base.import_seed_library(preset_filter=args.preset, overwrite=args.overwrite)
                _print_json({
                    "knowledge_base_dir": str(knowledge_base_dir),
                    "imported_entries": imported,
                    "index_md": str(knowledge_base.index_md_path),
                })
                return 0
            if cmd == "reindex":
                idx_path = knowledge_base.reindex()
                _print_json({"index_md": str(idx_path), "entries": len(knowledge_base.list_entries())})
                return 0

        if args.command == "campaign":
            ctrl = CampaignController(runs_dir)
            if args.campaign_command == "create":
                plan_path = args.plan or ((ws / "campaign.json") if ws else Path.cwd() / "campaign.json")
                if not plan_path.is_file():
                    raise ValueError(f"Missing campaign plan file: {plan_path}")
                state = ctrl.create(
                    json.loads(plan_path.read_text(encoding="utf-8")),
                    knowledge_base_dir=knowledge_base_dir,
                    entry_id=args.knowledge_entry,
                    entry_revision=args.knowledge_revision,
                )
                _print_json({
                    "campaign_id": state["campaign_id"],
                    "track": state["plan"]["track"],
                    "status": state["status"],
                    "runs_dir": str(runs_dir / state["campaign_id"]),
                })
                return 0
            if args.campaign_command == "baseline":
                trial = ctrl.begin_baseline(args.campaign_id)
                ctx = ctrl.get_context(args.campaign_id)
                _print_json({
                    "campaign_id": ctx["campaign_id"],
                    "trial": trial,
                    "dev_evaluator_ref": ctx["evaluators"]["dev_evaluator_ref"],
                    "remaining_budget": ctx["remaining_budget"],
                })
                return 0
            if args.campaign_command == "context":
                _print_json(ctrl.get_context(args.campaign_id))
                return 0
            if args.campaign_command == "propose":
                if args.proposal_file is not None:
                    prop = Proposal.from_dict(json.loads(args.proposal_file.read_text(encoding="utf-8")))
                else:
                    if not args.hypothesis or not args.changes:
                        raise ValueError("Provide --proposal-file or both --hypothesis and --changes")
                    prop = Proposal.from_dict({
                        "hypothesis": args.hypothesis,
                        "changes": _load_json_or_file(args.changes),
                        "reuse_simulation": args.reuse_simulation,
                    })
                res = ctrl.propose(
                    args.campaign_id,
                    prop,
                    allow_repeat=args.allow_repeat,
                    force_anti_pattern=args.force_anti_pattern,
                    dry_run=args.dry_run,
                )
                if args.dry_run:
                    _print_json(res)
                else:
                    ctx = ctrl.get_context(args.campaign_id)
                    _print_json({
                        "campaign_id": ctx["campaign_id"],
                        "trial_id": res["trial_id"],
                        "config_id": res["config_id"],
                        "status": res["run_status"],
                        "candidate_config": res["candidate_config"],
                        "frozen_architecture": res["frozen_architecture"],
                        "frozen_training_recipe": res["frozen_training_recipe"],
                        "dev_evaluator_ref": ctx["evaluators"]["dev_evaluator_ref"],
                    })
                return 0
            if args.campaign_command == "record":
                metrics = (
                    json.loads(args.metrics_file.read_text(encoding="utf-8"))
                    if args.metrics_file is not None
                    else (_load_json_or_file(args.metrics) or {})
                )
                cost = _load_json_or_file(args.cost) or {}
                artifacts = _load_json_or_file(args.artifacts) or {}
                ext_jobs = _load_json_or_file(args.external_jobs) or []
                trial = ctrl.record(
                    args.campaign_id,
                    trial_id=args.trial,
                    status=args.status,
                    metrics=metrics,
                    cost=cost,
                    artifacts=artifacts,
                    external_jobs=ext_jobs,
                    note=args.note,
                )
                ctx = ctrl.get_context(args.campaign_id)
                _print_json({
                    "campaign_id": ctx["campaign_id"],
                    "campaign_status": ctx["status"],
                    "trial_id": trial["trial_id"],
                    "decision": trial["decision"],
                    "reason": trial["decision_reason"],
                    "gain": trial["gain"],
                    "gain_pct": trial["gain_pct"],
                    "compute_value": trial["compute_value"],
                    "compute_ratio": trial["compute_ratio"],
                    "cost_value": trial["cost_value"],
                    "cumulative_cost": trial["cumulative_cost"],
                    "incumbent_trial_id": ctx["incumbent"]["trial_id"] if ctx["incumbent"] else None,
                    "remaining_budget": ctx["remaining_budget"],
                    "plateau_warning": ctx["search_diagnostics"]["plateau_warning"],
                    "results_tsv": str(runs_dir / ctx["campaign_id"] / "results.tsv"),
                })
                return 0 if ctx["status"] != "failed" else 1
            if args.campaign_command == "finalize":
                metrics = (
                    json.loads(args.metrics_file.read_text(encoding="utf-8"))
                    if args.metrics_file is not None
                    else (_load_json_or_file(args.metrics) or {})
                )
                cost = _load_json_or_file(args.cost) or {}
                artifacts = _load_json_or_file(args.artifacts) or {}
                ext_jobs = _load_json_or_file(args.external_jobs) or []
                state = ctrl.finalize(
                    args.campaign_id,
                    status=args.status,
                    metrics=metrics,
                    cost=cost,
                    artifacts=artifacts,
                    external_jobs=ext_jobs,
                    note=args.note,
                )
                _print_json({
                    "campaign_id": state["campaign_id"],
                    "status": state["status"],
                    "incumbent_trial_id": state["incumbent_trial_id"],
                    "holdout_report": state["holdout_report"],
                    "holdout_report_path": str(runs_dir / state["campaign_id"] / "holdout_report.json"),
                })
                return 0 if state["status"] == "succeeded" else 1
            if args.campaign_command == "status":
                _print_json(ctrl.status(args.campaign_id))
                return 0
            if args.campaign_command == "events":
                _print_json(ctrl.events(args.campaign_id))
                return 0
            if args.campaign_command == "stop":
                _print_json(ctrl.stop(args.campaign_id))
                return 0
        return 2
    except (ValueError, OSError, KeyError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
