---
title: "MCUFlowNet: Hardware-Aware Neural Architecture Search for Optical Flow on Microcontrollers"
authors: "Enmin Lin, Jona Beysens"
year: "2026"
venue: "arXiv:2611.08147v1; IEEE ISCAS 2027 under review"
paper_url: "https://arxiv.org/abs/2611.08147"
source_pdf: "https://arxiv.org/pdf/2611.08147"
parser: "Codex"
parsed_on: "2026-11-11"
status: codex_draft
tags: [nas, hardware-aware, pareto, microcontroller, peak-memory, real-device, traditional-baseline]
---

# MCUFlowNet

> 本笔记基于 arXiv v1 官方 PDF。PACE-NAS 不使用 LLM/Agent，归传统硬件感知 NAS 基线；作者数字不是本仓库实测。

## 一句话结论

- PACE-NAS 先用 macro redesign 把 peak SRAM 固定在 MCU tensor-arena 内，再以 weight-sharing supernet + NSGA-II 搜 operators/depth 的 EPE–latency Pareto；它把 memory feasibility 与 latency allocation 分开。（PDF pp.1–3, Figures 1–3）
- 在 Grove Vision AI V2/Ethos-U55 上，MCUFlowNet-S 作者实测 93.2 ms、peak SRAM 1170 KiB，对 retrained EdgeFlowNet 的 164.3 ms/1430 KiB；但 search 中 latency 和 SRAM 由 Vela 估计，energy 与端到端 host search cost 未报告。（PDF pp.3–4, Table III）

## 搜索对象、固定项与闭环

- macro 阶段人工确定 bilinear decoder、ECA 与 gate；micro 空间改变各 stage residual-block depth、3×3/5×5 operators。训练数据、loss、teacher、quantization/compiler 和 evaluator 固定，属于 NAS。（PDF pp.2–3）
- SPOS/FairNAS-style supernet 用 feature-alignment distillation；NSGA-II 以 inherited-weight FC2 validation EPE 与 Vela INT8 latency 评 800/23,328 subnets，得到 51 个 Pareto candidates 后只完整重训 S/L 两个。（PDF pp.2–3）
- proposal 是传统 NSGA-II，不使用 language model；archive 是 Pareto population。invalid、duplicate、compiler failure、OOM 与 retry 未报告。

## 评估、预算与真实测量

- supernet 200 epochs，NSGA-II 800 evaluations；作者估计合计 17 H200 GPU-hours，约半次完整 EdgeFlowNet training。最终模型另做 400 epochs FC2 + 10k/80k FT3D steps，未给最终重训 GPU-hours。（PDF p.3）
- search 用 Vela estimate；最终 INT8 latency 在 Grove Vision AI V2 上用 TFLM 实测，排除 image capture 和 pre/post-processing。部署模型实测 latency 与 estimate 偏差不超过 2.1%。（PDF pp.3–4）
- MCUFlowNet-S 相比 retrained EdgeFlowNet：EPE 6.50 vs 6.40，1170 vs 1430 KiB peak SRAM，93.2 vs 164.3 ms；194 个模拟飞行 trial success 51.5% vs 41.8%。（PDF p.4, Table III）
- segmentation 空间评 960/1.41M subnets；balanced variant 161.0 ms、mIoU 55.27±0.60，对 PIDNet-S 188.6 ms、55.23±0.55。（PDF p.4, Table IV）

## 公平性、复现性与缺口

- 同一训练 recipe 和 board 有利于结构比较，但 macro redesign 是人工先验；search 只在 proxy supernet 上评 candidates，最终只重训少数点。
- optical-flow decoder ablation 和 segmentation 最终训练各 3 seeds；NAS search seed 数、NSGA-II variance 和 final S/L 重训 seed 数未明确。
- peak SRAM 是 Vela estimate，不是运行时 trace；energy、flash、host CPU、完整 GPU/wall time、attempted/valid/duplicate ledger 未报告。
- 官方 GitLab 仓库于 2026-11-11 核验 HEAD `1281d7a29f79d3af214440f34093c76f8a64d487`；本轮未运行。

## 对本仓库的价值

- 归类：`传统 hardware-aware NAS`。可复用“macro 先闭合 memory feasibility、micro 再做 accuracy-latency Pareto”的两阶段协议，以及 estimate→board measurement 的校准检查。
- 不能把它作为 Agent policy 证据；也不能把 Vela SRAM/latency 全部写成实测。typed Conv1d 应让 evolution 与 Agent 使用同一 compiler/device evaluator。
- 最小复现需报告 4–10 层合法率、duplicate、800 attempted/valid/evaluated、search seeds、真实 latency/peak memory/energy、hypervolume 与完整 GPU/墙钟成本。

## 检索与人工核验记录

- 官方 PDF：5 页，SHA-256 `f96400e77852e1b864ab0a9640d3a0bd8a882018b2661baf31c5f8f025c107bf`；所有页可解析。
- [x] 搜索空间、800 evaluations 与 17 H200 GPU-hours 已核对
- [x] estimate 与 board measurement 已区分
- [x] Tables I/III/IV 主要数字已核对
- [ ] 人工决定 `retained` / `discarded`
