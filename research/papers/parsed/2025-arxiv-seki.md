---
title: "SEKI: Self-Evolution and Knowledge Inspiration based Neural Architecture Search via Large Language Models"
authors: "Zicheng Cai, Yaohua Tang, Yutao Lai, Hua Wang, Zhi Chen, Hao Chen"
year: "2025"
venue: "arXiv:2502.20422"
paper_url: "https://arxiv.org/abs/2502.20422"
source: "arXiv HTML full text, accessed 2026-07-26"
parser: "Codex"
parsed_on: "2026-07-26"
status: codex_draft
tags: [llm-nas, self-evolution, memory, nas-bench-201, transnas-bench-101]
---

# SEKI

> 本笔记基于 arXiv HTML 正文，而非本地 PDF。所有性能数字均为论文作者报告，尚未独立复现。

## 一句话结论

SEKI 先让 LLM 根据当前架构和性能反馈迭代生成改进策略，再从累计的高分架构库中抽取样本、归纳设计模式并生成新候选；论文在多个 NAS 搜索空间中报告较低的 GPU-day 搜索成本。（arXiv §4–5）

## 研究问题与贡献

- 问题：LLM 缺少架构先验或少样本示例时，如何仍以可控成本参与真实神经架构搜索。
- 自演化阶段：输入当前架构与评价分数，LLM 先生成优化策略、再生成新架构；高分候选及结果写入知识库。（§4.1）
- 知识启发阶段：从知识库 top-k 中随机选取 ξ 个候选，LLM 从其共性中归纳并提出新架构；随机抽样被作者用于降低只围绕当前最优解生成的风险。（§4.2）
- 论文使用 Qwen2.5-32B，另以 GPT-4o-mini 做不同 LLM 的对照；正文未提供可核验的公开代码链接。（§5.1、§5.3.3；arXiv metadata）

## 方法拆解

### 搜索或优化对象

- DARTS 风格 CNN 架构，以及 NAS-Bench-201 与 TransNAS-Bench-101 中的 cell 结构。
- NAS-Bench-201 的正文描述为 15,625 个候选，重复 cell 含六层、每层五个操作；TransNAS-Bench-101 使用四个候选操作、4,000 个架构。（§5.1.2–5.1.3）
- 该工作不是硬件感知 Pareto 搜索；主要比较准确率/错误率和作者报告的 GPU-day。

### Agent 与优化闭环

- 观察：目标任务、搜索空间、当前架构及其评价分数。
- 动作：先产生优化策略，再产生新的神经架构；不是受 JSON schema 约束的声明式 mutation。
- 记忆：保存高性能架构与评价结果的知识库；知识启发阶段对 top-k 随机采样 ξ 个条目。
- 迭代：总迭代数 n 由自演化次数 λ 和知识启发次数 γ 构成，λ + γ = n；消融固定 n=50。（§4、§5.3）

### 评估与预算

- 任务/数据：CIFAR-10、CIFAR-100、ImageNet-1K、NAS-Bench-201 的 CIFAR-10/CIFAR-100/ImageNet16-120，以及 TransNAS-Bench-101 多任务。（§5）
- 作者报告 CIFAR-10 上 2.29% test error、0.05 GPU-days；直接在 ImageNet 搜索时报告 76.1% top-1、2.0 GPU-days，并说明使用单张 RTX A100。（§1、§5.2）
- 最终架构训练：CIFAR-10/CIFAR-100 为 600 epochs、batch size 96；ImageNet-1K 为 250 epochs、batch size 1024。（§5.1）
- 可见正文未报告完整 LLM token/费用账、随机种子方差，亦未给出可核验代码链接；这些不能从“GPU-days”推断出来。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 作者报告低成本 CIFAR-10 搜索 | 2.29% test error，0.05 GPU-days | DARTS、NSGA-Net、LAPT-NAS 等表列方法 | §5.2, Table 1 | medium |
| 内存库加随机选样用于多样性 | 从 top-k 随机取 ξ 个候选，以减少围绕最优解的重复生成 | self-evolution only / 不同 k、ξ 设置 | §4.2, §5.3 | high |
| 跨空间结果 | NAS-Bench-201 与 TransNAS-Bench-101 多任务排名/指标 | NAS benchmark 对照 | §5.2.2–5.2.3 | medium |
| 直接 ImageNet 搜索 | 76.1% top-1，2.0 GPU-days，单张 RTX A100 | 论文表列方法 | §1, §5.2.1 | medium |

## 公平性与可信度检查

- Table 1 横向比较的是文献汇总结果；不同方法的训练协议、硬件、搜索空间和实现版本未在同一实验中统一重跑，不能仅凭表格作严格因果比较。
- 论文确实在多个 benchmark/任务上评估，但可见正文没有可用于复现的代码链接、LLM token 账或种子方差。应先补齐这些证据再作方法优劣判断。
- “0.05 GPU-days”只描述作者报告的 GPU 搜索成本，不能当作完整系统成本；LLM 推理成本与延迟需要单列。

## 与 AgenticNAS 的关系

- 可复用：把回放得到的 `ArchitectureSpec`、评价指标和受控的设计摘要存成有限大小的 memory，再以随机抽样防止仅复用最优候选。
- 不可直接复用：SEKI 让 LLM 生成架构；本项目仍应保持 Agent 只输出可校验的声明式 `MutationAction`，让 validator、训练评估器和 Pareto 更新保持确定性。
- 最值得验证的假设：在相同候选、训练、GPU 和 LLM 预算下，带随机 memory sampling 的 policy 是否能降低重复率，并提高 Pareto hypervolume。

## 最小复现实验

- 对照：native/random mutation、stateless LLM、memory-aware LLM。
- 固定：4–10 层 Conv1d Transformer 搜索空间、候选数、训练步骤、GPU 时间、LLM 调用数和随机种子集合。
- memory：只保存合法 action、候选 hash、Pareto 指标和枚举错误码；从 top-k 中随机取 ξ 条，不暴露私有代码、原始数据或完整内部日志。
- 指标：action validity、duplicate rate、hypervolume、每个有效候选的成本，以及多 seed 方差。

## 局限与风险

- 预印本状态，作者的 “SOTA” 表述尚未独立复现。
- LLM 直接产出架构缺乏本项目所需的 action schema/validator 边界；复制该做法会放大无效或不可审计动作风险。
- 没有完整的 LLM 成本、代码和种子证据时，不能把作者报告的 GPU-day 解释为公平的端到端预算。

## 可引用摘要

SEKI 提出两阶段的 LLM-guided NAS：先利用当前架构及其评价进行自演化，再从高性能候选库中随机抽样并归纳设计模式来生成新候选。作者在 DARTS、NAS-Bench-201 和 TransNAS-Bench-101 等设置上报告较低 GPU-day 和有竞争力的结果；但其跨论文比较的训练/硬件协议并未统一，且公开正文未给出可核验代码、种子方差和完整 LLM 成本。因此，它更适合作为“有界记忆 + 随机检索”政策的设计灵感，而非已被确认的公平预算结论。

## 检索与人工核验记录

- 原始来源：https://arxiv.org/abs/2502.20422
- 已核对：标题、作者、提交日期、arXiv ID、方法两阶段描述、主要搜索空间、可见训练/成本说明。
- 未核对：公开代码、所有表格数字、种子方差、LLM token/费用、独立复现。
- [ ] 已由人工决定 `retained` / `discarded`
