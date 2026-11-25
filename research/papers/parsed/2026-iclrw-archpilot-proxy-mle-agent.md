---
title: "ArchPilot: A Proxy-Guided Multi-Agent Approach for Machine Learning Engineering"
authors: "Zhuowen Yuan, Tao Liu, Yang Yang, Yang Wang, Feng Qi, Kaushik Rangadurai, Bo Li, Shuang Yang"
year: "2026"
venue: "ICLR 2026 Workshop on MALGAI / arXiv:2511.03985v2"
paper_url: "https://openreview.net/forum?id=6rEuy1CXQ1"
source_pdf: "https://arxiv.org/pdf/2511.03985"
parser: "Codex"
parsed_on: "2026-11-25"
status: codex_draft
tags: [mle-agent, mixed-search-space, multi-agent, mcts, proxy-evaluation, memory]
---

# ArchPilot

> 本笔记基于 arXiv v2 官方 PDF，并以 OpenReview MALGAI proceedings 页面核对书目信息。论文把方法称为 NAS，但 Agent 输出完整 PyTorch pipeline，可同时改变数据处理、模型和训练流程，因此准确归类为 `MLE Agent / mixed-search-space`，不能直接支持固定配方 NAS 或固定架构 HPO。

## 搜索对象、固定变量与闭环

- 搜索状态是完整可运行脚本；Generation Agent 的 draft 包含 data processing、model、training 和 validation，improve 每次只做一个原子修改，debug 根据日志修复失败脚本。数据集划分、公开 leaderboard metric、资源环境和任务时限固定，但 architecture、recipe 与数据处理均可变。（PDF pp.4–5）
- Orchestration Agent 用 MCTS/UCT 选择节点，保存计划、代码、proxy/true score、日志、runtime、cost 与 visit/debug 状态；短期 journal 和历史 best 作为后续 prompt memory。proxy 权重变化时重算分数并从 top-k 节点重启，保留 artifacts 但重置 visit counts。（PDF pp.4–5）
- Evaluation Agent 对候选执行 proxy 或 full training。proxy 固定为 10% 训练数据上的 1 epoch，并聚合 one-epoch validation、noisy validation 和 feature-dropout validation；累计至少 5 个 proxy/true-score 对后拟合非负权重。（PDF pp.5–6）

## 预算、失败处理与结果

- MLE-Bench 共 75 个 tabular/vision/NLP Kaggle-style tasks。作者为每个 task 分配 2.5 GPU-hours，使用 A100-SXM4-40GB 集群和 `gpt-4.1-2025-04-04`；LLM inference time 不计入该 GPU 预算。（PDF p.7）
- invalid node 的 reward 为 -1；proxy sentinel 会被 hard-zero，缺分数或 malformed JSON 会令节点本轮 ranking invalid；连续 debug 超限可终止分支，full evaluation 无有效 submission 时会换新候选重试。（PDF pp.4–6）
- 作者报告 ArchPilot 的 valid submission rate 为 0.893，ML-Master/AIDE 为 0.867/0.787；mean normalized ranking 为 0.6149，对照为 0.6535/0.6953。它在 high-difficulty tasks 的 ranking 为 0.6496，ML-Master 为 0.7262。以上均为作者结果，不是仓库实测。（PDF pp.7–8, Tables 1–2）
- 论文未报告 attempted/proxy/full/valid/unique 候选总数、完整 invalid/debug/retry/duplicate ledger、search seeds/方差、LLM calls/tokens/API 费用、实际总 GPU-hours、墙钟和 energy。2.5 GPU-hours 还排除了 inference time，不能视为端到端等成本。（PDF pp.5–8）

## 公平性、复现与课题价值

- 作者称三种 Agent 使用相同严格预算，但 ML-Master 的原报告硬件为 A100-SXM4-80GB，而 ArchPilot 是 40GB；论文未说明是否在同一环境重跑全部 baseline，也未给多随机种子，因此 matched-budget 公平性只能给中等置信度。（PDF p.7）
- 论文有 budget sensitivity，但没有分别隔离 memory、MCTS、proxy generation、weight refit 与 restart 的消融，也没有公开候选级 trace。OpenReview 已确认 workshop 发表；截至 2026-11-25 未找到作者官方代码仓库。
- 对本课题最有价值的是“node journal + proxy/true-score calibration + scoring-semantics 变化时 restart”的控制面。复现时应把 GA 动作收窄为 typed Conv1d architecture-only mutation，冻结 data/recipe/evaluator，并对 random/native、stateless LLM、memory-aware LLM 统一 attempted candidates、GPU、token 与墙钟预算。
- 官方 PDF：10 页，SHA-256 `bbb6213bfbe85b4c00faffc8d8d2fe2bb6e4c4510491e371104c1cded50efd42`。

- [x] 搜索变量、固定变量和 mixed/MLE 边界已区分
- [x] memory、restart、proxy、预算和主要结果已按页核对
- [ ] 人工决定 `retained` / `discarded`
