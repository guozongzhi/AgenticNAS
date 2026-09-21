---
title: "Evolving Executable Pipeline Programs for AutoML with Language Models"
authors: "Sofoklis Kitharidis, Cor J. Veenman, Jan N. van Rijn, Thomas Bäck, Niki van Stein"
year: "2026"
venue: "arXiv:2608.16416v1"
paper_url: "https://arxiv.org/abs/2608.16416"
source_pdf: "https://arxiv.org/pdf/2608.16416"
parser: "Codex"
parsed_on: "2026-09-22"
status: codex_draft
tags: [automl, program-evolution, mixed-search-space, executable-pipeline, leakage-control]
---

# Evolving Executable Pipeline Programs for AutoML with Language Models (LACE)

> 本笔记基于 arXiv v1 PDF；LACE 搜索经典 tabular pipeline 程序，而非神经网络架构，作为 mixed/AutoML 邻接证据收录。

## 一句话结论

- 核心主张：LACE 用 LLM 作为 `(μ+λ)` evolution 的 variation operator，在严格隔离的 inner-validation 上搜索完整可执行 pipeline；它的预算、失败和重复统计很完整，但不能当作 NAS 结果。
- 证据位置：PDF pp.2–7, 12–15，Fig. 1、Tables 2–4。

## 搜索对象、变量与层级

- 对象：实现固定 `fit-on-construction/predict-on-call` 接口的 Python pipeline program。
- 可变：preprocessing、classical learner、最多三模型 ensemble、代码结构和 generator-chosen hyperparameter defaults。
- 固定：scikit-learn/NumPy/SciPy/pandas；禁止内部 CV、model selection、nested HPO（prompt 约束，事后静态审计）；官方 test 仅最终一次使用。
- 无神经网络结构搜索；分类为 `mixed-search-space`/AutoML adjacent。

## Agent 与优化闭环

- `μ=4` parents、`λ=12` offspring；初始 4 个程序，之后 8 代，每次随机选 parent，提供代码、反馈、population summary 和 mutation instruction。
- evaluator 在隔离 subprocess 中运行；异常/timeout 得 worst fitness 和首条错误/源码行。
- elitist truncation 保留 best 4；invalid/timeout 也计入 100-candidate budget。

## 预算、基线与成本

- 68 OpenML classification tasks × 5 repetitions × 3 LLM backbones × 100 candidates = 102,000 planned；日志实际 101,959。
- per-candidate timeout：heavy task 4h，其余 1h；baseline 获得与对应 LACE run 相同外部 wall-clock limit。
- 基线：AutoGluon、auto-sklearn、H2O、fixed XGBoost；TabPFN 2.5/3 与 TabICL 作为不同信息/模型范式参考。
- 计算平台异构，统一 GPU/CPU 规格、tokens、货币成本未报告；论文明确不能做严格 runtime comparison。

## 核心结果与失败记账

| Claim | Metric/result | Evidence locator | Confidence |
|---|---|---|---|
| 候选有效性可量化 | 70,998/101,959 = 69.6% finite-fitness valid | PDF p.12 | high |
| GPT-5.4-mini 有效率最高 | 29,691/34,000 = 87.3%；DeepSeek 74.7%，Qwen3 46.8% | PDF p.12 | high |
| 结构重复较低 | 70,998 valid 中 65,298 unique signatures；median 68/100，GPT 86/100 | PDF p.15 | high |
| 与强 AutoML 接近 | GPT-5.4-mini 与 AutoGluon 无 detectable difference，优于 auto-sklearn/H2O/XGBoost | PDF pp.5–7, 14 | medium-high |

## 公平性、复现性与局限

- 统一 candidate 数并把失败计入预算，且 test isolation 清晰，是较好的 protocol。
- wall-clock 对齐不等于同硬件/能耗；LLM token/cost 也未匹配。
- prompt 约束不是 harness 强制；22 个最终程序确认违规，不过删除后主要统计结论不变（PDF pp.13–14）。
- coarse task summary 降低但不能消除 OpenML 预训练泄漏。

## 与当前 AgenticNAS 的关系

- 可直接借鉴 attempted-budget、invalid timeout、unique signature、test isolation 与 lineage trace 报告。
- 不能支撑神经架构、Conv1d Transformer 或硬件 Pareto 结论；若作基线，应标成 executable AutoML program search。

## 链接

- 论文：https://arxiv.org/abs/2608.16416
- artifact：https://doi.org/10.5281/zenodo.21886859
