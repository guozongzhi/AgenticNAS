---
title: "BoLT: A Benchmark to Democratize Black-box Optimization Research for Expensive LLM Tasks"
authors: "Ruth Wan Theng Chew, Zhiliang Chen, Apivich Hemachandra, Bryan Kian Hsiang Low"
year: "2026"
venue: "arXiv:2605.17000v2"
paper_url: "https://arxiv.org/abs/2605.17000"
source_pdf: "https://arxiv.org/pdf/2605.17000"
code_url: "https://github.com/chewwt/bolt"
parser: "Codex"
parsed_on: "2026-10-28"
status: codex_draft
tags: [hpo, benchmark, bayesian-optimization, llm-training, multi-fidelity, real-data]
---

# BoLT

> 本笔记基于 arXiv v2 官方 PDF。BoLT 是无 LLM Agent 的 BBO benchmark；只有 HPO family 可作为固定 backbone 的训练/LoRA HPO 证据，DMO/PO/PCO 必须分轨。

## 任务与固定架构 HPO 子集

- 四个 task families：LoRA HPO、data-mixture optimization、prompt optimization、parallelism configuration。HPO 分别固定 Qwen3-4B 或 Qwen3-8B backbone 与 100K OpenMathInstruct-2 subset，搜索 learning rate、batch、LoRA rank/alpha/dropout/layers/target modules；multi-fidelity 额外改变 tokens 或在 4B/8B fidelity 间切换。（PDF pp.2–5, Table 1）
- HPO base problem 在每个 emulator 内 backbone 固定，可归 `fixed-architecture HPO benchmark`；HPO-MF-Disc 改 model size、DMO 改 data、PO 改 prompt、PCO 改系统并行配置，不能并入本仓库 fixed-HPO 结论。
- emulator/lookup 由超过 22K 次真实 LLM evaluations 构建；HPO-8B train/test 8,513/785，HPO-4B 7,970/819。每个 HPO training run 使用 2×H200，checkpoints 每 200 steps 保存并 early stop；实际 GPU-hours、wall-time、energy 与 peak memory 未报告。（PDF pp.2, 6, 21–22, Tables 3/8）

## 比较协议与结果

- HPO/DMO/PCO emulator experiments 各 10 runs，PO 5 runs，每个方法先有 10 initial observations；HPO 主图到 200 observations，并比较 random、TS、TPE、CMA-ES、BOHB、ASHA 和多种 GP acquisition。（PDF pp.6–8）
- 作者报告 GP-based BO 总体优于非 GP HPO baselines，但赢家随 budget 改变：TPE 在 30 iterations 内有优势，之后被部分 GP methods 超过；没有单一方法跨 tasks 最优。（PDF p.7, Fig.3）
- 真实 LLM transfer check 在 HPO/DMO 上以 50 iterations×5 seeds 运行；HPO 中 LogNEI 与 emulator/real runs 均为最佳平均 ranking，但一个坏 seed 拉低 mean regret。emulator 对真实 HPO query region 的 Spearman `rho=0.66`、`R^2=0.50`，因此不能视为真实 oracle 的精确替代。（PDF pp.9, 21, Table 7）
- multi-fidelity 成本以估算 FLOPs/normalized budget 表示；没有完整 attempted failure/OOM/duplicate 账本。PCO 对 OOM 有显式 constraint value，但这不是 HPO training failure ledger。（PDF pp.24–27）

## 对本仓库的价值

- 可复用：固定 backbone 的 mixed-variable HPO space、真实训练构建 emulator、5-seed noise estimate、200-trial classical baselines、budget-dependent acquisition 分析。
- 必须补：同一 fixed Conv1d Transformer、真实 attempted trials、GPU-hours/wall-time/energy、failed/OOM/divergence、LLM proposer calls/tokens/费用；emulator 与真实训练结果要分开报告。
- 官方代码本轮可访问，`HEAD=7ca55480c812a70e47558c77821085182f29a247`；Hugging Face 提供 emulators/data，本轮未运行。

## 检索与人工核验记录

- v2 submitted 2026-10-27；官方 PDF 37 页，SHA-256 `2b9cd58b02c1b5ab4c03c7bbbb82cc5afa696d9a0185b1b3e57cff036bd41042`。
- [x] HPO search space、真实数据量、硬件和主比较预算已核对
- [x] HPO、DMO、PO、PCO 证据边界已分开
- [ ] 人工决定 `retained` / `discarded`
