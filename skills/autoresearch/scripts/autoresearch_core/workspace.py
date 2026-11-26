from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

from .campaign import CampaignController
from .contracts import CampaignPlan, Proposal, validate_proposal_bounds
from .knowledge_base import (
    KnowledgeBase,
    SEED_KNOWLEDGE_BASE_DIR,
    SKILL_ROOT,
    load_presets,
)
from .utils import get_by_path, has_path, write_json_atomic, write_text_atomic


def load_json_or_file(raw: str | None) -> Any:
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


def parse_str_list(raw: Any) -> list[str] | None:
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
    max_parallel_trials: int = 1,
    track: str = "architecture",
    stages: list[str] | None = None,
    preset_name: str | None = None,
) -> dict[str, Any]:
    root = workspace.resolve()
    root.mkdir(parents=True, exist_ok=True)
    presets = load_presets()
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
        "title": preset.get("title") or (
            f"{model_family} {'结构优化增益与算量' if track == 'architecture' else '固定架构超参调优'}经验知识库"
        ),
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
            "max_parallel_trials": max_parallel_trials,
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
        "## 异常分类与留出隔离约定",
        f"- 训练 OOM / NaN / 超时：先取消远端任务，再执行 `campaign record latest --status crash --failure-kind <oom|nan_divergence|timeout|infra_flake> --cost '{{\"{cost_metric}\": <已消耗>}}' --note \"<原因>\"`。",
        "- 集群瞬时抖动务必标 `--failure-kind infra_flake`，避免把有效配置误判为科学反例。",
        "- 开发迭代期只准调用 `dev_evaluator_ref`；仅在收束后对 `incumbent.model_ref` 调用唯一一次 `holdout_evaluator_ref`。",
        "",
    ]
    mcp_path = root / "mcp_tools.md"
    write_text_atomic(mcp_path, "\n".join(mcp_lines))

    cli_self = SKILL_ROOT / "scripts" / "autoresearch.py"
    ar_cmd = f'python3 "{cli_self}" --workspace "{root}"'
    prog_lines = [
        f"# Research Program · {model_family}（{track} 轨道）",
        "",
        f"- **主指标**：`{primary_metric}`（`{direction}`，`min_gain={min_gain}`，`holdout_target={holdout_target}`）",
        f"- **算量红线**：`{compute_metric}`（`<= {max_compute_ratio}x` 基线，上限 `{max_compute_value}` {compute_unit}）",
        f"- **总预算**：`max_trials={max_trials}`（含基线 + `{max_trials - 1}` 轮候选，最大并发 `{max_parallel_trials}`），`{cost_metric} <= {max_cost} {cost_unit}`",
        "",
        "## 标准命令流",
        "```bash",
        f"{ar_cmd} doctor",
        f"{ar_cmd} knowledge-base search --model-family {model_family} --track {track}",
        f"{ar_cmd} campaign create",
        f"{ar_cmd} campaign baseline latest",
        "# 调 MCP 跑基线后回填：",
        f"{ar_cmd} campaign record latest --status succeeded --metrics '{{\"{primary_metric}\": <val>, \"{compute_metric}\": <val>}}' --cost '{{\"{cost_metric}\": <val>}}' --artifacts '{{\"model_ref\": \"<uri>\"}}'",
        "# 多轮演化探索（支持跳板父节点、多保真预筛、并行批次与预测校准）：",
        f"{ar_cmd} campaign context latest",
        f"{ar_cmd} campaign propose latest --operator refine --fidelity full --hypothesis \"<单一清晰可归因假设>\" --changes '{{\"<field>\": <val>}}'",
        "# 唯一一次 Holdout 盲评、总结报告与知识库蒸馏：",
        f"{ar_cmd} campaign finalize latest --metrics '{{\"{primary_metric}\": <val>, \"{compute_metric}\": <val>}}' --cost '{{\"{cost_metric}\": <val>}}' --artifacts '{{\"model_ref\": \"<incumbent_uri>\"}}'",
        f"{ar_cmd} campaign report latest",
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
        "max_parallel_trials": max_parallel_trials,
    }


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

    spec = load_json_or_file(args.spec) or {}
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

    base_cfg = load_json_or_file(args.base_config) if args.base_config is not None else spec.get("base_config")
    base_arch = (
        load_json_or_file(args.base_architecture)
        if args.base_architecture is not None
        else spec.get("base_architecture")
    )
    base_recipe = load_json_or_file(args.base_recipe) if args.base_recipe is not None else spec.get("base_training_recipe")
    mut_fields = (
        parse_str_list(args.mutable_fields)
        if args.mutable_fields is not None
        else parse_str_list(spec.get("mutable_fields"))
    )
    p_bounds = load_json_or_file(args.param_bounds) if args.param_bounds is not None else spec.get("param_bounds")
    f_ops = (
        parse_str_list(args.forbidden_ops)
        if args.forbidden_ops is not None
        else parse_str_list(spec.get("forbidden_ops"))
    )
    guardrails = load_json_or_file(args.guardrails) if args.guardrails is not None else spec.get("guardrails")
    patterns = load_json_or_file(args.patterns) if args.patterns is not None else spec.get("patterns")
    anti_patterns = (
        load_json_or_file(args.anti_patterns) if args.anti_patterns is not None else spec.get("anti_patterns")
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
    if getattr(args, "max_parallel", None) is not None or "max_parallel_trials" in spec:
        val = args.max_parallel if getattr(args, "max_parallel", None) is not None else spec["max_parallel_trials"]
        plan_raw["budget"]["max_parallel_trials"] = int(val)

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
        "max_parallel_trials": validated.budget.get("max_parallel_trials", 1),
        "candidate_slots": validated.budget["max_trials"] - 1,
    }


def run_doctor(workspace: Path | None) -> dict[str, Any]:
    report: dict[str, Any] = {
        "ok": sys.version_info >= (3, 10),
        "python_version": sys.version.split()[0],
        "skill_root": str(SKILL_ROOT),
        "seed_knowledge_base_dir": str(SEED_KNOWLEDGE_BASE_DIR),
        "available_presets": sorted(load_presets()),
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
                "max_parallel_trials": plan.budget.get("max_parallel_trials", 1),
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
                "active_trial_ids": [t["trial_id"] for t in ctx.get("active_trials", [])],
                "incumbent_trial_id": ctx["incumbent"]["trial_id"] if ctx["incumbent"] else None,
                "pareto_frontier_size": len(ctx.get("pareto_frontier", [])),
                "remaining_budget": ctx["remaining_budget"],
            }
        except Exception as exc:
            report["warnings"].append(f"Failed to inspect latest campaign: {exc}")
    return report
