# AutoResearch CLI 全命令与契约速查

唯一控制面脚本（零第三方依赖，仅需 Python 3.10+ 标准库）：

```bash
AR="python3 <skill_dir>/scripts/autoresearch.py"
```

- 传入 `--workspace <ws>` 后，引擎自动定位 `<ws>/campaign.json`、`<ws>/knowledge_base/` 与 `<ws>/runs/`；
- 若未传 `--workspace`，运行 `$AR knowledge-base list` 或 `$AR knowledge-base search` 将直接检索技能内置的预置经验知识库（`assets/knowledge_base/`）。

---

## 1. 工作区脚手架、安全定制与体检

### 1.1 初始化工作区（`init`）

```bash
$AR init --workspace ./csi_autoresearch --preset cnn_csi \
  --model-family cnn_csi_feedback --entry-id CSI-ARCH-001 \
  --metric nmse_db --direction minimize --min-gain 0.3 \
  --tie-tolerance 0.05 --holdout-target -18.0 \
  --compute macs_m --compute-unit MMACs --max-compute-ratio 1.10 \
  --cost gpu_hours --cost-unit h --max-cost 4.0 --max-trials 6
```

- **内置 `--preset`**：`generic_arch`（默认架构轨道）、`conv1d_transformer`、`edge_vit`、`cnn_csi`、`hpo_recipe`（默认 HPO 轨道）。
- **`--max-trials` 口径**：包含 `trial-000` 基线！`--max-trials 6` = `1 次基线 + 5 次候选提案`。
- **生成目录结构**（纯文本 / JSON / TSV / Markdown，零二进制数据库）：
  ```text
  <workspace>/
    campaign.json          # 实验计划契约与冻结经验知识库快照
    program.md             # 定制化 Agent 执行指令书
    mcp_tools.md           # 环境 MCP 工具名与输入/输出字段映射表
    knowledge_base/        # 纯 Markdown 分层不可变经验知识库
    runs/                  # 各 Campaign 纯文件状态目录（state.json / results.tsv / trace.jsonl / holdout_report.json）
  ```

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
  --tie-tolerance 0.05
