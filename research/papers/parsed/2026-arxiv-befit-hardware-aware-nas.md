---
title: "BeFit: Shifting Complexity from Weights to Bernstein Activations for Resource-Constrained Sensing"
authors: "Malak Gamal El-Din, Yasser Shoukry, Salma Elmalaki"
year: "2026"
venue: "arXiv:2611.23520v1"
paper_url: "https://arxiv.org/abs/2611.23520"
source_pdf: "https://arxiv.org/pdf/2611.23520"
parser: "Codex"
parsed_on: "2026-11-23"
status: codex_draft
tags: [nas, mixed-search-space, hardware-aware, time-series, microcontroller, real-device]
---

# BeFit

> 本笔记基于 arXiv v1 官方 PDF。BeFit 不使用 LLM；搜索同时包含 architecture、Bernstein degree 与 learning rate，故严格归为传统 `mixed-search-space / hardware-aware NAS`，不是固定 recipe NAS。

## 搜索空间、固定变量与测量

- HAR CNN 搜索 dilation groups、filters、kernel、stride、normalization、learning rate、Bernstein degree 与 coefficient-lr multiplier；DS-CNN 搜索最多 5 个卷积层的 width、首层 kernel/stride、last-activation curves、learning rate 和 degree。（PDF pp.3, 8, Table 4）
- multi-objective TPE 近似 validation accuracy、instructions、flash、RAM 的 Pareto front；flash/RAM 来自搜索前真实编译的 cost table，instructions 来自与目标 binary 一致的 QEMU image。训练 recipe、数据划分和目标 MCU 固定，但 learning rate 仍在搜索内。（PDF pp.3–4）
- 目标板为 TI CC3220SF、80 MHz Cortex-M4、256 KiB RAM、1 MiB flash。latency 用 board cycle counter 对 seed-0 模型至少 100 个输入取 median；RAM 包含 static data 与 peak stack，flash 包含 model+runtime。（PDF p.7）

## 预算、公平性与结果

- 每 trial 从头训练 60 epochs、单 seed，在 epochs 7/20 pruning。HAR Bernstein/ReLU 各 500/300 trials，DS-CNN 各 200/150；Bernstein 因额外维度获得更多 trial，因此不是相同 attempted-trial budget。（PDF p.8）
- non-dominated rank≤2 候选再补 2 seeds，以 3-seed validation mean 重建 front。训练使用 A30/V100/A100，但论文未报告每个 search/全部实验的 GPU-hours 或墙钟。（PDF pp.4, 7）
- 与 MLPerf Tiny DS-CNN 相比，作者报告 BeFit-dense 高 1.0pp、latency 低 2.2×、flash 低 6.4×；projected 版本低 1.0pp、latency 低 5.9×、flash 低 2.3×、RAM 低 1.5×。这是作者真机结果，不是本仓库测量。（PDF p.7）
- invalid/OOM/divergence/duplicate/retry 和被 successive-halving 提前停止的完整计数未报告。energy 没有实测；论文明确列为 future work。RISC-V 无乘法器结果来自 emulation，不是真机。（PDF pp.15–16）

## 复现缺口与课题价值

- 论文未给出作者代码仓库；2026-11-23 未识别到官方实现。
- 对本课题可复用的是“先编译测量 cost table，再搜索 Pareto”的真机协议，以及 single-seed 初筛后 3-seed 重建 front。迁移时必须把 learning rate 从 architecture search 中移出，并为 random/evolution/Agent 使用相同 attempted trials。
- BeFit 的 HAR 网络是 1D sensing CNN，不是 4–10 层 Conv1d Transformer；其 transformer 扩展也不是本轮 NAS 主搜索对象。
- 官方 PDF：16 页，SHA-256 `a0baf322153489e5c27f027dd1d1fe25caf052516c2f7a0cae90f67a9774bb58`。

- [x] 真机 latency/RAM/flash 协议已核对
- [x] mixed search 与不等 trial budget 已标记
- [ ] 人工决定 `retained` / `discarded`
