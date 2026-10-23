---
title: "ATTUNE: Agentic Throughput Tuning for LLM Training"
authors: "Leo Fan, Hongyang Wang, Wenbo Chen, Jingguo Liu, Xian Li, Xuan Wang, Ruochen Wen, Yiming Yan, Hao Wu, Zheshen Wang, Benoit Dumoulin"
year: "2026"
venue: "arXiv:2610.17528v1"
paper_url: "https://arxiv.org/abs/2610.17528"
source_pdf: "https://arxiv.org/pdf/2610.17528"
code_url: "https://github.com/amazon-science/attune"
parser: "Codex"
parsed_on: "2026-10-23"
status: codex_draft
tags: [agentic-systems-tuning, throughput, gpu-hours, failure-ledger, memory]
---

# ATTUNE

> 本笔记基于 arXiv v1 的 23 页 PDF。ATTUNE 调整分布式训练系统 recipe，而不改变模型结构、数据或优化目标；它是 Agentic systems tuning 邻接证据，不是 NAS，也不是本仓库定义的训练超参数 HPO。

## 搜索对象、控制与记忆

- 可变字段包括 TP/PP/EP/CP/DP 布局、pipeline scheduling、recomputation/offload、communication dispatcher 和 kernels；模型、数据、sequence length、global batch、precision、GPU 数量、optimizer state、loss 与 routing semantics 固定。控制面拒绝改变目标的 proposal。（PDF pp.3–6）
- 单一 coding agent 读取 lever catalog、profile 与诊断，每轮提出 bottleneck hypothesis，通常只改变一个 lever 或一个耦合组合。durable ledger 保存运行、失败、结论与“lessons”，重复 recipe 会被拒绝；Agent 可判断剩余 GPU-hours 不足并提前停止。（pp.4–6）
- 候选运行 14 optimizer steps，以 4–13 步计 throughput；baseline 至少五次确定 noise band。最终候选再跑 20 steps，并要求相同数据/seed、loss 在容差内、最终偏差不超过 5%、相关系数至少 0.95。（pp.5–6）

## 实测预算、失败与结果

- 四个 141B–405B 模型，128×B200、128×H100 或 64×B200；每 tuner 在 GLM-4.5 和 MiniMax-M2 各跑三次 campaign，统一上限为一次 baseline run 成本的 30 倍。基础设施失败不收费；第二次同类 infra failure 会作为 recipe failure 计账。（pp.6–7）
- Table 2：GLM-4.5 平均 +33.9%、最佳 +54.7%，用 669.1/1,880 GPU-hours；Llama-3.1-405B +6.7%、最佳 +11.9%，393.9/1,850 GPU-hours；Mixtral-8x22B 无增益，173.4/740 GPU-hours。（p.6）
- Table 3：GLM-4.5 上 ATTUNE 平均 8.3 launches、24% 失败（60 GPU-hours）、6.4h wall-clock；OptiCo 为 22.7、19%（78）、15.7h；TPE 为 19.7、39%（186）、9.6h。MiniMax-M2 上 ATTUNE +164.1%、203 GPU-hours、13.3 launches、23%（25）、3.1h；预过滤 BO +55.5%、489 GPU-hours。（p.7）
- correctness gate 对 133 个合法 recipe 无误拒；24 个注入缺陷捕获 16 个、漏掉 8 个细微错误。论文报告 OOM/hang/crash 比例与失败 GPU-hours，但未给 LLM calls/tokens/API 费用或能耗。（pp.7–9）

## 边界与复现

- 论文以 stage/rank profile 诊断 HBM 压力，但没有汇总每个候选的实际 peak memory；也没有 energy。真实 GPU-hour、wall-clock 和失败账本比只匹配 evaluation count 更接近本仓库需要的成本协议。
- 代码本轮可访问，`HEAD=7a333b09fe671338794e4efc503ba58f52769acf`；未运行。PDF 为 23 页，SHA-256 `fcb2f0d2fb3e5cdff666867f50b12a5f4ff8897b2eedc377089746d633199cd8`。
- 可迁移设计是 objective-preserving typed actions、重复拒绝、失败收费、确定性 correctness gate 与 durable lessons；不能把 throughput recipe tuning 的增益解释为网络结构或训练算法改进。

## 可引用摘要

Fan 等提出 ATTUNE，以 coding agent、profile 诊断和持久运行账本搜索分布式 LLM 训练 recipe，并以确定性 gate 保证候选不改变训练目标。作者在 GLM-4.5 上报告平均 33.9% throughput 增益、669 GPU-hours 和 6.4 小时 campaign wall-clock，同时公开 OOM/hang/crash 的失败比例。该系统只调整并行与运行时配置，因此应归为 Agentic systems tuning，而非 NAS 或训练 HPO。
