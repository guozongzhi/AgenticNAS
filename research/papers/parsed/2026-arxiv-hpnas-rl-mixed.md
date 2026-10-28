---
title: "Hyperparameter and Neural Architecture Search via Evolutionary Optimization for Reinforcement Learning: HPNAS-RL"
authors: "Nihal Acharya Adde, Hanno Gottschalk"
year: "2026"
venue: "arXiv:2610.36882v1"
paper_url: "https://arxiv.org/abs/2610.36882"
source_pdf: "https://arxiv.org/pdf/2610.36882"
code_url: "not found"
parser: "Codex"
parsed_on: "2026-10-28"
status: codex_draft
tags: [mixed-search-space, nas, hpo, reinforcement-learning, evolution, multi-objective]
---

# HPNAS-RL

> 本笔记基于 arXiv v1 官方 PDF。方法同时改变 architecture 与 PPO recipe，必须归 `mixed-search-space`。

## 搜索空间与算法

- NAS branch 搜索由 normal/reduction cells 组成的 8-cell CNN：可变 convolution/pooling/skip operations 与 DAG connectivity；HPO branch 搜索 batch size 64–512、discount 0.95–0.999、learning rate `1e-5`–`1e-2`、time horizon 32–256。PPO epochs=3 和 entropy coefficient=0.01 固定。（PDF pp.5–10, Tables 1–2）
- 两支共享 `-reward/FLOPs/parameters` 三目标 fitness；architecture 用 discrete crossover/mutation，HPO 用 SBX 与 polynomial mutation，20% survival、10% random offspring。EEPI 拒绝超过 5M 参数的架构，OTL 用上一代 best policy 的 behavior cloning 和 optimizer state 初始化下一代。（PDF pp.5–11）
- 论文未使用 LLM/Agent、自然语言 reflection 或 memory；population survival/weight transfer 只是 evolutionary state reuse。

## 预算与证据

- 六组 `(generations,population)` 为 `(6,6)/(10,4)/(10,10)/(10,15)/(15,15)/(15,20)`，候选以 40 PPO epochs、84×84×3 输入和固定 depth=8 做 low-fidelity 评估；所有训练并行运行于 NVIDIA H100，但 GPU 数、GPU-hours、wall-time、seeds、attempted/failed/OOM/duplicate 均未报告。（PDF p.11）
- 搜索阶段只与 NAS-only EMNAS 比较；作者明确不把先前 HPO-only 结果放入 low-fidelity search comparison，因为训练预算不兼容。较大预算 Exp.6 中作者报告 HPNAS reward 787、0.53M params、0.44 GFLOPs，对 NAS 604、0.51M、0.42G。（PDF pp.11–13, Table 3）
- 最佳 joint configuration full-train 后 peak reward 1205，对 NAS-only 1190、HPO-only 1190、manual 1140；但缺 search seeds 和完整成本，不能解释为稳定或等预算优势。（PDF p.13）

## 边界与复现价值

- 结构字段与训练字段在同一 fitness loop 联合变化，不能作为本仓库固定配方 NAS 或固定架构 HPO 的独立证据。
- 可借鉴的是“两轨独立编码 + 同一 evaluator”的实现形式；本仓库应先拆成 architecture-only 与 recipe-only 两个 matched-budget 实验，再把 joint search 留作未来工作。
- 最小复现需固定 Unity task/data split/evaluator，分别给 random/NSGA-II 与 random/TPE/CMA-ES 相同 attempted trials、epochs、GPU-hours 和 seeds，并公开 EEPI reject、训练失败、重复与 OTL 继承账本。

## 检索与人工核验记录

- 官方 PDF：16 页，SHA-256 `aa3a0f256f63f6338832ebadea2ccdd20f60f5289b94590e155e05e6754d15d2`。
- 本轮未找到作者官方代码；论文中的 BNN surrogate 仅为 future work，当前方法未启用。
- [x] 关键搜索字段、预算与 Table 3 已核对
- [x] mixed 与独立 NAS/HPO 证据边界已区分
- [ ] 人工决定 `retained` / `discarded`
