---
name: autoresearch
description: >-
  Self-contained, model-agnostic, BYO-MCP autonomous ML research skill backed by a
  pure-Markdown knowledge base and a zero-dependency evolutionary gain/compute ratchet CLI.
  Use when the user wants to scaffold a new model's autoresearch workspace ("搭建 autoresearch 流程",
  "新模型接入"), run multi-round architecture optimization focusing on gain and
  compute/FLOPs/MACs/latency with existing MCP tools ("跑几轮结构优化", "开始 autoresearch 迭代"),
  resume or diagnose an interrupted campaign ("继续上次搜索", "恢复 campaign", "检查工作区"),
  generate an experiment report ("生成实验报告"), distill/prune findings in the Markdown
  knowledge base ("沉淀经验知识库", "修剪知识库"), or launch a separate post-architecture
  HPO follow-up track ("收尾 HPO").
---

# AutoResearch · 自包含模型自主优化技能

本技能自带**零第三方依赖、纯文件存储**的控制面引擎 `scripts/autoresearch.py`（仅需 Python 3.10+ 标准库，可独立复制到任何机器或外部模型仓库运行），内置**纯 Markdown 经验知识库**（[assets/knowledge_base/INDEX.md](assets/knowledge_base/INDEX.md)），融合业界先进自主研究机制（**跳板谱系与 2D Pareto/MAP-Elites 精英池、Context Folding 上下文折叠、多保真预筛、多卡同步并行批次、原理坍缩检测、Predict-Then-Verify 校准与基础设施故障隔离**），与用户环境中**已挂载的 MCP 工具**协作完成**结构优化主线（增益 + 算量双优先）**与**独立收尾 HPO**。

- **控制面唯一入口**：
  ```bash
  AR="python3 <path/to/this/skill>/scripts/autoresearch.py"
  ```
- **按需查阅参考手册与预置知识库**：
  - 预置纯 Markdown 经验知识库（Conv1d / 边缘视觉 ViT / CNN-CSI / 收尾 HPO）：[assets/knowledge_base/INDEX.md](assets/knowledge_base/INDEX.md)
  - 业界 AutoResearch 核心机制映射与组合范式：[references/industry-patterns.md](references/industry-patterns.md)
  - 全命令参数、JSON 契约与棘轮裁决规则：[references/cli-reference.md](references/cli-reference.md)
  - BYO-MCP 字段映射、并行/多保真与故障分类对账：[references/byo-mcp-guide.md](references/byo-mcp-guide.md)
  - 结构搜索与收尾 HPO 五算子假设与防坍缩手册：[references/hypothesis-playbook.md](references/hypothesis-playbook.md)
  - 纯 Markdown 经验知识库格式、SHA-256 完整性与修剪规范：[references/knowledge-base-format.md](references/knowledge-base-format.md)

---

## 硬红线（严禁违反）

1. **禁止绕过控制面**：所有试验必须先经 `campaign baseline` 或 `campaign propose` 校验（白名单、`param_bounds`、`forbidden_ops`、同保真去重与反例拦截），拿到冻结配置后再调用户 MCP，最后用 `campaign record` 回填。
2. **禁止手改已签名经验文档**：`knowledge_base/entries/<ENTRY_ID>/CURRENT.md` 与 `revisions/*.md` 带 `content_sha256` 完整性校验；定制初始 `v1` 种子统一用 `configure`，迭代沉淀与修剪统一走 `knowledge-base distill / prune` 并由用户确认发布。
3. **严格分轨（`architecture` 主线 vs `hpo` 收尾）**：`track=architecture` 阶段冻结 `base_training_recipe`，严禁混搜学习率/epochs 等超参；仅在架构完成 Holdout 验收后，才用独立 HPO 条目（`track=hpo`）与 `configure --from-holdout <arch_ws>` 冻结胜出结构启动收尾调参。
4. **严格隔离低保真、基础设施抖动与留出集**：
   - `smoke / proxy` 低保真筛查绝不覆盖全保真 `incumbent`；集群抖动必须标 `--failure-kind infra_flake` 以免污染反例库；
   - 开发期只准调 `dev_evaluator_ref`；仅在进入 `awaiting_holdout` 或主动收束且无在途试验后，对 `incumbent.model_ref` 调用**唯一一次** `holdout_evaluator_ref`（严禁重训）并执行 `campaign finalize`。
