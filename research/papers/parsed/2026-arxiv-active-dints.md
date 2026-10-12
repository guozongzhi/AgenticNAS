---
title: "Active-DiNTS: Active Differentiable Network Topology Search"
authors: "Gean Trindade Pereira, Thierry Urruty, Muriel Visani, Andre C. P. L. F. de Carvalho"
year: "2026"
venue: "arXiv:2610.04787v1"
paper_url: "https://arxiv.org/abs/2610.04787"
source_pdf: "https://arxiv.org/pdf/2610.04787"
code_url: "https://github.com/geantrindade/Active-DiNTS"
parser: "Codex"
parsed_on: "2026-10-12"
status: codex_draft
tags: [nas, active-learning, mixed-search-space, medical-imaging, peak-memory]
---

# Active-DiNTS

> 基于 arXiv v1 的 19 页 PDF 与作者仓库核验。方法不使用 LLM；它把 topology search 与样本标注选择耦合，作为 NAS×data-selection 邻接证据，而不是固定配方纯 NAS。

## 搜索对象与闭环

- macro space 为 12 layers×4 resolutions 的 encoder–decoder graph；micro space 在每条 edge 上选择 skip、3D convolution 或三种 P3D operators。连续 relaxation 结束后每条 edge 取最高概率 operator；训练 recipe、数据预处理和 evaluator 基本固定（PDF p.4）。
- 同时维护 weight-update pool 与 topology-update pool：每轮按 entropy/variance/std 选待标注 MRI volume，外层更新 weights，内层更新 architecture parameters。weights-only、topology-only、joint 三种 regime 同时改变“看到哪些标签”和结构更新路径，因此分类为 mixed data-selection/NAS，而非本仓库的 architecture-only NAS（pp.4–7）。
- 所有实验使用 RAM-density factor `sigma=0.8`，使 topology 偏密；query size、每 query epochs 和 warm-up 通过同一 5-fold CV grid search，存在额外 method-selection 成本但论文未汇总 grid 的 attempted runs（p.8）。

## 预算、结果与真实资源

- 单机 Intel Xeon Silver 4215、126 GB RAM、单 V100 32 GB。Table 3 报告 peak GPU memory 14.7–17.3 GB；最快达到 DiNTS(Pancreas)精度的 Variance checkpoint 为 0.21 GPU-days，对比论文引用的 DiNTS 5.8 GPU-days/8 V100（pp.8、13–14）。
- final Entropy/Variance/Std average Dice 为 77.83/77.40/77.77，DiNTS(Brain)为 72.97；但 Active-DiNTS FLOPs 为约 8,220–9,650 G，远高于 DiNTS 334 G，说明收益不是同等 inference-cost Pareto（pp.13–14, Tables 2–3）。
- baseline 数字来自原论文而未本地重跑，继承 preprocessing/post-processing 差异；作者也未做 fold significance tests。annotation budget 与 GPU budget 改善不能解释为严格 matched end-to-end compute 下的 topology policy 优势（pp.8、14）。
- attempted architectures、invalid/duplicate/OOM、energy、inference latency 与完整 wall-time 未报告。作者链接仓库本轮 `HEAD=6cd8b08f259ca7311f785794b4137d08d3628c7b`，但 API tree 仅有 README/LICENSE，公开实现存在复现缺口。

## 当前价值与局限

- 对当前方向最有价值的是把 peak memory、annotation acquisition 与 topology update 拆开记账，以及用 uncertainty-driven data selection检验 feedback 的信息价值。
- 它没有 LLM、Pareto archive、真实 endpoint latency/energy，也不是 Conv1d Transformer。若迁移，应固定 labeled set 或把 data acquisition 单列 objective/controller，避免将数据选择收益归因于 architecture proposer。

## 链接

- 论文：https://arxiv.org/abs/2610.04787
- 代码声明：https://github.com/geantrindade/Active-DiNTS
