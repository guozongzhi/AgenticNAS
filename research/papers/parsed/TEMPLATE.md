---
title: "{{PAPER_TITLE}}"
authors: "{{AUTHORS}}"
year: "{{YEAR}}"
venue: "{{VENUE_OR_ARXIV}}"
paper_url: "{{PAPER_URL}}"
source_pdf: "{{SOURCE_PDF}}"
parser: "Codex"
parsed_on: "{{YYYY-MM-DD}}"
status: codex_draft
tags: []
---

# {{PAPER_TITLE}}

> 本笔记由 Codex 基于本地 PDF 检索片段生成。所有结论在人工核验前均视为草稿。

## 一句话结论

- 核心主张：
- 证据位置：

## 研究问题与贡献

- 解决的问题：
- 相比已有方法的变化：
- 作者明确声明的贡献：
- 证据位置：

## 方法拆解

### 搜索或优化对象

- 架构/训练参数/Agent 工作流：
- 搜索空间及表示：
- 约束：

### Agent 与优化闭环

- Agent 输入/观察：
- Agent 输出/动作：
- 记忆、反思或工具：
- 搜索/优化算法：
- 无效动作与失败处理：

### 评估与预算

- 数据集与任务：
- 低保真评估：
- 完整评估：
- GPU/候选数/LLM 调用预算：
- 硬件指标：

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
|  |  |  | page/section/table | low/medium/high |

## 公平性与可信度检查

- 基线是否使用相同搜索和训练预算：
- 是否报告多随机种子：
- 是否有消融实验隔离 LLM/Agent 的贡献：
- 是否可能存在 benchmark 或代码泄漏：
- 论文未报告的重要信息：

## 与 AgenticNAS 的关系

- 可复用设计：
- 与 block/cell/op + Pareto 方案的对应：
- 与训练超参 Agent 的对应：
- 与公司内部 clean-room 边界的冲突：
- 最值得验证的研究假设：

## 最小复现实验

- 假设：
- 对照组：
- 修改变量：
- 固定预算：
- 指标：
- 预期成本：
- 停止条件：

## 局限与风险

- 作者承认的局限：
- 解析模型识别的额外威胁：
- 需要回看原文的位置：

## 可引用摘要

用 2–4 句中性语言总结方法、主要证据和关键局限；不要使用宣传性措辞。

## 检索与人工核验记录

- 解析问题：
- 使用片段页码：
- [ ] 标题、作者、年份已核对
- [ ] 主要数字已对照原表或原图
- [ ] 预算和硬件信息已核对
- [ ] 没有把相关性写成因果性
- [ ] 已由人工决定 `retained` / `discarded`
