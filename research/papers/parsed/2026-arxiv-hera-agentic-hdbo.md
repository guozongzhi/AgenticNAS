---
title: "Agentic High-Dimensional Bayesian Optimization with Hypothesis- and Evidence-Guided Search"
authors: "Zhixuan Gao, Ke Xue, Rongxi Tan, Ming Chen, Chao Qian"
year: "2026"
venue: "arXiv:2609.34281v1"
paper_url: "https://arxiv.org/abs/2609.34281"
source_pdf: "https://arxiv.org/pdf/2609.34281"
parser: "Codex"
parsed_on: "2026-10-02"
status: codex_draft
tags: [agentic-bo, high-dimensional, hybrid, strategy-selection, memory]
---

# Agentic High-Dimensional Bayesian Optimization with Hypothesis- and Evidence-Guided Search

> 本笔记基于 arXiv v1 PDF 与其官方 source package。HERA 是通用高维黑箱优化，不是固定架构 HPO 或 NAS；作者结果不是本仓库实测。

## 一句话结论

- HERA 用 LLM 作为策略控制器，在 Vanilla BO、LassoBO、ALEBO-like、Add-GP-UCB 与 TuRBO 之间选择、重构或重启；PRISM 负责合法候选生成，并将每次 observation 写入共享历史。
- 它展示了“Agent 决策层 + classical optimizer backend + evidence memory”的可迁移结构，但 12 个任务包含控制、芯片、分子 latent 等通用黑箱，不能直接支持本仓库 fixed-architecture HPO 结论。
- 证据位置：PDF pp.3–13、17–22，Figures 2–7、Tables 1–3。

## 搜索对象、闭环与固定项

- LLM 根据假设、历史 observation、backend 状态和文本 metadata，决定使用哪个 BO backend、子空间/重启策略以及 1–50 的 block length；PRISM 生成候选并校验 bounds、constraints 与 duplicate。
- 所有方法每个任务 100 次 objective evaluations，其中 5 个共享 scrambled Sobol 初始点；4 个 synthetic metadata-free tasks 和 8 个 real-world tasks 各跑 10 seeds。
- 主控制器为 DeepSeek-V4.1-Flash、temperature 0。LLAMBO、Centaur、Sara 与 HERA 使用同样 task wrapper、budget 和 opening points；classical baseline 不读取自然语言 metadata，因此比较的是完整系统而非纯策略模块。

## 预算、成本和失败

- 主实验共 4 个 LLM methods × 8 个 real-world tasks × 10 seeds = 320 个 LLM-agent campaigns；每个 campaign 100 attempted evaluations。
- HERA 的 token 总量在比较方法中最高，但 prompt cache hit 为 94%；LLAMBO/Centaur/Sara 分别为 16.4%/27.3%/36.2%。论文没有汇总 USD、墙钟、GPU/CPU 成本。
- PRISM 会拒绝越界、约束不满足和重复点，但论文未给各类 invalid/retry 分母；objective failure、OOM/divergence 不适用于所有任务，也未统一成 trial ledger。

## 核心结果与局限

| Claim | Result | Evidence locator | Confidence |
|---|---|---|---|
| Synthetic | 与经典高维 BO 竞争，但没有在所有函数/维度稳定领先 | PDF pp.8–10, Figs. 3–4 | medium-high |
| Real-world | 对 strongest classical baseline 在 8 个任务中 6 个取得最佳 mean；对其他 LLM agents 为 7/8 | PDF pp.10–12, Figs. 5–6 | medium |
| 结构证据 | ablation 改变 backend/strategy 使用分布，但 aggregate optimization 优势并非所有任务都清晰 | PDF pp.12–13, Fig. 7 | medium |

- seed variance 较大，metadata 的帮助依任务而异；没有固定架构 ML HPO 专门实验。
- 作者声称代码在 supplemental files，但本轮下载的官方 arXiv source package 只有论文源文件和图，没有可运行实现；网页检索也未找到官方仓库，故复现材料仍缺失。

## 与当前 AgenticNAS 的关系

- 可借鉴共享 observation memory、后端切换和 duplicate validation，但 HERA 的策略动作不是 neural architecture mutation。
- 若用于 HPO track，必须固定 architecture/data/evaluator，按 attempted trials 比较 random、TPE、CMA-ES、pure LLM 和 hybrid，并分别报告失败、tokens、wall-time 与计算成本。

## 链接

- 论文：https://arxiv.org/abs/2609.34281
- 代码：论文称随 supplemental 提供；截至 2026-10-02 官方 source package 中未见实现
