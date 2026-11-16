---
title: "Multi-objective Hyperparameter Optimization with Expert Priors"
authors: "Soham Basu, Nastaran Alipour, Frank Hutter, Danny Stoll"
year: "2025"
venue: "arXiv:2511.08371v2"
paper_url: "https://arxiv.org/abs/2511.08371"
source_pdf: "https://arxiv.org/pdf/2511.08371"
code_url: "https://anonymous.4open.science/r/momfpriors_anon-7AE5"
parser: "Codex"
parsed_on: "2026-11-16"
status: codex_draft
tags: [hpo, multi-objective, multi-fidelity, expert-prior, traditional-baseline, mixed-search-space]
---

# PriMO

> 本笔记基于 arXiv v2 官方 PDF。主体是不用 LLM 的 multi-objective HPO baseline；但 LCBench 与 OpenCLIP 同时改变结构字段，必须单列 `mixed-search-space` 边界。

## 方法与搜索空间

- PriMO 先用 MOASHA 做 `n_init=5` 的 initial design，再用 prior-weighted GP Bayesian optimization；默认 prior mixing `epsilon=.25`，expert prior 权重随轮次衰减。（PDF pp.3–5）
- 8 个 benchmark tasks、20 equivalent full evaluations、25 seeds。PD1 固定网络，只改变 learning-rate decay/initial/power、momentum 与 epoch fidelity，是可迁移的 fixed-architecture HPO 证据。（PDF pp.5–8）
- LCBench 同时改变 `num_layers`、`max_units`、dropout；OpenCLIP 同时改变 learning rate、warmup、vision/text width 与 epochs。因此全集结果不能整体解释成 fixed-HPO。OpenCLIP 预算为 10 PFLOPs、20 seeds、三目标 model size/ImageNet error/COCO error。（PDF pp.8–10）

## 结果、成本与公平性

- 作者报告 PriMO 在 OpenCLIP 获得最高 hypervolume；但结构和 recipe 联合变化，且论文未报告真实 GPU 型号、GPU-hours、wall-time、energy 或 failure ledger，不能只凭 10 PFLOPs 与 fixed-HPO 对齐。
- surrogate/synthetic benchmark 总成本约 208 CPU-hours/6,240 core-hours；单 seed/benchmark 约 0.025 CPU-hour/0.75 core-hour。sampling 约 10 s，而一次 model evaluation 约 8,307 s。（PDF p.4 and compute appendix）
- expert prior 的构造会在最大 fidelity 上采样并评价 100,000 configurations，再选择 good/worst priors；这类 oracle/prior-building 成本不在在线 20-evaluation budget 内，是 matched-budget 比较必须显式计费的资源差异。
- 论文只把 LLM 列为未来可能的 prior source，当前 proposer 不是 LLM Agent。

## 代码与课题价值

- 论文声称公开匿名仓库和 raw results；官方 source 中的 URL 为 `https://anonymous.4open.science/r/momfpriors_anon-7AE5`，但 2026-11-16 访问返回 HTTP 401，当前无法核验 commit 或运行结果。
- 对本课题只保留 PD1 fixed-architecture 子集为传统 HPO baseline；OpenCLIP/LCBench 作为 mixed-search-space 邻接证据，不能合并成 HPO 胜率。
- 官方 PDF：34 页，SHA-256 `bb3fffde3269320705a5866c4cffb53b0c8f60ef64486de89ad1795f9c521a01`。

- [x] fixed-HPO 与 mixed-search-space 字段已拆分
- [x] prior-construction 与在线预算边界已记录
- [ ] 人工决定 `retained` / `discarded`
