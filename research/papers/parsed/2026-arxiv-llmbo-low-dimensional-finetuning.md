---
title: "How Low Can You Go: Fine-Tuning LLMs with Bayesian Optimization (LlMBO)"
authors: "Aditya Kulkarni, Davide Sartor, Carlos Soto, Nathan Wycoff"
year: "2026"
venue: "arXiv:2610.18504v1"
paper_url: "https://arxiv.org/abs/2610.18504"
source_pdf: "https://arxiv.org/pdf/2610.18504"
code_url: "not publicly linked"
parser: "Codex"
parsed_on: "2026-10-23"
status: codex_draft
tags: [bayesian-optimization, parameter-search, peft, memory, baseline]
---

# LlMBO

> 本笔记基于 arXiv v1 的 35 页 PDF。名称中的 LLM 指被微调模型，不是 LLM optimizer；方法以 BO 搜索低维 adapter 权重，属于固定模型的参数优化邻接证据，不是 NAS，也不是训练 recipe HPO。

## 搜索对象与协议

- 基座结构固定。作者先构造 TinyLoRA 随机/SVD basis，再用 TuRBO 在 `u=1,2,4,...` 维系数盒 `[-eta S, eta S]^u` 中选择 adapter 参数；learning rate、optimizer、batch、schedule 等不是搜索变量。（PDF pp.3–6）
- 十个模型、四个 family；`u<=4` 时 GRPO、LlMBO batch=1 与 batch=4 各 8 seeds，更高维一般 3 seeds。每个 GRPO step 使用 64 prompts×4 rollouts=256 completions，LlMBO 每 batch 同样评估 256 completions；GP 在 CPU，GPU 只用于 inference。（pp.7–10）
- 没有 LLM proposal/reflection/memory loop。停止由 evaluation/completion budget 决定；正文没有完整 invalid、duplicate、OOM 或 retry ledger。

## 结果与成本口径

- 作者报告 LlMBO 达到 GRPO 结果约需其 30% training FLOPs；约 2,000 completions 后即可超过 GRPO 最终 greedy accuracy。需要同时保留的反例是：计入 initial design 后，LlMBO median 完整消耗约 123k completions，而 GRPO median 为 101k，低维优势不能概括为所有端到端预算都更低。（PDF pp.8–12）
- 24GB L4 的 Table 2 以可容纳 sequences 表示 memory：Qwen 71、Llama 27、Mistral 34，GRPO 对前三者均无法装入；DeepSeek 为 LlMBO 10、GRPO 6。它说明 inference-only BO 的显存优势，但不是 measured peak-memory GB。（p.10）
- `u>=8` 后优势减弱，`u=64/256` 时固定预算相对维数过薄，结果不稳。论文没有报告 GPU-hours、wall-time、energy、API calls/tokens（方法本身无需外部 LLM API）或美元成本。

## 边界与复现

- 这不是固定架构“训练超参数”搜索，而是模型参数的低维黑箱优化；可作为 memory-constrained PEFT/BO baseline，不能替代 optimizer/LR/batch HPO 证据。
- 论文提到匿名 supplementary，metadata 没有公开代码 URL。PDF 为 35 页，SHA-256 `db81fdccd509f56c5d8e90b22fffbea685e33fab3af9da5b6ba0d6ada144305a`；本轮未运行。
- 没有真实 latency、energy、Pareto 或 Conv1d 证据。若复现，应同时匹配 completions、GPU-hours、wall-time、initial-design 开销和 seed，并报告 OOM/failed evaluations。

## 可引用摘要

Kulkarni 等把 LLM adapter 限制在极低维随机/SVD 子空间，并用 TuRBO 直接搜索 adapter 系数。作者报告低维设置可用约 30% 的 GRPO training FLOPs 达到相近结果，并在 24GB L4 上容纳更多序列；但计入 initial design 后 median completions 并非总是更少。该工作是固定模型参数优化，而非 LLM-assisted HPO 或 NAS。
