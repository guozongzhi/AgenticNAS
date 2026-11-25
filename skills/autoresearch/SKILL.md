---
name: autoresearch
description: >-
  Self-contained, model-agnostic, BYO-MCP autonomous ML research skill backed by a
  pure-Markdown knowledge base and a zero-dependency gain/compute ratchet CLI. Use when
  the user wants to scaffold a new model's autoresearch workspace ("搭建 autoresearch 流程",
  "新模型接入"), run multi-round architecture optimization focusing on gain and
  compute/FLOPs/MACs/latency with existing MCP tools ("跑几轮结构优化", "开始 autoresearch 迭代"),
  resume or diagnose an interrupted campaign ("继续上次搜索", "恢复 campaign", "检查工作区"),
  distill verified findings into the Markdown knowledge base ("沉淀经验知识库", "distill"),
  or launch a separate post-architecture HPO follow-up track ("收尾 HPO").
---

# AutoResearch · 自包含模型自主优化技能

本技能自带**零第三方依赖、纯文件存储**的控制面引擎 `scripts/autoresearch.py`（仅依赖 Python 3.10+ 标准库，可独立复制到任何机器或模型仓库运行），内置开箱即用的**纯 Markdown 经验知识库（Knowledge Base）**（[assets/knowledge_base/INDEX.md](assets/knowledge_base/INDEX.md)），与用户环境中**已挂载的 MCP 工具**（训练/仿真/评测执行面）协作，完成**结构优化主线（增益 + 算量双优先）**、**经验知识库沉淀**、**断点对账恢复**与**独立收尾 HPO**。

- **控制面唯一入口**：
  ```bash
  AR="python3 <path/to/this/skill>/scripts/autoresearch.py"
  ```
- **按需查阅参考手册与预置知识库**：
  - 预置纯 Markdown 经验知识库（Conv1d / 边缘视觉 ViT / CNN-CSI / 收尾 HPO）：[assets/knowledge_base/INDEX.md](assets/knowledge_base/INDEX.md)
  - 全命令参数、JSON 契约与棘轮裁决规则：[references/cli-reference.md](references/cli-reference.md)
  - BYO-MCP 字段映射、多阶段复用与异常对账：[references/byo-mcp-guide.md](references/byo-mcp-guide.md)
  - 结构搜索与收尾 HPO 假设生成与防坍缩策略：[references/hypothesis-playbook.md](references/hypothesis-playbook.md)
  - 纯 Markdown 经验知识库格式、SHA-256 完整性与去重规范：[references/knowledge-base-format.md](references/knowledge-base-format.md)

---

## 硬红线（严禁违反）

1. **禁止绕过控制面**：所有试验必须先经 `campaign baseline` 或 `campaign propose` 校验（白名单、`param_bounds`、`forbidden_ops`、配置去重与反例拦截），拿到冻结配置后再调用户 MCP，最后用 `campaign record` 回填。
2. **禁止手改已签名经验文档**：`knowledge_base/entries/<ENTRY_ID>/CURRENT.md` 与 `revisions/*.md` 带有 `content_sha256` 完整性校验；初始化阶段定制 `v1` 种子统一用 `configure` 子命令，实验沉淀统一走 `knowledge-base distill` → 用户审批 → `knowledge-base publish`。
3. **严格分轨（`architecture` 主线 vs `hpo` 收尾）**：`track=architecture` 阶段冻结 `base_training_recipe`，严禁触碰学习率/epochs 等超参；仅在架构完成 Holdout 验收后，才用独立 HPO 知识库条目（`track=hpo`）与 `configure --from-holdout <arch_ws>` 冻结胜出结构启动收尾调参。
4. **严格隔离留出集（Holdout 盲评铁律）**：开发迭代期间只准调用 `dev_evaluator_ref`；当达到 `max_trials`、`max_cost`（状态自动转为 `awaiting_holdout`）或提前收敛时，对 `incumbent.model_ref` 调用**唯一一次** `holdout_evaluator_ref`（严禁重训）并执行 `campaign finalize`。
5. **禁止自动覆盖已发布经验**：Agent 只能执行 `knowledge-base distill` 生成隔离草案（`drafts/*.md`），**未经用户明确确认严禁执行 `knowledge-base publish`**。

---

## 路由速查表

