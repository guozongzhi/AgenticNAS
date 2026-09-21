---
title: "Bi-EZP: LLM-Guided Bilevel Program Evolution for Ensemble Zero-Cost Proxy Discovery"
authors: "Yutao Lai, Kezhao Lai, Hai-Lin Liu"
year: "2026"
venue: "arXiv:2608.21927v1"
paper_url: "https://arxiv.org/abs/2608.21927"
source_pdf: "https://arxiv.org/pdf/2608.21927"
parser: "Codex"
parsed_on: "2026-09-22"
status: codex_draft
tags: [llm-nas, zero-cost-proxy, program-evolution, cma-es, adjacent-method]
---

# Bi-EZP

> 本笔记基于 arXiv v1 PDF；Bi-EZP 搜索的是架构评分代理程序，不是架构本身，故归为 NAS evaluator 邻接方法。

## 一句话结论

- 核心主张：LLM 在上层演化四种 zero-cost proxy 的可执行聚合程序，CMA-ES 在下层校准每个程序的连续参数；冻结后可用于 DARTS 架构排序，但 proxy discovery 本身使用 benchmark accuracies，不能称为全流程 training-free NAS。
- 证据位置：PDF pp.1, 4–12，Figs. 1–5、Tables I–VII。

## 搜索对象、变量与闭环

- 真实搜索对象：聚合四种 base proxies 的 Python program、其 operator/结构和参数 bounds。
- 固定：用于 discovery 的架构 pool 与四 proxy basis；外层以 validation Kendall τ 选择，内层只在 train split 用 CMA-ES 校准。
- 下游 DARTS 才搜索真实架构；Bi-EZP 提供 frozen evaluator，不替代 architecture-search algorithm（PDF p.7）。
- executable gate 检查 AST/interface/bounds；重复失败时使用固定 weighted-sum fallback。semantic duplicate 不拒绝。

## 预算与复现字段

- population `P=20`，outer generations `T=20`；每个结构 CMA-ES 最多 1,500 objective evaluations。
- LLM：GLM-4.7-Flash，temperature 1.0，thinking off；top-p/max output tokens 使用 API defaults。Python/NumPy/PyTorch seed=1；LLM 和 CMA-ES 没有独立 seed。
- NATS-Bench 采样 1,000 architectures、NDS 500、DARTS discovery 100；最终 split 细节见 PDF pp.7–8。
- LLM calls/tokens/费用、GPU-hours、墙钟、correction/fallback rates 未报告。

## 核心结果

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| rank correlation 改善 | TSS CIFAR-10 完整方法 0.809，w/o LLM 0.784 | ECP/AZ-NAS/EZNAS variants | PDF pp.8–11, Tables I–IV | high |
| 可用于下游 DARTS | CIFAR-10/100 test error 2.47%/16.10% | representative NAS methods | PDF pp.10–11, Table V | high |
| 表中 search cost 不含 discovery | 0.06 GPU-days 只计 downstream DARTS；LLM/CMA-ES/proxy extraction 另计 | tabulated baselines | PDF p.9–10 | high |
| budget sweep 非单调 | P=20/T=20 是测试中的折中，50 generations 未持续改善 | P/T sweeps | PDF p.12, Figs. 2–3 | high |

## 公平性、复现性与局限

- discovery 用 ground-truth benchmark accuracies，冻结后才是 zero-cost；必须把一次性 discovery 成本与 downstream cost 分开。
- 只有单一显式 seed，未报告不确定性区间；LLM 无 deterministic seed。
- 0.06/0.07 GPU-days 与其他方法的 tabulated search cost 不包含相同成本边界，不能直接判定总成本更低。
- 作者自己指出 operator grammar 未封闭、program complexity 不受罚、semantic duplicates 不过滤，且未来才考虑 device latency 多目标。

## 与当前 AgenticNAS 的关系

- 可作为低成本 evaluator 候选，尤其适合研究 proxy fidelity 与真实训练排序的偏差。
- 不应放入“LLM 直接提出架构”的主方法对比；应将 proxy-discovery、architecture-search、final-training 三段成本分别报告。

## 链接

- 论文：https://arxiv.org/abs/2608.21927
- 代码（论文给出的匿名归档）：https://anonymous.4open.science/r/Bi-EZP-318D
