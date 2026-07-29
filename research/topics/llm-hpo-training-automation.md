# 课题二：LLM 辅助的超参数优化（LLM × HPO）

> 状态：独立研究课题
>
> 定义：用 LLM 辅助固定目标模型的训练超参数优化。目标模型可以是小型 ViT、CNN 或 Encoder-Decoder，不限定为大语言模型。

本课题只搜索训练配方：学习率、weight decay、batch size、dropout、优化器、warmup、调度器、增强和训练轮数。模型深度、宽度、heads、算子和连接方式属于 NAS 变量，在本课题中必须固定。完整边界见 [研究课题边界](README.md)。

> 证据状态：下列数字是论文报告的候选证据。本仓库对应条目均已补为带页码的 `codex_draft`，但在人工复核原表、预算和代码前不得作为 retained 结论引用。

## 1. 待核验的核心发现（先建立正确预期）

相邻方法证据：[Can LLMs Beat Classical Hyperparameter Optimization Algorithms? (arXiv 2603.24647v5, 2026)](../papers/parsed/2026-arxiv-llm-vs-classical-hpo.md)——在 nanochat 式 LM 训练任务上系统对比 LLM 优化器（Qwen3.5 0.8B/27B、Gemini、Claude Opus 4.6）与 TPE / CMA-ES / 随机搜索。其 14 个字段含 `DEPTH`、`HEAD_DIM`、attention window 等结构变量，按本仓库规则属于 `mixed-search-space`，只能用于方法设计，不能当作固定架构 HPO 的直接结果：

1. **在该评测的固定搜索空间内，纯 LLM 提议打不过 TPE**——不要默认 LLM 可以替代 Optuna；
2. **该评测中的混合模式有效**：Centaur 让 CMA-ES 保留完整搜索状态，并在部分 trials 向 LLM 暴露均值、步长和协方差；0.8B LLM 已有竞争力；
3. **代码级优化是 LLM 的差异化价值**：在该实验设置中，无约束直接改训练源码（学习率调度、增强、正则）的 "Karpathy Agent" 模式有竞争力，但需要 ≥27B 模型才可靠（0.8B 失败；Gemini 3.1 Flash-Lite 87–94% 试次生成无效代码）；
4. 规模缩窄差距但不逆转：Claude Opus 4.6 代码编辑 0.9770±0.0027 vs TPE 0.9768±0.0019（越低越好）。

**对本课题的含义**：LLM Agent 的定位应是「给先验、改空间、读日志、做诊断」，而不是在固定数值网格里替代 BO/TPE。

## 2. 与微小 ViT / Encoder-Decoder 直接相关的实践

