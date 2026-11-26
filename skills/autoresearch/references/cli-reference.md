# AutoResearch CLI 全命令与契约速查

唯一控制面脚本（零第三方依赖，仅需 Python 3.10+ 标准库）：

```bash
AR="python3 <skill_dir>/scripts/autoresearch.py"
```

- 传入 `--workspace <ws>` 后，引擎自动定位 `<ws>/campaign.json`、`<ws>/knowledge_base/` 与 `<ws>/runs/`；
- 未传 `--workspace` 时，运行 `$AR knowledge-base list / search` 直接检索技能内置预置知识库（`assets/knowledge_base/`）。

---

## 1. 工作区脚手架、安全定制与体检

### 1.1 初始化工作区（`init`）

```bash
$AR init --workspace ./csi_autoresearch --preset cnn_csi \
  --model-family cnn_csi_feedback --entry-id CSI-ARCH-001 \
  --metric nmse_db --direction minimize --min-gain 0.3 \
  --tie-tolerance 0.05 --holdout-target -18.0 \
  --compute macs_m --compute-unit MMACs --max-compute-ratio 1.10 \
  --cost gpu_hours --cost-unit h --max-cost 4.0 \
  --max-trials 8 --max-parallel 2
```

- **内置 `--preset`**：`generic_arch`、`conv1d_transformer`、`edge_vit`、`cnn_csi`、`hpo_recipe`。
- **`--max-trials` 口径**：包含 `trial-000` 基线（`8` = `1 次基线 + 7 次候选`）。
- **`--max-parallel`**：单轮允许同时处于 `awaiting_result` 的并发试验数（默认 `1`；多 GPU MCP 集群可设 `2~8`）。

### 1.2 安全定制 `v1` 种子与 NAS→HPO 交接（`configure`）

```bash
$AR configure --workspace ./csi_autoresearch \
  --base-config '{"encoder": {"num_blocks": 4, "channels": 64, "use_se": false}}' \
  --base-recipe '{"epochs": 30, "lr": 0.001, "weight_decay": 0.01, "seed": 42}' \
  --mutable-fields 'encoder.num_blocks,encoder.channels,encoder.use_se' \
  --param-bounds '{
    "encoder.num_blocks": {"type": "int", "min": 2, "max": 8},
    "encoder.channels": {"type": "int", "enum": [32, 48, 64, 96, 128]},
    "encoder.use_se": {"type": "bool"}
  }' \
  --forbidden-ops 'nn.Linear' \
  --guardrails '{"max_metrics": {"latency_ms": 2.5}}' \
  --tie-tolerance 0.05 --max-parallel 2
```

- **结构验收后交接收尾 HPO**：`$AR configure --workspace <hpo_ws> --from-holdout <arch_ws> ...`，自动把胜出 `incumbent_config` 冻结为 `base_architecture` 并继承 `baseline_model_ref`。

### 1.3 环境与工作区体检（`doctor`）

```bash
$AR doctor --workspace ./csi_autoresearch
```

---

## 2. 纯 Markdown 经验知识库命令（`knowledge-base`）

| 子命令 | 说明 |
| --- | --- |
| `knowledge-base list [--track architecture\|hpo] [--status published\|draft]` | 列出条目及模式/反例/实证/草案计数 |
| `knowledge-base search [--query ...] [--model-family ...] [--track ...] [--field ...] [--direction gain_up_compute_down] [--max-compute-ratio 1.02] [--min-gain-pct 2.0] [--failure-type compute_budget_exceeded]` | 多维检索经验模式与反例 |
| `knowledge-base show <entry_id> [--revision v1]` | 查看当前生效条目或指定历史不可变修订 |
| `knowledge-base drafts [entry_id]` | 查看 `drafts/*.md` 中隔离的待审草案 |
| `knowledge-base distill [campaign_id\|latest] [--entry-id ...]` | 从全保真试验轨迹提炼有效模式、失效反例及旧模式衰减观测，生成待审草案（自动剔除 `infra_flake` 与低保真试验） |
| `knowledge-base publish <entry_id> [--revision ...] [--reviewer <name>]` | 人工审批后按 `change_signature` 加权合并，生成不可变修订 `vN.md` 并追加 `EVIDENCE.md` |
| `knowledge-base prune <entry_id> [--min-win-rate 0.34] [--min-observations 2] [--apply] [--reviewer <name>]` | 预览或淘汰低胜率失效模式（MLEvolver Skill Deletion），默认保留 `verified_holdout` 与全部 `anti_patterns` |
| `knowledge-base import-presets [--preset ...] [--overwrite]` | 将内置预置条目导入目标 `knowledge_base/` |
| `knowledge-base reindex` | 从 `entries/` 全量重建 `INDEX.md` |

