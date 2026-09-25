---
title: "FINNAS: FINN-Guided Hardware-Aware NAS and Pruning for FPGA Jet Substructure Classification"
authors: "Eva Chauffour, Changhong Li, Georgios Floros, Shreejith Shanker"
year: "2026"
venue: "ICECS 2026; arXiv:2609.16367v1"
paper_url: "https://arxiv.org/abs/2609.16367"
source_pdf: "https://arxiv.org/pdf/2609.16367"
parser: "Codex"
parsed_on: "2026-09-25"
status: codex_draft
tags: [nas, evolutionary, hardware-aware, fpga, quantization, latency, adjacent-baseline]
---

# FINNAS

> 本笔记基于 arXiv v1/ICECS 2026 PDF。FINNAS 是非 LLM 的硬件感知 evolutionary NAS，应作为传统 NAS 邻接基线，而不是 Agent policy 证据。

## 一句话结论

- 核心主张：FINNAS 在 2–6 层量化 MLP 空间中联合搜索 depth、width 与全局 bit-width，用 16-epoch proxy accuracy 加 FINN 估算 LUT/latency 排序，再对 finalist 做完整训练、剪枝、RTL simulation 和 Vivado OOC synthesis。
- 证据位置：PDF pp.1–4，Tables I–III、Figs. 1–2。

## 搜索对象与固定变量

- 架构变量：hidden depth `L∈{2,3,4,5,6}`；每层 width 从 13 个离散值中选择；global weight/input/hidden/output precision 分别从给定 bit sets 中选择（PDF p.2, Table I）。
- 动作：suffix crossover；width mutation；insert/remove layer；precision resampling；repair 强制 layer/width/bit constraints。它是真实 architecture/quantization search，不是 HPO。
- 固定：CERNBox JSC 数据与 16 个高层输入特征、fully parallel FINN mapping、proxy recipe、latency budget 15 ns、最大 LUT 250k；不同搜索只改变 LUT budget `70/100/150/160k`（PDF pp.2–3）。
- post-search unstructured pruning 不改变 tensor shape，属于 finalist 后处理，不是搜索空间的一部分。

## 搜索闭环与失败处理

- population 30、20 generations、1 elite、tournament size 2、每代注入 4 个 random candidates；crossover probability 0.3、mutation probability 0.9（PDF p.2, Table I）。
- repair 处理非法层数、宽度和跨 bit-field 约束；duplicates 被移除，历史 candidate 复用 cached fitness（PDF pp.2–3）。
- 未报告 attempted、repaired、duplicate、proxy-training failure、OOM 或 synthesis failure 的具体数量/比例。
- 没有 LLM proposal、feedback、reflection、memory 或 LLM budget。

## 目标、预算与硬件

- reward 把 proxy validation accuracy 与 estimated LUT/latency 的预算惩罚相乘，并对超过 250k LUT 的架构加额外 penalty；这是 constrained scalar reward，不是显式 Pareto archive（PDF p.2, Eq. 2）。
- 每个 candidate proxy-train 16 epochs；单次搜索实际 evaluates 500 candidates，约 6 h。四个 LUT budgets 对应至少四次报告搜索；每次选择 top 5，因此共有 20 个 dense finalists 做实际 synthesis/RTL 验证（PDF pp.2–3）。
- finalists 最多完整训练 500 epochs、early-stopping patience 50；剪枝后在 accuracy drop 超阈值时最多 fine-tune 100 epochs（PDF p.3）。
- search workstation：NVIDIA RTX 5070 Ti、AMD Ryzen 5 9600X、CUDA 13.0、FINN Docker；最终硬件为 Virtex UltraScale+ `xcvu9p-flgb2104-2-i`，Vivado 2022.2（PDF p.3）。
- GPU-hours、总 wall time（含四次搜索和 20 次 synthesis）、seed、tokens/费用、peak memory 和 energy 未报告。

## 核心结果

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| proxy 保留硬件相对排序 | LUT Spearman `ρ=0.854`；latency `ρ=0.781`，但绝对误差明显 | 20 个实际 synthesis/RTL finalists | PDF p.3 | high |
| compact finalist 改善 FINN frontier | Design E: accuracy 74.36% vs 73.78%，LUT 6,806 vs 57,893（8.5×），latency 62.2 vs 110.17 ns（1.77×） | hand-optimized dense FINN | PDF pp.3–4, Table II | high |
| 剪枝产生真实硬件节省 | 30/50/70% USP 平均 LUT 降低 14.7/28.6/39.8%，FF 降低 17.2/26.9/41.4% | dense finalists | PDF p.4, Table III | high |

## 公平性、复现性与局限

- 与 dense/sparse FINN 的比较在同一 toolchain/device 上较可比；与专用 LUT accelerators 的比较使用不同映射、设备或流程，不能视为统一搜索预算基线。
- 未报告 random search、纯 evolutionary accuracy-only 或显式 Pareto baseline 在相同 500-candidate/training/GPU budget 下的结果；无法隔离 FINN proxy、reward 和 search operator 的贡献。
- 只给单任务、未报告 search seeds/variance；estimated latency 只粗略建模，实际测量只覆盖 20 finalists。
- 没有 peak memory 或 energy 目标；论文报告的硬件结果不能转述为本仓库实测。

## 与当前 AgenticNAS 的关系

- 可作为真实硬件闭环和 typed repair/cache/duplicate handling 的传统基线：先低保真筛选，再对少量 finalist 做真实设备验证。
- 与当前 4–10 层 Conv1d Transformer 不同：本工作是 2–6 层量化 MLP、单一约束 reward；若迁移，应保持训练/evaluator 固定并比较 random/native evolution/stateless LLM/memory-aware LLM 的相同 candidate/GPU budgets，同时报告真实 latency、memory、energy 和 hypervolume。

## 链接

- 论文：https://arxiv.org/abs/2609.16367
- 代码：未报告
