---
title: "EvoPrompting: Language Models for Code-Level Neural Architecture Search"
authors: "Angelica Chen, David M. Dohan, David R. So"
year: "2023"
venue: "NeurIPS 2023"
paper_url: "https://arxiv.org/abs/2302.14838"
source_pdf: "../pdfs/2302.14838-evoprompting.pdf"
parser: "Codex"
parsed_on: "2026-07-26"
status: codex_draft
tags: [llm-nas, evolution, code-generation]
---

# EvoPrompting

> 本笔记由 Codex 基于本地 PDF 生成，关键数字仍需人工抽查。

## 一句话结论

EvoPrompting 把代码 LLM 作为可随搜索历史更新的 mutation/crossover 算子，通过演化 in-context 样例和 soft prompt-tuning，优于一次性 few-shot 架构生成。（PDF pp.1–2）

## 研究问题与贡献

- 用完整模型代码代替固定离散操作空间，LLM 根据高适应度父代生成子代。
- 已评估个体既用于选择下一轮 in-context parents，也用于 prompt-tuning。
- 在 MNIST-1D 搜索卷积模型，在 CLRS 搜索 GNN processor 变体。（PDF pp.2, 4–6）

## 方法拆解

- 搜索对象：可执行 Python 模型代码；适应度是验证误差与模型参数量乘积的负值。
- Agent 输入：父代代码、目标准确率和目标规模；输出：新的模型代码。
- 闭环：过滤不可训练/重复模型，统一训练并反馈验证指标，更新全局 population。
- 默认搜索为 10 轮、每轮 10 个 prompts、每 prompt 16 个样本，共 1600 个生成样本。（PDF p.6）

## 评估与预算

- MNIST-1D：每个候选在单张 Tesla P100 上训练 8000 steps。
- CLRS：每个候选在单张 P100 上训练 2000 steps，搜索信号使用 validation accuracy。
- 论文未报告完整 GPU-hours 和 LLM 推理成本。（PDF pp.6, 10）

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 更好的精度/规模权衡 | top-20 模型形成更靠近原点的 Pareto frontier | naive few-shot、无 prompt-tuning、随机父代 | pp.7–8, Fig. 2 | high |
| CLRS 有跨任务改进 | 30 个任务中 21 个优于 Triplet-GMPNN | Triplet-GMPNN | pp.1, 10, Table 1/Appx. | high |
| 搜索依赖演化闭环 | few-shot 单独效果差，去 prompt-tuning/随机父代较弱 | 消融变体 | pp.6–8 | medium |

## 公平性与可信度检查

- 各变体匹配 LLM 生成样本总数，候选使用相同训练超参。
- 搜索由 4 个已知 seed models warm-start，结果不能解释为完全无先验发现。
- 1600 个“生成样本”包含重复和不可训练模型；有效训练数与总生成数应同时报告。

## 与 AgenticNAS 的关系

- 最直接映射：让 Agent 仅替换当前 `MutationAction` 提议器，保留 evaluator/Pareto。
- 不建议复制代码生成边界；当前声明式 JSON 更易校验、适合公司 clean-room 环境。
- 可复用其父代选择、失败过滤、历史个体形成 prompt context 的机制。

## 最小复现实验

- 对照 random mutation、stateless Codex mutation、带 top-k 历史样例的 Codex mutation。
- 固定 100 个候选和真实训练预算，报告 hypervolume、有效率、重复率与 LLM 成本。
- 只允许 block/cell/op 单字段动作，避免代码生成混入实现能力。

## 局限与风险

- 训练 1600 个候选仍然昂贵，且 GPU-hours 未汇总。
- 代码 LLM 可能利用预训练中的常见架构知识；创新性难与代码先验完全分离。
- MNIST-1D 和 CLRS 与小型语言模型结构搜索仍有任务差异。

## 可引用摘要

EvoPrompting 将代码语言模型嵌入演化 NAS，使其根据高适应度父代生成并通过 prompt-tuning 迭代改进候选。论文在 MNIST-1D 和 CLRS 上展示了优于 naive prompting 的结果，但依赖已知 seed models、代码生成和大量候选训练，完整搜索成本未被统一报告。

## 检索与人工核验记录

- 解析问题：LLM mutation/crossover、候选预算、消融和 Pareto 对应。
- 使用片段页码：1–4, 6–10, 14。
- [ ] 主要数字已对照原表
- [x] 1600 样本预算已核对
- [x] GPU 型号和每候选训练步数已核对
- [ ] 已由人工决定 `retained` / `discarded`
