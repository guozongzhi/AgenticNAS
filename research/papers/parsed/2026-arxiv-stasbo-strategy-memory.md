---
title: "STaSBO: LLM-Guided Strategy Planning and Configuration Selection for Bayesian Optimization"
authors: "Youngseok Yoon, Peng Li"
year: "2026"
venue: "arXiv:2611.19214v1"
paper_url: "https://arxiv.org/abs/2611.19214"
source_pdf: "https://arxiv.org/pdf/2611.19214"
parser: "Codex"
parsed_on: "2026-11-23"
status: codex_draft
tags: [agentic-bo, llm, strategy, memory, surrogate-selection, acquisition-selection]
---

# STaSBO

> 本笔记基于 arXiv v1 官方 PDF。STaSBO 控制通用 BO 的 surrogate–acquisition 配置，数值 BO 负责候选生成；它不是神经架构搜索，也不是固定架构训练 HPO。

## 搜索对象与 Agent loop

- 外层目标仍是昂贵黑箱函数。LLM 不直接提出 evaluation point，而是在每轮先规划 search behavior，再从 surrogate profile × acquisition profile 的联合空间选配置；候选点由对应数值 BO 产生且只评估一个。（PDF pp.2, 4–6）
- memory 分为 history memory（observations + decision records）和 strategy memory（trajectory summary + behavioral plans）。每轮记录 intent、配置、prospective candidate diagnostics 与 outcome，下一轮据此保留或修订策略。（PDF pp.4–5）
- 每轮包含 planning、shortlisting、joint selection 三个 LLM decisions；fit evidence 与 candidate diagnostics 由数值程序计算。没有改变被优化模型的结构或训练 recipe，因此这里只归 `Agentic BO` 邻接证据。（PDF p.5, Algorithm 1）

## 预算、公平性与结果

- 12 个 synthetic 与 10 个科学/工程任务；每个 task/seed 有 5 个共同初始点和 45 个新增 evaluation，共 50 次 objective evaluations，10 seeds。所有 LLM 方法使用 `gpt-6-luna`、medium reasoning。（PDF pp.6–7）
- 作者报告 synthetic/application 平均 rank 分别为 2.17/2.60；最强对照分别为 TuRBO 4.08、BO-UCB 4.10。跨 22 任务的 final normalized regret 为 0.449，TuRBO 为 0.525。均为作者结果。（PDF pp.6–8, Tables 2–3, Figure 3）
- Ackley-8D 的 matched-budget ablation 为 10 seeds；full STaSBO final simple regret `8.25±5.75`，去掉 planning 为 `12.27±7.55`，去掉 candidate diagnostics 为 `11.68±7.79`。这只证明该任务上的组件贡献，不能外推到 NAS。（PDF p.8, Table 4）
- objective-evaluation budget 和 seeds 匹配，但 3 次 LLM decisions/iteration 的 tokens、费用、墙钟、失败/retry、GPU/CPU 资源未报告；因此未形成完整成本公平性证据。

## 复现缺口与课题价值

- 论文未给出公开代码 URL；2026-11-23 的 GitHub repository search 未识别出作者官方实现。
- 对本课题最有价值的是把 memory 显式拆为“历史事实”和“可修订策略”，并让数值候选 diagnostics 约束 LLM 决策。迁移到 typed Conv1d 时应只让 Agent 选择合法 mutation policy，而不是同时改 evaluator/recipe。
- 最小复现需要 random/native mutation、stateless LLM 与 memory-aware LLM 同候选/训练预算；另记录每次 LLM call、token、retry、duplicate 与 action validity。
- 官方 PDF：34 页，SHA-256 `5b98b8f0a41aa3a0e715e183953ba8e66224efa23a491a31e281398f3241f56a`。

- [x] 搜索对象与 BO 配置控制已区分
- [x] objective-evaluation budget 与 ablation 已核对
- [ ] 人工决定 `retained` / `discarded`