```

- 支持 `--spec <json_or_file>` 一次性传入复合覆盖配置。
- **结构验收后交接收尾 HPO**：在 `--track hpo` 工作区执行 `$AR configure --workspace <hpo_ws> --from-holdout <arch_ws> ...`，自动提取胜出 `incumbent_config` 写入不可变 `base_architecture` 并继承 `baseline_model_ref`。
- **历史保护**：一旦目标 `entry_id` 已发布 `v2+` 或已有实证记录，`configure` 拒绝覆盖 `v1`，强制走 `knowledge-base distill` + `knowledge-base publish`。

### 1.3 环境与工作区体检（`doctor`）

```bash
$AR doctor --workspace ./csi_autoresearch
```

检查项：Python 版本、技能内置预置知识库完整性、`<ws>/knowledge_base/` 所有条目的 `content_sha256` 完整性、`campaign.json` 字段与分轨隔离、`mutable_fields` 是否均已定义 `param_bounds`、`mcp_tools.md` 是否残留 `<your_*_mcp_tool>` 占位符，以及 `runs/latest.txt` 指向的当前活跃状态。

---

## 2. 纯 Markdown 经验知识库命令（`knowledge-base`）

| 子命令 | 说明 |
| --- | --- |
| `knowledge-base list [--track architecture\|hpo] [--status published\|draft]` | 列出经验条目与模式/反例/实证/草案统计 |
| `knowledge-base search [--query ...] [--model-family ...] [--track ...] [--field ...] [--direction gain_up_compute_down] [--max-compute-ratio 1.02] [--min-gain-pct 2.0] [--failure-type compute_budget_exceeded]` | 多维检索经验模式与反例 |
| `knowledge-base show <entry_id> [--revision v1]` | 查看当前生效条目或指定历史不可变修订 |
| `knowledge-base drafts [entry_id]` | 查看 `drafts/*.md` 中隔离的待审草案 |
| `knowledge-base distill [campaign_id\|latest] [--entry-id ...]` | 从 Campaign 轨迹自动提炼 `keep` 模式与失败反例生成待审草案 |
| `knowledge-base publish <entry_id> [--revision ...] [--reviewer <name>]` | 人工审批后按 `change_signature` 加权去重合并，生成新修订 `vN.md` 并追加 `EVIDENCE.md` |
| `knowledge-base import-presets [--preset ...] [--overwrite]` | 将技能内置预置经验条目导入目标 `knowledge_base/` 目录 |
| `knowledge-base reindex` | 从 `entries/` 源文件全量重建 `INDEX.md` |

---

## 3. 棘轮研究循环命令（`campaign`）

| 子命令 | 说明 |
| --- | --- |
| `campaign create [--plan <json>] [--knowledge-entry <entry_id>] [--knowledge-revision v1]` | 冻结经验知识库快照创建新 Campaign 并更新 `runs/latest.txt` |
| `campaign baseline [id\|latest]` | 开启 `trial-000` 基线工单（返回 `candidate_config` 与冻结项） |
| `campaign context [id\|latest]` | 输出 `incumbent`、`param_bounds`、`remaining_budget`、`search_diagnostics`（含 `untried_knowledge_priors`、已测签名、`plateau_warning`）与 `results_tsv` |
| `campaign propose [id\|latest] --hypothesis "..." --changes '{...}' [--reuse-simulation] [--dry-run] [--allow-repeat] [--force-anti-pattern]` | 硬校验白名单、`param_bounds`、`forbidden_ops`、无变化拦截、全局 `config_id` 去重与反例拦截；`--dry-run` 仅预检不落盘 |
| `campaign record [id\|latest] [--trial ...] --status succeeded\|crash\|failed\|timeout\|cancelled --metrics '{...}' --cost '{...}' --artifacts '{...}' [--external-jobs '[...]'] [--note "..."]` | 回填 MCP 实测指标与成本，执行棘轮裁决并实时刷新 `results.tsv` |
| `campaign finalize [id\|latest] --metrics '{...}' --cost '{...}' --artifacts '{"model_ref":"..."}'` | 对 `incumbent.model_ref` 记录唯一一次 Holdout 盲评并生成 `holdout_report.json` |
| `campaign status / events / stop [id\|latest]` | 查看完整状态 JSON、审计事件流 `trace.jsonl`，或提前结束探索进入 `awaiting_holdout` |

---

## 4. 棘轮裁决与状态流转规则

1. **护栏校验**：违反 `acceptance.guardrails`（`max_metrics / min_metrics`）→ `discard`。
2. **算量红线**：超出 `compute_metric.max_value` 或 `max_ratio` → `discard`。
3. **增益胜出（`gain win`）**：相对当前 `incumbent` 的方向归一化改进 `delta >= min_gain`（当 `min_gain == 0` 时要求 `delta > tie_tolerance`）→ `keep` 并晋升 `incumbent`。
4. **同增益算量胜出（`compute win`）**：`abs(delta) <= tie_tolerance` 且算量更优 → `keep`。
5. **同算量简洁胜出（`simplicity win`）**：`abs(delta) <= tie_tolerance` 且 `complexity_score`（相对 `base_config` 修改字段数）更小 → `keep`。
6. **其余** → `discard`；`crash / failed / timeout` → `crash`（成本照计，非基线轮次不中断后续探索）。
7. **自动收束保护（`awaiting_holdout`）**：当累计成本达到 `max_total` 或试验数达到 `max_trials` 时，状态自动转为 `awaiting_holdout`——此时拦截任何新训练提案，但**始终允许执行唯一一次 `campaign finalize`**，彻底避免预算耗尽锁死最终盲评。
