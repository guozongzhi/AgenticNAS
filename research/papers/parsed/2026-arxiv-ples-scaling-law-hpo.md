---
title: "Efficiently Estimating Optimal Hyperparameter Scaling Laws through Power-Law Entropy Search"
authors: "Zhiliang Chen, Sebastian Ament, David Eriksson, Maximilian Balandat, Bryan Kian Hsiang Low, Eytan Bakshy, Jihao Andreas Lin"
year: "2026"
venue: "arXiv:2609.01431v3"
paper_url: "https://arxiv.org/abs/2609.01431"
source_pdf: "https://arxiv.org/pdf/2609.01431"
code_url: "not found"
parser: "Codex"
parsed_on: "2026-10-23"
status: codex_draft
tags: [mixed-search-space, bayesian-optimization, scaling-law, multi-fidelity, baseline]
---

# PLES

> 本笔记基于 arXiv v3 的 14 页 PDF。PLES 是传统 BO 方法，不使用 LLM/Agent；真实语言模型实验同时改变模型规模、数据量和学习率，归 `mixed-search-space` 基线。

## 搜索对象与方法

- 候选为 `(N,D,theta)`：模型参数规模 `N`、训练 token 数 `D` 与待调超参数 `theta`。真实 LLM 实验通过层数和 intermediate hidden dimension 改变 9.4M–600M 参数规模，`D` 为 199.8M–12B tokens，学习率为 `1e-4`–`0.1`；固定一 epoch、global batch 2048、sequence length 2048。（PDF pp.6–8）
- PLES 对 power-law scaling law 的最优超参数后验做 entropy search，按 `(ND)^d` 近似计算成本选择信息增益最大的候选；后验不确定性提供自然停止信号。没有 proposal-feedback reflection、LLM memory 或 Agent loop。

## 预算与结果

- 基线为 grid search、ladder BO（EI）与 Sobol；在相同累计 `ND` compute 下比较，并报告 10 个随机种子。（pp.6–9）
- 作者在 Figure 4 报告，PLES 用不到 grid-search 总预算的十分之一即可接近可达到的最低 loss 并定位最优超参数；多数查询点成本低于 held-out full-scale run 的 6%。（pp.7–9, Fig.4/7）
- 论文没有把 `ND` proxy 换算为 GPU-hours、实际 accelerator、wall-time、peak memory、energy 或美元成本，也没有 attempted/failed/OOM/duplicate ledger。因而预算是模型化 compute proxy，不是完整实测成本。

## 边界与复现价值

- 同时改变 depth、intermediate width、训练 token fidelity 和 learning rate，不可把结果写成固定架构 HPO；可作为“规模—数据—超参联合规划”的 mixed baseline。
- 方法依赖预设 power-law functional form；当低保真观测不遵循该形式时，后验和停止判断都可能失真。代码链接未在论文 metadata 中发现。
- PDF 为 14 页，SHA-256 `a9e5798dbb932d38208c680f373f5cb2a73ba505cedc8124394104499dbb3f1b`。没有 Conv1d、真机 Pareto、memory 或 energy 证据。

## 可引用摘要

Chen 等提出 PLES，通过对最优超参数 scaling law 的信息增益选择不同模型规模、数据量与超参数的训练点。作者报告在十个种子下，以不足 grid-search 十分之一的代理计算预算接近最优结果。由于真实实验同时改变网络层数、宽度、数据 fidelity 与学习率，且成本仅以 `ND` proxy 表示，该证据属于 mixed-search-space BO，而非固定架构 HPO。
