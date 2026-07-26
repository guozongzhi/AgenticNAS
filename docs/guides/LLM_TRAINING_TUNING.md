# LLM 训练参数调优方案

本项目中的 LLM 不应直接改训练代码或任意修改 YAML。它应根据已记录的训练曲线和资源预算，输出受约束、可验证的训练参数补丁；训练控制器负责校验、执行和记录。

## 1. 与 NAS 的边界

结构搜索和训练参数调优必须分阶段进行，否则很难判断收益来自架构还是训练配方。

1. 在一个固定的 canonical architecture 上调出全局训练配方；
2. 主 NAS 实验使用这套固定配方和相同训练预算；
3. 对最终 Pareto 前沿的少量模型，以每个模型相同的额外预算做调优；
4. 若研究“架构与训练参数联合搜索”，单独建立实验组，并将所有训练次数、GPU-hours 和 LLM 调用都计入同一总预算。

不要为某一个 NAS 候选单独调优后，再与未调优候选比较。

## 2. Agent 可观察状态

每次请求应只暴露已批准的聚合信息：

```json
{
  "run_id": "run_042",
  "architecture_id": "anonymous_arch_17",
  "fidelity": "short_train",
  "training_config": {"learning_rate": 0.0003, "warmup_ratio": 0.03},
  "curve_summary": {"train_loss": [2.4, 1.9], "val_loss": [2.5, 2.1]},
  "stability": {"nan_count": 0, "grad_norm_p95": 1.8},
  "resources": {"gpu_hours": 0.4, "peak_memory_gb": 8.1},
  "remaining_budget": {"trials": 12, "gpu_hours": 10}
}
```

同时提供当前允许参数及范围。不要向外部服务发送内部数据、完整训练样本、未审批的架构图或访问令牌。

## 3. 受约束动作

第一版只开放下列参数；每个动作最多修改两个相关字段。

| 类别 | 参数 | 建议范围/约束 |
|---|---|---|
| 优化 | `learning_rate` | 对数尺度；必须位于项目批准的上下界 |
| 优化 | `weight_decay` | `0` 到项目批准的上界 |
| 调度 | `warmup_ratio` | `0` 到 `0.1` |
| 正则 | `dropout` | `0` 到 `0.3` |
| 批处理 | `micro_batch_size`、`grad_accumulation` | 保持或显式记录 effective batch size |
| 稳定性 | `grad_clip_norm` | 仅在梯度异常或不稳定时开放 |

```json
{
  "base_run_id": "run_042",
  "changes": [
    {"name": "learning_rate", "value": 0.00018},
    {"name": "warmup_ratio", "value": 0.05}
  ],
  "fidelity": "short_train",
  "expected_effect": "reduce validation-loss instability"
}
```

控制器必须拒绝未知参数、越界值、超过变更数上限的动作，以及与已完成 trial 完全重复的配置。LLM 的解释不作为执行依据。

## 4. 评估和晋升流程

使用固定的三档 fidelity：

1. `smoke`：少量 step，仅检查 loss、显存、NaN 和吞吐；
2. `short_train`：固定短周期，作为 Agent 的主要反馈；
3. `full_train`：只晋升少量短训表现好且稳定的配置。

每个阶段记录配置、随机种子、数据/代码版本、checkpoint 来源、训练曲线、验证指标、wall time、GPU-hours 和 LLM 请求/响应 hash。优先使用 ASHA/Successive Halving 或随机搜索作为非 LLM 基线；LLM 方案必须在相同 trial 数和总成本下比较。

## 5. 给 LLM 的任务提示

```text
你是受约束的训练参数提议器。目标是在剩余预算内改善验证指标并保持训练稳定。
只能使用 allowed_parameters 中的字段；最多修改两个相关字段；严格返回 JSON。
不要修改架构、数据、评估代码或预算。不要把短训代理结果描述为最终结果。
```

建议将一个模型用于主实验，另一个模型仅用于迁移验证；记录模型名称、版本、temperature、最大 token 和提示词版本。更多内部 Agent 边界见 [INTERNAL_AGENT_GUIDE.md](INTERNAL_AGENT_GUIDE.md)。

## 6. 最小研究验收

- 固定架构下，LLM、随机搜索和标准 HPO 的预算完全相同；
- 至少报告三个随机种子下的最佳验证指标、稳定性失败率和成本；
- NAS 主实验使用固定训练配方；
- 最终模型调优只在明确标注的额外预算中进行；
- 所有提议、拒绝理由和结果可从 trace 回放。
