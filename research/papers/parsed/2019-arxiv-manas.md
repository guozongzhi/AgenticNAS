---
title: "MANAS: Multi-Agent Neural Architecture Search"
authors: "Vasco Lopes et al."
year: "2019"
venue: "arXiv:1909.01051"
paper_url: "https://arxiv.org/abs/1909.01051"
source_pdf: "../pdfs/1909.01051-manas.pdf"
parser: "Codex"
parsed_on: "2026-07-26"
status: codex_draft
tags: [evolution, multi-agent, nas]
---

# MANAS: Multi-Agent Neural Architecture Search

> 本笔记由 Codex 基于本地 PDF 生成，关键数字仍需人工抽查。

## 一句话结论

MANAS 将一个网络的架构选择拆给多个协同学习器，在非 LLM 条件下证明了多 Agent 分解可以降低 NAS 的组合搜索和显存压力，是 AgenticNAS 的历史对照而不是 LLM-Agent 基线。（PDF pp.1–3）

## 研究问题与贡献

- 每个 Agent 控制网络的一部分，通过全局奖励和 credit assignment 隐式协调。
- 给出两种轻量实现，并声称累计 regret 为 `O(sqrt(T))`。
- 使用 DARTS CNN 搜索空间，但允许直接搜索完整的 20-cell CIFAR-10 或 14-cell ImageNet 网络。（PDF pp.3–4）

## 方法拆解

- 搜索对象：cell 中边上的候选操作；单 cell 联合空间可达 `8^14`。
- Agent 动作：为所负责位置选择操作；全局模型性能形成共享反馈。
- 记忆/反思：没有 LLM 记忆，核心是在线学习、探索利用和 credit assignment。
- 评估：CIFAR-10、ImageNet、Sport-8、Caltech-101、MIT-67；搜索训练 50–500 epochs，取决于 cell 数和数据集。（PDF p.4）

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 显存显著降低 | 8-cell MANAS 约 1 GB，DARTS v1/v2 超过 8.5/9.6 GB | DARTS | p.11, Sec. 6.1 | high |
| 可直接搜索 ImageNet | 最佳直接搜索模型报告 25.26% test error | SNAS/DARTS/GDAS 等 | pp.12–13, Sec. 6.2 | medium |
| 搜索更高效 | 论文概括为 DARTS 搜索时间的 70% | DARTS | p.3 | medium |

## 公平性与可信度检查

- CIFAR-10 采用 4 个随机种子后选最佳，与当时 NAS 报告惯例一致，但会高估典型表现。
- 新数据集实验报告 8 次运行均值和标准差，并加入 random search/random sampling。
- extended training protocol 与搜索算法贡献需要分开看；论文同时报告 AutoAugment 和更长训练结果。

## 与 AgenticNAS 的关系

- 可复用设计：按 block/cell/op 切分局部控制权，并用统一 evaluator 反馈。
- 差异：当前项目让 LLM 提出声明式 mutation；MANAS 的 Agent 是在线学习器，不具备语义推理。
- 最值得验证：在相同 Pareto 预算下，单一 LLM 提议器与按 cell 分工的多个提议器是否有显著差异。

## 最小复现实验

- 在当前 4–10 层搜索空间中，将每层 FFN/attention 动作分配给独立策略。
- 与全局随机 mutation、单 LLM Agent 比较 hypervolume、无效动作率和重复率。
- 固定候选数、训练预算与随机种子；不复现其完整视觉搜索成本。

## 局限与风险

- 不是 LLM 驱动方法，不能证明语言模型带来收益。
- 搜索协议年代较早，部分结果依赖选最佳架构和扩展训练策略。
- 多 Agent 的通信成本及随网络深度扩展的稳定性需要重新测量。

## 可引用摘要

MANAS 将 NAS 表述为多个学习器对网络局部结构的协同优化，并通过 credit assignment 共享全局反馈。论文报告了相对 DARTS 更低的显存需求以及 CIFAR-10/ImageNet 上的竞争性结果，但其 Agent 并非语言模型，且部分比较采用多次搜索取最佳和扩展训练协议。

## 检索与人工核验记录

- 解析问题：多 Agent 分解、预算、公平性和历史定位。
- 使用片段页码：1, 2, 3, 4, 11, 12, 13, 17–19。
- [ ] 主要表格数字已逐项人工核对
- [x] 搜索协议和数据集已定位
- [x] 已区分非 LLM Agent 与 LLM Agent
- [ ] 已由人工决定 `retained` / `discarded`
