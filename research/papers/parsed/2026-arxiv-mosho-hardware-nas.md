---
title: "MOSHO: A Native Discrete Shark-Inspired Metaheuristic for Hardware-Aware Neural Architecture Search"
authors: "Nazim Abdeerhmane Aouni, Zakaria Soualah Mohammed, Maroua Ogab, Nour El Imane Elbar, Rayane Rahmat Errahmane Smara, Billel Moussous, Adriane Anis Khaled, Malika Bessedik, Fatima Benbouzid-Si Tayeb, Hadjer Benmeziane"
year: "2026"
venue: "arXiv:2610.33358v1"
paper_url: "https://arxiv.org/abs/2610.33358"
source_pdf: "https://arxiv.org/pdf/2610.33358"
code_url: "https://github.com/Orama-team/orama-nas-framework"
parser: "Codex"
parsed_on: "2026-10-28"
status: codex_draft
tags: [nas, hardware-aware, pareto, discrete-search, archive, traditional-baseline]
---

# MOSHO

> 本笔记基于 arXiv v1 官方 PDF。MOSHO 不使用 LLM/Agent，归传统 hardware-aware NAS Pareto baseline。

## 搜索对象与算法

- 固定 NAS-Bench-201 macro skeleton、训练结果与 evaluator，搜索 4-node cell 的 6 条边，每边从 zero/skip/1×1 conv/3×3 conv/3×3 avg-pool 选一项，共 `5^6=15,625` architectures。目标为 validation accuracy 最大化和 device latency 最小化。（PDF pp.5–6）
- 六个 native discrete operators 直接编辑整数架构；archive 同时为 gene source、restart seed 和 improvement feedback。energy-regulated restart、5-iteration improvement window、budget progress 与 deferred crowding truncation 控制 exploration/exploitation。（PDF pp.7–10, Algorithm 1）
- 终止条件是 evaluation budget `B`；论文未单列 duplicate proposals、repeated lookups、invalid/OOM 或 retry。tabular space 本身保证每个编码可查，但不等于 proposal 唯一。

## 预算、硬件与结果

- 18 个 dataset×device contexts，预算 `1K/2K/5K/7K/10K/15K` evaluations，每 method/context 30 个固定 seeds。主比较为 15K evaluations，对 MOWSO、NSGA-II、ABC、Firefly、MOPSO；搜索运行在 Ryzen 7 5800H/32GB/RTX3060，但 objective 是预计算 table lookup。（PDF pp.11–13, 16）
- latency 来自 HW-NAS-Bench 对 EdgeGPU、EdgeTPU、Eyeriss、FPGA、Pixel 3、Raspberry Pi 4 的既有 measurements，不是本轮重新上机。主实验只做 accuracy+latency；三目标扩展另加 benchmark energy，未报告 peak memory。（PDF pp.11, 18, Table 4）
- 作者报告 18 contexts median nHV=0.9987、IGD+=0.0064、runtime=0.64s；NSGA-II nHV=0.9993，摘要给出其 runtime 17.72s。高质量与低算法 overhead 主要反映 deterministic lookup search，不含训练或真机测量成本。（PDF pp.16–17, Fig.6）

## 公平性与本仓库价值

- search evaluation budget 和 30 seeds 匹配，archive limit 对 MOWSO 设为 50；但 MOSHO hyperparameters 用一个 held-out context 做 Optuna tuning，完整 tuning trials/cost 未计入主 search budget。（PDF pp.12–14, Table 2）
- 可迁移：typed discrete operators、archive-improvement feedback、deferred archive truncation、budget-progress schedule 和精确 Pareto front 评测。
- 本仓库复现需换成 4–10 层 Conv1d typed space，并把 table lookup 替换为真实训练与 device latency/memory/energy；与 random/native evolution/stateless/memory-aware LLM 匹配 attempted、unique、trained、GPU/LLM/wall-time。
- 官方代码本轮可访问，`HEAD=bb885dc4262c2dbb8bfb6db6f263ea4a5e2cb4ef`；未运行。

## 检索与人工核验记录

- 官方 PDF：26 页，SHA-256 `a22a7f277296d90c83c0e6be7942935ac7fa069ce6b7dab3abb23cb330d91b5e`。
- [x] 搜索空间、预算、设备、Table 4 与主结果已核对
- [x] benchmark measurement 与本轮真机实测已区分
- [ ] 人工决定 `retained` / `discarded`
