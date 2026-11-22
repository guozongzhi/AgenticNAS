# BYO-MCP 对接指南（将已有 MCP 接入 AutoResearch 闭环）

当用户环境中已经配置好仿真、训练、评测 MCP（例如挂在 Claude Code / Codex / OpenCode 的 MCP Server 列表中）时，**不要在 Python 中重新封装 MCP SDK**，而是由 Agent 直接调度已有 MCP，并用 Harness CLI 充当控制面。

## 1. 启动前核对三件事

1. **工具清单**：阅读 `<workspace>/mcp_tools.md`，并在当前 Agent 工具列表中确认对应 MCP 工具确实可用。
2. **输入映射**：每次调用 `campaign baseline` 或 `campaign propose` 后，以返回的 `candidate_config` 和 `frozen_training_recipe` 作为唯一输入传给训练 MCP，禁止临场夹带未登记的超参或结构改动。
3. **指标与算量提取**：向评测 MCP 确认以下字段的真实数值来源：
   - 主增益指标：`context.primary_metric.name`（例如 `nmse_db`、`map50`、`accuracy`、`val_bpb`）
   - 推理/模型算量：`context.compute_metric.name`（例如 `flops_m`、`macs_m`、`latency_ms`、`params_m`）
   - 护栏指标：`context.compute_limits.guardrails` 中列出的每个指标
   - 训练/搜索成本：`context.cost_metric.name`（例如 `gpu_seconds`、`gpu_hours`）
   - 模型产物引用：`artifacts.model_ref`（用于最终 Holdout 一致性防篡改校验）

## 2. 长任务与异常恢复规范

- **记录远端任务 ID**：把每阶段拿到的远端 `job_id` 放入 `campaign record --external-jobs '[{"stage":"training","tool":"...","job_id":"..."}]'`，保证可追溯。
- **提交超时/响应丢失**：若调用训练 MCP 时超时，先调用平台查询工具核实远端是否已创建任务，确认未接收后再重提，避免双提交浪费 GPU。
- **OOM / 训练发散 / 单轮超时**：
  1. 若平台支持取消接口，先停止远端任务并保存关键错误日志片段；
  2. 执行 `campaign record latest --status crash --cost '{"<cost_metric>": <已消耗>}' --note "<根因>"`；
  3. 不要因为单轮失败就终止整个 Campaign，读 `campaign context latest` 后避开故障点继续下一轮。

## 3. Holdout 盲评铁律

- 探索过程中只能调用 `dev_evaluator_ref` 对应的评测集。
- 决定停止探索或 `remaining_trials == 0` 时，取 `context.incumbent.model_ref`，对**该已有模型权重**调用一次 `holdout_evaluator_ref` 对应的评测 MCP（严禁重新训练），再用 `campaign finalize latest --metrics ... --artifacts '{"model_ref": "<incumbent_model_ref>"}'` 完成验收。
- 若 Holdout 未达标，保留负结果并调用 `kb distill latest` 沉淀教训；严禁把同一留出集的逐例错误反馈重新喂回当前开发循环。
