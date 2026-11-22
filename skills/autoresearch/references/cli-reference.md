# AutoResearcher Harness CLI 速查

所有命令默认从包含 `demos/autoresearcher_harness` 的仓库根目录运行，通用全局参数：

```bash
PYTHONPATH=demos python3 -m autoresearcher_harness \
  --output <workspace>/outputs \
  --kb-dir <workspace>/kb \
  <subcommand> ...
```

## 1. 工程师自助脚手架（`init`）

```bash
PYTHONPATH=demos python3 -m autoresearcher_harness init \
  --workspace ./my_model_autoresearch \
  --model-family cnn_csi_feedback \
  --kb-id CSI-ARCH-001 \
  --metric nmse_db --direction minimize --min-gain 0.3 --holdout-target -18.0 \
  --compute macs_m --compute-unit MMACs --max-compute-ratio 1.10 \
  --cost gpu_hours --cost-unit h --max-cost 4.0 \
  --max-trials 10 --track architecture --stages training,evaluation
```

生成文件：`campaign.json`、`program.md`、`mcp_tools.md`、`kb/INDEX.md`、`kb/entries/<kb_id>/{CURRENT.md, revisions/v1.md, EVIDENCE.md}`。

## 2. 纯 Markdown 结构经验库（`kb`）

| 命令 | 作用 |
| --- | --- |
| `kb list [--track architecture\|hpo\|data_recipe] [--status published\|draft]` | 列出经验条目与统计 |
| `kb search [--model-family ...] [--track ...] [--field ...] [--direction gain_up_compute_down] [--max-flops-ratio 1.0] [--min-gain-pp 5] [--failure-type compute_budget_exceeded]` | 多维检索匹配的条目、模式与反例 |
| `kb show <kb_id> [--revision v1]` | 查看完整条目或按历史修订精确回查 |
| `kb drafts [kb_id]` | 列出隔离在 `drafts/*.md` 中的待审草案 |
| `kb distill [campaign_id\|latest] [--kb-id ...]` | 从已完成 Campaign 蒸馏生成待审草案（不改写已发布文档） |
| `kb publish <kb_id> [--revision ...] [--reviewer <name>]` | 人工审核后去重聚合发布不可变 `revisions/vN.md` 并追加 `EVIDENCE.md` |
| `kb reindex` | 从 `entries/` 下的 Markdown 源文件重建 `INDEX.md` |

## 3. 多轮棘轮研究循环（`campaign`）

| 命令 | 模式 | 作用 |
| --- | --- | --- |
| `campaign create --plan <json> [--kb <kb_id>] [--kb-revision v1]` | 通用 | 冻结经验快照与计划创建 Campaign |
| `campaign baseline [id\|latest]` | 通用 | `external_mcp` 返回 `trial-000` 基线配置工单；`managed` 自动跑完基线 |
| `campaign context [id\|latest]` | 通用 | 输出 `incumbent`、`mutable_fields`、`param_bounds`、`compute_limits`、`remaining_budget` 与 `results.tsv` |
| `campaign propose [id\|latest] --hypothesis "..." --changes '{...}' [--reuse-simulation] [--run]` | 通用 | 校验白名单与 `param_bounds`，返回冻结后的完整 `candidate_config`（`managed` 可加 `--run` 自动推进） |
| `campaign record [id\|latest] [--trial trial-001] --status succeeded\|crash\|failed\|timeout\|cancelled --metrics '{...}' --cost '{...}' --artifacts '{...}' [--external-jobs '[...]'] [--note "..."]` | BYO-MCP | 回填用户 MCP 执行结果，自动计算方向归一化增益、算量倍率与 `keep/discard/crash` 裁决并刷新 `results.tsv` |
| `campaign finalize [id\|latest] --metrics '{...}' --cost '{...}' --artifacts '{"model_ref":"..."}'` | BYO-MCP / 托管 | 锁定 `incumbent` 记录唯一一次独立 Holdout 盲评并产出 `holdout_report.json` |
| `campaign status / events / stop / export [id\|latest]` | 通用 | 查看状态、轨迹、请求停止、导出 `campaign.json / results.tsv / holdout_report.json / trace.jsonl` |
| `campaign demo [--plan ...]` | 托管 | 离线演示完整多轮棘轮流程 |

## 4. 棘轮裁决规则

1. **护栏检查**：违反 `acceptance.guardrails`（`max_metrics / min_metrics`）→ `discard`。
2. **推理算量红线**：超出 `compute_metric.max_value` 或 `max_ratio` → `discard`。
3. **增益优先**：方向归一化增益 `delta >= primary_metric.min_gain` → `keep` 并推进 `incumbent`。
4. **同增益算量优先（`compute win`）**：`abs(delta) <= tie_tolerance` 且推理算量更优 → `keep`。
5. **同算量简洁优先（`simplicity win`）**：`abs(delta) <= tie_tolerance` 且相对基线的配置变更字段更少 → `keep`。
6. **其余** → `discard`；训练失败/超时 → `crash`（计入总成本，不中断后续探索）。
