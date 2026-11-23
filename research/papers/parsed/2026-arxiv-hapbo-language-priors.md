---
title: "HapBO: Harnessed alpha-pi Bayesian Optimization via Expert Natural Language Priors"
authors: "Jean-Sebastien Giroux, Rose Guay Hottin, Marco Bonizzato"
year: "2026"
venue: "arXiv:2611.25100v1"
paper_url: "https://arxiv.org/abs/2611.25100"
source_pdf: "https://arxiv.org/pdf/2611.25100"
code_url: "https://github.com/mbonizzato/HapBO"
parser: "Codex"
parsed_on: "2026-11-23"
status: codex_draft
tags: [agentic-bo, hpo, llm-prior, bayesian-optimization, cost-reporting, mixed-search-space]
---

# HapBO

> 本笔记基于 arXiv v1 官方 PDF。HapBO 只在搜索前调用 LLM，把自然语言先验编译为 acquisition multiplier；它不是 in-loop Agent。HPOBench 同时含多种模型族和结构字段，整体只能作为 Agentic BO / mixed-HPO 邻接证据。

## 搜索对象与先验机制

- LLM 读取 typed search space 与 task description，一次性输出 Prior Specification Language 文档；确定性 compiler 将其变成正值 belief function，alpha-piBO 用有下界的 multiplier 调整任意非负 acquisition。BO loop 本身仍是标准 GP+EI。（PDF pp.1–5）
- LLM 不在每轮接收 observation，也不更新 belief；没有 proposal–feedback–reflection loop。优点是先验错误时不排除搜索区域，并保留 EI 的 regret rate 到有界因子。（PDF pp.4–5）
- HPOBench 40 tasks 跨 logistic regression、random forest、XGBoost、neural network、SVM；其中 neural/configuration families 可含结构字段，不能整体视为固定架构 HPO。另有 cortical neurostimulation、constrained solar design 和 synthetic BO。（PDF pp.5–8）

## 预算、成本与结果

- HPOBench 每 task 16 queries、10 paired seeds；同一 locally served `Qwen3.5-122B` 与相同 task descriptions。prior 在 temperature 0 下每 task elicitation 一次，schema 错误最多 4 次 correction，典型 1–2 calls。（PDF pp.6, Appendix E）
- HapBO 一次 setup 约 15,001 tokens，在线每 query `0` tokens、0.20s；作者报告 LLAMBO 约 79,650 tokens 和 28.59s/query、ColaBO 104.30s/query。论文说明部分 archived baseline hardware 不同，因此墙钟只是 order-of-magnitude，不是严格受控成本对照。（PDF p.6, Appendix E, Table 4）
- 作者报告 HapBO 在 40 个 HPOBench tasks 的 aggregate regret 最低，并在 HPO/cortical/SOLAR pooled task-seed runs 中 `fail%=0.0`；LLAMBO 为 1.9%。这些是作者结果，且不同 family 的 raw regret 不可横向比较。（PDF pp.6–8, Table 1）
- attempted queries 和 completion failure 有汇总，但 invalid/OOM/divergence/duplicate、LLM serving GPU/energy、surrogate compute 的完整账本未报告。

## 复现与课题价值

- 作者仓库在 2026-11-23 可访问，静态核验 `main=d371ba1bf883685e0c4c74d26fca8499ecff6963`；本轮未运行。
- 对 fixed-architecture HPO 可复用“一次编译先验 + 纯 BO 在线循环”，但应只在明确冻结 depth/width/heads/operators 的子空间中比较 random、TPE、CMA-ES、pure LLM 和 hybrid，统一 attempted trials、token 与墙钟上限。
- 对 NAS memory-aware policy 的价值有限：HapBO 没有在线 memory 更新；它更适合作为 prior-only 对照，检验持续 memory 是否真的优于静态语言先验。
- 官方 PDF：41 页，SHA-256 `6e936d1af29b8e0f5d9d7c27e91ed6de61791bae9f3c6a715111b8888858bbd4`。

- [x] one-shot prior 与 in-loop Agent 已区分
- [x] query/token/failure 成本口径已核对
- [ ] 人工决定 `retained` / `discarded`
