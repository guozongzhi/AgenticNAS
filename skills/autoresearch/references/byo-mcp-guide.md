# BYO-MCP 对接与异常对账指南

本技能采用 **BYO-MCP（自带 MCP）** 架构：Agent 直接调用当前会话已挂载的仿真/训练/评测 MCP 工具，`autoresearch.py` 只负责纯本地配置冻结、合法域拦截、棘轮账本与经验知识库沉淀，无需编写任何额外 MCP 客户端胶水代码。

---

## 1. 启动前核对三要素

1. **体检无警告放行**：运行 `python3 <skill_dir>/scripts/autoresearch.py doctor --workspace <ws>`，确认 `<ws>/mcp_tools.md` 中已填入当前环境真实可用的 MCP 工具名。
2. **输入零夹带**：`campaign baseline` 或 `campaign propose` 返回后，严格将 `candidate_config` 与冻结项（`frozen_training_recipe` 或 `frozen_architecture`）原样传入训练 MCP，禁止临场夹带未登记字段。
3. **回填字段齐全**：
   - 主指标：`primary_metric.name`（如 `nmse_db`、`map50`、`accuracy`、`val_bpb`）
   - 推理/模型算量：`compute_metric.name`（如 `flops_m`、`macs_m`、`latency_ms`、`params_m`，正有限数）
   - 护栏指标：`guardrails` 中声明的每一项指标
   - 成本指标：`cost_metric.name`（如 `gpu_seconds`、`gpu_hours`）
   - 产物引用：`artifacts.model_ref`（及含仿真阶段时的 `artifacts.dataset_ref`）

---

## 2. 单轮交互数据流示例

```text
[Step 1] 控制面提案校验与冻结：
  $WS campaign propose latest \
    --hypothesis "编码器引入轻量化 SE 注意力，预期算量增幅 <3% 且降低 NMSE" \
    --changes '{"encoder.use_se": true}'
  ──> 输出：
      {
        "trial_id": "trial-001",
        "config_id": "9f2c8d1a44b0",
        "status": "awaiting_result",
        "candidate_config": {"encoder": {"num_blocks": 4, "channels": 64, "kernel_size": 3, "use_se": true}, ...},
        "frozen_training_recipe": {"epochs": 30, "lr": 0.001, "weight_decay": 0.01, "seed": 42},
        "dev_evaluator_ref": "uri://evaluators/cnn_csi-dev"
      }

[Step 2] Agent 调度用户已有 MCP：
  - 训练 MCP(candidate_config, frozen_training_recipe) -> job_id="job-881", model_ref="s3://models/t001.pt", gpu_hours=0.42
  - Dev 评测 MCP(model_ref, dev_evaluator_ref) -> nmse_db=-18.45, macs_m=51.1, latency_ms=2.10, gpu_hours=0.03

[Step 3] 回填控制面自动裁决：
  $WS campaign record latest --trial trial-001 --status succeeded \
    --metrics '{"nmse_db": -18.45, "macs_m": 51.1, "latency_ms": 2.10}' \
    --cost '{"gpu_hours": 0.45}' \
    --artifacts '{"model_ref": "s3://models/t001.pt"}' \
    --external-jobs '[{"stage": "training", "tool": "mcp_train", "job_id": "job-881"}]'
```

- 若链路含 `simulation` 阶段且本轮未改动数据生成条件，提案时加 `--reuse-simulation` 复用 `incumbent.dataset_ref`。

---

## 3. 中断恢复与长任务异常处理

- **会话重连 / 断点恢复**：
  先运行 `$WS campaign context latest` 检查 `active_trial`：
  - 若 `active_trial != null`（`run_status == "awaiting_result"`），说明提案已落盘但尚未回填。**严禁再调 `campaign propose`**；先调平台查询 MCP 核实远端任务是否已在跑或已完成——已跑完则直接 `campaign record`，未入队再按 `active_trial.candidate_config` 发起 MCP 调用。
- **提交超时防双跑**：训练提交 MCP 超时未返回 `job_id` 时，先查询远端队列确认未创建任务后再重提。
- **OOM / NaN 发散 / 超时隔离**：
  先通过 MCP 取消远端失控任务，再执行 `$WS campaign record latest --status crash --cost '{"<cost_metric>": <实际已消耗>}' --note "<根因>"`。非基线轮次的 `crash` 仅记账并保留原 `incumbent`，下一轮避开故障配置继续探索。

---

## 4. Holdout 盲评铁律

- 探索全过程仅允许调用 `dev_evaluator_ref`。
- 进入 `awaiting_holdout`（或主动 `campaign stop`）后，取 `context.incumbent.model_ref`，对**该已有模型产物**调用唯一一次 `holdout_evaluator_ref` 评测 MCP（严禁重训）。
- 若基线模型尚未在 Holdout 上测过，建议同步测一次基线模型，把结果作为 `"baseline_<primary>"` 与 `"baseline_<compute>"` 传入 `campaign finalize --metrics '{...}'` 以获得同分布 Holdout 净增益。
- 无论 `holdout_report.accepted` 真假，均如实归档并执行 `knowledge-base distill latest`；严禁根据 Holdout 结果回头继续调参刷分。
