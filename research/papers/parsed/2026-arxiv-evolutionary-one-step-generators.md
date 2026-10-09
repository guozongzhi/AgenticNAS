---
title: "Evolutionary One-Step Generators: Fast and Diverse Sampling for Discrete Design"
authors: "Marcus Vukojevic, Erik Nielsen, Veronica Lachi, Andrea Passerini, Giovanni Iacca"
year: "2026"
venue: "arXiv:2610.08367v1"
paper_url: "https://arxiv.org/abs/2610.08367"
source_pdf: "https://arxiv.org/pdf/2610.08367"
parser: "Codex"
parsed_on: "2026-10-09"
status: codex_draft
tags: [nas, proposal-generator, evolutionary-strategy, validity, duplication-control, adjacent-baseline]
---

# Evolutionary One-Step Generators (EGO)

> 基于 arXiv v1 的 64 页 PDF。主任务是离散/分子生成；NAS-Bench-101 只验证 offline proposal generator，因此归 NAS proposal-generator 邻接证据，不是端到端 NAS 或 LLM-NAS。

## 搜索对象与实验协议

- EGO 用 antithetic low-rank evolution strategy 训练 one-step generator，hard graph criterion 同时考虑结构约束与分布 Energy；NAS 实验从 offline high-performing NAS-Bench-101 corpus 学 proposal distribution，而非在线训练候选或闭环更新 evaluator（PDF pp.3–9、58–61）。
- generator 将 128-d noise 映射为 7-node graph 的 21 edge bits 与 5 operation choices。数据按 seed 2026 做 80/10/10 architecture split；test-partition labels 只作最终评估，canonical hash 在 pruning 后去重（pp.58–60）。
- EGO/STE/Soft 各 3 seeds、15,000 updates、每个最终模型 10,000 proposals；update count 相同，但 EGO 评估 184.32M candidate graphs，STE/Soft 各 0.96M，故不是 matched objective-evaluation budget（p.60）。

## 核心结果与成本

- EGO validity 72.35%、valid-and-unique yield 55.51%、held-out elite yield 2.22%；STE 为 77.45/33.25/1.38，Soft 为 89.56/25.12/1.44（p.9, Table 2）。EGO 得到 221.7±7.5 distinct test elites，对比 138.0±28.9/143.7±18.6。
- 代价是 mean test accuracy 91.85%，低于 STE 92.38 与 Soft 92.70；feature MMD 也更差。它证明“更多不重复候选”，不是“平均更准”（p.9）。
- update time 46.12s vs 34.06/34.37s；另有 compilation/validation 时间，表中没有端到端总和。未报告 GPU 型号、energy、peak memory、代码 URL或可锁定 commit（pp.60–61）。

## 当前价值

- 对本仓库可复用的指标是 `valid-and-unique / all attempts` 与 canonical-hash duplication；invalid 和 duplicate 必须留在分母。
- 若作为 proposal baseline，generator pretraining 的 184.32M objective evaluations 必须摊入成本，并与 native/random/LLM proposer 采用 matched attempts、训练与 wall-time；不能只比较 one-step inference。

## 链接

- 论文：https://arxiv.org/abs/2610.08367
