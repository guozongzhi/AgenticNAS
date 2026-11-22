---
name: autoresearch
description: >-
  Model-agnostic, BYO-MCP autonomous ML research workflow backed by a pure-Markdown
  architecture knowledge base and gain/compute ratchet harness. Use when the user wants
  to scaffold a new model's autoresearch pipeline ("搭建 autoresearch 流程", "新模型接入"),
  run multi-round architecture optimization focusing on gain and compute/FLOPs/MACs/latency
  with existing MCP tools ("跑几轮结构优化", "开始 autoresearch 迭代"), distill verified
  findings into the Markdown knowledge base ("沉淀经验库", "distill"), or launch a
  separate post-architecture HPO follow-up track ("收尾 HPO").
---

# AutoResearch · 通用模型自主优化技能

本技能驱动 `autoresearcher_harness`（通用控制面）与用户环境中**已搭好的 MCP 工具**（执行面）协作，完成面向任意模型的**结构优化主线（增益 + 算量双优先）**、**纯 Markdown 结构经验库沉淀**与**独立收尾 HPO**。

- **控制面入口**：在包含 `demos/autoresearcher_harness` 的仓库根目录（或设置 `PYTHONPATH=<repo>/demos`）运行 `python3 -m autoresearcher_harness`。
- **详细速查（按需读取）**：
  - 完整 CLI 与字段契约：[references/cli-reference.md](references/cli-reference.md)
  - 对接已有 MCP 工具与失败处理：[references/byo-mcp-guide.md](references/byo-mcp-guide.md)
  - 纯 Markdown 经验库与 `param_bounds` 写法：[references/kb-format.md](references/kb-format.md)

---

## 硬红线（严禁违反）

1. **禁止绕过控制面**：所有试验必须先经 `campaign baseline` 或 `campaign propose` 校验并生成冻结配置，再调用用户的 MCP 工具，最后用 `campaign record` 回填。
2. **禁止越界修改**：只允许修改 `mutable_fields` 白名单且满足 `param_bounds` 的字段；禁止直接篡改评测脚本、留出集或 Harness 状态数据库。
3. **严格分轨（NAS 主线 vs HPO 收尾）**：`track=architecture` 阶段冻结训练配方，严禁混搜学习率/epochs 等超参；仅在架构锁定并完成 Holdout 验收后，才另起独立 `track=hpo` 收尾 Campaign。
4. **严格隔离留出集**：开发迭代期间严禁调用 `holdout_evaluator_ref`；仅在探索结束锁定最终 `incumbent` 后执行唯一一次 Holdout 评测，并核对 `model_ref` 一致。
5. **禁止自动覆盖已发布经验**：Agent 只能调用 `kb distill` 生成隔离草案（`drafts/*.md`），**严禁未经用户明确确认执行 `kb publish`**。

---

## 路由 A：为新模型搭建 AutoResearch 流程（Scaffold）

当用户说“给 XX 模型搭一套 autoresearch 流程 / 接入新模型”时执行：

1. 向用户确认（若未提供）：
   - `workspace` 目录路径、`model_family`、`kb_id`
   - 主指标 `metric` 及方向（`maximize` 或 `minimize`）、单轮最小有效增益 `min_gain`、Holdout 验收目标 `holdout_target`
   - 推理/模型算量指标 `compute`（如 `flops_m / macs_m / latency_ms`）与红线倍率 `max_compute_ratio`
   - 搜索/训练成本指标 `cost`（如 `gpu_seconds / gpu_hours`）与总预算 `max_cost`
   - 环境中已搭好的仿真/训练/评测 MCP 工具名
2. 运行脚手架生成专属工作区（无需改任何 Harness 代码）：
   ```bash
   PYTHONPATH=demos python3 -m autoresearcher_harness init \
     --workspace <workspace> \
     --model-family <model_family> \
     --kb-id <kb_id> \
     --metric <metric> --direction <maximize|minimize> --min-gain <min_gain> \
     --holdout-target <target> \
     --compute <compute_metric> --max-compute-ratio <ratio> \
     --cost <cost_metric> --max-cost <max_cost> \
     --stages <training,evaluation>
   ```