| 用户意图 | 执行路由 |
| --- | --- |
| 新模型接入 / 初始化工作区 / 配置搜索空间 | **路由 A**（`init` → `configure` → 填 `mcp_tools.md` → `doctor`） |
| 开始多轮结构优化 / 跑 N 轮棘轮探索 | **路由 B**（探活与查知识库 → Baseline → 假设棘轮 → Holdout 盲评） |
| 沉淀经验知识库 / 审批草案 / 启动结构后收尾 HPO | **路由 C**（`knowledge-base distill` 汇报审批 / `configure --from-holdout` 一键交接） |
| 中断后继续 / 远端任务对账 / 工作区体检 | **路由 D**（`doctor` + `campaign context` 对账恢复） |

---

## 路由 A：为新模型搭建工作区（Scaffold & Configure）

1. **确认核心参数**（若用户未指定则询问）：
   - `workspace` 路径、`model_family`、经验知识库条目编号 `entry_id`、可选预设 `--preset`（`conv1d_transformer | edge_vit | cnn_csi | generic_arch | hpo_recipe`）
   - 主指标 `metric`、方向（`maximize | minimize`）、最小有效增益 `min_gain`、平局容差 `tie_tolerance`、Holdout 验收目标 `holdout_target`
   - 推理/模型算量 `compute`（`flops_m / macs_m / latency_ms / params_m`）与红线倍率 `max_compute_ratio`
   - 训练/搜索成本 `cost`（`gpu_seconds / gpu_hours`）、总预算 `max_cost`、**探索轮数 $N$**（注意 `--max-trials` 含基线 `trial-000`，故传 `$((N + 1))`）
   - 当前环境已有的训练/仿真/评测 MCP 工具名
2. **初始化并安全写入模型真实配置**：
   ```bash
   $AR init --workspace <ws> --preset <preset> \
     --model-family <model_family> --entry-id <entry_id> \
     --metric <metric> --direction <maximize|minimize> --min-gain <min_gain> \
     --tie-tolerance <tol> --holdout-target <target> \
     --compute <compute_metric> --max-compute-ratio <ratio> \
     --cost <cost_metric> --max-cost <max_cost> --max-trials <N_plus_1>

   $AR configure --workspace <ws> \
     --base-config '<真实嵌套结构 JSON 或文件路径>' \
     --base-recipe '<冻结训练配方 JSON 或文件路径>' \
     --mutable-fields '<dot.path 逗号列表或 JSON 数组>' \
     --param-bounds '<字段类型与范围 JSON>' \
     --guardrails '<可选护栏 JSON>'
   ```
3. **绑定 MCP 并自检**：将 `<ws>/mcp_tools.md` 中的 `<your_*_mcp_tool>` 替换为真实工具名，运行 `$AR doctor --workspace <ws>` 确认 `ok: true`。

---

## 路由 B：执行多轮自主研究闭环（BYO-MCP Ratchet）

以下简写 `WS="$AR --workspace <ws>"`。

1. **启动前探活与检索经验知识库**
   - 先运行 `$WS doctor`：若 `latest_campaign` 处于 `running` 或 `awaiting_holdout`，**严禁重复 `campaign create`**，直接转入**路由 D** 续跑！
   - 阅读 `<ws>/mcp_tools.md` 与 `<ws>/program.md`，检索工作区与预置知识库中的先验模式和反例：
     ```bash
     $WS knowledge-base search --model-family <model_family> --track architecture
     $WS knowledge-base show <entry_id>
     ```
2. **建立基线（Baseline-first）**
   ```bash
   $WS campaign create
   $WS campaign baseline latest
   ```
   调用用户的训练 + **Dev** 评测 MCP 执行 `trial-000` 的 `candidate_config` 与 `frozen_training_recipe`，回填实测值：
   ```bash
   $WS campaign record latest --status succeeded \
     --metrics '{"<primary>": <val>, "<compute>": <val>}' \
     --cost '{"<cost>": <val>}' \
     --artifacts '{"model_ref": "<base_model_uri>"}' \
     --external-jobs '[{"stage": "training", "tool": "<tool>", "job_id": "<id>"}]'
   ```
