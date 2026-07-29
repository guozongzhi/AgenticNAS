# 研究课题边界

当前把 `LLM × NAS` 与 `LLM × HPO` 作为两个独立课题推进。两条线可以引用相同的 Agent 设计思想，但近期不做联合搜索，也不以“未来可融合”为由混用搜索空间、预算或实验结论。

## 课题一：LLM × NAS

- **研究对象**：真实神经网络架构；
- **可变项**：深度、宽度、block/cell/op、连接方式等结构变量；
- **固定项**：训练配方、数据划分、训练预算和评估器；
- **核心基线**：random/native mutation、进化式 NAS、stateless LLM、memory-aware LLM；
- **核心指标**：任务质量、参数量/FLOPs、真实延迟/显存/能耗、Pareto hypervolume、动作合法率、重复率、搜索成本和随机种子方差。

论文入口见 [`papers/INDEX.md` 的 LLM × NAS 部分](../papers/INDEX.md#llm-nas)。

## 课题二：LLM × HPO

这里的含义是“用 LLM 辅助目标模型的超参数优化”，目标模型可以是小型 ViT、CNN 或 Encoder-Decoder，并不限定为大语言模型。

- **研究对象**：固定架构的训练配方；
- **可变项**：学习率、weight decay、batch size、dropout、优化器、warmup、调度器、数据增强和训练轮数；
- **固定项**：模型深度/宽度/heads/算子/连接方式、数据划分和最终评估器；
- **核心基线**：random search、TPE、CMA-ES、纯 LLM 提议器、LLM + 经典 HPO 混合方法；
- **核心指标**：best-so-far、regret、达到目标质量所需 trials、训练/GPU/LLM 成本、无效配置率、OOM/发散率和随机种子方差。

专题综述见 [LLM 辅助的超参数优化](llm-hpo-training-automation.md)，论文入口见 [`papers/INDEX.md` 的 LLM × HPO 部分](../papers/INDEX.md#llm-hpo)。

## 当前不做的融合事项

以下内容只记入远期 backlog，不进入近期实现或实验：

- 同时搜索架构与训练配方；
- 用 HPO 重新排序 NAS 的 Pareto 候选；
- NAS Agent 与 HPO Agent 共享 memory、reward 或候选 archive；
- manager 同时调度 NAS/HPO 子代理；
- 把架构质量提升归因给 HPO，或把训练配方收益归因给 NAS。

只有当两条线都至少完成一个可复现实验，并在相同预算、至少三个随机种子下建立各自的非 LLM 基线后，再单独立项讨论融合。