5. **禁止自动覆盖已发布经验**：Agent 只能执行 `knowledge-base distill`（或预览 `knowledge-base prune`），**未经用户明确确认严禁执行 `knowledge-base publish` 或 `prune --apply`**。

---

## 路由速查表

| 用户意图 | 执行路由 |
| --- | --- |
| 新模型接入 / 初始化工作区 / 配置搜索空间与并发度 | **路由 A**（`init` → `configure` → 填 `mcp_tools.md` → `doctor`） |
| 开始多轮结构优化 / 多保真或并行批次探索 | **路由 B**（探活与查知识库 → Baseline → 五算子演化棘轮 → Holdout 盲评与 `report`） |
| 沉淀或修剪经验知识库 / 启动结构后收尾 HPO | **路由 C**（`distill` / `prune` 汇报审批 / `configure --from-holdout` 一键交接） |
| 中断后继续 / 远端在途任务对账 / 展开折叠历史 | **路由 D**（`doctor` + `campaign context` + `campaign inspect`） |

---

## 路由 A：为新模型搭建工作区（Scaffold & Configure）

1. **确认核心参数**（若用户未指定则询问）：
   - `workspace` 路径、`model_family`、经验条目编号 `entry_id`、可选预设 `--preset`（`conv1d_transformer | edge_vit | cnn_csi | generic_arch | hpo_recipe`）
   - 主指标 `metric`、方向（`maximize | minimize`）、最小有效增益 `min_gain`、平局容差 `tie_tolerance`、Holdout 验收目标 `holdout_target`
   - 推理/模型算量 `compute`（`flops_m / macs_m / latency_ms / params_m`）与红线倍率 `max_compute_ratio`
   - 成本 `cost`（`gpu_seconds / gpu_hours`）、总预算 `max_cost`、**探索轮数 $N$**（`--max-trials $((N + 1))`）与**并发槽位 `--max-parallel`**（单卡默认 `1`，多卡 MCP 集群可设 `2~4`）
2. **初始化并原子化写入真实配置**：
   ```bash
   $AR init --workspace <ws> --preset <preset> \
     --model-family <model_family> --entry-id <entry_id> \
     --metric <metric> --direction <maximize|minimize> --min-gain <min_gain> \
     --tie-tolerance <tol> --holdout-target <target> \
     --compute <compute_metric> --max-compute-ratio <ratio> \
     --cost <cost_metric> --max-cost <max_cost> \
     --max-trials <N_plus_1> --max-parallel <K>

   $AR configure --workspace <ws> \
     --base-config '<真实嵌套结构 JSON 或文件路径>' \
     --base-recipe '<冻结训练配方 JSON 或文件路径>' \
     --mutable-fields '<dot.path 逗号列表或 JSON 数组>' \
     --param-bounds '<字段类型与范围 JSON>' \
     --guardrails '<可选护栏 JSON>'
   ```
3. **绑定 MCP 并自检**：替换 `<ws>/mcp_tools.md` 中的 `<your_*_mcp_tool>` 占位符，运行 `$AR doctor --workspace <ws>` 确认 `ok: true`。

---

## 路由 B：执行多轮演化棘轮闭环（BYO-MCP Evolutionary Ratchet）

以下简写 `WS="$AR --workspace <ws>"`。

1. **启动前探活与检索经验知识库**
   - 运行 `$WS doctor`：若 `latest_campaign` 处于 `running` 或 `awaiting_holdout`，**严禁重复 `campaign create`**，转入**路由 D**！
   - 阅读 `<ws>/mcp_tools.md` 与 `<ws>/program.md`，检索匹配模式与反例：
     ```bash
     $WS knowledge-base search --model-family <model_family> --track architecture
     $WS knowledge-base show <entry_id>
     ```
2. **建立基线（Baseline-first）**
   ```bash
   $WS campaign create
   $WS campaign baseline latest
   ```
   调训练 + **Dev** 评测 MCP 跑完 `trial-000` 后回填：
   ```bash
   $WS campaign record latest --trial trial-000 --status succeeded \
     --metrics '{"<primary>": <val>, "<compute>": <val>}' \
     --cost '{"<cost>": <val>}' \
     --artifacts '{"model_ref": "<base_model_uri>"}'
   ```
