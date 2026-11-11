---
title: "AutoCompress: Automated Hardware-Guided Model Compression"
authors: "Sheldon Liang, Ali Taghibakhshi, Saurav Muralidharan, Sharath Turuvekere Sreenivas, Ashwath Aithal, Pavlo Molchanov, Nima Tajbakhsh"
year: "2026"
venue: "arXiv:2611.08290v1"
paper_url: "https://arxiv.org/abs/2611.08290"
source_pdf: "https://arxiv.org/pdf/2611.08290"
parser: "Codex"
parsed_on: "2026-11-11"
status: codex_draft
tags: [nas, differentiable-search, pruning, hardware-aware, real-device, peak-memory, traditional-baseline]
---

# AutoCompress

> 本笔记基于 arXiv v1 官方 PDF。标题中的 LLM 是被压缩模型，不是 proposer；方法不使用 LLM Agent，归传统 differentiable architecture search / compression baseline。

## 一句话结论

- AutoCompress 用 differentiable router + weight-sharing supernet 联合搜索 global hidden size、Mamba heads、逐层 MoE experts/FFN widths 与 layer removal，并用目标 serving engine 的 latency/throughput/memory cost model 施加部署约束。（PDF pp.3–8, Figures 2–4, Table 2）
- RTX 5070/5080 的最终学生实测满足 latency+memory 约束；8×H100 满足 throughput 目标。作者报告 matched recovery 下 Avg8 高于 Minitron++，但搜索规模极大且没有多 search seeds 或 energy 结果。（PDF pp.9–12, Table 3, Figures 5/11–12）

## 搜索对象、固定项与停止机制

- 可变结构包括 global hidden size、Mamba heads、逐层 routed experts、routed/shared FFN width 和 layer removal；attention layers 与 parent topology 的其余部分固定。Lightning/Nano 空间约 `2.37×10^42` / `1.20×10^52`。（PDF p.8, Table 2）
- router 的 soft masks 同时接受 distillation 与 budget gradients；250 steps 内温度退火，所有 gate leading probability≥0.95 时提取离散架构。三个主场景在 step 170/249/179 收敛。（PDF pp.4, 8）
- 不是 proposal-feedback Agent loop；没有 reflection/archive。invalid/OOM/duplicate/retry 未报告，约束违反由 continuous budget penalty 处理。

## 部署测量、预算与结果

- 场景：RTX 5070 latency≤750 ms/memory≤4.0 GiB；RTX 5080 latency≤11.5 s/memory≤13.96 GiB；8×H100 throughput≥7,330 tok/s/GPU。（PDF p.7, Table 1）
- cost model 用真实 serving-engine layer profiles；held-out architecture median error 为 latency 0.6%/1.7%、H100 throughput 1.6%。profiling 成本分别为 4.5、3.5、24.8 GPU-hours。（PDF pp.18–19, Figure 11, Table 4）
- AutoCompress 实测 RTX 5070 为 739.7 ms/3.93 GiB，RTX 5080 为 11.1 s/13.61 GiB；8×H100 throughput 达目标。search tokens 为 4.18B/2.85B/3.00B，对 Minitron++ 8.49B/8.57B/9.98B；recovery tokens matched。（PDF pp.9–10, Figure 5, Table 3）
- B200 case：120B→74B，128K context measured memory 178 GB；search 约 4B tokens，recovery 120B tokens，32 GB200 nodes/128 GPUs 约 64 h。因成本未跑 Minitron++。（PDF pp.10–11, Figure 6）

## 公平性、复现性与缺口

- Minitron++ 使用相同 deployment budgets 和 recovery data/schedule，但它只保留 uniform dimensions/all layers，搜索空间表达能力弱于 AutoCompress；不是完全相同 proposal space。（PDF pp.8–10）
- 只报告单次 architecture search；没有 search seed variance。B200 case 无 matched baseline，不能用作方法相对优势证据。
- profiling、search、recovery 的 GPU 使用有部分报告，但主三场景的完整 GPU-hours、wall time、energy、failure ledger 与代码仓库未给出。
- memory model 明确补 CUDA graph/prefill/runtime buffers；传统 parameter formula 会低估 31–43%，这对本仓库的真实 peak-memory gate 很重要。（PDF pp.18–20, Figure 12）

## 对本仓库的价值

- 归类：`传统 hardware-aware differentiable NAS`。可复用 target-engine profiling、held-out cost-model validation 与真实部署复测。
- 不可把 LLM compression 写成 LLM-guided NAS。typed Conv1d 仍需 evolution 与 Agent 在同一结构空间、真实 evaluator 和 attempted budget 下比较。
- 最小复现应加入 energy，记录 cost-model calibration runs、attempted/valid architecture、constraint violation、真实 measurement error、GPU-hours 与多 seed hypervolume。

## 检索与人工核验记录

- 官方 PDF：21 页，SHA-256 `d715851aa010626a9de44ab4f62ac6c927b822664d900c4731fb3173cd33abc1`；所有页可解析。
- 未发现作者官方代码链接；本轮未把论文模型成本写成仓库实测。
- [x] 实际结构变量与固定项已核对
- [x] Tables 1–4 与 Figures 5/6/11/12 已核对
- [x] measured / predicted / author-reported 已区分
- [ ] 人工决定 `retained` / `discarded`
