---
title: "NOVA: A Verification-Aware Agent Harness for Architecture Evolution in Industrial Recommender Systems"
authors: "Shaohua Liu et al."
year: "2026"
venue: "arXiv:2606.27243v3"
paper_url: "https://arxiv.org/abs/2606.27243"
source_pdf: "https://arxiv.org/pdf/2606.27243"
parser: "Codex"
parsed_on: "2026-09-22"
status: codex_draft
tags: [llm-nas, recommender, mixed-search-space, verification, memory, production]
---

# NOVA

> 本笔记由 Codex 基于 arXiv v3 PDF 的带页码文本生成；生产数据和在线结果均为作者报告。

## 一句话结论

- 核心主张：NOVA 用语义校验、候选排序、局部测试、离线训练和轨迹记忆提高工业推荐架构修改的有效通过率；但其空间同时包含图结构、feature configuration、训练目标和结构超参，因此必须归为 `mixed-search-space`。
- 证据位置：PDF pp.3–10，尤其是 Fig. 2、Tables 1–5。

## 搜索对象与变量审计

- 真实对象：生产 RankMixer-style 推荐模型的可执行代码实现。
- L2 ScaleUp 可变：`token_cnt`、`token_dim`、RankMixer block 数等耦合结构字段，模型大小限制在基线 ±10%。
- L3 Literature-to-Production 可变：把 TokenMixer-Large/MixFormer 交互模块接入生产骨干，同时可能修改 computation graph、feature configuration 和训练约束。
- 固定：同一月度 billion-scale 生产数据、1000+ feature fields、相同离线评估上限；候选均从头训练。
- 分类：结构与训练/feature 字段没有冻结，不能作为纯 NAS 或固定架构 HPO 证据。

## Agent 与优化闭环

- 每轮生成 4 个候选；语义规则过滤，evidence-guided ranker 选 Top-1，再做 local testing 与最多一次 offline evaluation。
- trajectory memory 把语义诊断、本地测试和离线 AUC 结果压缩成下一轮方向与 forbidden patterns。
- 失败分为 semantic、local/execution、offline ineffectiveness；瞬时基础设施失败不进入记忆，但仍保留候选结果记录。
- 证据位置：PDF pp.3–6。

## 预算、公平性与硬件

- 每个 setting 20 个 task；每 task 最多 10 轮、每轮 4 candidates、至多一次 offline evaluation；阈值为相对基线 `+0.15 pp AUC`。
- 自动方法的最大 offline-evaluation budget 对齐；human reference 是回顾性材料，不匹配预算。
- 所有 LLM-dependent stages 通常使用 Claude Sonnet 4.6；四模型 ranking ensemble 例外。
- LLM inference cost **未在方法间匹配**。NOVA 单 task 平均分阶段成本见 Table 5：Initialization $8.17、Solution Design $4.68、Code Generation $9.30、Quality Review $4.80 等。
- GPU 型号、GPU-hours、单候选墙钟、真实 serving latency/memory/energy：未报告。

## 核心结果

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| L2 有效通过率最高 | EPR 53.3%，R&D-Agent 29.2% | OpenHands/ReAct/R&D-Agent/Optuna-TPE | PDF p.6, Table 1 | high |
| L3 有效通过率最高 | EPR 51.7%，R&D-Agent 28.3% | coding-agent baselines | PDF p.6, Table 1 | high |
| 轨迹记忆贡献明显 | 去掉 trajectory memory + structured feedback 后 EPR 51.7%→23.8% | 同预算 ablation | PDF pp.6–7, Table 2 | high |
| 有生产在线结果 | 5% traffic、6-day A/B，GMV 报告 +1.25%/+1.70%/+2.02% | production baseline | PDF p.8, Table 4 | medium |

## 复现性与局限

- 提供规则、流程和 per-stage token/cost，但生产代码、数据和完整 prompts 受限；公开复现性有限。
- 专家 post-hoc semantic labels 提高了统计一致性，但不等同于可公开复跑的自动 oracle。
- offline evaluation 数对齐不代表总 GPU/LLM/工程成本对齐；不能把结果转述为纯架构搜索优势。
- 置信度：预算/表格高；跨组织泛化低到中。

## 与当前 AgenticNAS 的关系

- 强相关的是“语义 gate → execution gate → expensive evaluator”及失败分层记账。
- 候选数和 offline evaluator 对齐仍不够；本仓库应额外匹配 LLM calls/tokens、GPU-hours、墙钟并报告重复率。
- 不应把 NOVA 的生产 AUC/GMV 写成仓库结果，也不应用它支持 fixed-recipe Conv1d Transformer NAS。

## 链接

- 论文：https://arxiv.org/abs/2606.27243
