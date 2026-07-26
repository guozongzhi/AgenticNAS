---
title: "MLAgentBench: Evaluating Language Agents on Machine Learning Experimentation"
authors: "Qian Huang, Jian Vora, Percy Liang, Jure Leskovec"
year: "2023"
venue: "arXiv:2310.03302"
paper_url: "https://arxiv.org/abs/2310.03302"
source_pdf: "../pdfs/2310.03302-mlagentbench.pdf"
parser: "Codex"
parsed_on: "2026-07-26"
status: codex_draft
tags: [benchmark, ml-agent, experimentation]
---

# MLAgentBench

> 本笔记由 Codex 基于本地 PDF 生成，关键数字仍需人工抽查。

## 一句话结论

MLAgentBench 用 13 个可执行 ML 任务评测 Agent 的读写文件、运行代码、解释输出和迭代改进能力；最佳报告结果仍只有 37.5% 平均成功率，主要瓶颈是长期规划与幻觉。（PDF p.1）

## 研究问题与贡献

- 每个任务包含任务描述、starter files/data 和自动 evaluator。
- Agent 基于 ReAct，在隔离 workspace 中执行读写文件和 Python 命令。
- 评价 competence（相对 starter baseline 至少改善 10%）与 efficiency（时间和 LM tokens）。（PDF pp.1–2）

## 方法拆解

- 搜索对象不是固定超参空间，而是完整实验方案、代码和训练配置。
- Observation 包含文件、执行输出和指标；Action 是工具调用和代码修改。
- 保存完整 interaction trace 与 workspace snapshots，支持失败分析。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 最强 Agent 仍不稳定 | Claude 3 Opus 平均成功率 37.5% | 多个 Claude/GPT/Gemini/Mixtral Agent | p.1, Abstract | high |
| 任务新旧影响显著 | 旧数据集最高可到 100%，新 Kaggle challenge 可为 0% | 跨任务比较 | p.1 | high |
| 失败集中于 Agent 能力 | 长期规划、结果解释和 hallucination 被识别为关键挑战 | trace analysis | pp.13–16 | medium |

## 公平性与可信度检查

- 模型版本、token/时间成本需要随时代重新测量，原排名会快速过时。
- “相对 baseline 改善 10%”在不同指标尺度上并非完全同质。
- benchmark 可能被后续模型训练数据收录，需保留 post-cutoff 或私有任务。

## 与 AgenticNAS 的关系

- 可借鉴 workspace + tool trace + automatic evaluator 三层评测结构。
- AgenticNAS 应将成功定义为合法候选、真实指标改善和预算内 hypervolume，而非只看是否完成任务。
- 建议加入隐藏架构任务，降低模型背诵公开 benchmark 的影响。

## 最小复现实验

- 建立 5 个固定 NAS debugging/configuration 任务，每个含 starter search state 和 evaluator。
- 比较 Codex、内部 Agent、随机策略在成功率、GPU-hours、token 和人工干预次数上的表现。
- 保留完整 action/result trace，但对内部字段进行匿名化。

## 局限与风险

- 它是 Agent benchmark，不是 HPO 算法，也不搜索专门的神经架构空间。
- 允许自由改代码，安全边界比当前声明式动作宽。
- 公开 benchmark 的污染风险会随时间增加。

## 可引用摘要

MLAgentBench 将端到端机器学习实验组织为可执行任务，并同时衡量性能改善和 Agent 成本。其结果表明，即使强语言模型也容易在长期规划和结果解释上失败，因此 AgenticNAS 需要自动 evaluator、可回放 trace 和隐藏任务，而不能只依赖主观工作流展示。

## 检索与人工核验记录

- 解析问题：实验 Agent 的任务定义、成功率、成本和失败模式。
- 使用片段页码：1, 2, 5, 6, 8–10, 13, 14, 16。
- [x] 任务数和 37.5% 成功率已核对
- [ ] 各模型完整排名已核对
- [x] 主要失败类别已定位
- [ ] 已由人工决定 `retained` / `discarded`
