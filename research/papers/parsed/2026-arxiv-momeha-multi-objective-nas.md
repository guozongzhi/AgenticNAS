---
title: "Efficient Hessian-Free Methods for Multi-Objective Bilevel Optimization with Nonconvex Lower Level"
authors: "Yicong Jiang, Feihu Huang"
year: "2026"
venue: "arXiv:2608.12704v3"
paper_url: "https://arxiv.org/abs/2608.12704"
source_pdf: "https://arxiv.org/pdf/2608.12704"
parser: "Codex"
parsed_on: "2026-09-25"
status: codex_draft
tags: [nas, multi-objective, bilevel-optimization, darts, hypervolume, adjacent-baseline]
---

# MOMEHA / MB-MOMEHA

> 本笔记基于 arXiv v3 PDF。论文主贡献是多目标非凸双层优化；NAS 只是其中一个连续 DARTS 实验，且没有 LLM/Agent。

## 一句话结论

- 核心主张：MB-MOMEHA 用 Moreau-envelope reformulation、smooth Tchebycheff preference 和 momentum 做 stochastic multi-objective bilevel optimization，在 CIFAR-10 DARTS 搜索上报告更宽的 objective trade-off 和更高 2-objective hypervolume。
- 证据位置：PDF pp.1–14、46–49，Fig. 3、Figs. 11–12、Table 3。

## 搜索对象与固定变量

- 可变：DARTS normal/reduction cells 各 edge 的八类 operation soft weights；lower level 优化 network weights，upper level 优化 architecture parameters。
- 固定：CIFAR-10、1:1 train/validation split、3-cell `Normal-Reduction-Normal` search network、50 search epochs，以及 DARTS search space/大部分 hyperparameters（PDF pp.46–47）。
- 四个 objectives：validation loss、FLOPs loss、skip-connection density、pooling density；后两项是防止 parameter-free operation collapse 的 regularizers，不是 deployment metric。另做 validation loss + FLOPs 的 2-objective 对比（PDF pp.14, 46–47）。
- 属于 differentiable NAS；不是离散 attempted-candidate search，也不是训练 HPO。

## 优化闭环、停止与失败

- MB-MOMEHA 在 50 epochs 内交替更新 network weights 和 continuous architecture weights，并按给定 preference vector 探索 trade-off。
- 没有 proposal/feedback/reflection/memory Agent loop；没有 duplicate/retry 概念。invalid/OOM/divergence rate 未报告。
- WC-MHGD 在 meta-learning comparison 中被描述为未收敛；NAS experiment 还因 VRAM 限制用 finite difference 近似其 hypergradient（PDF pp.12, 47）。

## 预算、硬件与公平性

- NAS search budget：每种方法/偏好 50 epochs；attempted/valid/trained/evaluated discrete candidates 不适用，最终离散架构数量未报告。
- 单 NVIDIA RTX 4090，Python 3.12.11、PyTorch 2.5.1；NumPy/PyTorch/CUDA 等统一 seed=42（PDF p.41）。
- GPU-hours、wall time、峰值显存、energy、代码版本和运行费用未报告；只有单 seed，不能估计 search variance。
- 2-objective baselines：WC-MHGD、WC-penalty、MoCo；4-objective 图主要与 WC-MHGD/WC-penalty 比较。论文声明共享 DARTS space/hyperparameters，但没有报告各方法实际 GPU/time 成本是否匹配。

## 核心结果

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 2-objective Pareto set 的 HV 更高 | MB-MOMEHA 1.522；WC-MHGD 1.323；WC-penalty 1.216；MoCo 1.192 | three gradient baselines | PDF p.14, Fig. 3, Table 3 | high |
| 4-objective preference coverage 更宽 | validation/pooling objectives 上覆盖更广，其他 objectives 与 WC-MHGD 相近 | WC-MHGD, WC-penalty | PDF pp.47–49, Figs. 11–12 | medium |

## 复现性与局限

- 只报告 search-phase validation objectives，没有给最终 discretized architecture、从头训练后的 test accuracy、真实 latency、memory 或 energy。
- FLOPs 与 operation density 是 analytical/search regularizers，不是设备测量；不能作为硬件感知 Pareto 实证。
- 单 seed 且 reference point/归一化细节没有在主结果旁完整展开，HV 差异缺少方差或统计检验。
- 未报告公开代码；本轮没有复现，因此状态保持 `codex_draft`。

## 与当前 AgenticNAS 的关系

- 可借鉴 preference-conditioned multi-objective search 与 HV 报告，但它不提供 LLM proposal、action validity、duplication 或 archive-memory 证据。
- 当前仓库应继续保留 evolutionary Pareto baseline，并在相同离散 Conv1d Transformer space、真实 evaluator 和至少三 seeds 下比较；不要把连续 DARTS 的单 seed validation HV 直接迁移为 AgenticNAS 效果结论。

## 链接

- 论文：https://arxiv.org/abs/2608.12704
- 代码：未报告
