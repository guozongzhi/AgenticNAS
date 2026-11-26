# BYO-MCP 对接、并行/多保真与故障分类对账指南

本技能采用 **BYO-MCP（自带 MCP）** 架构：Agent 直接调用当前环境已挂载的仿真/训练/评测 MCP 工具，`autoresearch.py` 负责纯本地配置冻结、合法域拦截、多保真/并行状态管理、反作弊审计与经验知识库沉淀。

---

## 1. 启动前核对三要素

1. **体检放行**：运行 `python3 <skill_dir>/scripts/autoresearch.py doctor --workspace <ws>`，确认 `<ws>/mcp_tools.md` 已替换为真实可用的 MCP 工具名。
2. **输入零夹带**：严格将 `campaign baseline / propose` 返回的 `candidate_config` 与冻结项（`frozen_training_recipe` 或 `frozen_architecture`）原样送入训练 MCP。
3. **全保真产物溯源必填**：`fidelity == "full"` 的成功试验必须在 `--artifacts '{"model_ref": "<uri>"}'` 中登记模型权重 URI，避免触发反作弊审计器的 `missing_model_ref_on_full_trial` 告警，并保障最终 Holdout 一致性核验。

---

## 2. 进阶执行模式对接

### 2.1 多卡同步并行批次（`--max-parallel K`）
当用户的训练 MCP 支持多卡并发作业队列时（例如 `init --max-parallel 4`）：
1. 在同一轮连续调用最多 4 次 `campaign propose`（建议沿 4 个正交结构轴生成提案），分别拿到 `trial-001 .. trial-004`；
2. 并发提交 4 个训练 MCP 任务；
3. 按远端完成顺序逐个调用 `campaign record latest --trial trial-00X ...` 回填（当有多个活跃试验时，`--trial` 参数为必填）。

### 2.2 两级多保真筛查（`--fidelity proxy -> full`）
若训练 MCP 支持短训步数或数据子集参数：
1. 提案时指定 `--fidelity proxy`：调训练 MCP 的快速筛查档位并将结果回填 `campaign record`（得分仅判 `proxy_pass / proxy_discard`，绝不污染全保真 `incumbent`）；
2. 读取 `context.search_diagnostics.ready_to_promote_proxies`，对筛查胜出的配置重新调用 `--fidelity full` 跑完整冻结训练配方。

---

## 3. 故障精细分类与断点对账（防止污染经验库）

调用 `campaign record --status crash/failed/timeout` 时，**务必准确填写 `--failure-kind`**：

| `--failure-kind` | 含义 | 控制面与经验库行为 |
| --- | --- | --- |
| `oom` | 显存溢出或算子内存超限 | 记为科学失效边界；`distill` 归入 `compute_budget_exceeded` 反例 |
| `nan_divergence` | Loss NaN / 梯度爆炸发散 | 记为科学失效边界；`distill` 归入 `training_crash` 反例 |
| `timeout` | 候选结构过慢导致单轮训练超时 | 记为科学失效边界；`distill` 归入 `training_crash` 反例 |
| `infra_flake` | 远端节点掉线、网络抖动、存储挂载瞬时失败 | **物理隔离**：仅记实际已耗成本，**不计入停滞轮数、允许原配置重提、绝不写入 `anti_patterns`** |

### 会话中断对账流程
重连后先查 `$WS campaign context latest` 的 `active_trials` 列表：对每个在途 `trial_id` 先调平台查询 MCP 核实远端任务是否已完成或仍在运行，切勿盲目重提导致双倍扣费。

---

## 4. Holdout 盲评与反作弊铁律

- 开发期严禁调用 `holdout_evaluator_ref`。
- 全部在途试验回填完毕且探索收束后，对 `context.incumbent.model_ref` 调用**唯一一次** `holdout_evaluator_ref`（严禁重训），执行 `campaign finalize`（引擎会硬核对 `model_ref` 一致性并自动写出 `REPORT.md`）。
