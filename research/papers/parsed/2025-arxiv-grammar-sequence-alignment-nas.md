---
title: "Evolutionary Architecture Search through Grammar-Based Sequence Alignment"
authors: "Adri Gómez Martín, Felix Möller, Steven McDonagh, Monica Abella, Manuel Desco, Elliot J. Crowley, Aaron Klein, Linus Ericsson"
year: "2025"
venue: "arXiv:2512.04992v2"
paper_url: "https://arxiv.org/abs/2512.04992"
source_pdf: "https://arxiv.org/pdf/2512.04992"
code_url: "https://github.com/flxai/rcswx-paper"
parser: "Codex"
parsed_on: "2026-11-16"
status: codex_draft
tags: [nas, evolution, grammar, crossover, sequence-alignment, traditional-baseline]
---

# Evolutionary Architecture Search through Grammar-Based Sequence Alignment

> 本笔记基于 arXiv v2 官方 PDF。方法改变 depth、branching、routing 与 operators，属于传统 evolutionary NAS。

## 搜索空间与 proposal

- grammar 把有效网络编码为 derivation sequence；CSWX/RCSWX 先对齐两个 parent sequences，再在对齐位置 crossover，以维持语法可执行性。mutation 若生成无效个体最多重采样 100 次。（PDF pp.3–8）
- 7 个 Unseen NAS datasets、5 seeds；每轮 population 100，再产生 900 offspring，总计 1,000 evaluations。比较 no crossover、STX、CSWX、RCSWX 四种 proposer，训练/evaluator 固定。（PDF pp.9–12）

## 结果与成本

- 七任务平均 accuracy：no crossover 70.71、STX 74.97、CSWX 73.73、RCSWX 74.44；Friedman `p=.0997`，没有统计显著差异，不能写成 RCSWX 明确优于其他 crossover。（PDF pp.11–13）
- SEPX 对长序列不可行；alignment runtime 比较没有统一硬件/共同总搜索墙钟。RCSWX 的原始实现到约 71 nodes 首次超过 1 s，且深层嵌套有 peak-memory 问题；Rust 实现的示例把 ResNet34/MLP-Mixer depth-12 从 741.57 min 降至 97.136 s，但这不是完整 NAS search cost。（PDF pp.13–16, Appendix）
- 未报告 search GPU-hours、端到端 wall-time、energy、peak memory 数值或完整 invalid/duplicate ledger。

## 代码与课题价值

- 论文仓库 `flxai/rcswx-paper` 核验 HEAD `3820b18ef3a30c343ae33f48d99397bc7470c4ae`；实现仓库 `flxai/rcswx` 核验 HEAD `fdd61a5b7cfdd3873c5f20874990784028c46bf9`。本轮仅静态核对，未运行。
- 可借鉴 grammar-valid proposal 与 invalid-resampling 账本；应用到 typed Conv1d 时仍需 matched 1,000 attempted proposals、unique/duplicate/invalid、训练成本与多 seed Pareto 报告。
- 官方 PDF：30 页，SHA-256 `7c69e4fb5573bcbea15e4e80d1266d48c1a6c1e4e77cc248093644e3388383ac`。

- [x] 搜索预算与显著性结论已核对
- [x] crossover runtime 与端到端 search cost 已区分
- [ ] 人工决定 `retained` / `discarded`