3. **多轮假设棘轮循环**（重复直到状态转为 `awaiting_holdout` 或提前收敛）
   - **看诊断上下文**：`$WS campaign context latest`，重点阅读 `incumbent`、`remaining_budget`、`search_diagnostics`（`untried_knowledge_priors`、`evaluated_signatures`、`known_anti_patterns`、`plateau_warning`）与 `results_tsv`。
   - **提可归因单一假设**（策略详见 [references/hypothesis-playbook.md](references/hypothesis-playbook.md)）：
     - 每轮相对 `incumbent` 优先只改 **1 个字段**（或 1 条未测先验模式），保持低 `complexity_score`；
     - 可先加 `--dry-run` 预检合法域、去重哈希 `config_id` 与反例拦截，再正式提交：
       ```bash
       $WS campaign propose latest \
         --hypothesis "<说明具体改动、预期增益方向与算量影响>" \
         --changes '{"<dot.path>": <value>}'
       ```
     - 若 `plateau_warning == true`（连续 ≥3 轮未 `keep`）或 Dev 已稳超 `holdout_target` 且算量合规，调用 `$WS campaign stop latest` 提前转入 `awaiting_holdout`，节省算力。
   - **调用户 MCP 执行并回填裁决**：
     - 成功：`$WS campaign record latest --status succeeded --metrics '{...}' --cost '{...}' --artifacts '{"model_ref": "..."}' --external-jobs '[...]'`
     - OOM / NaN / 超时：先通过平台 MCP 取消远端任务，再执行 `$WS campaign record latest --status crash --cost '{...}' --note "<根因>"`（隔离单轮故障并继续探索）。
4. **唯一一次独立 Holdout 盲评**
   - 当探索收束（`campaign_status == "awaiting_holdout"` 或主动结束）时，读取 `context.incumbent.model_ref`，对**该已有模型权重**调用一次 `holdout_evaluator_ref` 评测 MCP（严禁重训；推荐同步测出基线在 Holdout 上的 `baseline_<primary>` 与 `baseline_<compute>`）：
     ```bash
     $WS campaign finalize latest \
       --metrics '{"<primary>": <holdout_val>, "<compute>": <val>, "baseline_<primary>": <base_holdout_val>}' \
       --cost '{"<cost>": <eval_cost>}' \
       --artifacts '{"model_ref": "<incumbent_model_ref>"}'
     ```

---

## 路由 C：经验知识库沉淀与独立收尾 HPO

1. **蒸馏草案并提请人工审批**：
   ```bash
   $WS knowledge-base distill latest
   $WS knowledge-base drafts <entry_id>
   ```
   向用户展示 `results.tsv` 胜出链、Holdout 验收结论（含 `gain_per_cost`）以及拟新增/加权合并的 `patterns` 与 `anti_patterns`。**仅在用户明确同意后**执行：
   ```bash
   $WS knowledge-base publish <entry_id> --reviewer <user_name>
   ```
2. **启动独立收尾 HPO（可选）**：
   - 使用全新 HPO 经验知识库条目编号（`track=hpo`）初始化独立工作区，并用 `--from-holdout <arch_ws>` 自动将胜出 `incumbent_config` 冻结为不可变 `base_architecture`：
     ```bash
     $AR init --workspace <hpo_ws> --preset hpo_recipe \
       --model-family <model_family> --entry-id <MODEL>-HPO-001 --track hpo \
       --metric <metric> --direction <maximize|minimize> --min-gain <min_gain> \
       --compute <compute_metric> --max-compute-ratio 1.02 \
       --cost <cost_metric> --max-cost <hpo_budget> --max-trials <M_plus_1>

     $AR configure --workspace <hpo_ws> --from-holdout <arch_ws> \
       --base-config '<初始训练配方 JSON>' \
       --mutable-fields 'lr,weight_decay,warmup_ratio,dropout,epochs' \
       --param-bounds '<超参合法域 JSON>'
     ```
   - 随后在 `<hpo_ws>` 中执行**路由 B** 的相同闭环。

---

## 路由 D：断点恢复与远端对账（Resume & Reconcile）

运行 `$WS doctor` 与 `$WS campaign context latest` 检查当前状态：
- **`active_trial != null`（`run_status == "awaiting_result"`）**：说明上一轮提案已生成但尚未回填。先调用用户的平台查询 MCP 对账远端任务——若已完成则直接 `campaign record latest`；若仍在运行则等待完成后回填；仅在确认远端未收到任务时才按 `active_trial.candidate_config` 补提 MCP（**切勿重复执行 `campaign propose`**）。
- **`status == "running"` 且 `active_trial == null`**：直接从**路由 B Step 3** 继续下一轮提案。
- **`status == "awaiting_holdout"`**：探索预算已收束，直接执行**路由 B Step 4**（`campaign finalize latest`）。
