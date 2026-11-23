---
title: "ICICLE: In-Context Inference for Curve-Learning Extrapolation"
authors: "Laurits Fredsgaard, Michael Riis Andersen, Mikkel N. Schmidt"
year: "2026"
venue: "NeurIPS 2026 AXIOM Workshop / arXiv:2611.24469v1"
paper_url: "https://arxiv.org/abs/2611.24469"
source_pdf: "https://arxiv.org/pdf/2611.24469"
code_url: "https://github.com/lauritsf/icicle"
parser: "Codex"
parsed_on: "2026-11-23"
status: codex_draft
tags: [hpo, multi-fidelity, freeze-thaw, surrogate, mixed-search-space, classical-baseline]
---

# ICICLE

> 本笔记基于 arXiv v1 官方 PDF。ICICLE 是不使用 LLM 的 multi-fidelity HPO surrogate；PD1/TaskSet 可作 fixed-architecture HPO 证据，LCBench/Meta-Album 含结构或模型选择字段，必须按 mixed 解释。

## 搜索对象与方法

- ICICLE 预测部分 learning curve 的后续值，支持数量可变、continuous/ordinal/nominal 的 typed hyperparameters；它用 shared set encoder 代替 FT-PFN 固定 10-slot encoder，随后用 prefix-attention transformer 输出分布。（PDF pp.1–3）
- 搜索动作是推进某个已有 configuration 到更高 fidelity，配置本身来自 benchmark candidate table；surrogate 不直接生成神经架构，也没有 proposal–reflection Agent loop。
- synthetic prior 覆盖 4–8 层 BNN、heavy-tailed noise、quantization 和 configuration-dependent divergence；main ICICLE model 1.28M parameters，为 FT-PFN parameter count 的 8.7%。（PDF pp.2–3）

## 预算、结果与分类边界

- LCBench 35 tasks、PD1 28 instances、TaskSet 24 instances；ICICLE/FT-PFN 共享初始观察，跑 1,000 iterations 和 20 BO seeds。PD1/TaskSet 的 task-model/optimizer instance 固定，可作为 training-only HPO；LCBench 含结构字段，属于 mixed。（PDF pp.3–4, Appendix A.3）
- Meta-Album 为 86 tasks、33 hyperparameters，ICICLE/Quick-Tune/ASHA/random 共用 candidate pools 与初始 configurations，20 BO seeds；micro/mini/extended budget 按 table training+evaluation time 限制为 1/4/16 hours。Meta-Album 的 model/configuration axes 不应概括成固定架构 HPO。（PDF pp.3–4, Appendix A.1）
- 作者报告 ICICLE 与 FT-PFN 在 LCBench/PD1/TaskSet 的 mean-regret trajectory 相近；Meta-Album overall/extended 低于 Quick-Tune，而 micro/mini 无明确差异。结论是 benchmark-level aggregate，不是本仓库实测。（PDF pp.4–5）
- main comparison 用 ICICLE training seed 0；附录另比较 seeds 0–2。每个 model 训练 80,000 updates、batch 128，但训练 GPU/总 GPU-hours、失败/OOM ledger 未报告。（PDF Appendix B.3/D）

## 复现与课题价值

- 作者仓库在 2026-11-23 可访问，静态核验 `main=de92f65990716a826db9ea5637eb219636398326`；本轮未运行。
- 可作为 fixed-backbone HPO 的 learning-curve early-stopping baseline，但必须只取 PD1/TaskSet 子集，并把 surrogate pretraining 成本与在线 attempted trials 分开计费。
- 对 NAS 轨只可借鉴 divergence-aware prior 与 freeze–thaw budget accounting，不能把 mixed benchmark 的成绩转述为 architecture-only policy 效果。
- 官方 PDF：19 页，SHA-256 `3a4cdfc58ea289facb876bb1f75444d2dd68a5d8eedc2aed73abf32a7318037d`。

- [x] fixed-HPO 与 mixed benchmark 已分开
- [x] 在线预算与 surrogate 预训练缺口已标记
- [ ] 人工决定 `retained` / `discarded`
