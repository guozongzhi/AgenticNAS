---
title: "FGSS-BO: Feedback-Guided Hypothesis Management for LLM-Based Bayesian Optimization"
authors: "Hao Chen, Ziyang Ling, Ronald X. Xu, Mingzhai Sun"
year: "2026"
venue: "arXiv:2610.21246v1"
paper_url: "https://arxiv.org/abs/2610.21246"
source_pdf: "https://arxiv.org/pdf/2610.21246"
code_url: "not found"
parser: "Codex"
parsed_on: "2026-10-23"
status: codex_draft
tags: [hpo, fixed-architecture, llm, bayesian-optimization, reflection, memory]
---

# FGSS-BO

> 本笔记基于 arXiv v1 的 21 页 PDF。主科学案例是离线 retrospective optimization；附录的六个 Bayesmark 任务固定 RF/SVM 模型并只调整其超参数，可作为 fixed-architecture LLM-HPO 的小规模迁移证据。

## 方法与搜索对象

- FGSS 用带持久 ID 的 hypothesis records 保存 evidence、anchor、intervention、预期方向与 test history；LLM reflector 在每轮更新记录，确定性 curator 合并重复、管理生命周期，并允许受约束的 test overrides。候选构造器再保证配置合法且未评估。（PDF pp.3–6）
- HPO transfer 包含 breast/digits/diabetes 上的 RandomForest 与 SVM。RF 变量为 max depth、max-feature fraction、min impurity decrease、min leaf/split/weighted leaf；SVM 为 `C`、`gamma`、tolerance。算法/结构与训练数据固定，符合本仓库 fixed-architecture HPO 边界。（pp.17–19）
- 每 task `K=10` initial + `T=20` sequential evaluations，batch 1，6 paired seeds；LLAMBO 和 FGSS 共 72 runs、2,160 次配置评估。LLM 为 GPT-4o mini，每轮 reflector 另一次调用，temperature 0、output cap 1,500、失败重试一次。（pp.16–19）

## 结果、记忆与成本

- Table 14 的终点结果并非一致胜出：breast RF 两者 final 都为 0.93187；digits RF LLAMBO final 0.53550、FGSS 0.52727，而 AUC 为 0.46033 vs 0.47376；diabetes RF MSE（低为好）0.58558 vs 0.57109，但 AUC 0.61024 vs 0.61335；diabetes SVM final 0.57768 vs 0.51711、AUC 0.61046 vs 0.55636。（pp.18–19）
- 主科学任务的 6 paired runs 中，iPSC final 0.691→0.813、AUC 0.494→0.640；C2C12 final 1.281→1.725、AUC 1.025→1.167。它们是 retrospective nearest-neighbor objective，不能外推为在线实验发现。（pp.7–10）
- Reflector-only token 表：iPSC 六次运行合计 2,079,239 prompt + 62,333 completion tokens；C2C12 为 2,403,748 + 69,019。elapsed 只累计 API call latency，不是 optimizer wall-time；HPO transfer 未给完整 token/cost 汇总，也未报告 GPU-hours、energy 或训练 wall-time。（pp.14–16）
- curator 明确合并重复，candidate builder 要求 legal/unseen，LLM parse 失败可重试一次；主运行 20 个 final reflection records 均解析成功。论文没有 attempted/invalid/OOM/duplicate/retry 的完整逐轮账本。

## 公平性、局限与复现

- 对照 LLAMBO 使用相同 initial points、objective-evaluation budget 与 paired seeds，隔离了 hypothesis memory/feedback 管理；但 FGSS 每轮多一次 reflection call，总 LLM 成本不匹配。
- 主任务多个 ablation（如 No-Override 或去掉 tests）在部分 AUC 指标上超过完整 FGSS，说明各组件贡献不稳定。HPO 只有 6 tasks×6 seeds，结果有胜有负，不支持“普遍优于 LLAMBO”。
- 代码链接未在 metadata 中发现。PDF 为 21 页，SHA-256 `898a89582241a124abc501e1764a7087bbca1bf25d488c98f4f66080edb5b698`；本轮未运行。无 Conv1d、真实 latency、peak memory、energy 或 Pareto 证据。

## 可引用摘要

Chen 等提出 FGSS-BO，用结构化 hypothesis records、LLM reflection 与确定性去重/生命周期管理为 BO 保存可追踪的反馈记忆。六个固定 RF/SVM Bayesmark 任务在相同 30 次 objective evaluations 和六个 paired seeds 下显示混合结果，部分任务改善、部分任务退化。该工作提供 fixed-architecture LLM-HPO 的记忆设计证据，但额外 reflection 调用未做端到端成本匹配。
