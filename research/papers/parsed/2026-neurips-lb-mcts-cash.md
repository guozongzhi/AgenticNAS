---
title: "Tree-Structured Synergy of Large Language Models and Bayesian Optimization for Efficient CASH"
authors: "Beicheng Xu, Weitong Qian, Lingching Tung, Yupeng Lu, Bin Cui"
year: "2026"
venue: "NeurIPS 2026 / arXiv:2601.12355v3"
paper_url: "https://arxiv.org/abs/2601.12355"
source_pdf: "https://arxiv.org/pdf/2601.12355"
code_url: "https://github.com/PKU-DAIR/open-box"
parser: "Codex"
parsed_on: "2026-10-23"
status: codex_draft
tags: [automl-agent, cash, mcts, bayesian-optimization, memory, reflection]
---

# LB-MCTS

> 本笔记基于 arXiv v3 的 46 页 PDF。论文已声明接收于 NeurIPS 2026；它搜索算法族及其超参数，属于 CASH / MLE Agent 邻接证据，不是神经架构搜索，也不是固定目标架构的训练 HPO。结果均为作者报告，未在本仓库运行。

## 搜索对象与闭环

- 搜索空间先在 8 个机器学习算法间选择，再进入算法专属的 45（分类）或 46（回归）维条件超参数空间；数据、60/20/20 划分与评价器固定。改变算法族意味着它不能直接支撑 fixed-architecture HPO。（PDF pp.7–8）
- MCTS 根层分配算法预算，算法子树内由 GP-BO proposer 与 LLM proposer共同提案。LLM 读取基础配置、算法专属历史、全局 Pareto 高表现试验和当前祖先轨迹；每次评估后产生 reflection，并回传树统计。（pp.3–7）
- 系统根据 GP 交叉验证的 Kendall tau 动态改变 BO/LLM proposer 概率；预算耗尽后停止。没有独立的真实硬件目标或 Pareto 多目标搜索。

## 预算、证据与公平性

- 104 个 AMLB 数据集（71 classification、33 regression），每个方法每数据集评估 300 个配置；比较 SMAC、OptDivBO、Rising Bandit、MOSAIC、OPRO、LLAMBO、BOPRO、BORA。LLM 方法统一使用 `gpt-4o-mini-2024-07-18`，BO 部分基于 OpenBox 0.8.1。（p.7）
- Figure 3 的作者结果：LB-MCTS 最终 validation average rank 2.16，第二名 Rising Bandit 为 3.49；validation-best 配置在 test set 的平均 rank 为 3.05。（pp.7–8）
- Appendix 成本分析给出约 **US$0.127/task** 的 API cost；正文没有报告 exact input/output tokens、总 LLM calls、GPU-hours 或能耗。不同数据集单次评估耗时不同，论文以 300 次 evaluation 对齐，因而不是 wall-time 对齐。（p.8）
- 论文没有完整列出 attempted、合法、训练成功、OOM/divergence、duplicate 与 retry 总账本；因此 300 evaluated configurations 不能替代 end-to-end attempt budget。

## 复现与边界

- 代码链接本轮可访问，`HEAD=2ab34cc01dd8b790f1c5273b436981cdedddb493`；未运行代码。PDF 为 46 页，SHA-256 `ea23340e9f3795813e0a12b3a8aa67aae010a6611db1bcdf38974f1ba1d16a17`。
- 没有 Conv1d、真实 latency、peak memory、energy 或设备 Pareto 证据。最可迁移的是算法专属短期记忆、祖先轨迹、反思及基于 surrogate 可靠度的 proposer 切换；若迁移到 NAS，必须固定 typed architecture space 并记录 attempted/valid/trained/duplicate/retry。
- 论文讨论理论收敛与条件预算比较，但依赖有限时间 BO regret、树分配和误排序预算等假设；不能把名义预算式理解为实测 hitting-time 比率。

## 可引用摘要

Xu 等提出 LB-MCTS，以树结构分离算法选择与算法内 HPO，并在每个子树中结合 GP-BO、LLM reflection 与轨迹相关记忆。作者在 104 个 AMLB 数据集、每方法 300 次配置评估下报告 validation average rank 2.16。由于搜索对象包含算法族且仅匹配 evaluation count，结果应作为 CASH/MLE Agent 的邻接证据，而非固定架构 HPO 或 NAS 的直接结论。
