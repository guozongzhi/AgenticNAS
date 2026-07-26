---
title: "AgentHPO: Large Language Model Agent for Hyper-Parameter Optimization"
authors: "Siyi Liu, Chen Gao, Yong Li"
year: "2024"
venue: "CPAL 2025"
paper_url: "https://arxiv.org/abs/2402.01881"
source_pdf: "../pdfs/2402.01881-agenthpo.pdf"
parser: "Codex"
parsed_on: "2026-07-26"
status: codex_draft
tags: [hpo, llm-agent, experiment-automation]
---

# AgentHPO

> 本笔记由 Codex 基于本地 PDF 生成，关键数字仍需人工抽查。

## 一句话结论

AgentHPO 用 Creator 负责根据任务和历史日志提出超参，Executor 负责改配置、训练、分析和记录，在 10-trial 预算内展示了 LLM Agent 自动迭代 HPO 的可行性。（PDF pp.1, 3–6）

## 方法拆解

- Creator 输入自然语言任务、搜索空间和实验日志，输出配置及理由。
- Executor 使用工具修改配置、训练/测试、分析曲线并记录结果。
- 日志同时保存超参、理由、metrics 和训练分析，作为下一轮动态 memory。
- 最终 Creator 输出最优配置、解释和后续建议。（PDF pp.4–6）

## 评估与预算

- 12 个跨领域 ML HPO tasks，包含部分晚于 GPT 知识截止的数据。
- AgentHPO 每 run 10 trials，在 `1/3/5/10` milestones 记录 best-so-far。
- random search 和 Bayesian optimization 各执行 10 runs × 10 trials，用 100 次结果近似 “human best”。（PDF p.6）

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| GPT-4 10 trials 优于 random | 平均改善 6.66% | random search | p.8, Sec. 5.1 | high |
| GPT-4 可超过 human best | 平均改善 1.52% | 100-trial human-best proxy | p.8 | medium |
| 完整训练日志有帮助 | 优于只记录 HP-score 的 OPRO | OPRO | pp.8–9, Fig. 4 | medium |
| post-cutoff 数据仍有效 | Butterfly 85.92±0.57%，human 78.27% | human result | p.8 | high |

## 公平性与可信度检查

- “human best”实际由 100-trial baseline peak 近似，并非真实专家统一预算。
- LLM 只有 10 trials，而 baseline 同时报告 100 trials peak；不同图表的比较口径需仔细区分。
- 使用 GPT-3.5/GPT-4 专有模型，提示词和模型版本对结果影响较大。

## 与 AgenticNAS 的关系

- Creator/Executor 可映射为 proposal policy 与现有 evaluator，但 Executor 不应自由修改公司源码。
- 完整 learning curve 可先在内部压缩为 overfit/underfit/diverged 等枚举信号。
- 其 memory 结构适合训练参数 Agent，不应与架构历史混在同一 archive。

## 最小复现实验

- 建立 `TrainingConfigAction`：learning rate、batch size、weight decay、warmup、epochs。
- 对比只给 final metric 与加入曲线摘要的 Codex Agent。
- 固定 10 trials，另设 random/TPE 10-trial 与 TPE 100-trial 参考上限。

## 局限与风险

- 自由工具执行与内部源码安全边界不兼容。
- 百分比改善跨不同 metrics 聚合，解释不如逐任务 standardized regret 清晰。
- 10-trial 优势可能来自模型先验，需隐藏任务验证。

## 可引用摘要

AgentHPO 将 HPO 拆分为提出配置的 Creator 和执行、分析、记录实验的 Executor，并把训练日志作为持续更新的记忆。论文在 12 个任务和 10-trial 设置中报告了较强结果，但 “human best” 与 Agent 的预算口径不同，且专有 GPT 模型和自由工具执行限制了 clean-room 复用。

## 检索与人工核验记录

- 解析问题：Creator/Executor、日志 memory、trial 预算和基线公平性。
- 使用片段页码：1–6, 8–10, 14。
- [x] 10-trial 与 baseline 100-trial 口径已核对
- [x] GPT-4 平均改善数字已核对
- [ ] 12 个任务逐项结果已核对
- [ ] 已由人工决定 `retained` / `discarded`
