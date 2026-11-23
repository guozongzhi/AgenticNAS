---
title: "Self-EvolveRec: Self-Evolving Recommender Systems with LLM-based Directional Feedback"
authors: "Sein Kim, Sangwu Park, Hongseok Kang, Wonjoong Kim, Jimin Seo, Yeonjun In, Kanghoon Yoon, Hyunsik Jeon, Chanyoung Park"
year: "2026"
venue: "NeurIPS 2026 / arXiv:2602.12612v3"
paper_url: "https://arxiv.org/abs/2602.12612"
source_pdf: "https://arxiv.org/pdf/2602.12612"
code_url: "https://github.com/Sein-Kim/self_evolverec"
parser: "Codex"
parsed_on: "2026-11-23"
status: codex_draft
tags: [mle-agent, mixed-search-space, recommender, code-evolution, directional-feedback, memory]
---

# Self-EvolveRec

> 本笔记基于 arXiv v3 官方 PDF。它在开放代码空间里同时改变架构、loss、数据处理和训练逻辑，属于 `MLE Agent / mixed-search-space`，不能作为固定配方 NAS 或固定架构 HPO 的直接证据。

## 搜索对象、固定变量与闭环

- 搜索对象是完整推荐系统 codebase；seed codebase 包含模型架构、data loader、loss 与参数更新逻辑。数据集、leave-last-out 划分、NDCG@5/HR@5 evaluator 固定，但 architecture、loss、negative sampling、数据处理和训练流程均可改变。（PDF pp.1–3, 6）
- 每轮从 evolutionary archive 选 parent，User Simulator 生成定性反馈，DIAG 用 representation/ranking probes 定量诊断；planner 形成检索问题，RAG 取 3 篇文献，coding agent 修改 codebase，结果与反馈写回 archive。已完整评估的 parent 会复用缓存。（PDF pp.4–5）
- DIAG 会随 codebase 与用户反馈共同演化，能为新模块新增 probe；这提供了 proposal–feedback–memory loop，但也让 evaluator 随搜索对象变化，不能把结果直接解释为固定 evaluator 下的纯 NAS。（PDF pp.4–5）

## 预算、结果与失败记账

- AlphaEvolve、DeepEvolve 与 Self-EvolveRec 均最多 21 个 evolution steps；主流程用 GPT-5-mini 做 planning/retrieval、GPT-5 做 coding，单 NVIDIA A6000 48GB。推荐模型统一 embedding=50、batch=128、lr=0.001、最多 300 epochs。（PDF p.24）
- 作者另做 5M input+completion token 的等预算比较；在 SASRec 上，Self-EvolveRec 的 CDs NDCG@5/HR@5 为 0.3843/0.5209，Electronics 为 0.2472/0.3580，均高于两个 code-evolution baseline。该表是作者报告，不是仓库实测。（PDF p.28, Table 10）
- CDs/SASRec 平均每轮时间：AlphaEvolve 6m23s、DeepEvolve 13m59s、Self-EvolveRec 19m21s；后者通常 8–11 轮达到峰值。论文给出若干达到峰值的总墙钟示例，但未报告全部任务总 GPU-hours。（PDF p.27, Table 9）
- 尝试轮数上限明确，但 successful/failed/invalid/OOM/duplicate/retry 的完整 ledger、每轮实际 token、API 费用和全项目 GPU 成本未报告。不同方法虽匹配最大轮数和额外 5M-token 实验，NAS baseline 的 search epoch 口径并不等于 code-evolution attempts。

## 证据边界、复现与课题价值

- 标准 NDCG/HR 来自真实 held-out interactions，不由 LLM judge 决定；但 user-satisfaction 和技术质量评分依赖 LLM judge，应与标准指标分开解释。（PDF pp.6–8）
- zero-cost 版本只做一次 mini-batch forward/backward，以 representation/gradient signals 代理完整训练；作者报告最高约 12× 每轮加速，但它不是设备 latency/energy 代理。（PDF pp.6, 28, Table 11）
- 作者仓库在 2026-11-23 可访问，静态核验 `master=edeff0126f237483e2d30651b5179eaea0b0ad22`；本轮未运行代码。
- 对本课题可复用的是“定性 critique + 定量 probe + archive”的失败定向机制。最小复现应冻结 typed Conv1d architecture-only 动作和 evaluator，禁止 code/data/recipe 漂移，并统一记录 attempted/valid/unique/trained、GPU、LLM token 和墙钟。
- 官方 PDF：43 页，SHA-256 `ba9a249b4c0c59b99d62629fdd190c1f19d88ce167900ddd1cc3588e2185fab8`。

- [x] 搜索变量与固定变量已区分
- [x] feedback、archive、token 与墙钟证据已核对
- [ ] 人工决定 `retained` / `discarded`
