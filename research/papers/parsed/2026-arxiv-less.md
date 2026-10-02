---
title: "LESS: Lightweight Evolutionary Supernet Search in Minutes"
authors: "Aviral Gandhi, Jinglue Xu, Jialong Li, Hitoshi Iba"
year: "2026"
venue: "arXiv:2610.01468v1"
paper_url: "https://arxiv.org/abs/2610.01468"
source_pdf: "https://arxiv.org/pdf/2610.01468"
parser: "Codex"
parsed_on: "2026-10-02"
status: codex_draft
tags: [nas, evolutionary, weight-sharing, cma-es, calibration, duplicate-control]
---

# LESS

> 本笔记基于 arXiv v1 PDF。LESS 不使用 LLM/Agent，作为传统 evolutionary NAS、candidate-conditioned calibration 与重复控制的邻接基线。

## 一句话结论

- LESS 用 CMA-ES 在离散 cell space 提案，并在每个候选评分前做同预算的 candidate-conditioned calibration；它主要改善“从已访问候选中选谁”，而不是显著发现更好的候选。
- 论文把 warmup/search、候选重复、fallback 与 search-time/peak memory 报得较清楚；但 DARTS 最终 600-epoch retraining 不计入 search cost，且作者给出的 GitHub URL 在本轮核验时不可访问。
- 证据位置：PDF pp.4–11、16–24，Algorithms 1–3、Tables 1–7。

## 搜索对象、预算与失败处理

- 搜索标准 cell genotype，训练 recipe、数据 split、supernet 和 evaluator 固定。先 warmup 25 epochs，再 search 60 epochs；每 epoch 12 个 proposals 加 incumbent，共 780 candidate evaluations/run。
- 解码后按 genotype 去重；proposal 尝试达到上限时走 deterministic fallback。最终用多个 calibrated signals 做 Borda ranking。
- NB201 共 24 个 paired CIFAR-10 seeds（16 initial +8 prospective）比较 K0/K6，CIFAR-100 与 ImageNet16 各 8 seeds；单张 RTX 4090。DARTS transfer 每数据集 3 个 search seeds，但 final retraining 仅 seed 123。
- K6 的 60-epoch search 共 4,680 次 calibration updates、23,400 次 hard-path forward/backward passes。NB201 unique genotypes 平均 124.9，K0 为 147；duplicate/fallback 机制有描述，但完整 proposal rejection ledger 未随代码公开。

## 核心结果与成本

| Claim | Result | Evidence locator | Confidence |
|---|---|---|---|
| NB201 搜索时间 | CIFAR-10/100/ImageNet16 约 409.1/408.9/453.1 秒 | PDF pp.7–9, Tables 1–3 | high |
| 选模改善大于探索改善 | K6 selected validation 提升 0.577pp，best-visited 仅提升 0.054pp | PDF pp.8–10 | high |
| CIFAR-10 结果 | K6 test accuracy 93.189±0.467 | PDF pp.7–9, Table 1 | high |
| 峰值显存 | DARTS search peak allocated memory 约 4.2 GiB | PDF pp.10–11 | medium-high |

- DARTS search 为约 43.5 分钟，但 600-epoch final retraining 被排除；端到端比较必须补算。无真实 latency、energy 或 deployment cost。
- 这是传统 NAS，不能支持 LLM policy 效果；价值在于 candidate fairness、duplication control、bounded retry 和多 seed 协议。
- 论文列出 `https://github.com/AviralGandhi/LESS`，本轮 `git ls-remote` 返回 repository not found，故代码和原始 ledger 暂不可复核。

## 与当前 AgenticNAS 的关系

- 可作为 evolutionary Pareto baseline 的协议参考：每个候选统一 evaluator 状态、显式去重、bounded attempts、fallback 与 paired seeds。
- 迁移时仍需加入真实多目标/Pareto、hypervolume、action validity、GPU-hours 和最终重训成本，并与 native/random mutation 统一预算。

## 链接

- 论文：https://arxiv.org/abs/2610.01468
- 代码：https://github.com/AviralGandhi/LESS （截至 2026-10-02 不可访问）
