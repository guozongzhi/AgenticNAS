#!/usr/bin/env python3
"""Self-contained zero-dependency CLI for the AutoResearch Agent Skill."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any


SCRIPT_DIR = Path(os.path.realpath(__file__)).parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from autoresearch_core.campaign import CampaignController  # noqa: E402
from autoresearch_core.contracts import (  # noqa: E402
    DIRECTIONS,
    FAILURE_TYPES,
    FIDELITIES,
    KNOWLEDGE_STATUSES,
    PATTERN_DIRECTIONS,
    PROPOSAL_OPERATORS,
    Proposal,
    RECORD_FAILURE_KINDS,
    TRACKS,
)
from autoresearch_core.knowledge_base import (  # noqa: E402
    KnowledgeBase,
    SEED_KNOWLEDGE_BASE_DIR,
)
from autoresearch_core.workspace import (  # noqa: E402
    configure_workspace,
    init_workspace,
    load_json_or_file,
    parse_str_list,
    run_doctor,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "AutoResearch · 自包含零依赖模型自主优化控制面"
            "（BYO-MCP + 纯 Markdown 经验知识库 + 跳板谱系/多保真/并行棘轮）"
        )
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
    init_p.add_argument("--workspace", dest="init_workspace", type=Path, default=None)
    init_p.add_argument("--preset", default=None, help="预设：generic_arch | conv1d_transformer | edge_vit | cnn_csi | hpo_recipe")
    init_p.add_argument("--model-family", required=True)
    init_p.add_argument("--entry-id", required=True)
    init_p.add_argument("--track", choices=TRACKS, default="architecture")
    init_p.add_argument("--metric", required=True)
    init_p.add_argument("--direction", choices=DIRECTIONS, default="maximize")
    init_p.add_argument("--min-gain", type=float, default=0.5)
    init_p.add_argument("--tie-tolerance", type=float, default=0.0)
    init_p.add_argument("--holdout-target", type=float, default=None)
    init_p.add_argument("--compute", default="flops_m")
    init_p.add_argument("--compute-unit", default="MFLOPs")
    init_p.add_argument("--max-compute", type=float, default=None)
    init_p.add_argument("--max-compute-ratio", type=float, default=1.10)
    init_p.add_argument("--cost", default="gpu_seconds")
    init_p.add_argument("--cost-unit", default="s")
    init_p.add_argument("--max-cost", type=float, default=3600.0)
    init_p.add_argument("--max-trials", type=int, default=6, help="总试验数（含 trial-000 基线）")
    init_p.add_argument("--max-parallel", type=int, default=1, help="单轮最大并发活跃试验数（多卡集群可设 2~8）")
    init_p.add_argument("--stages", default="training,evaluation")

    cfg_p = sub.add_parser("configure", help="安全更新初始 v1 配置、param_bounds 与 NAS->HPO 胜出结构交接")
    cfg_p.add_argument("--workspace", dest="cfg_workspace", type=Path, default=None)
    cfg_p.add_argument("--spec", default=None)
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
    cfg_p.add_argument("--max-parallel", type=int, default=None)
    cfg_p.add_argument("--patterns", default=None)
    cfg_p.add_argument("--anti-patterns", default=None)
    cfg_p.add_argument("--from-holdout", type=Path, default=None)

    doc_p = sub.add_parser("doctor", help="检查引擎环境、知识库 SHA-256 完整性、campaign.json 契约与活跃运行状态")
    doc_p.add_argument("--workspace", dest="doc_workspace", type=Path, default=None)

    kb_p = sub.add_parser("knowledge-base", help="纯 Markdown 分层不可变经验知识库管理（检索 / 蒸馏 / 发布 / 淘汰修剪）")
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
    kb_prune = kb_sub.add_parser("prune", help="淘汰低胜率失效经验（MLEvolver Skill Deletion），默认仅预览")
    kb_prune.add_argument("entry_id")
    kb_prune.add_argument("--min-win-rate", type=float, default=0.34)
    kb_prune.add_argument("--min-observations", type=int, default=2)
    kb_prune.add_argument("--include-verified", action="store_true")
    kb_prune.add_argument("--apply", action="store_true", help="经用户确认后实际生成精简后的新修订版本")
    kb_prune.add_argument("--reviewer", default="human")
    kb_seed = kb_sub.add_parser("import-presets")
    kb_seed.add_argument("--preset", default=None)
    kb_seed.add_argument("--overwrite", action="store_true")
    kb_sub.add_parser("reindex")

    cmp_p = sub.add_parser("campaign", help="多维演化与增益-算量棘轮研究闭环控制器")
    cmp_sub = cmp_p.add_subparsers(dest="campaign_command", required=True)
    c_create = cmp_sub.add_parser("create")
    c_create.add_argument("--plan", type=Path, default=None)
    c_create.add_argument("--knowledge-entry", default=None)
    c_create.add_argument("--knowledge-revision", default=None)

    c_base = cmp_sub.add_parser("baseline")
    c_base.add_argument("campaign_id", nargs="?", default="latest")

    c_ctx = cmp_sub.add_parser("context")
    c_ctx.add_argument("campaign_id", nargs="?", default="latest")
    c_ctx.add_argument("--recent-window", type=int, default=6, help="Context Folding 保留完整细节的近期试验窗口大小")

    c_insp = cmp_sub.add_parser("inspect", help="按需展开查看任意折叠历史试验的完整记录与逐字段配置差异")
    c_insp.add_argument("campaign_id", nargs="?", default="latest")
    c_insp.add_argument("--trial", required=True, help="目标 trial_id，如 trial-001")

    c_prop = cmp_sub.add_parser("propose")
    c_prop.add_argument("campaign_id", nargs="?", default="latest")
    c_prop.add_argument("--hypothesis", default=None)
    c_prop.add_argument("--changes", default=None)
    c_prop.add_argument("--proposal-file", type=Path, default=None)
    c_prop.add_argument("--parent-trial", default=None, help="指定跳板父节点（默认当前 incumbent；支持回退分支或取 Pareto 精英）")
    c_prop.add_argument("--inspiration-trials", default=None, help="逗号分隔的跨分支灵感参考节点（如 trial-001,trial-003）")
    c_prop.add_argument("--operator", choices=PROPOSAL_OPERATORS, default="refine")
    c_prop.add_argument("--fidelity", choices=FIDELITIES, default="full", help="smoke / proxy（低保真筛查不污染 incumbent）或 full")
    c_prop.add_argument("--expected-primary", type=float, default=None, help="Predict-Then-Verify 预期主指标数值")
    c_prop.add_argument("--expected-compute-ratio", type=float, default=None, help="Predict-Then-Verify 预期算量比")
    c_prop.add_argument("--reuse-simulation", action="store_true")
    c_prop.add_argument("--allow-repeat", action="store_true")
    c_prop.add_argument("--force-anti-pattern", action="store_true")
    c_prop.add_argument("--dry-run", action="store_true")

    c_rec = cmp_sub.add_parser("record")
    c_rec.add_argument("campaign_id", nargs="?", default="latest")
    c_rec.add_argument("--trial", default=None)
    c_rec.add_argument("--status", choices=("succeeded", "failed", "timeout", "crash", "cancelled"), default="succeeded")
    c_rec.add_argument("--failure-kind", choices=RECORD_FAILURE_KINDS, default=None, help="区分 oom / nan_divergence / timeout / infra_flake")
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

    c_rep = cmp_sub.add_parser("report", help="生成结构化实验晨报与谱系分析 Markdown（REPORT.md）")
    c_rep.add_argument("campaign_id", nargs="?", default="latest")

    for simple_cmd in ("status", "events", "stop"):
        sc = cmp_sub.add_parser(simple_cmd)
        sc.add_argument("campaign_id", nargs="?", default="latest")

    return p


def _resolve_dirs(args: argparse.Namespace) -> tuple[Path | None, Path, Path]:
    ws: Path | None = args.workspace.resolve() if args.workspace is not None else None
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
                max_parallel_trials=args.max_parallel,
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
            if cmd == "prune":
                _print_json(knowledge_base.prune(
                    args.entry_id,
                    min_win_rate=args.min_win_rate,
                    min_observations=args.min_observations,
                    include_verified=args.include_verified,
                    apply=args.apply,
                    reviewer=args.reviewer,
                ))
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
            cmd = args.campaign_command
            if cmd == "create":
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
            if cmd == "baseline":
                trial = ctrl.begin_baseline(args.campaign_id)
                ctx = ctrl.get_context(args.campaign_id)
                _print_json({
                    "campaign_id": ctx["campaign_id"],
                    "trial": trial,
                    "dev_evaluator_ref": ctx["evaluators"]["dev_evaluator_ref"],
                    "remaining_budget": ctx["remaining_budget"],
                })
                return 0
            if cmd == "context":
                _print_json(ctrl.get_context(args.campaign_id, recent_window=args.recent_window))
                return 0
            if cmd == "inspect":
                _print_json(ctrl.inspect_trial(args.campaign_id, args.trial))
                return 0
            if cmd == "propose":
                if args.proposal_file is not None:
                    prop = Proposal.from_dict(json.loads(args.proposal_file.read_text(encoding="utf-8")))
                else:
                    if not args.hypothesis or not args.changes:
                        raise ValueError("Provide --proposal-file or both --hypothesis and --changes")
                    prop = Proposal.from_dict({
                        "hypothesis": args.hypothesis,
                        "changes": load_json_or_file(args.changes),
                        "parent_trial_id": args.parent_trial,
                        "inspiration_trial_ids": parse_str_list(args.inspiration_trials) or [],
                        "operator": args.operator,
                        "fidelity": args.fidelity,
                        "reuse_simulation": args.reuse_simulation,
                        "expected_primary": args.expected_primary,
                        "expected_compute_ratio": args.expected_compute_ratio,
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
                        "parent_trial_id": res["parent_trial_id"],
                        "fidelity": res["fidelity"],
                        "operator": res["operator"],
                        "config_id": res["config_id"],
                        "status": res["run_status"],
                        "candidate_config": res["candidate_config"],
                        "frozen_architecture": res["frozen_architecture"],
                        "frozen_training_recipe": res["frozen_training_recipe"],
                        "dev_evaluator_ref": ctx["evaluators"]["dev_evaluator_ref"],
                        "open_parallel_slots": ctx["remaining_budget"]["open_parallel_slots"],
                    })
                return 0
            if cmd == "record":
                metrics = (
                    json.loads(args.metrics_file.read_text(encoding="utf-8"))
                    if args.metrics_file is not None
                    else (load_json_or_file(args.metrics) or {})
                )
                cost = load_json_or_file(args.cost) or {}
                artifacts = load_json_or_file(args.artifacts) or {}
                ext_jobs = load_json_or_file(args.external_jobs) or []
                trial = ctrl.record(
                    args.campaign_id,
                    trial_id=args.trial,
                    status=args.status,
                    failure_kind=args.failure_kind,
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
                    "fidelity": trial.get("fidelity", "full"),
                    "decision": trial["decision"],
                    "failure_kind": trial.get("failure_kind"),
                    "reason": trial["decision_reason"],
                    "gain": trial["gain"],
                    "gain_pct": trial["gain_pct"],
                    "compute_value": trial["compute_value"],
                    "compute_ratio": trial["compute_ratio"],
                    "cost_value": trial["cost_value"],
                    "cumulative_cost": trial["cumulative_cost"],
                    "prediction_calibration": trial.get("prediction_calibration"),
                    "audit_warnings": trial.get("audit_warnings", []),
                    "incumbent_trial_id": ctx["incumbent"]["trial_id"] if ctx["incumbent"] else None,
                    "pareto_hypervolume": ctx["pareto_hypervolume"],
                    "remaining_budget": ctx["remaining_budget"],
                    "plateau_warning": ctx["search_diagnostics"]["plateau_warning"],
                    "principle_collapse_warning": ctx["search_diagnostics"]["principle_diversity"]["principle_collapse_warning"],
                    "results_tsv": str(runs_dir / ctx["campaign_id"] / "results.tsv"),
                })
                return 0 if ctx["status"] != "failed" else 1
            if cmd == "finalize":
                metrics = (
                    json.loads(args.metrics_file.read_text(encoding="utf-8"))
                    if args.metrics_file is not None
                    else (load_json_or_file(args.metrics) or {})
                )
                cost = load_json_or_file(args.cost) or {}
                artifacts = load_json_or_file(args.artifacts) or {}
                ext_jobs = load_json_or_file(args.external_jobs) or []
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
                    "report_md_path": str(runs_dir / state["campaign_id"] / "REPORT.md"),
                })
                return 0 if state["status"] == "succeeded" else 1
            if cmd == "report":
                report_path, md_text = ctrl.write_report(args.campaign_id)
                _print_json({
                    "campaign_id": ctrl.resolve_id(args.campaign_id),
                    "report_md_path": str(report_path),
                    "markdown": md_text,
                })
                return 0
            if cmd == "status":
                _print_json(ctrl.status(args.campaign_id))
                return 0
            if cmd == "events":
                _print_json(ctrl.events(args.campaign_id))
                return 0
            if cmd == "stop":
                _print_json(ctrl.stop(args.campaign_id))
                return 0
        return 2
    except (ValueError, OSError, KeyError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
