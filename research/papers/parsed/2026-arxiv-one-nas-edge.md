---
title: "Evolve on the Host, Predict on the Edge: Deploying Online Neuroevolutionary Architecture Search for Cross-sectional Stock Return Prediction"
authors: "Jonathan Chang, Zimeng Lyu"
year: "2026"
venue: "arXiv:2610.10038v1"
paper_url: "https://arxiv.org/abs/2610.10038"
source_pdf: "https://arxiv.org/pdf/2610.10038"
code_url: "https://github.com/zimenglyu/ONENAS"
parser: "Codex"
parsed_on: "2026-10-09"
status: codex_draft
tags: [nas, traditional-baseline, neuroevolution, recurrent-network, real-device, energy]
---

# ONE-NAS host-to-edge pilot

> 基于 arXiv v1 的 13 页 PDF与作者仓库。方法不使用 LLM/Agent，只作为在线 recurrent NAS、真实设备 latency/energy 与多 seed baseline。

## 搜索对象、协议与预算

- ONE-NAS 在线演化小型 recurrent genomes，mutation/crossover 改 graph、cell types 与 weights；每个新窗口在 host 更新 population，把 global champion 或 40 island champions 发送到 Raspberry Pi 4B 推理。结构与权重共同演化，不是固定架构 HPO（PDF pp.2–4）。
- 配置只在 2016–2019 tuning span 选择，2020–2024 不再更改；主要结果用 2022–2024、4 panels×10 seeds。每次 search 占一个 128-core Anvil CPU node；论文没有给累计 CPU-hours、wall-time、invalid/duplicate/OOM ledger（pp.4–5）。
- baseline 是 online LSTM/GRU、monthly-retrained LSTM 与 online AR，使用相同 prequential inputs/target/trading rules/costs，但不是 matched attempted-architecture budget（p.4）。

## 真机测量与结果

- Pi 4B 单 champion 对 50-stock window 为 24.6 ms；40-island ensemble 556.2 ms。energy 由 INA219 测 whole-board，并在每 run 开头量 idle；ensemble 约 1,652 mJ，其中 328 mJ 为 idle（pp.4–5、11, Tables 8–9）。
- 40-island ensemble 2022–2024 net return +27.5±1.1%，single champion +4.5%，online LSTM/GRU/monthly LSTM 为 +11.3% 至 +14.8%；这些是特定金融回测作者结果，不能外推为通用预测优势（pp.5–7, Tables 1–2）。
- ensemble 39× weights、约 23× inference time；设备成本主要反映 inference，search 仍在 host，energy 不含演化训练（pp.5–6）。
- 公开代码本轮 `HEAD=255542e6a1021461d31796b3fc6b57d74a2a6814`；本轮未运行代码或复现交易结果。

## 当前价值与局限

- 它提供少见的 latency+whole-board energy 真机测量和 40 个 paired seed-panel cells，但没有 peak memory、Pareto archive、LLM 成本或端到端 search energy。
- 对当前方向最有价值的是“host search / endpoint inference”成本拆账和 population ensemble trade-off；迁移到 Conv1d 时应把 single/ensemble latency、energy、memory 与 search cost 分开，并保留 hypervolume 与 seed variance。

## 链接

- 论文：https://arxiv.org/abs/2610.10038
- 代码：https://github.com/zimenglyu/ONENAS
