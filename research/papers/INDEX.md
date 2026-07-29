# 论文阅读索引

本索引把 `LLM × NAS` 与 `LLM × HPO` 分开维护。前者搜索神经网络结构并固定训练配方；后者搜索固定架构的训练超参数。当前不做联合搜索，完整约定见 [研究课题边界](../topics/README.md)。

<a id="llm-nas"></a>

## 课题一：LLM × NAS

| Status | Paper | Year/Venue | Tags | Note | Next action |
|---|---|---|---|---|---|
| codex_draft | [Agentic Neural Architecture Search](https://arxiv.org/abs/2607.07984) | 2026/arXiv | `llm-nas`, `slotted-architecture`, `evolution` | [解析](parsed/2026-arxiv-agentnas.md) | 复现 v1.0 tag，并核对 matched-budget 与 LLM 成本 |
| codex_draft | [Structuring Open-Ended NAS: Semi-Automated Design Knowledge Structuring with LLMs for Efficient Neural Architecture Search](https://arxiv.org/abs/2605.19247) | 2026/arXiv | `llm-nas`, `pareto`, `open-ended` | [解析](parsed/2026-arxiv-fairnad.md) | 核对知识库授权、LLM token 成本与公开代码 |
| codex_draft | [LLM-NAS: LLM-driven Hardware-Aware Neural Architecture Search](https://arxiv.org/abs/2510.01472) | 2026/GECCO | `llm-nas`, `pareto`, `hardware-aware` | [解析](parsed/2026-gecco-llm-nas.md) | 复算 HV/IGD，并核验预测器训练与真实设备外推 |
| codex_draft | [EvoPrompting: Language Models for Code-Level Neural Architecture Search](https://arxiv.org/abs/2302.14838) | 2023/arXiv | `llm-nas`, `evolution` | [解析](parsed/2023-neurips-evoprompting.md) · [PDF](pdfs/2302.14838-evoprompting.pdf) | 核对搜索预算与消融表格 |
| codex_draft | [LLMatic: Neural Architecture Search via Large Language Models and Quality Diversity Optimization](https://arxiv.org/abs/2306.01102) | 2024/GECCO | `llm-nas`, `evolution` | [解析](parsed/2024-gecco-llmatic.md) · [PDF](pdfs/2306.01102-llmatic.pdf) | 对比 QD archives 与 Pareto 前沿 |
| codex_draft | [NADER: Neural Architecture Design via Multi-Agent Collaboration](https://arxiv.org/abs/2412.19206) | 2024/arXiv | `llm-nas` | [解析](parsed/2024-arxiv-nader.md) · [PDF](pdfs/2412.19206-nader.pdf) | 将图动作映射到 block/cell/op |
| codex_draft | [SEKI: Self-Evolution and Knowledge Inspiration based Neural Architecture Search via Large Language Models](https://arxiv.org/abs/2502.20422) | 2025/arXiv | `llm-nas`, `memory`, `nas-bench-201` | [解析](parsed/2025-arxiv-seki.md) | 核对代码、随机种子、LLM 调用成本与完整预算 |
| codex_draft | [Data-Local Autonomous LLM-Guided Neural Architecture Search for Multiclass Multimodal Time-Series Classification](https://arxiv.org/abs/2603.15939) | 2026/arXiv | `llm-nas` | [解析](parsed/2026-arxiv-data-local-llm-nas.md) · [PDF](pdfs/2603.15939-data-local-llm-nas.pdf) | 核验两项数据集改进与退化结果 |
| codex_draft | [LLM-Guided Neural Architecture Search for Robust Co-Design of Physical Neural Networks](https://arxiv.org/abs/2606.10294) | 2026/arXiv | `llm-nas`, `pareto`, `hardware-aware` | [解析](parsed/2026-arxiv-uh-nas.md) · [PDF](pdfs/2606.10294-uh-nas.pdf) | 提取硬件目标与非理想性假设 |
| codex_draft | [MANAS: Multi-Agent Neural Architecture Search](https://arxiv.org/abs/1909.01051) | 2019/arXiv | `evolution` | [解析](parsed/2019-arxiv-manas.md) · [PDF](pdfs/1909.01051-manas.pdf) | 保留为非 LLM 多智能体基线 |

<a id="llm-hpo"></a>

## 课题二：LLM × HPO

这里的 HPO 是“LLM 辅助固定目标模型调参”，目标模型可以是 ViT、CNN、Encoder-Decoder 或 LM；层数、宽度、heads、算子和连接方式不属于本表的 HPO 搜索变量。

| Status | Paper | Year/Venue | Tags | Note | Next action |
|---|---|---|---|---|---|
| codex_draft | [Using Large Language Models for Hyperparameter Optimization](https://arxiv.org/abs/2312.04528) | 2023/arXiv | `hpo` | [解析](parsed/2023-arxiv-llm-hpo.md) · [PDF](pdfs/2312.04528-llm-hpo.pdf) | 核对预算与 BO 对比 |
| codex_draft | [AgentHPO: Large Language Model Agent for Hyper-Parameter Optimization](https://arxiv.org/abs/2402.01881) | 2025/CPAL | `hpo` | [解析](parsed/2024-cpal-agenthpo.md) · [PDF](pdfs/2402.01881-agenthpo.pdf) | 人工复核 T5-Small Table 3 与 5/10-run 口径 |
| codex_draft | [Large Language Models to Enhance Bayesian Optimization](https://arxiv.org/abs/2402.03921) | 2024/ICLR | `hpo` | [解析](parsed/2024-iclr-llambo.md) · [PDF](pdfs/2402.03921-llambo.pdf) | 复用 LLM + BO 基线设计 |
| codex_draft | [Sequential Large Language Model-Based Hyper-parameter Optimization](https://arxiv.org/abs/2410.20302) | 2024/arXiv | `hpo`, `hybrid` | [解析](parsed/2024-arxiv-sllmbo.md) · [PDF](pdfs/2410.20302-sllmbo.pdf) | 人工复核单 seed 与 9/14 task 结论 |
| codex_draft | [AutoMMLab: Automatically Generating Deployable Models from Language Instructions for Computer Vision Tasks](https://arxiv.org/abs/2402.15351) | 2025/AAAI | `hpo`, `edge-vision`, `deployment` | [解析](parsed/2025-aaai-autommlab.md) · [PDF](pdfs/2402.15351-autommlab.pdf) | 复核 test-feedback 泄漏与不等轮次基线 |
| codex_draft | [Automated deep learning by recurrent hyperparameter optimization (Rocket)](https://doi.org/10.1038/s41467-026-72413-9) | 2026/Nature Communications | `hpo`, `tinyvit`, `rl` | [解析](parsed/2026-nature-rocket-hpo.md) · [PDF](pdfs/2026-nature-rocket-hpo.pdf) | 运行公开代码并核验 policy-training 摊销成本 |
| codex_draft | [Hyperparameter Optimization for Large Language Model Instruction-Tuning](https://arxiv.org/abs/2312.00949) | 2023/AAAI | `hpo`, `transformer` | [解析](parsed/2023-aaai-instruction-tuning-hpo.md) · [PDF](pdfs/2312.00949-llm-instruction-tuning-hpo.pdf) | 作为非 Agent HPO 基线 |

## 相邻方法：Mixed Search Space

这些论文同时改变结构与训练字段，不能直接支撑固定架构 HPO 或固定配方 NAS 的效果结论。

| Status | Paper | Year/Venue | Tags | Note | Next action |
|---|---|---|---|---|---|
| codex_draft | [Can LLMs Beat Classical Hyperparameter Optimization Algorithms? A Study on autoresearch](https://arxiv.org/abs/2603.24647) | 2026/arXiv | `hpo`, `benchmark`, `hybrid`, `mixed-search-space` | [解析](parsed/2026-arxiv-llm-vs-classical-hpo.md) · [PDF](pdfs/2603.24647-llm-vs-classical-hpo.pdf) | 固定结构字段后再复现 TPE/CMA-ES/Centaur |

## 相邻方法：跨 NAS/HPO 任务的多保真 Agent

这类方法用统一 Agent 分别处理架构、训练超参或数据配置任务，但不在单个搜索空间里联合优化它们。

| Status | Paper | Year/Venue | Tags | Note | Next action |
|---|---|---|---|---|---|
| codex_draft | [AutoLLMResearch: Training Research Agents for Automating LLM Experiment Configuration](https://arxiv.org/abs/2605.11518) | 2026/arXiv | `hpo`, `transformer`, `multi-fidelity` | [解析](parsed/2026-arxiv-autollmresearch.md) · [PDF](pdfs/2605.11518-autollmresearch.pdf) | 分别复现 architecture 与 training-HPO 任务 |

## 邻接基准：MLE Agent

端到端 MLE Agent 可以同时改数据、代码、模型和训练流程，不能直接作为固定架构 HPO 的证据。

| Status | Paper | Year/Venue | Tags | Note | Next action |
|---|---|---|---|---|---|
| codex_draft | [MLAgentBench: Evaluating Language Agents on Machine Learning Experimentation](https://arxiv.org/abs/2310.03302) | 2023/arXiv | `benchmark`, `mle-agent` | [解析](parsed/2023-arxiv-mlagentbench.md) · [PDF](pdfs/2310.03302-mlagentbench.pdf) | 将失败类型纳入 Agent 评测 |

## 状态定义

- `inbox`：已收集、尚未通读；
- `codex_draft`：已由 Codex 生成初稿、尚未完成人工证据核验；
- `reading`：正在阅读并填写笔记；
- `retained`：已提炼出可引用结论、局限和行动项；
- `reproduced`：已运行公开代码或重现关键实验。

每篇 retained/reproduced 论文都必须链接到对应笔记文件。NAS 论文优先记录层次化搜索空间、Pareto 指标和动作合法性；HPO 论文优先记录固定架构、trial/训练/GPU/LLM 预算、best-so-far 和经典 HPO 基线。两类结论不得互相替代。

## 主题档案

- 两条独立主线及当前停止线见 [研究课题边界](../topics/README.md)；
- `hpo` 标签的论文由主题档案 [LLM 辅助的超参数优化](../topics/llm-hpo-training-automation.md) 统一组织；
- `hardware-aware` / 边缘部署方向由 [边缘视觉小模型](../topics/edge-vision-small-models.md) 统一组织。
