---
title: "Agentic Bayesian Optimization through Surrogate-Augmented Autoresearch"
authors: "Paul Brunzema, Louis Tiao, Nhat Le, Kevin De Angeli, Yao Xuan, Djordje Gligorijevic"
year: "2026"
venue: "arXiv:2608.00316v2"
paper_url: "https://arxiv.org/abs/2608.00316"
source_pdf: "https://arxiv.org/pdf/2608.00316"
parser: "Codex"
parsed_on: "2026-09-22"
status: codex_draft
tags: [agentic-bo, hpo, bayesian-optimization, mixed-search-space, pareto]
---

# Agentic Bayesian Optimization through Surrogate-Augmented Autoresearch

> 本笔记基于 arXiv v2 PDF；Sara 是通用 agentic BO 方法，而 LCBench 实验同时改变网络宽度与层数，故不计入严格固定架构 HPO。

## 一句话结论

- 核心主张：Sara 让 LLM 控制问题定义、bounds、acquisition、候选提交与动态重构，同时把不确定性建模交给 BoTorch 后端 lenz；它是“Agent + classical optimizer”混合设计的强邻接证据。
- 证据位置：PDF pp.1–16, 23–29，Figs. 1, 5–6, 13, 18，Tables 1–4。

## 搜索对象、变量与分类

- 通用对象：昂贵 black-box 的连续参数，包括单目标、约束、多目标、HPO 和化学反应条件。
- LCBench：固定 funnel-shaped feed-forward family，但搜索 `max_units` 和 `num_layers`，另含 learning rate、batch size、momentum、weight decay、dropout；按本仓库规则为 `mixed-search-space`。
- synthetic multi-objective：2/4/6/8-D 两个 GP sample paths，以 hypervolume 衡量；不是 NAS。
- 固定项：各 benchmark oracle、per-problem evaluation budget 和给 LLM 方法的自然语言 prior。

## Agent 闭环

- Agent 读取 trial history、surrogate diagnostics 和自然语言上下文；可请求/覆盖 proposal，修改 bounds/acquisition/objective/constraint partition。
- `commit` 消耗一次 black-box evaluation；predict/score/diagnostics 等只消耗 tokens/backend compute，不占 evaluation budget。
- 失败、非法候选与重复 proposal 的具体总数：未报告。

## 预算与公平性

- LCBench 每 task 80 evaluations；synthetic 为 50–200，多目标为 40/60/80/120，reaction yield 为 40（PDF p.23, Table 4）。
- Sara、Sobol、Ax、LLAMBO、Centaur 使用相同 evaluation budget；但 Ax 有 5 个 Sobol init，Centaur 前 10 次是 CMA-ES，warm start 机制不同。
- 默认高能力 LLM 为 Claude Opus 4.8/high reasoning；另测 Sonnet 4.6、Haiku 4.5、GPT-5.5。
- Figure 18 给每 run token 总量；GPT-5.5 约为 Opus 4.8 的 1.5–2×。货币费用、GPU-hours、wall-clock parity 未报告。

## 核心结果

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 无 prior 时保留经典 BO 可靠性 | synthetic 上总体与 Ax 相近，LLM-only 方法明显较弱 | Ax, Sobol, LLAMBO, Centaur | PDF pp.12, 15, Figs. 5, 11 | medium-high |
| LCBench 初期强、最终趋同 | Sara/LLAMBO warm start 强，80 eval 后 Sara、LLAMBO、Ax 接近 | same-budget baselines | PDF p.13, Fig. 6 | high |
| 支持多目标与动态重构 | agent 可改变 objective/constraint partition；多目标报告 hypervolume | bash-only/full system | PDF pp.3, 15–16 | medium |

## 复现性与局限

- benchmark 身份通过随机 token/sandbox 隐藏，降低直接识别风险；公开 benchmark 仍可能存在预训练记忆。
- 图中报告多 seed 分布，但正文/附录需进一步核对各任务 seed 数；LLM nondeterminism 明确承认。
- 相同 evaluation 次数不等于相同 token、backend calls 或墙钟成本；Figure 18 也显示模型间 token 差异。
- LCBench 结构字段使其不能支撑本仓库 fixed-architecture HPO 总结。

## 与当前 AgenticNAS 的关系

- 最值得复用的是 Agent 决策层与显式 uncertainty-aware backend 的分工，以及 evaluation action 与 free diagnostic action 分开记账。
- 可用于 Pareto controller 邻接设计，但必须在本仓库 typed architecture space、固定 training recipe 和相同 candidate/GPU/LLM budget 下重测。

## 链接

- 论文：https://arxiv.org/abs/2608.00316
