---
title: "Large Language Models to Enhance Bayesian Optimization"
authors: "Tennison Liu, Nicolás Astorga, Nabeel Seedat, Mihaela van der Schaar"
year: "2024"
venue: "ICLR 2024"
paper_url: "https://arxiv.org/abs/2402.03921"
source_pdf: "../pdfs/2402.03921-llambo.pdf"
parser: "Codex"
parsed_on: "2026-07-26"
status: codex_draft
tags: [hpo, bayesian-optimization, llm-optimizer]
---

# LLAMBO

> 本笔记由 Codex 基于本地 PDF 生成，关键数字仍需人工抽查。

## 一句话结论

LLAMBO 不替代 Bayesian Optimization，而是用 GPT-3.5 分别增强 zero-shot warm-start、surrogate modeling 和 candidate sampling，收益主要出现在观测稀疏的搜索早期。（PDF pp.1, 3–8）

## 方法拆解

- 将 model card、data card、搜索空间和历史 `(hyperparameters, score)` 序列化为自然语言。
- warm-start：无需相似任务历史，zero-shot 生成初始点。
- surrogate：用 ICL 做带不确定性的回归，或做“好/坏”二分类。
- candidate sampling：条件生成达到目标值的高潜力配置；最终仍由 acquisition function 选点。（PDF pp.3–7）

## 评估与预算

- 全文组件实验覆盖 Bayesmark/HPOBench 的 74 个任务。
- warm-start：5 initial points、25 trials、10 seeded searches。
- end-to-end：50 HPT tasks，每任务 5 seeds × 25 trials；所有方法共享 5 个随机初始点。
- baselines：GP-DKL、SKOpt GP、Optuna TPE、SMAC3 RF。（PDF pp.4, 8）

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| zero-shot warm-start 降低早期 regret | dataset context 越完整，前 5 trials 优势越明显 | random/Sobol/Latin Hypercube | p.4, Fig. 2 | high |
| LLM surrogate 预测更强 | 少样本时 NRMSE/R2 优于 GP/SMAC | GP、SMAC | pp.5–7, Fig. 3 | medium |
| 不确定性校准仍弱 | GP 的 LPD/coverage 优于 LLAMBO | GP | p.7 | high |
| 端到端平均 regret 最低 | public 与 private/synthetic tasks 均领先 | 4 个生产 BO 基线 | p.8, Fig. 7 | medium |

## 公平性与可信度检查

- end-to-end 统一初始点、trials 和 seeds，比较设计较强。
- proprietary/synthetic datasets 用于减轻记忆污染，但具体泄漏风险仍需看数据构造。
- LLM 调用成本未与传统 surrogate 的计算成本统一折算。

## 与 AgenticNAS 的关系

- 这是训练参数 Agent 最重要的混合基线：Codex 提供 warm-start/候选，BO 保留统计选择。
- 不应让 LLM 取代 uncertainty-aware acquisition；其校准弱于 GP。
- 对架构搜索可只借鉴 warm-start，不把连续 BO 假设硬套到离散 block/cell/op。

## 最小复现实验

- 在训练 HPO 中比较 TPE、Codex warm-start + TPE、全程 Codex。
- 每组共享前置任务描述、总 25 trials 和 5 seeds。
- 报告 best-so-far、regret、LLM token 和 wall-clock。

## 局限与风险

- 主要任务低维，难直接外推到大规模离散架构空间。
- 依赖 GPT-3.5 编码的公开先验。
- LLM surrogate 的不确定性不具严格概率校准。

## 可引用摘要

LLAMBO 将语言模型以模块化方式接入 Bayesian Optimization 的初始化、surrogate 和候选采样环节。统一预算实验显示其在少样本阶段具有优势，但概率校准仍弱于 Gaussian Process；因此它更适合作为传统优化器的知识型补充，而不是完全替换 BO。

## 检索与人工核验记录

- 解析问题：BO 三个插入点、统一预算、早期收益和校准。
- 使用片段页码：1–7, 9, 10, 16。
- [x] 74/50 tasks 和 25-trial 设置已核对
- [x] 共享 5 初始点与 baseline 已核对
- [ ] 图 7 的具体 regret 数值已人工读取
- [ ] 已由人工决定 `retained` / `discarded`