3. 协助用户完善生成目录中的三处配置：
   - `<workspace>/campaign.json`：`base_config`（支持任意嵌套 JSON）、`mutable_fields`（支持 dot-path）、`guardrails`；
   - `<workspace>/kb/entries/<kb_id>/CURRENT.md`：填入 `scope.param_bounds` 与已知初始先验/反例；
   - `<workspace>/mcp_tools.md`：登记当前环境实际的 MCP 工具名与输入/输出字段映射。

---

## 路由 B：执行多轮自主研究闭环（BYO-MCP Ratchet）

当用户说“按 autoresearch 流程开始优化 / 跑 N 轮结构搜索”时执行。以下简写 `AR="PYTHONPATH=demos python3 -m autoresearcher_harness --output <ws>/outputs --kb-dir <ws>/kb"`：

1. **阅读工作区协议与结构经验库**
   - 读取 `<ws>/mcp_tools.md` 与 `<ws>/program.md`。
   - 检索历史结构先验与反例，避免重复踩坑：
     ```bash
     $AR kb search --model-family <model_family> --track architecture
     $AR kb show <kb_id>
     ```
2. **创建 Campaign 并建立基线（Baseline-first）**
   - 若尚未创建 Campaign：
     ```bash
     $AR campaign create --plan <ws>/campaign.json --kb <kb_id>
     $AR campaign baseline latest
     ```
   - 使用用户已搭好的 MCP 工具对 `trial-000` 的 `base_config` 执行基线训练与 **Dev** 评测，然后回填：
     ```bash
     $AR campaign record latest --status succeeded \
       --metrics '{"<primary>": <val>, "<compute>": <val>}' \
       --cost '{"<cost>": <val>}' \
       --artifacts '{"model_ref": "<uri>"}'
     ```
3. **多轮棘轮循环（直到目标达成、收敛或预算耗尽）**
   每轮严格执行 4 步：
   - **看上下文**：`$AR campaign context latest`（重点检查 `incumbent`、`param_bounds`、`compute_limits`、`remaining_budget` 与 `results.tsv`）。
   - **提单一清晰假设**：优先基于经验库高性价比模式（增益上升且算量持平/下降）或针对当前 `incumbent` 压低算量；调用：
     ```bash
     $AR campaign propose latest \
       --hypothesis "<简洁假设，说明预期增益与算量影响>" \
       --changes '{"<dot.path>": <value>}'
     ```
   - **调用户已有 MCP 执行**：把返回的 `candidate_config` 与冻结配方送入用户 MCP（详见 [references/byo-mcp-guide.md](references/byo-mcp-guide.md)）。
   - **回填裁决**：
     - 成功：`$AR campaign record latest --status succeeded --metrics '{...}' --cost '{...}' --artifacts '{"model_ref": "..."}'`
     - OOM / 失败 / 超时：先通过 MCP 取消远端任务，再执行 `$AR campaign record latest --status crash --cost '{...}' --note "<原因>"`（隔离单轮失败，继续下一轮）。
   - 观察返回结果中的 `decision`（`keep / discard / crash`）、`gain`、`compute_ratio` 和 `remaining_budget`，再构思下一轮假设。
4. **锁定最终 Incumbent 跑唯一一次独立 Holdout 盲评**
   - 读取 `context.incumbent.model_ref`，直接调用用户的 Holdout 评测 MCP（**绝不重新训练**），回填验收：
     ```bash
     $AR campaign finalize latest \
       --metrics '{"<primary>": <holdout_val>, "<compute>": <val>}' \
       --cost '{"<cost>": <eval_cost>}' \
       --artifacts '{"model_ref": "<incumbent_model_ref>"}'
     ```

---

## 路由 C：经验沉淀回写与收尾 HPO

1. **蒸馏结构经验草案**：
   ```bash
   $AR kb distill latest
   $AR kb drafts <kb_id>
   ```
   向用户汇报本轮 `results.tsv` 摘要、Holdout 结论、拟新增/合并的 `patterns` 与 `anti_patterns`。**仅在用户明确批准后**再执行：
   ```bash
   $AR kb publish <kb_id> --reviewer <user_name>
   ```
2. **启动独立收尾 HPO（可选）**：
   - 当结构已锁定并通过 Holdout 验收、用户希望继续调训练超参时，使用 `init --track hpo ...` 新建独立 HPO 工作区，冻结胜出结构，仅开放学习率/weight_decay/schedule/epochs 等字段，沿用同一套 `baseline → propose → record → finalize` 闭环。
