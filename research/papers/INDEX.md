# NAS 论文阅读索引

| Status | Paper | Year/Venue | Tags | Note | Next action |
|---|---|---|---|---|---|
| codex_draft | [EvoPrompting: Language Models for Code-Level Neural Architecture Search](https://arxiv.org/abs/2302.14838) | 2023/arXiv | `llm-nas`, `evolution` | [解析](parsed/2023-neurips-evoprompting.md) · [PDF](pdfs/2302.14838-evoprompting.pdf) | 核对搜索预算与消融表格 |
| codex_draft | [LLMatic: Neural Architecture Search via Large Language Models and Quality Diversity Optimization](https://arxiv.org/abs/2306.01102) | 2024/GECCO | `llm-nas`, `evolution` | [解析](parsed/2024-gecco-llmatic.md) · [PDF](pdfs/2306.01102-llmatic.pdf) | 对比 QD archives 与 Pareto 前沿 |
| codex_draft | [NADER: Neural Architecture Design via Multi-Agent Collaboration](https://arxiv.org/abs/2412.19206) | 2024/arXiv | `llm-nas` | [解析](parsed/2024-arxiv-nader.md) · [PDF](pdfs/2412.19206-nader.pdf) | 将图动作映射到 block/cell/op |
| codex_draft | [Data-Local Autonomous LLM-Guided Neural Architecture Search for Multiclass Multimodal Time-Series Classification](https://arxiv.org/abs/2603.15939) | 2026/arXiv | `llm-nas` | [解析](parsed/2026-arxiv-data-local-llm-nas.md) · [PDF](pdfs/2603.15939-data-local-llm-nas.pdf) | 核验两项数据集改进与退化结果 |
| codex_draft | [LLM-Guided Neural Architecture Search for Robust Co-Design of Physical Neural Networks](https://arxiv.org/abs/2606.10294) | 2026/arXiv | `llm-nas`, `pareto`, `hardware-aware` | [解析](parsed/2026-arxiv-uh-nas.md) · [PDF](pdfs/2606.10294-uh-nas.pdf) | 提取硬件目标与非理想性假设 |
| codex_draft | [MANAS: Multi-Agent Neural Architecture Search](https://arxiv.org/abs/1909.01051) | 2019/arXiv | `evolution` | [解析](parsed/2019-arxiv-manas.md) · [PDF](pdfs/1909.01051-manas.pdf) | 保留为非 LLM 多智能体基线 |
| codex_draft | [Using Large Language Models for Hyperparameter Optimization](https://arxiv.org/abs/2312.04528) | 2023/arXiv | `hpo` | [解析](parsed/2023-arxiv-llm-hpo.md) · [PDF](pdfs/2312.04528-llm-hpo.pdf) | 核对预算与 BO 对比 |
| codex_draft | [Large Language Model Agent for Hyper-Parameter Optimization](https://arxiv.org/abs/2402.01881) | 2024/CPAL | `hpo` | [解析](parsed/2024-cpal-agenthpo.md) · [PDF](pdfs/2402.01881-agenthpo.pdf) | 复用 observation/action 循环 |
| codex_draft | [Large Language Models to Enhance Bayesian Optimization](https://arxiv.org/abs/2402.03921) | 2024/ICLR | `hpo` | [解析](parsed/2024-iclr-llambo.md) · [PDF](pdfs/2402.03921-llambo.pdf) | 复用 LLM + BO 基线设计 |
| codex_draft | [AutoLLMResearch: Training Research Agents for Automating LLM Experiment Configuration](https://arxiv.org/abs/2605.11518) | 2026/arXiv | `hpo`, `transformer` | [解析](parsed/2026-arxiv-autollmresearch.md) · [PDF](pdfs/2605.11518-autollmresearch.pdf) | 核对多保真协议与成本估算 |
| codex_draft | [Hyperparameter Optimization for Large Language Model Instruction-Tuning](https://arxiv.org/abs/2312.00949) | 2023/AAAI | `hpo`, `transformer` | [解析](parsed/2023-aaai-instruction-tuning-hpo.md) · [PDF](pdfs/2312.00949-llm-instruction-tuning-hpo.pdf) | 作为非 Agent HPO 基线 |
| codex_draft | [MLAgentBench: Evaluating Language Agents on Machine Learning Experimentation](https://arxiv.org/abs/2310.03302) | 2023/arXiv | `benchmark`, `hpo` | [解析](parsed/2023-arxiv-mlagentbench.md) · [PDF](pdfs/2310.03302-mlagentbench.pdf) | 将失败类型纳入 Agent 评测 |

## 状态定义

- `inbox`：已收集、尚未通读；
- `codex_draft`：已由 Codex 生成初稿、尚未完成人工证据核验；
- `reading`：正在阅读并填写笔记；
- `retained`：已提炼出可引用结论、局限和行动项；
- `reproduced`：已运行公开代码或重现关键实验。

每篇 retained/reproduced 论文都必须链接到对应笔记文件。优先记录与本仓库直接相关的内容：层次化搜索空间、Pareto 指标、训练参数公平性、LLM Agent 状态/动作，以及 NAS benchmark。
