---
title: "ENAS: An Efficient Hardware-Aware Neural Architecture Search Framework for TinyML on Resource-Constrained Microcontrollers"
authors: "Mohd Moin Khan, Naman Srivastava, Pandarasamy Arjunan"
year: "2026"
venue: "arXiv:2609.30272v1"
paper_url: "https://arxiv.org/abs/2609.30272"
source_pdf: "https://arxiv.org/pdf/2609.30272"
parser: "Codex"
parsed_on: "2026-09-28"
status: codex_draft
tags: [nas, hardware-aware, tinyml, microcontroller, memory, cpu-only, adjacent-baseline]
---

# ENAS (TinyML)

> 本笔记基于 arXiv v1 PDF。ENAS 不使用 LLM/Agent，只作为传统硬件感知 NAS 邻接基线。arXiv submission history 显示 v1 于 2026-08-10 提交，本轮由 2026-09-28 OAI datestamp 和 2026-09 月度分类列表发现。

## 一句话结论

- 核心主张：在 CPU-only TinyML NAS 中，先用静态 activation-memory 下界拒绝明显不可部署候选，再用 `30 random → top-8 → 40 mutations` 的 70-candidate search 和 persistent cache，以 3-epoch proxy 筛选，最后完整训练并用 MCU toolchain 测 RAM/Flash。
- 最有价值的证据是“真实结构变量 + measured peak activation RAM/Flash + 明确失败分母”；但 latency/energy 仍只用 MACC proxy，且没有 time-matched 扩展搜索对照。
- 证据位置：PDF pp.1–12，Fig. 1–4、Algorithm 1、Tables 2–7。

## 搜索对象、变量与固定项

- 架构表示为 stem width `k∈{1,…,16}` 和 1–6 个 cells。每个 cell 搜 block type（standard/depthwise-separable/bottleneck）、kernel 3/5、stride 1/2、skip flag、ReLU/ReLU6、expansion 1/2；cell channels 由固定 schedule 从 stem width 推导（PDF pp.4–5）。
- 搜索空间约 `10^4` 个 structural configurations；它真实改变 depth、width、block/operator 和 connectivity，属于 NAS，不是 HPO。
- 固定数据和 recipe：Visual Wake Words、Melanoma Cancer；search proxy 为 30% training data 上 3 epochs，最终完整训练 100 epochs、cosine LR；INT8 PTQ 和 evaluator/toolchain 固定（PDF pp.5–6）。
- score 组合 proxy validation accuracy、Flash/RAM/MACC resource efficiency 和 budget headroom；它是标量排序，不是显式 Pareto archive（PDF p.5）。

## 搜索闭环、预算与失败处理

- 每个 hardware/resolution cell 先采样 30 个 random candidates，保留 top 8，每个 survivor 生成 5 个 single-edit mutations，共 40 mutants；总预算 70 candidates（PDF pp.3、5）。
- 静态检查用输入/activation tensor 下界拒绝 RAM 必然不可行者；mutation 产生的 infeasible candidate 被丢弃而不重采样。历史架构以 persistent cross-run cache 避免重复评价，但论文未报告 duplicate/cache-hit 数（PDF pp.4–5、12）。
- 8 个 MCU × 9 个输入分辨率=72 个配置/数据集；19 个被静态判为不可行，53 个可行。每个可行 cell、方法、数据集各跑 3 次，合计 `53×3×2×2=636` 个完整训练模型，报告 deployment pipeline failure 为 0（PDF pp.2、6）。
- 全部实验约 297 CPU-hours，使用单个 16-core node，无 GPU。没有 LLM calls/tokens/费用（PDF p.11）。
- 未报告 70-candidate pass 中 valid、proxy-trained、cache-hit、duplicate 的精确数量，也没有 OOM/divergence/retry ledger；静态不可行分母和最终 pipeline failure 分母较清楚。

## 硬件目标与测量口径

- search 中的 Flash、RAM/MACC feasibility/score 主要由解析式或工具估计；final selected models 的 peak RAM 和 Flash 用 STMicroelectronics `stm32tflm` 工具测量，因此是 on-tool resource measurement（PDF p.6）。
- MACC 只是 latency/energy proxy，不是实机延迟或功耗。论文明确把 empirical on-board power measurement 列为缺口（PDF p.12）。
- 跨 8 个 MCU 的硬件预算为 20 KB–1 MB SRAM、0.75M–15M MACC；结果不能等同于当前仓库的真实 device latency/peak-memory/energy Pareto 闭环。

## 核心结果

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 搜索更快 | Visual Wake Words 平均 2.41×、Melanoma 1.70× search-time speedup | NanoNAS greedy CPU-only | PDF pp.1、7, Table 2 | high |
| selected models 更省 peak RAM | 全部 cells 的 ENAS/NanoNAS RAM 比约 0.30/0.21；matched-accuracy 子集两数据集均约 0.38 | 同 toolchain 的 NanoNAS | PDF p.7, Table 3 | high |
| 高容量 MCU 上有 accuracy gain | STM32H743 配置达到 79.4%，比 greedy baseline 高 2.6 percentage points | NanoNAS | PDF pp.1、9–10, Table 6 | medium |
| 代价与局限 | ENAS 的 Flash 和 MACC 通常更高；大输入下 3-epoch proxy 排序退化 | NanoNAS | PDF pp.7、9、12 | high |

## 公平性、复现性与局限

- ENAS/NanoNAS 使用相同数据、硬件 budget 和 toolchain，但 candidate budget、搜索机制与实际 wall time 不相同。论文明确没有让 ENAS 用 NanoNAS 更长的 runtime 做 time-matched 扩展搜索，因此不能断言 search efficiency 与最终 quality 同时占优。
- 只有 2 个图像任务；audio/time-series/generalization 未验证。没有 search-seed variance 之外的更广泛任务复现，也没有显式 hypervolume。
- paper/code 映射仓库存在，`EdgeIntelligenceLab/ENAS` 的核验 `main` SHA 为 `11d6eb2da746ac9e8664a42f653785670242943b`，包含 configs、search implementation 和 reproducibility 文档；本轮未运行其 297 CPU-hour实验。
- 所有 accuracy、RAM、Flash 和时间均为作者论文结果，不得写成仓库实测。

## 与当前 AgenticNAS 的关系

- 可作为 native/random mutation 的硬件感知传统基线参考：typed cell schema、pre-flight feasibility、cache、低保真 proxy 和 finalist 真实 resource measurement 都可迁移。
- 对当前 4–10 层 Conv1d Transformer，应保持相同 candidate/training/GPU budget，比较 random/native evolution/stateless LLM/memory-aware LLM，并把静态拒绝、duplicate、trained/evaluated 分母完整记账。
- 需要把 MACC proxy 升级为真实 latency、peak memory、energy/deployment cost，并用 Pareto archive/hypervolume 而不是单一混合 score 支撑多目标结论。

## 链接

- 论文：https://arxiv.org/abs/2609.30272
- 代码：https://github.com/EdgeIntelligenceLab/ENAS
- 核验 commit：https://github.com/EdgeIntelligenceLab/ENAS/commit/11d6eb2da746ac9e8664a42f653785670242943b
