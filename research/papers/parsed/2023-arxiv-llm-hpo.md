---
title: "Using Large Language Models for Hyperparameter Optimization"
authors: "Michael R. Zhang, Nishkrit Desai, Juhan Bae, Jonathan Lorraine, Jimmy Ba"
year: "2023"
venue: "arXiv:2312.04528"
paper_url: "https://arxiv.org/abs/2312.04528"
source_pdf: "../pdfs/2312.04528-llm-hpo.pdf"
parser: "Codex"
parsed_on: "2026-07-26"
status: codex_draft
tags: [hpo, llm-optimizer, bayesian-optimization]
---

# Using Large Language Models for Hyperparameter Optimization

> 本笔记由 Codex 基于本地 PDF 生成，关键数字仍需人工抽查。

## 一句话结论

论文让 LLM 根据任务描述和历史 `(configuration, loss)` 顺序提出新超参，在极小预算的早期搜索中优于 random/部分 BO，并进一步尝试把模型与优化器代码本身作为超参数。（PDF pp.1–2, 5–9）

## 方法拆解

- 输入：dataset/model/search-space 描述、已评估配置和 loss，可选 chain-of-thought。
- 输出：下一组结构化超参，或可执行 model/optimizer code。
- 闭环：真实训练→返回 validation metric→追加历史→继续提议。
- 模型：GPT-3.5、GPT-4、GPT-4 Turbo，temperature 0。（PDF p.5）

## 评估与预算

- 标准 HPO：8 datasets × 4 model/search spaces，共 32 tasks；主表预算 10 evaluations。
- CIFAR-10 ViT/ResNet：5 个超参、每 trial 20 epochs、最多 30 iterations。
- code generation：NYC Taxi post-cutoff 数据，5 evaluations。（PDF pp.5, 7–9）

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 小预算下 GPT-4 Turbo 最强 | 32 tasks 中 81.25% 胜 random，mean rank 2.42 | random、SMAC RF/GP 等 | p.5, Table 1 | high |
| 可用于 BO warm-start | 前 10 个 LLM 点使 30-step BO 在 21/32 tasks 改善或持平 | BO random init | p.7 | high |
| 代码空间也可搜索 | 5 trials 后 test loss 明显低于 random | random、固定 config LLM | pp.8–9, Table 4 | medium |

## 公平性与可信度检查

- 主表所有方法预算 10 次；random 用 500 个离线样本 bootstrap 估计给定预算表现。
- GPT 模型可能见过公开 HPO benchmark；post-cutoff Taxi 仅覆盖 code-generation 子实验。
- 生成代码的合法性、安全性和搜索空间大小与结构化 HPO 不完全可比。

## 与 AgenticNAS 的关系

- 最适合做“Codex 前 5–10 个 warm-start + 传统 BO/TPE 后续”的基线。
- 架构代码不应直接生成；沿用声明式 `TrainingConfigAction` 和 validator。
- observation 应只提供聚合曲线特征和历史配置，避免完整内部日志。

## 最小复现实验

- 在一个固定 Transformer 架构上给 random、TPE、Codex、Codex→TPE 各 20 trials。
- 对前 5/10/20 trials 分别报告 best-so-far、成本和无效配置率。
- 使用一个内部/新构造任务检查公开知识污染。

## 局限与风险

- 收益集中于低预算早期，长 horizon 是否持续优于 BO 并不确定。
- 依赖专有 GPT 版本，结果难完全复现且会随模型更新。
- 自由代码搜索不满足当前 clean-room 和安全执行边界。

## 可引用摘要

Zhang 等将语言模型作为序贯 HPO 提议器，根据任务描述和历史验证损失持续生成配置。GPT-4 Turbo 在 10-evaluation 基准上优于 random，并可改善 BO warm-start；但公开 benchmark 污染和专有模型版本限制了结论，代码生成扩展也不适合直接用于受约束内部 NAS。

## 检索与人工核验记录

- 解析问题：LLM HPO 闭环、小预算结果、BO 混合和代码搜索。
- 使用片段页码：1, 2, 4, 5, 7–9, 12–14。
- [x] 10/30/5 evaluations 预算已核对
- [x] 81.25% 与 21/32 已核对
- [ ] 全部 32 tasks 单项结果已核对
- [ ] 已由人工决定 `retained` / `discarded`
