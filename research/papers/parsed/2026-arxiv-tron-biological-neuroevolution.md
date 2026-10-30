---
title: "TRON: Transferring Naturally Evolved Network Architectures into Neuroevolution"
authors: "Konstantinos Zacharopoulos, Alexandra Bekou, Jose M. Serradell, Foteini Paraskevopoulou, Apostolos Fournaris, Ioannis Arapakis, Oscar Lao"
year: "2026"
venue: "arXiv:2610.35647v1"
paper_url: "https://arxiv.org/abs/2610.35647"
source_pdf: "https://arxiv.org/pdf/2610.35647"
parser: "Codex"
parsed_on: "2026-10-30"
status: codex_draft
tags: [nas, neuroevolution, biological-prior, topology-search, quarantine, traditional-baseline]
---

# TRON

> 本笔记基于 arXiv v1 官方 PDF。TRON 不使用 LLM/Agent，归传统神经进化 NAS 基线；论文数字均为作者报告，不是本仓库实测。

## 一句话结论

- TRON 把实验 PPI 图映射为稀疏神经拓扑，联合进化连接权重与 protein assignment；当 species 停滞时触发结构突变，并把新拓扑放入 quarantine 独立成熟后再与 parent population 竞争。（PDF pp.4–12, Figures 1–2）
- 作者在 3 个分类和 3 个回归任务上报告 TRON 通常具有更高均值和更低 run variance，但论文没有给出 generations、population、attempted/evaluated 数、独立 run 数、硬件配置或完整 CPU/memory 数值表，无法判断和基线是否端到端等预算。（PDF pp.13–17, Tables 4–9, Figures 3–4）

## 搜索对象、变量与固定项

- 搜索对象是真实神经网络拓扑和连接权重。结构变量包括 depth、layer dimensionality、protein-to-neuron assignment，以及由 PPI 边诱导的 inter-layer connectivity；训练数据、任务目标与 fitness evaluator 固定。（PDF pp.5–8）
- 每个 biological species 对应一个 organism-specific PPI graph；其下再按 depth、layer dimension 和 connectivity 划分 topology species。PPI 的 k-core、layer pools 与 biological reachability 同时限制初始化和结构突变。（PDF pp.5–8）
- weight mutation 在 element/neuron/block/layer 四个尺度扰动参数；protein mutation 改变 assignment 后重建连接并检查 forward connectivity、output reachability 和 PPI consistency。因此它是 NAS，不是固定架构 HPO。（PDF pp.9–11, Tables 1–2）

## Proposal、feedback、memory 与停止机制

- proposal 来自经典 reproduction/mutation，不使用语言模型。fitness feedback 更新个体、lineage 和 species 的 best score；停滞达到阈值后才触发 protein/topology mutation。（PDF pp.8–12）
- lineage identifier 与 lineage-size penalty 是显式 genealogy/diversity memory；ordinary generations 在 lineage 内替换，周期性 global selection 才跨 lineage 竞争。（PDF pp.8, 11–12）
- 结构突变 offspring 进入 quarantine cooldown，只有 fitness 超过 parent species 的 eligible member 才回迁。这为大结构变更提供 maturity gate，但会引入额外 evaluations。（PDF pp.9, 11, 16）
- 论文写明结构验证条件，却没有报告 invalid/rejected、duplicate、retry、OOM/divergence 或 quarantine attempted/accepted 数；总 generations、population 与停止阈值的实验取值也未报告。

## 评估、预算与硬件

- 分类任务为 CORA/CITESEER/PUBMED，回归任务为 DIABETES/FRIEDMAN/CALIFORNIA；对照为 CMA-ES、ES-MLP、DE、PSO、NEAT。（PDF pp.4, 13–15）
- 作者报告分类 mean：CORA 0.8262、CITESEER 0.7250、PUBMED 0.8313；对应 strongest listed baseline 为 0.7429/0.7065/0.7728。回归中 DIABETES/FRIEDMAN 为 0.5614/0.8962，CALIFORNIA 为 0.7336，与 strongest listed CMA-ES 0.7288 接近。（PDF pp.13–14, Tables 4–9）
- Figures 3–4 比较 CPU seconds 与 memory usage，但正文/PDF 文本没有给出可复核的数值表；作者只定性指出 TRON memory 更高、quarantine 增加 evaluation burden。GPU-hours、wall-time、energy、peak memory、总训练次数均未报告。（PDF p.16, Figures 3–4）

## 公平性、复现性与局限

- 表格给 min/max/median/mean/SD，却没有说明独立 run 数或 seeds；也没有证明各方法的 objective evaluations、population、CPU/墙钟预算匹配。
- 论文未消融 biological prior、speciation 与 quarantine，作者也明确承认无法拆分三者贡献，因此不能把性能差异单独归因于 PPI prior。（PDF p.16）
- 未发现作者官方代码或配置链接；完整 PPI 数据版本、实验超参数和逐 candidate ledger 不可核验。

## 对本仓库的价值

- 可复用的是 quarantine maturity gate 与 lineage-aware replacement：typed Conv1d 的 depth/width/op/connectivity 大改动可先在隔离队列中固定短训，达到同预算 acceptance rule 后再进入 Pareto archive。
- 不能迁移的是 PPI prior 的效果结论；应在同一 4–10 层 typed space 中对 random/native evolution、无 quarantine、quarantine、stateless/memory-aware Agent 做 attempted/valid/trained/GPU/LLM/wall-time 匹配。
- 最小实验还应报告 quarantine attempted/accepted/rejected、duplicate、invalid/OOM、真实 latency/peak memory/energy、hypervolume 与 seed variance。

## 检索与人工核验记录

- 官方 PDF：19 页，SHA-256 `9a2c4377849637691c498396e9d3a454209082dffcc7dc297a9ae7890604a814`。
- arXiv Atom 于 2026-10-30 核对为 v1；未找到作者官方代码。
- [x] 搜索对象、结构变量和固定项已核对
- [x] Tables 4–9 与主要结果已核对
- [x] 缺失预算、失败账本与消融已明确标记
- [x] 作者结果与仓库实测已区分
- [ ] 人工决定 `retained` / `discarded`
