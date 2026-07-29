---
title: "AutoLLMResearch: Training Research Agents for Automating LLM Experiment Configuration"
authors: "Taicheng Guo, Nitesh V. Chawla, Olaf Wiest, Xiangliang Zhang"
year: "2026"
venue: "arXiv:2605.11518"
paper_url: "https://arxiv.org/abs/2605.11518"
source_pdf: "../pdfs/2605.11518-autollmresearch.pdf"
parser: "Codex"
parsed_on: "2026-07-26"
status: codex_draft
tags: [hpo, llm-agent, multi-fidelity, transformer]
---

# AutoLLMResearch

> 本笔记由 Codex 基于本地 PDF 生成；该 2026 年工作是较新的 arXiv 预印本。

## 一句话结论

AutoLLMResearch 把 LLM 实验配置建模为长 horizon MDP，让 Agent 从低/中保真离线实验学习可迁移规律，再在最多 5 次高保真查询预算中选择架构、预训练、RL 或数据配置。（PDF pp.1, 3–5, 9）

## 研究问题与贡献

- LLMConfig-Gym 汇集四类任务和超过 100 万 GPU-hours 的已计算结果。
- 四类任务：模型架构、预训练超参、GRPO 超参、数据 mixture。
- 训练流程包含 train/test experiment curation、trajectory simulation、policy distillation 和 multi-turn RL。
- 目标是跨 configuration-space shift 与 optimization-landscape shift 外推。（PDF pp.1, 3–5）

## 方法拆解

- State：历史配置/结果、当前 trial、总预算。
- Action：文本 Think + 结构化 Execute tool call。
- Environment：`tell/exec_config` 查询离线结果并返回可验证 reward。
- 训练：Qwen3-1.7B/4B，先蒸馏再 multi-turn GRPO，允许最多 5 次 Agent–Gym 交互。（PDF pp.5–9）

## 评估与预算

- 测试预算为每任务 1–5 次高保真配置。
- Agent 训练使用单节点 4 × A100 80GB。
- 对照包含 random、top-k warm-start、MetaBO/NAP/FSBO 和强 reasoning/LLM HPO 方法。
- 架构任务从较小 embedding/layer 空间外推到 34–36 层、更大 embedding 的测试空间。（PDF pp.5, 9, 12）

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 覆盖高成本配置环境 | 4 tasks、>1M GPU-hours outcomes | 无同规模公开环境 | pp.1, 9 | high |
| 低保真经验可跨 fidelity | held-out 高保真 normalized regret 优于多类基线 | random/meta/LLM baselines | pp.9–12 | medium |
| 多任务摊销成本 | 30 个任务时估算累计 GPU-hours 降低 3.6× | from-scratch baselines | p.12 | medium |

## 公平性与可信度检查

- 100 万 GPU-hours 是数据来源总量，不是训练该 Agent 本身的新增成本。
- 3.6× 是基于累积成本模型和特定复用假设的估算，不是独立实测集群账单。
- 离线 gym 可能存在表格覆盖和 nearest-valid matching，真实连续空间中的失败更复杂。
- 2026 预印本需要优先核查公开代码、数据许可和复现实验。

## 与本仓库独立课题的关系

- 归类为跨 `LLM × NAS` / `LLM × HPO` 任务的多保真邻接工作：论文用同一类 Agent 分别处理模型架构、预训练 HPO、GRPO HPO 和数据 mixture 四类任务，并未在单个搜索空间中联合优化架构与训练配方。（PDF pp.4–5, Table 2）
- 当前 NAS/HPO 两条线不共享 Agent 训练或结果归因；若复现，架构任务和训练配方任务必须分别记录。
- 可先实现轻量版本：short-train/medium/full 三层 evaluator，不必立即训练专用 RL Agent。
- nearest-valid matching 不应静默替换非法动作；当前 validator 应记录 reject 与显式修复。

## 最小复现实验

- 构建 50–100 个小模型的 3-fidelity outcome table。
- 比较 random、top-k warm-start、Codex extrapolation、TPE/ASHA。
- 固定 5 次 full-train 预算，报告最终质量、总 GPU-hours 和 fidelity rank correlation。

## 局限与风险

- 环境构建成本极高，难在公司项目早期直接复刻。
- 离线表格和真实训练环境之间可能存在 distribution shift。
- 用统一 Agent 跨架构与训练配置任务学习会增加归因难度；当前只把该论文作为多保真与跨任务迁移的方法证据。

## 可引用摘要

AutoLLMResearch 通过 LLMConfig-Gym 和多阶段 Agent 训练，将便宜实验到昂贵实验的配置外推建模为长 horizon MDP。其四类独立任务分别覆盖架构、预训练 HPO、GRPO HPO 和数据 mixture，并在高保真查询受限时报告优势；但结果依赖大型离线 outcome corpus 和成本摊销假设，更适合作为跨任务多保真研究路线，而不是 NAS/HPO 联合搜索的证据。

## 检索与人工核验记录

- 解析问题：多保真环境、架构/HPO 分立任务、预算和成本摊销。
- 使用片段页码：1, 3–6, 9, 12, 23, 32, 33。
- [x] 四任务、>1M GPU-hours 和 1–5 budget 已核对
- [x] Agent 训练硬件和 backbone 已定位
- [ ] 主结果表的 normalized regret 已逐项核对
- [ ] 已由人工决定 `retained` / `discarded`
