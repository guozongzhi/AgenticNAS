---
title: "Agent Stack for ML Training Lifecycle: Generation, Validation, and Optimization"
authors: "Jaideep Ray et al."
year: "2026"
venue: "arXiv:2611.00384v1"
paper_url: "https://arxiv.org/abs/2611.00384"
source_pdf: "https://arxiv.org/pdf/2611.00384"
parser: "Codex"
parsed_on: "2026-11-11"
status: codex_draft
tags: [mle-agent, automl-agent, mixed-search-space, production, memory, failure-handling]
---

# Agent Stack for ML Training Lifecycle

> 本笔记基于 arXiv v1 官方 PDF。AutoResearch 可同时改架构、训练配置与代码，归 mixed/MLE Agent 邻接证据，不是独立 NAS 或固定架构 HPO。

## 一句话结论

- LinkedIn 的 AutoTorch 负责模型生成/迁移与 executable repair，AutoResearch 在固定 incumbent 上同步并行试验，外部 orchestrator 保存 trial、artifact、budget 与失败状态；这是生产控制面证据，不是 typed search-space benchmark。（PDF pp.2–8, Figures 1–8）
- 作者报告 AutoTorch 115 次 workflow 中 92 次完成全训练，77/92 通过质量要求；AutoResearch 在 100 条 production pipeline 中 28 条通过最终 held-out 指标改善原 baseline，但论文未公开完整 trial/GPU/LLM 成本分布或 classical optimizer matched-budget 对照。（PDF pp.7–8, Tables 1–2）

## 搜索对象、变量与闭环

- AutoTorch 可生成 architecture、data/training pipeline 与迁移代码；AutoResearch 可改 encoder、MoE/head/input compression、loss、optimizer、learning rate、batch size 及代码实现。数据、primary metric、并发与 clock-hour budget 由 research plan 固定。（PDF pp.2–6）
- 每轮从同一 incumbent 建独立 Git worktree，通常并行 4 个实验；等整轮全部结束后选一个完整 candidate，绝不自动 merge siblings。若无提升则保留 incumbent。（PDF pp.3, 6, Figures 3/6）
- external memory 保存 execution events、metrics、lineage、dead ends 与 artifact；plateau 时专门技能切换研究方向。停止条件是 clock-hour budget 或配置条件。（PDF pp.3, 6）
- failed validation 返回诊断供修复；harness failure 可由 Agent 修复并走 PR/测试。论文没有汇总 invalid/OOM/duplicate/retry 数，也没有逐 pipeline attempted/valid/trained ledger。（PDF pp.4, 6）

## 评估、预算与证据

- AutoTorch：115 attempted workflow，92 operational completion，77 quality pass；Stage 1 generate-repair iterations p50/p90 为 4/10，wall time 6.3/32 h。（PDF p.7, Table 1）
- AutoResearch 搜索通常 48–72 h。三个非随机案例包括：GNN 49 trials、Recall@1000 +9.3%；MLP `[24,12]→[64,32]`、held-out AUC +1.2%；0.6B SLM heads 比较只报告 validation +1.2%。（PDF pp.7–8, Table 2）
- GPU 由 H100/H200 warm pool 弹性分配，但每个 run 的 GPU-hours/卡数、LLM calls/tokens/费用、energy 与 peak memory 未报告。48–72 h 是 wall-clock 范围，不是统一 trial budget。
- 28/100 是最终 held-out 改善率；AR-1 同时改变层宽、采样、四次 inference 与训练，不能把 +9.3% 归因于某一架构动作。（PDF p.8, Table 2 notes）

## 公平性、复现性与局限

- 论文使用 live production workloads，没有公开数据、实现或 random/TPE/evolution/人工专家的 matched-budget 对照；100 条 pipeline 的任务组成与 trial 分布未披露。
- online serving、latency/throughput SLA 与 A/B testing 明确不在范围；offline improvement 不能当生产效果。（PDF pp.2, 8）
- 生产平台依赖强，外部复现需要重建数据、训练、Evals 和权限控制面；Member Data 不进入 LLM context，但 benchmark/code contamination 风险无法独立核验。

## 对本仓库的价值

- 归类：`mixed-search-space / MLE Agent`。最有价值的是固定 incumbent 的同步 round、整 candidate 替换、external ledger、objective-preserving validation 与 failure repair。
- 不能把 28/100 pipeline improvement 当作 LLM×NAS 或 fixed-HPO 的效果；需要先把 architecture-only 与 recipe-only action contracts 分开。
- 最小复现：在 typed Conv1d 上固定 4 trials/round 与总 attempted/GPU/LLM/wall-time，比较 evolution、stateless LLM、memory-aware LLM，并记录 failed validation、duplicate、repair 与 final held-out leakage boundary。

## 检索与人工核验记录

- 官方 PDF：10 页，SHA-256 `93101aa2e80a3d36841325612270fc3db9b4ad239c019c3eec80a17675ecb442`；所有页可解析。
- 论文未提供作者官方代码仓库；关键结果和限制已按 Tables 1–2 核对。
- [x] mixed/MLE 分类已按实际变量核对
- [x] attempted workflow 与 held-out 口径已区分
- [x] 未报告成本与失败账本已标记
- [ ] 人工决定 `retained` / `discarded`
