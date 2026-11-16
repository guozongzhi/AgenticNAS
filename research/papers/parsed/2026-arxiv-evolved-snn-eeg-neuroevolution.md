---
title: "Evolved Spiking Neural Networks for EEG Seizure Detection: Calcium Dynamics and Delay Mechanics"
authors: "Tuba Aksoy"
year: "2026"
venue: "arXiv:2611.03841v1"
paper_url: "https://arxiv.org/abs/2611.03841"
source_pdf: "https://arxiv.org/pdf/2611.03841"
code_url: "available on reasonable request"
parser: "Codex"
parsed_on: "2026-11-16"
status: codex_draft
tags: [nas, neuroevolution, spiking-neural-network, eeg, traditional-baseline]
---

# Evolved Spiking Neural Networks for EEG Seizure Detection

> 本笔记基于 arXiv v1 官方 PDF。这是传统 neuroevolution NAS，不使用 LLM/Agent。

## 搜索空间与预算

- EONS 同时演化 network topology、weights、neuron thresholds、calcium parameters 与 synaptic delays；数据预处理和 fitness protocol 固定。初始 population 100、30 generations，个体初始为 30 hidden neurons/30 synapses。（PDF pp.3–6）
- 每个实验臂做 20 次独立 runs。可粗记为每 run 30 个 population fitness cycles、名义上 `100×30` 个体评估，但论文没有给出去重后的 unique architectures、初始代是否额外计费或 invalid/failed 数，不能写成精确 3,000 次有效训练。

## 结果与边界

- CHB-MIT 的 10 个 held-out subjects 中，Ca-IFneu 的 MCC 从 0.592 升至 0.726，adjusted `p=.025`，FPR 从 0.17 降至 0.10；演化 1–3 tick delays 的 MCC 为 0.703，adjusted `p=.024`。（PDF pp.7–10）
- 在 inference 时移除或打乱 calcium state 没有显著改变结果，支持其作用更像 search-path mechanism，而不是部署时必须保留的机制。
- Siena split 的两个增益分别约 0.059（unadjusted `p=.052`，不显著）和 0.096（adjusted `p=.021`）；cross-cohort 结果不显著，不能概括成跨数据集稳定优势。（PDF pp.10–12）
- 实验仅为软件仿真，没有 neuromorphic device latency、energy、peak memory；GPU/CPU 型号、GPU-hours、wall-time、失败/OOM/duplicate 和重试成本未报告。

## 复现与课题价值

- 代码只注明“available on reasonable request”，本轮没有可核验公开 commit。适合作为 topology+mechanism 联合演化的传统基线，但必须和固定 recipe、相同 population evaluation budget 的 random/evolution 对照。
- 官方 PDF：16 页，SHA-256 `30f1602476ef1878a8a3555542b76d682070b64426e1bc9ba0aff9acc7bb7c34`。

- [x] population、generations、重复次数与统计显著性已核对
- [x] 软件仿真与真实硬件边界已区分
- [ ] 人工决定 `retained` / `discarded`