---

## 3. 多维演化棘轮命令（`campaign`）

| 子命令 | 说明 |
| --- | --- |
| `campaign create [--plan <json>] [--knowledge-entry <entry_id>] [--knowledge-revision v1]` | 冻结经验知识库快照创建 Campaign |
| `campaign baseline [id\|latest]` | 开启 `trial-000` 基线工单 |
| `campaign context [id\|latest] [--recent-window 6]` | 输出 Context Folding 上下文（`folded_history` + `recent_trials`）、`incumbent`、`pareto_frontier`、`compute_elites`、`pareto_hypervolume` 与 `search_diagnostics` |
| `campaign inspect [id\|latest] --trial <trial-XXX>` | 按需无损展开任意历史试验的完整记录、`diff_vs_baseline` 与 `diff_vs_parent` |
| `campaign propose [id\|latest] --hypothesis "..." --changes '{...}' [--parent-trial <id>] [--inspiration-trials <t1,t2>] [--operator refine\|explore\|recombine\|ablate\|shrink] [--fidelity smoke\|proxy\|full] [--expected-primary <val>] [--expected-compute-ratio <val>] [--reuse-simulation] [--dry-run]` | 校验白名单、`param_bounds`、`forbidden_ops`、同保真去重与反例拦截；支持跳板父节点、多保真筛查、并发批次与预测登记 |
| `campaign record [id\|latest] [--trial <id>] --status succeeded\|crash\|failed\|timeout\|cancelled [--failure-kind oom\|nan_divergence\|timeout\|metric_invalid\|infra_flake] --metrics '{...}' --cost '{...}' --artifacts '{...}' [--external-jobs '[...]'] [--note "..."]` | 回填 MCP 结果，执行保真分层裁决、预测误差校准与反作弊审计，实时刷新 `results.tsv` |
| `campaign finalize [id\|latest] --metrics '{...}' --cost '{...}' --artifacts '{"model_ref":"..."}'` | 对 `incumbent.model_ref` 记录唯一一次 Holdout 盲评，自动产出 `holdout_report.json` 与 `REPORT.md` |
| `campaign report [id\|latest]` | 生成/刷新结构化实验总结报告 `REPORT.md` |
| `campaign status / events / stop [id\|latest]` | 查看完整状态 JSON、事件流 `trace.jsonl`，或提前收束进入 `awaiting_holdout` |

---

## 4. 保真分层与棘轮裁决规则

- **低保真筛查（`fidelity = smoke | proxy`）**：
  - 绝不改写全保真 `incumbent`；护栏与算量合规且相对 `incumbent` 不差于 `-tie_tolerance` 判 `proxy_pass`（列入 `ready_to_promote_proxies`），否则判 `proxy_discard`；
  - 允许对 `proxy_pass` 的相同配置再次提交 `--fidelity full` 完成正式晋升验证。
- **全保真棘轮（`fidelity = full`）**：
  1. 护栏违规 → `discard`；
  2. 算量超 `max_value` 或 `max_ratio` → `discard`；
  3. 方向归一化改进 `delta >= min_gain`（`min_gain==0` 时须 `delta > tie_tolerance`）→ `keep`（`gain win`）；
  4. `abs(delta) <= tie_tolerance` 且算量更优 → `keep`（`compute win`）；
  5. `abs(delta) <= tie_tolerance` 且 `complexity_score` 更低 → `keep`（`simplicity win`）；
  6. 其余 → `discard`。
- **异常与基础设施隔离**：
  - `--failure-kind infra_flake` 计入成本账本，但允许重提相同配置，不计入 `consecutive_non_keep` 停滞，也不进入 `anti_patterns`。
