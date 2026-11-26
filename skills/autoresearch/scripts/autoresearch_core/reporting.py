from __future__ import annotations

from typing import Any

from .utils import canonical_change_signature


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
        "fidelity",
        "operator",
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
            _tsv_cell(trial.get("fidelity", "full")),
            _tsv_cell(trial.get("operator", "baseline" if trial.get("is_baseline") else "refine")),
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


def _md_cell(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return str(value).replace("|", "\\|").replace("\n", " ").strip() or "-"


def render_campaign_report_markdown(state: dict[str, Any], context: dict[str, Any]) -> str:
    plan = state["plan"]
    p_spec = plan["acceptance"]["primary_metric"]
    c_spec = plan["acceptance"]["compute_metric"]
    cost_spec = plan["budget"]["cost_metric"]
    trials = state.get("trials", [])
    diag = context["search_diagnostics"]
    inc = context.get("incumbent")
    holdout = state.get("holdout_report")

    total_attempted = len(trials)
    full_trials = [t for t in trials if t.get("fidelity", "full") == "full" and not t.get("is_baseline")]
    proxy_trials = [t for t in trials if t.get("fidelity", "full") in {"smoke", "proxy"}]
    keep_count = sum(1 for t in trials if t.get("decision") == "keep")
    discard_count = sum(1 for t in trials if t.get("decision") == "discard")
    crash_trials = [t for t in trials if t.get("decision") == "crash"]
    failure_breakdown: dict[str, int] = {}
    for ct in crash_trials:
        fk = ct.get("failure_kind") or "other"
        failure_breakdown[fk] = failure_breakdown.get(fk, 0) + 1

    lines = [
        f"# AutoResearch 实验总结报告 · `{state['campaign_id']}`",
        "",
        "## 1. 概览与当前裁决（Executive Summary）",
        "",
        f"- **研究轨道 / 模型族**：`{plan['track']}` / `{plan['model_family']}`（绑定知识库：`{plan['knowledge_entry_ref']}@{plan['knowledge']['revision']}`）",
        f"- **运行状态**：`{state['status']}`（停止原因：`{state.get('stop_reason') or '-'}`）",
        f"- **主指标**：`{p_spec['name']}`（`{p_spec['direction']}`，`min_gain={p_spec.get('min_gain')}`，`tie_tolerance={p_spec.get('tie_tolerance')}`）",
        f"- **推理算量约束**：`{c_spec['name']}`（`<= {c_spec.get('max_ratio')}x` 基线，上限 `{_md_cell(c_spec.get('max_value'))}` {c_spec.get('unit', '')}）",
    ]
    if inc:
        lines.append(
            f"- **当前胜出 Incumbent**：`{inc['trial_id']}`（`config_id={inc['config_id']}`，"
            f"`{p_spec['name']}={inc['primary_value']}`，`{c_spec['name']}={inc['compute_value']}` "
            f"[{inc['compute_ratio']}x]，复杂度 `{inc['complexity_score']}`）"
        )
    if holdout:
        verdict = "PASSED (验收通过)" if holdout.get("accepted") else f"REJECTED ({holdout.get('rejection_reason')})"
        lines.append(
            f"- **独立留出集（Holdout）盲评结论**：**{verdict}** — "
            f"`{p_spec['name']}={holdout.get('candidate_primary_value')}` "
            f"（相对基线增益 `{holdout.get('gain')} / {_md_cell(holdout.get('gain_pct'))}%`），"
            f"算量比 `{holdout.get('compute_ratio')}x`，单位成本增益效率 `{_md_cell(holdout.get('gain_per_cost'))}`"
        )

    lines.extend([
        "",
        "## 2. 预算、有效率与故障分类账本（Budget & Failure Ledger）",
        "",
        "| 统计项 | 数值 | 说明 |",
        "| --- | --- | --- |",
        f"| 总立项 Trials | `{total_attempted}` / `{plan['budget']['max_trials']}` | 含基线 `trial-000`、全保真 `{len(full_trials)}` 次、低保真筛查 `{len(proxy_trials)}` 次 |",
        f"| 提案被拒拦截次数 | `{diag.get('rejected_proposals_count', 0)}` | 提交 MCP 前被合法域、去重或反例护栏零成本拦截 |",
        f"| 全保真晋升 / 淘汰 | `{keep_count}` keep / `{discard_count}` discard | 棘轮裁决统计 |",
        f"| 异常崩溃细分 | `{len(crash_trials)}` crash (`{failure_breakdown or '-'}`) | `infra_flake` 已与模型 `oom`/`nan_divergence` 物理隔离 |",
        f"| 累计消耗成本 | `{state.get('total_cost', 0.0)} {cost_spec.get('unit', '')}` / `{_md_cell(cost_spec.get('max_total'))}` | `{cost_spec['name']}` 实测累计 |",
        f"| 2D Pareto Hypervolume | `{_md_cell(context.get('pareto_hypervolume'))}` | 增益(%) × 算量节省率二维超体积指标 |",
        "",
        "## 3. 二维增益-算量 Pareto 前沿与算量分档精英（MAP-Elites）",
        "",
        "| Trial | Config ID | 算子 | 主指标 | 相对基线增益(%) | 推理算量 | 算量比 | 复杂度 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for pf in context.get("pareto_frontier", []):
        g_txt = f"{pf['gain_pct']:+.2f}%" if pf.get("gain_pct") is not None else "0.00%"
        lines.append(
            f"| `{pf['trial_id']}` | `{pf['config_id']}` | `{pf['operator']}` | `{pf['primary_value']}` "
            f"| {g_txt} | `{pf['compute_value']}` | `{pf.get('compute_ratio')}x` | `{pf.get('complexity_score')}` |"
        )
    if not context.get("pareto_frontier"):
        lines.append("| - | - | - | - | - | - | - | - |")

    lines.extend([
        "",
        "## 4. 演化谱系轨迹（Lineage Trajectory）",
        "",
        "| Trial | 父节点 | 保真度 | 算子 | 裁决 | 主指标 | 增益(%) | 算量比 | 变更签名 | 假设摘要 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for t in trials:
        g_txt = f"{t['gain_pct']:+.2f}%" if t.get("gain_pct") is not None else "-"
        r_txt = f"{t['compute_ratio']}x" if t.get("compute_ratio") is not None else "-"
        insp = f" (+{','.join(t.get('inspiration_trial_ids') or [])})" if t.get("inspiration_trial_ids") else ""
        lines.append(
            f"| `{t['trial_id']}` | `{_md_cell(t.get('parent_trial_id'))}{insp}` | `{t.get('fidelity', 'full')}` "
            f"| `{t.get('operator', 'baseline')}` | `{_md_cell(t.get('decision') or t.get('run_status'))}` "
            f"| `{_md_cell(t.get('primary_value'))}` | {g_txt} | {r_txt} "
            f"| `{canonical_change_signature(t.get('changes') or {})}` | {_md_cell(t.get('hypothesis'))} |"
        )

    p_div = diag.get("principle_diversity") or {}
    lines.extend([
        "",
        "## 5. 搜索多样性与反作弊审计（Diversity & Sanity Audit）",
        "",
        f"- **有效探索原理数（Inverse Simpson $N_{{\\text{{eff}}}}$）**：`{p_div.get('effective_principle_count', 0.0)}`"
        f"（主导方向：`{_md_cell(p_div.get('dominant_family'))}`，占比 `{p_div.get('dominant_family_share', 0.0):.0%}`，"
        f"坍缩告警：`{p_div.get('principle_collapse_warning', False)}`）",
        f"- **尚未触碰的可变字段**：{', '.join(f'`{f}`' for f in diag.get('untouched_mutable_fields', [])) or '已全部覆盖'}",
        f"- **审计告警记录**：`{len(diag.get('audit_warnings', []))}` 条"
        + (f" — `{diag['audit_warnings']}`" if diag.get("audit_warnings") else ""),
        "",
    ])
    return "\n".join(lines)
