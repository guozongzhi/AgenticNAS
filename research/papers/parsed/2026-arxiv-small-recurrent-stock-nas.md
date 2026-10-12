---
title: "Forecast Accuracy Is Not Trading Profit: Evolving Small Recurrent Networks for Stock Return Prediction"
authors: "Jonathan Chang, Zimeng Lyu"
year: "2026"
venue: "arXiv:2610.07825v1"
paper_url: "https://arxiv.org/abs/2610.07825"
source_pdf: "https://arxiv.org/pdf/2610.07825"
code_url: ""
parser: "Codex"
parsed_on: "2026-10-12"
status: codex_draft
tags: [nas, traditional-baseline, neuroevolution, recurrent-network, real-device, energy]
---

# Small recurrent stock NAS

> 基于 arXiv v1 的 8 页 PDF。方法不使用 LLM/Agent，只作为小型 recurrent NAS、CPU search 与真实 endpoint latency/power 的传统基线。

## 搜索对象、固定项与预算

- EXAMM 演化 recurrent topology：node type 可为 simple neuron、Delta-RNN、GRU、LSTM、MGU 或 UGRNN，允许 deep recurrent connections，mutation/crossover 改 nodes、edges、cell type 与 time skip。数据、六个输入 features、walk-forward split、10-epoch candidate training 与 validation MSE evaluator 固定，属于 NAS 而非 HPO（PDF pp.2–4）。
- 每 run 有 10 islands、每岛最多 10 genomes，生成并训练 10,000 genomes；mutation/intra-island/inter-island crossover 概率为 0.7/0.2/0.1。attempted=10,000，但 valid、duplicate、training failure、retry 和 early-stop 数量未报告（p.4）。
- 32-core 配置在 dual-socket AMD EPYC Milan node 上 CPU-only search，10,000-genome run 为 16.2±2.8 minutes、8.65 core-hours；8–128 ranks 的 total compute 为 8.26–9.88 core-hours（p.7, Table 9）。

## 结果与真机证据

- 四个 50-stock validation portfolios×2022–2024 中，作者报告 EXAMM mean information coefficient +0.0106、net return +11.02%、Sharpe +0.74、MDD -10.76%，优于列出的 linear/fixed-RNN/Transformer/mixing baselines；这些是特定金融数据与交易规则下的作者回测，且 portfolio construction 有 survivorship bias（pp.3、5–7, Tables 4–8）。
- 演化网络平均 66 weights；Raspberry Pi Zero 真机 latency 10.82 microseconds、throughput 100.5k/s、INA219 测得 power above idle 476.7 mW。该测量提供真实 endpoint latency+power，但未给每次 inference energy、peak memory 或 host search energy（p.7, Table 9）。
- baseline 训练使用 RTX 4090，而 NAS search 使用 CPU；论文没有统一 wall-time/energy budget，也没有 matched random/evolution alternative 或多 search-seed variance。搜索代码链接未在正文/metadata 中给出，复现材料缺失。

## 当前价值与局限

- 这是本轮最贴近“4–10 层小模型+真机”的传统 baseline，但搜索的是自由 recurrent graph，不是 4–10 层 Conv1d Transformer；也没有 LLM/memory-aware policy 或 Pareto/hypervolume。
- 可直接借鉴 CPU attempted-trial 预算、host search 与 endpoint inference 分账、真实 latency/power 采样。下一步需要补 peak memory、每 inference energy、duplicates/failures、多 search seeds 和 matched proposer budget。

## 链接

- 论文：https://arxiv.org/abs/2610.07825
