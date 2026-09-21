---
title: "Self-Evolving Recommendation System: End-To-End Autonomous Model Optimization With LLM Agents"
authors: "Haochen Wang, Yi Wu, Daryl Chang, Li Wei, Lukasz Heldt"
year: "2026"
venue: "RecSys 2026 / arXiv:2602.10226v3"
paper_url: "https://arxiv.org/abs/2602.10226"
source_pdf: "https://arxiv.org/pdf/2602.10226"
parser: "Codex"
parsed_on: "2026-09-22"
status: codex_draft
tags: [llm-agent, recommender, mixed-search-space, production, architecture, hpo]
---

# Self-Evolving Recommendation System

> 本笔记基于 arXiv v3/RecSys 2026 PDF；线上指标和成本均为作者报告。

## 一句话结论

- 核心主张：Gemini 驱动的 Offline Fast Loop 与 Online Slow Loop 在 YouTube 生产系统中共同搜索 optimizer、architecture、reward 和训练 recipe；这是重要的端到端 MLE 证据，但不是固定训练配方 NAS，也不是固定架构 HPO。
- 证据位置：PDF pp.3–8，Fig. 1、Tables 1–5。

## 搜索对象、变量与层级

- 可变：optimizer 类型与参数、batch size、epochs、模型拓扑/interaction layer、reward function 及其超参。
- 固定：底层 ranking/RL 生产系统及离线 loss/在线 north-star 框架；更多 production 细节未公开。
- 空间是开放式代码/semantic configuration，不是可枚举 typed NAS space；结构、训练和 reward 同时变化，分类为 `mixed-search-space`。

## Agent 闭环

- Offline Agent 每日运行、每 5 分钟唤醒，实例化 optimizer/architecture/reward personas，生成代码并调用 loss/query evaluator。
- Online Agent 每日按 Experiment Journal 排名 top-K，决定训练、上线、继续观察或清理。
- 共享 Journal 保存成功、失败、离线和在线结果；论文指出约 400k context tokens 后会出现 hallucination，故使用专门 persona。
- 失败率、无效动作率、重复率和自动修复次数：未报告。

## 目标与预算

- 目标：offline proxy loss/相关性与延迟的在线 north-star business metrics。
- 主消融：6 次独立运行，每次探索 70 ideas（optimizer component）。完整生产阶段总 attempted/evaluated candidates 未报告。
- 人类流程约 `Θ(1)–Θ(10)` experiments/week，Agent 约 `Θ(100)`/week；工程人工成本表述为 0 hours/week，不等价于总系统成本。
- LLM tokens/费用：六个月约 `$20,000`；逐候选 tokens、GPU-hours 和墙钟未报告。per-model compute/memory 据称与人类流程相同，但模型数增加会线性增大基础设施成本。
- 证据位置：PDF pp.7–8, Tables 4–5、Sec. 5.5。

## 核心结果

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 结构发现产生在线增益 | Gated Path: YouTube +0.06%、surface +0.14%；Wide & Deep: +0.08%/+1.10% | human-engineered baseline | PDF p.7, Tables 1–2 | high for reported numbers |
| recipe 优化缩短训练时间 | 调 batch/epochs/optimizer 后作者报告 8× training-time improvement | 原生产 recipe | PDF p.6, Sec. 5.2.2 | medium |
| 完整历史有助于 proposal | 6 runs × 70 ideas 的 Gemini/context ablation | no/top-k/unsorted context | PDF pp.7–8, Table 4 | medium |

## 公平性、复现性与局限

- 与人类流程的候选、训练、GPU 和时间预算未匹配；不同组件和生产面使用不同证据口径。
- 论文给出 prompts 和示例，但生产代码、数据、完整 traces 与模型配置不可公开复现。
- 在线 A/B 结果支持生产可行性，不隔离 LLM、Agent loop、工程基础设施和扩大实验吞吐的独立贡献。
- 置信度：表内作者数字高；因果归因和外部泛化低到中。

## 与当前 AgenticNAS 的关系

- Journal、双速反馈和 personas 可启发 memory-aware proposal policy。
- 本仓库必须拆成 architecture-only 与 training-only 两条轨道，禁止复刻其共享 mixed archive/reward 作为当前实验设计。
- `quality_proxy`/`latency_proxy_ms` 仍只是流程占位符；本论文的生产指标不能替代本仓库实测。

## 链接

- 论文：https://arxiv.org/abs/2602.10226
- DOI：https://doi.org/10.1145/3773078.3831919