3. **多轮演化探索循环**（重复至 `awaiting_holdout` 或收敛早停）
   - **读折叠上下文与诊断**：`$WS campaign context latest`（若需细看某条早期折叠试验，调用 `$WS campaign inspect latest --trial <trial-XXX>`）。重点检查：
     - `incumbent`、`pareto_frontier` 与 `compute_elites`（轻量化/均衡/扩展三档跳板精英）；
     - `search_diagnostics`：`untried_knowledge_priors`、`ready_to_promote_proxies`、`untouched_mutable_fields`、`principle_collapse_warning`、`plateau_warning`。
   - **按诊断选择演化算子提交提案**（详见 [references/hypothesis-playbook.md](references/hypothesis-playbook.md)）：
     - `refine`（围绕 `incumbent` 单轴微调）、`explore`（当 `principle_collapse_warning=true` 时切向 `untouched_mutable_fields` 或跳回 `--parent-trial` 精英跳板）、`recombine`（结合 `--inspiration-trials` 融合两条互补有效分支）、`ablate`（剥离多字段胜出者中的冗余修改）、`shrink`（在 `tie_tolerance` 内压算量赢 `compute win`）；
     - 昂贵训练可先用 `--fidelity proxy` 快速预筛，通过后再对同一变更提 `--fidelity full` 正式晋升；推荐填写 `--expected-primary` 与 `--expected-compute-ratio` 做预测自校准：
       ```bash
       $WS campaign propose latest \
         --operator <refine|explore|recombine|ablate|shrink> \
         --fidelity <proxy|full> \
         --parent-trial <optional_stepping_stone_id> \
         --expected-primary <pred_val> --expected-compute-ratio <pred_ratio> \
         --hypothesis "<说明改动、预期增益与算量影响>" \
         --changes '{"<dot.path>": <value>}'
       ```
   - **调用户 MCP 执行并按故障分类回填**：
     - 成功：`$WS campaign record latest --trial <id> --status succeeded --metrics '{...}' --cost '{...}' --artifacts '{"model_ref": "..."}'`
     - 失败：先用 MCP 取消远端失控任务，再执行 `$WS campaign record latest --trial <id> --status crash --failure-kind <oom|nan_divergence|timeout|infra_flake> --cost '{...}' --note "<根因>"`。
4. **唯一一次独立 Holdout 盲评与实验晨报生成**
   - 当全部在途试验已回填且探索收束时，对 `context.incumbent.model_ref` 调用唯一一次 `holdout_evaluator_ref` 评测 MCP（严禁重训）：
     ```bash
     $WS campaign finalize latest \
       --metrics '{"<primary>": <holdout_val>, "<compute>": <val>, "baseline_<primary>": <base_holdout_val>}' \
       --cost '{"<cost>": <eval_cost>}' \
       --artifacts '{"model_ref": "<incumbent_model_ref>"}'
     $WS campaign report latest
     ```
     （自动在 `<ws>/runs/<campaign_id>/REPORT.md` 生成含预算账本、2D Pareto 超体积、谱系树与多样性审计的完整报告。）

---

## 路由 C：经验知识库蒸馏、修剪与独立收尾 HPO

1. **蒸馏新经验与修剪失效旧规则**：
   ```bash
   $WS knowledge-base distill latest
   $WS knowledge-base drafts <entry_id>
   $WS knowledge-base prune <entry_id>   # 预览低胜率陈旧经验（不改写文件）
   ```
   向用户汇报 `REPORT.md` 核心结论与待审草案，**仅在用户明确批准后**执行 `knowledge-base publish <entry_id> --reviewer <name>`（或 `prune <entry_id> --apply --reviewer <name>`）。
2. **启动独立收尾 HPO（可选）**：
   - 用全新 `track=hpo` 条目初始化工作区，并通过 `--from-holdout <arch_ws>` 一键将已验收胜出结构锁定进不可变 `base_architecture`：
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

---

## 路由 D：断点恢复与在途对账（Resume & Reconcile）

运行 `$WS doctor` 与 `$WS campaign context latest`：
- **`active_trials` 非空**：逐个对在途 `trial_id` 调用平台查询 MCP 对账——已跑完则执行 `campaign record latest --trial <id> ...`；确认远端未入队才按 `candidate_config` 补提（切勿重复 `propose`）。
- **`status == "running"` 且 `active_trials` 为空**：直接继续**路由 B Step 3**。
- **`status == "awaiting_holdout"`**：直接执行**路由 B Step 4**（`campaign finalize latest`）。
