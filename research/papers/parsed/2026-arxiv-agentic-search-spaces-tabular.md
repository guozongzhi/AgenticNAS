---
title: "Agentic Search Spaces for Tabular Machine Learning"
authors: "Renat Sergazinov, Artem Chistyakov, Sergey Pankevich, Artem Babenko"
year: "2026"
venue: "arXiv:2609.16309v1"
paper_url: "https://arxiv.org/abs/2609.16309"
source_pdf: "https://arxiv.org/pdf/2609.16309"
parser: "Codex"
parsed_on: "2026-09-28"
status: codex_draft
tags: [llm-agent, hpo, mixed-search-space, tabular, tpe, code-generation]
---

# Agentic Search Spaces for Tabular Machine Learning

> 本笔记基于 arXiv v1 PDF。它同时改变 preprocessing、embedding、architecture、training 和 inference 模块，属于 mixed-search-space；不能作为固定架构 HPO 或固定配方 NAS 的直接证据。

## 一句话结论

- 核心主张：LLM Agent 不在每个数据集的 trial loop 中直接优化，而是针对一个 tabular model 一次性生成可执行模块候选；随后标准 Optuna TPE 在这些 categorical modules 与原始数值超参数的联合空间中调优。
- 论文把 Agent 生成成本摊销到多个数据集，并用相同 trial 数比较 base/agentic space；但 enlarged space 的单 trial 计算成本可显著不同，且结构、训练和数据/推理字段混合。
- 证据位置：PDF pp.2–10、37–38，Fig. 1–4、Tables 3–8、17。

## 搜索对象、变量与固定项

- 对 MLP、TabM、RealMLP，Agent 可生成 preprocessing、feature embedding、architecture、training、inference 五类代码模块；LightGBM 和 TabICLv2 的学习算法冻结，只扩 preprocessing/inference（PDF pp.2、5）。
- Agent 最多为每个 task type 生成 64 个候选，并过滤重复、已有负面文献证据或反复 smoke-test 失败的实现。每个模块作为 categorical variable，与 model author 的默认连续/离散超参数一起交给 TPE（PDF p.5）。
- HPO 阶段固定每个数据集的 train/validation/test split、native metric、Optuna univariate TPE 和最后 hold-out test 规则；但不同 candidate 会改变真实网络结构、optimizer/training、数据变换和 test-time inference。
- 因存在 architecture modules 且 recipe/data/inference 同时变化，本工作明确归 `mixed-search-space`。它不是纯 NAS，也不是仓库定义的 fixed-architecture HPO。

## LLM/Agent 与优化闭环

- 主 Agent 是 Claude Code + Opus 4.8（max effort）；补充稳定性/速度比较用 Codex + GPT-5.5（xhigh）。Agent读取 base model code、原论文压缩 title/abstract，并可运行 inspection、implementation 和 synthetic smoke-test 工具，但不接触目标数据集（PDF pp.4–5、37–38）。
- Agent 内部有“提出—实现—smoke test—调试/丢弃”反馈，但每个 model family 只生成一次 search space；它不读取后续 HPO trial score，不做跨 trial reflection、memory 或 proposal。
- 真正的 sequential optimizer 是 TPE。每个 trial 训练一个 pipeline，在 validation 上打分；停止条件是固定 attempted-trial budget（PDF p.4）。
- 论文另做 50-iteration dataset-specific autoresearch 对照，LLM逐次编辑代码并看 validation，但该分支平均比 classical HPO 低 0.1%，且每数据集花 20–50 USD（PDF pp.4–5, Table 3）。

## 预算、失败与成本

- 主单模型对比：小/中数据集 200 TPE trials，大数据集 100；前 20 trials 随机。best validation configuration 最后在 test 上用 15 个随机 seed 评价。Agentic TabICLv2 每个数据集固定 100 trials，默认 TabICLv2 不调优（PDF p.4）。
- ensemble 分支每个 space 随机采样并训练 100 个 configurations，大数据集 20 个；与单模型 TPE trajectories 分开（PDF pp.4、7）。
- Table 6 的一次性 Agent 输出成本：Claude 36,221–90,579 output tokens、30–100 分钟；Codex 32,456–102,542 output tokens、24–71 分钟。作者估计每个 model family 一次 generation loop 约 10 USD，但省略 input/cached tokens（PDF p.8）。
- 论文没有汇总 Agent proposal attempted/kept/rejected/smoke-test failure/duplicate 数，也没有报告 HPO completed/failed/OOM/divergence trial 数、GPU-hours、峰值内存或能耗。
- search-space 候选最终有明确清单；例如 released MLP space 在 Table 17 列出 67 个去重 module candidates。代码仓库 `yandex-research/agentic-hpset` 的 `main` 核验 SHA 为 `3d7349b36df9bea48a5c236830a8f313ba1819c9`。

## 核心结果

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 多模型平均收益 | tuned single models 平均相对提升：DNN 约 0.5%，LightGBM 0.8%，TabICLv2 0.5%；小/中回归可达约 2.0% | 同 model family 的 author-provided base space、matched trial count | PDF pp.2、6, Fig. 2/Table 4 | high |
| ensemble 的主要收益来自多样性 | Agentic pool 的 strongest member 平均只变化 `+0.1/+0.4/-1.0/0.0%`，ensemble 为 `+1.3/+1.1/+0.2/+0.3%` | base-space random pool | PDF p.8, Table 5 | high |
| 生成稳定性 | Claude/Codex 各 5 次 regeneration 都改善 base MLP；Codex variance 较小 | 相同 45 datasets | PDF p.9, Table 7 | medium |
| matched trial 下收益不是只在大预算出现 | 小/中数据集从 50 trials 起多数 family 为正；大数据集更混合 | base vs agentic space | PDF pp.9–10, Fig. 4 | medium |

## 公平性、复现性与局限

- base/agentic 使用相同 attempted-trial 数、split 和 evaluator，这是较好的 trial-budget 对照；但 Agent search-space generation 是新增成本，且 agentic pipeline 单次 fit 的 median time 是 base 的 0.9–2.4 倍，所以 wall-time/GPU budget 不匹配（PDF p.10）。
- mixed modules 使收益无法归因于 architecture、training 或 preprocessing 的任一轨道；要服务本仓库 HPO 课题，必须先固定架构、数据处理和 evaluator，只保留 training recipe 变量。
- 45 个数据集覆盖较广，但 search-space generation 不看目标数据，既降低直接 leakage，也可能遗漏 dataset-specific 结构；LLM 预训练和检索语料污染仍未消除。
- 论文承认生成代码可能含 bug，需要人工审查；未公布失败 trial ledger，因此无法审计 attempted/valid/evaluated 的完整分母。

## 与当前 AgenticNAS 的关系

- 可借鉴“Agent 只设计候选 basis，经典 optimizer 负责探索”的职责分离，以及 generation 成本一次性计入、后续按数据集摊销的成本口径。
- 对 NAS 轨道，应只允许 Agent 扩展 typed architecture modules，并固定 training/data/inference；对 HPO 轨道，应锁定 depth/width/heads/operators/connectivity，只让 TPE/CMA-ES/LLM 比较 training fields。
- 后续若复用，应以 attempted trials 为主预算，同时给每个 trial 相同 wall cap，记录 failed/OOM/divergence/duplicate，并分别报告 Agent tokens、GPU 与墙钟成本。

## 链接

- 论文：https://arxiv.org/abs/2609.16309
- 代码：https://github.com/yandex-research/agentic-hpset
- 核验 commit：https://github.com/yandex-research/agentic-hpset/commit/3d7349b36df9bea48a5c236830a8f313ba1819c9
