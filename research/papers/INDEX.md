# NAS 论文阅读索引

| Status | Paper | Year/Venue | Tags | Note | Next action |
|---|---|---|---|---|---|
| inbox | [EvoPrompting: Language Models for Code-Level Neural Architecture Search](https://arxiv.org/abs/2302.14838) | 2023/arXiv | `llm-nas`, `evolution` | [PDF](pdfs/2302.14838-evoprompting.pdf) | Extract its mutation/crossover protocol |
| inbox | [LLMatic: Neural Architecture Search via Large Language Models and Quality Diversity Optimization](https://arxiv.org/abs/2306.01102) | 2023/arXiv | `llm-nas`, `evolution` | [PDF](pdfs/2306.01102-llmatic.pdf) | Compare QD archives with the Pareto frontier |
| inbox | [NADER: Neural Architecture Design via Multi-Agent Collaboration](https://arxiv.org/abs/2412.19206) | 2024/arXiv | `llm-nas` | [PDF](pdfs/2412.19206-nader.pdf) | Map graph actions to block/cell/op |
| inbox | [Data-Local Autonomous LLM-Guided Neural Architecture Search for Multiclass Multimodal Time-Series Classification](https://arxiv.org/abs/2603.15939) | 2026/arXiv | `llm-nas` | [PDF](pdfs/2603.15939-data-local-llm-nas.pdf) | Review the data-local controller boundary |
| inbox | [LLM-Guided Neural Architecture Search for Robust Co-Design of Physical Neural Networks](https://arxiv.org/abs/2606.10294) | 2026/arXiv | `llm-nas`, `pareto`, `hardware-aware` | [PDF](pdfs/2606.10294-uh-nas.pdf) | Extract hardware-aware objectives |
| inbox | [MANAS: Multi-Agent Neural Architecture Search](https://arxiv.org/abs/1909.01051) | 2019/arXiv | `evolution` | [PDF](pdfs/1909.01051-manas.pdf) | Record the non-LLM historical baseline |
| inbox | [Using Large Language Models for Hyperparameter Optimization](https://arxiv.org/abs/2312.04528) | 2023/arXiv | `hpo` | [PDF](pdfs/2312.04528-llm-hpo.pdf) | Extract its budget and BO comparison |
| inbox | [Large Language Model Agent for Hyper-Parameter Optimization](https://arxiv.org/abs/2402.01881) | 2024/arXiv | `hpo` | [PDF](pdfs/2402.01881-agenthpo.pdf) | Specify the observation/action loop |
| inbox | [Large Language Models to Enhance Bayesian Optimization](https://arxiv.org/abs/2402.03921) | 2024/arXiv | `hpo` | [PDF](pdfs/2402.03921-llambo.pdf) | Reuse its LLM plus BO baselines |
| inbox | [AutoLLMResearch: Training Research Agents for Automating LLM Experiment Configuration](https://arxiv.org/abs/2605.11518) | 2026/arXiv | `hpo`, `transformer` | [PDF](pdfs/2605.11518-autollmresearch.pdf) | Extract the multi-fidelity protocol |
| inbox | [Hyperparameter Optimization for Large Language Model Instruction-Tuning](https://arxiv.org/abs/2312.00949) | 2023/arXiv | `hpo`, `transformer` | [PDF](pdfs/2312.00949-llm-instruction-tuning-hpo.pdf) | Record the non-Agent HPO baseline |
| inbox | [MLAgentBench: Evaluating Language Agents on Machine Learning Experimentation](https://arxiv.org/abs/2310.03302) | 2023/arXiv | `benchmark`, `hpo` | [PDF](pdfs/2310.03302-mlagentbench.pdf) | Extract evaluation tasks and failures |

## 状态定义

- `inbox`：已收集、尚未通读；
- `reading`：正在阅读并填写笔记；
- `retained`：已提炼出可引用结论、局限和行动项；
- `reproduced`：已运行公开代码或重现关键实验。

每篇 retained/reproduced 论文都必须链接到对应笔记文件。优先记录与本仓库直接相关的内容：层次化搜索空间、Pareto 指标、训练参数公平性、LLM Agent 状态/动作，以及 NAS benchmark。
