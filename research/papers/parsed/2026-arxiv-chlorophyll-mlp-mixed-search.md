---
title: "Evolutionary Architecture Search for Chlorophyll-a Prediction in Lakes using Sentinel-2"
authors: "Kursat Komurcu, Linas Petkevicius"
year: "2026"
venue: "AutoML4EO 2026 workshop; arXiv:2610.10496v1"
paper_url: "https://arxiv.org/abs/2610.10496"
source_pdf: "https://arxiv.org/pdf/2610.10496"
code_url: "https://github.com/VU-AIML/automl4eo-bloom-nas"
parser: "Codex"
parsed_on: "2026-10-12"
status: codex_draft
tags: [nas, mixed-search-space, evolutionary-search, tiny-mlp, edge]
---

# Chlorophyll-a MLP mixed search

> 基于 arXiv v1 的 4 页正文加参考文献、AutoML4EO 接收说明和作者仓库核验。方法不使用 LLM；由于同时改变结构与训练 recipe，不能作为纯 NAS 或固定架构 HPO 证据。

## 搜索空间、协议与预算

- 结构变量包括 1–6 blocks、base width 16–256、width profile、五种 block type、heads、normalization、activation、dropout；训练变量同时包括 optimizer、learning rate、schedule、warm-up、weight decay、batch、epochs、label smoothing、class weighting、gradient clipping、EMA。约 `10^12` configurations，明显属于 mixed-search-space（PDF pp.2–3, Table 1）。
- regularized evolution 以 64 个随机 population 起步，每轮产生 20 children，tournament size 10，每个 child 编辑 1–3 个 dimensions，按 age 淘汰。每个 candidate 用 5 folds×3 weight seeds；共 evaluated 2,720 candidates，折叠 inactive dimensions 后 1,827 distinct architectures，20 CPU cores 约 5 hours（p.3）。
- 训练/测试按 lake 分组，801 train/350 held-out test；search 只看 inner 5-fold CV AUC，test 在搜索结束后开启一次。最终候选以 10 weight seeds 报告，避免直接 test-feedback（pp.2–3）。

## 结果、重复与成本缺口

- 最佳候选 409–433 parameters；作者报告 test AUC 0.8181–0.8203，对比 strongest baseline 0.7902，accuracy 0.7449–0.7483 对比 0.7306–0.7329（p.3, Table 2）。前 100 名一致收敛到 single narrow layer、RMSprop、step decay、RMS normalization、tanh、EMA 和 class weighting（p.4）。
- attempted 2,720、distinct 1,827 提供了部分 duplication 信息，但 inactive-dimension collapse 之外的 canonical duplicate、invalid/rejected/OOM 未报告。作者明确指出 top-10 narrowly converge，未来需要 duplicate suppression/random reinjection（p.4）。
- 1.6 kB/约 400 MAC 是静态估计；没有代表性硬件上的 latency、peak memory 或 energy。作者仓库本轮 `HEAD=f27f935c2b00a3f2f57b1db81f2e8e20c4cf8099`，含 search code 与 JSON results，但本轮未运行。

## 当前价值与局限

- 对当前项目的价值是完整 attempted/distinct 口径、grouped split、inner-CV-only selection 和 CPU wall-time；但 structure/recipe 混合意味着结果不能转移为固定架构 HPO 或固定配方 NAS 的 policy 证据。
- 下一步应拆成 architecture-only 与 recipe-only 两轨，分别与 random/TPE/CMA-ES/evolution 做 matched attempted trials，并在真实设备测 latency/memory/energy。

## 链接

- 论文：https://arxiv.org/abs/2610.10496
- 代码：https://github.com/VU-AIML/automl4eo-bloom-nas
