---
title: "Large Language Model-Guided Evolutionary Discovery of Native Neural Architectures for Spiking Sequence Modeling"
authors: "Ruoyu Zhao, Jiaqi Wu, Chenyu Zhu, Zhichao Lu"
year: "2026"
venue: "arXiv:2609.40258v1"
paper_url: "https://arxiv.org/abs/2609.40258"
source_pdf: "https://arxiv.org/pdf/2609.40258"
parser: "Codex"
parsed_on: "2026-10-02"
status: codex_draft
tags: [llm-nas, evolution, spiking, sequence-modeling, surrogate, novelty]
---

# LLM-Guided Evolutionary Discovery of Native Neural Architectures

> 本笔记基于 arXiv v1 PDF。下述数字为作者报告；论文承诺发布代码和架构程序，截至 2026-10-02 未找到官方仓库。

## 一句话结论

- 方法以 20 个专家 SNN 为初始 archive，让 Gemini-2.5-Flash 生成开放式代码和 rationale，用 21 维 fingerprint、TabPFN fitness surrogate、novelty 与 island/NSGA-II 选择推进搜索；这是开放式 LLM-driven NAS/NAD。
- 最重要的审计结论是主搜索只做 1 次，且搜索期直接使用 ListOps test split 作为 fitness；因此其漂亮的下游结果不能当作无泄漏、等预算的稳健证据。
- 证据位置：PDF pp.5–11、19–25、28–29，Tables 2、8–10。

## 搜索对象、Agent 闭环与停止

- 可变对象是可执行 spiking sequence-model architecture，包括神经动力学、门控、状态更新和连接；任务 wrapper、输入输出 contract、训练协议固定。Agent 产出代码与设计 rationale，不是 typed mutation。
- archive 保存 code、rationale、fingerprint、fitness 与 novelty；LLM 根据父代和 archive 生成候选，执行筛查移除非法代码和近重复，再用 surrogate/novelty 与 island selection 选评估对象。
- 主配置 10 个 outer iterations、每轮 batch 16、总训练 evaluation budget 160。Table 8 写每轮 1,080 个 accepted candidates；正文同时报告约 49% acceptance、每轮超过 2,000 次 LLM calls。具体 reject taxonomy 未完整给出。

## 预算、成本与失败

- 去重后共训练 151 个新架构；每个架构在 WikiText-2 训练 30 epochs，并在约三分之一 ListOps 训练 25 epochs。作者折算总计 3,171 V100 GPU-hours（约 132 GPU-days），不含 20 个 seed experts、下游重训和 LLM inference。
- generation 上限为 32,768 tokens；论文没有报告实际 input/output token 总量、API 费用、端到端墙钟、OOM/divergence 分项或每轮 duplicate 数。
- energy 是基于 SOP/MAC 次数和 Horowitz 常数的算术估计，不是真机功耗。作者报告相对 dense Transformer 约 17–51×、LoopMem 50.6× 的估计能耗降低；无真实 latency、peak memory 或 device energy。

## 核心结果与证据风险

| Claim | Result | Evidence locator | Confidence |
|---|---|---|---|
| 搜索规模 | 151 个新架构完成训练，折算 3,171 V100 GPU-hours | PDF pp.20–25, Tables 8–10 | high |
| 下游语言建模 | NeuroGate 在 WikiText-103 报 PPL 26.4，表中 ANN DeltaNet 为 27.5 | PDF pp.8–10, Table 2 | medium |
| 候选接受率 | accepted 约 49%，每轮 LLM calls 超过 2,000 | PDF pp.20–23, Table 8 | medium-high |

- 搜索期 WikiText-2 使用 validation fitness，但 ListOps 使用 LRA test split；下游 ListOps 又在同一 test split 汇报，构成明确的 test-feedback/generalization 风险。
- 主搜索单 run；部分小型消融有重复，但不能替代完整搜索 seed variance。
- 表中外部 baseline 混合引用值和本地协议，训练预算与模型规模并非统一。

## 与当前 AgenticNAS 的关系

- archive 同时存 code/rationale/fingerprint/result，适合作为 memory-aware policy 的邻接设计；novelty 与近重复筛查也直接对应 duplication control。
- 复现时应使用 validation-only fitness、typed Conv1d action space、至少 3 个 search seeds，并统一 random/native/stateless/memory-aware 的 attempted、valid、trained、GPU 和 LLM 预算。

## 链接

- 论文：https://arxiv.org/abs/2609.40258
- 代码：作者声明未来发布；截至 2026-10-02 未找到官方仓库