| 论文/系统 | 目标模型与任务 | LLM 扮演的角色 | 主要证据 | 对边缘小模型的实际意义 |
|---|---|---|---|---|
| [Using Large Language Models for Hyperparameter Optimization](https://arxiv.org/abs/2312.04528) | CIFAR-10 上的 ViT/ResNet；本档案尚未核验 ViT 参数规模 | 根据任务描述和历史 loss 顺序提议训练超参 | ViT/ResNet 实验搜索 5 个训练超参，每 trial 20 epochs，最多 30 次；LLM warm-start 可改善后续 BO | 是“小型视觉任务 + LLM HPO”的直接候选证据，但尚不能据此称为微型边缘模型，也没有延迟/能耗目标 |
| [AgentHPO](../papers/parsed/2024-cpal-agenthpo.md) | T5-Small 英法翻译，以及视觉/表格任务 | Creator 提议配置，Executor 训练、分析日志并回传 | 10th trial：GPT-4 BLEU 28.02±0.61、random 25.72±0.92、Bayesian 26.70±0.59；27.47 “human”是 100 baseline trials 的 peak proxy | 表明小型 Encoder-Decoder 可进入 Agent 闭环；10-trial Agent 与 100-trial proxy 不是同预算比较 |
| [AutoMMLab / HPO-LLaMA](../papers/parsed/2025-aaai-autommlab.md) | MobileNet、MobileViT、ViT 等模型库 | 用 8,000 个真实训练结果微调 LLaMA-7B 生成训练配置 | 模型选择按参数量/FLOPs/速度过滤；HPO 搜六类训练参数，1–3 轮；论文直接回传 test metric | 很接近边缘工作流，但硬件约束作用于选模/部署，且 test feedback 不符合本仓库协议 |
| [Rocket](../papers/parsed/2026-nature-rocket-hpo.md) | ImageNet 上的 TinyViT 等视觉模型 | Qwen2.5-0.5B policy 通过循环强化学习提议 20+ 混合型训练超参 | TinyViT 最佳准确率 75.34%，高于 GPT-4o 72.47% 和 DeepSeek-R1 74.05%，低于 public expert 76.25%；结果带 split-data 标记 | 是“小 LLM policy + TinyViT HPO”的直接候选证据，但未优化端侧延迟、内存或能耗 |

**本次收集的结论**：公开论文报告了 LLM 给 ViT、MobileNet 和 T5-Small 调训练超参的结果；但相关数字仍待本仓库人工核验，且 CIFAR-10 ViT 尚不能直接归类为微型边缘模型。在本次收集范围内，也未发现把端侧真实延迟、内存或能耗直接纳入 LLM HPO 目标的成熟范式。若目标同时改变层数、宽度或算子，那是 hardware-aware NAS，不应记作本课题成果。

## 3. 方法谱系

| 方法 | 年份 | 模式 | 要点 | 本仓库笔记 |
|---|---|---|---|---|
| LLM HPO (Zhang et al.) | 2023 | 零样本初始化 | 从问题描述给初始超参，小预算（~10 次）内可比 RS/BO | [解析](../papers/parsed/2023-arxiv-llm-hpo.md) |
| AgentHPO | 2024 | 双 Agent（Creator+Executor） | 视觉/表格/翻译任务超 RS、部分超人 | [解析](../papers/parsed/2024-cpal-agenthpo.md) |
| LLAMBO | 2024 | LLM + BO 混合 | LLM 暖启动 + 代理模型精搜 | [解析](../papers/parsed/2024-iclr-llambo.md) |
| SLLMBO | 2024 | LLM + TPE 混合 | 14 个表格任务、单 seed；复杂 CV/NLP 留作后续 | [解析](../papers/parsed/2024-arxiv-sllmbo.md) |
| AutoMMLab / HPO-LLaMA | 2025 | 领域微调的 HPO LLM | 用 8,000 个真实实验微调 LLaMA-7B，并衔接选模和部署 | [解析](../papers/parsed/2025-aaai-autommlab.md) |
| Rocket | 2026 | 小 LLM + 循环 RL | Qwen2.5-0.5B 学习跨任务的 HPO policy | [解析](../papers/parsed/2026-nature-rocket-hpo.md) |
| Can LLMs Beat Classical HPO? | 2026 | mixed-space 公平对比 | TPE/CMA-ES 优于纯 LLM；Centaur 最佳，但空间含架构字段 | [解析](../papers/parsed/2026-arxiv-llm-vs-classical-hpo.md) |
| AutoLLMResearch | 2026 | 跨任务多保真 | 四类独立任务分别覆盖架构、训练超参和数据配置，不是联合搜索 | [解析](../papers/parsed/2026-arxiv-autollmresearch.md) |

## 4. 邻接方向：MLE Agent，而非本课题主证据

MLE Agent 可以改数据管道、特征、模型代码和训练脚本，范围大于 HPO。它适合参考日志诊断、失败恢复和工具调用设计，但不能直接作为“固定架构 HPO 有效”的证据。

相关入口：[MLE-bench](https://arxiv.org/abs/2410.07095)、[MLAgentBench](https://arxiv.org/abs/2310.03302)（[本仓库解析](../papers/parsed/2023-arxiv-mlagentbench.md)）。这些工作单独标为 `benchmark` / `mle-agent`，不混入核心 HPO 排名。

## 5. 独立研究协议

### 5.1 第一阶段：结构化训练超参

- 固定一个小型目标模型、数据划分、训练脚本和最终评估器；
- 首轮只搜索学习率、weight decay、batch size、dropout、warmup 和 scheduler；优化器、增强和训练轮数属于本课题的后续搜索变量，但在首轮固定；
- 以“尝试的 trial 数”为主搜索预算；每个 trial 使用相同的样本/token 上限和 wall-time 上限，失败 trial 也计入预算并记录实际成本；
- GPU 时长、LLM token/费用和完成的训练步数作为结果报告，不再同时充当必须完全相等的硬预算；
- 用三个配对的 outer seeds 重复完整 HPO run；每个 seed 固定 HPO 采样种子和 trial 对应的训练/数据种子序列，LLM 采样种子或不可控性另行记录；
- 在上述口径下比较 random、TPE、CMA-ES、纯 LLM 和 LLM→TPE；
- 默认 20-trial 原型中，LLM→TPE 用前 5 个 LLM 配置 warm-start、后 15 个由 TPE 提议；TPE 对照用 5 个 random warm-start 加 15 个 TPE trial；
- 在 `1/3/5/10/20` trials 记录 best-so-far、regret、总成本、无效配置率、OOM/发散率；
- LLM 侧额外记录模型版本、prompt hash、temperature、token 数、调用延迟和费用。

这仍是协议骨架，不是可直接运行的正式实验。启动前必须在独立 `PROTOCOL.md` 中选定目标模型/数据集、质量指标、参数范围、validation/test 规则、early stopping、失败记账方式和 regret 参照值。

### 5.2 第二阶段：日志诊断

只有第一阶段建立可靠基线后，才增加压缩后的训练曲线和失败类型，让 Agent 选择有限、可校验的诊断动作。代码级自由修改单独立项，不与结构化 HPO 的结果合并。

## 6. 待办与停止线

- [ ] 人工复核 Codex 已定位的 TinyViT、T5-Small 和 MobileNet 主要数字，并运行可用的公开代码；
- [ ] 为一个固定小模型写独立 HPO `PROTOCOL.md`，先跑 random/TPE/CMA-ES；
- [ ] 增加纯 LLM 与 LLM→TPE，保持相同的 attempted trials、每 trial 样本/token 上限和 wall-time 上限，并分别报告实际 GPU/LLM 成本；
- [ ] 至少运行三个随机种子，报告 best-so-far 曲线而不只报告单个最优点；
- [ ] 单独评估日志摘要对诊断动作的增益；
- [ ] **停止线**：不增加 `ArchitectureSpec`、不搜索结构字段、不维护联合 Pareto、不让 NAS/HPO 共享 archive。

## 7. 未来融合（当前不做）

联合搜索、NAS 候选的 HPO 精调、共享 memory/reward、manager + NAS/HPO 子代理都保留为远期问题。只有 NAS 与 HPO 两条线各自完成可复现基线和预算核验后，才新建独立课题讨论，不在当前档案提前设计接口。

## 8. 主要参考

- [Can LLMs Beat Classical HPO Algorithms? (arXiv 2603.24647v5)](../papers/parsed/2026-arxiv-llm-vs-classical-hpo.md)
- [Using Large Language Models for Hyperparameter Optimization (arXiv 2312.04528)](https://arxiv.org/abs/2312.04528)
- [AgentHPO (arXiv 2402.01881)](https://arxiv.org/abs/2402.01881)
- [LLAMBO (arXiv 2402.03921)](https://arxiv.org/abs/2402.03921)
- [SLLMBO (arXiv 2410.20302)](../papers/parsed/2024-arxiv-sllmbo.md)
- [AutoMMLab / HPO-LLaMA (AAAI 2025)](../papers/parsed/2025-aaai-autommlab.md)
- [Rocket (Nature Communications, 2026)](../papers/parsed/2026-nature-rocket-hpo.md)
- 全部 HPO 与相邻工作见 [论文阅读索引](../papers/INDEX.md#llm-hpo)。
