---
title: "When Is an LLM Worth It for Hyperparameter Optimization? A Budget-Matched Study on Tabular Data Finds the Warm-Start Is a Default Configuration, Not the Model"
authors: "Carson Rodrigues, Oysturn Vas, Isaiah Abner DCosta, Nithish Kumar Prabhakaran"
year: "2026"
venue: "arXiv v2"
status: codex_draft
paper_url: "https://arxiv.org/abs/2606.21641"
code_url: ""
tags: [hpo, budget-matching, warm-start, classical-baseline, mixed-search-space]
read_on: "2026-09-20"
---

# When Is an LLM Worth It for Hyperparameter Optimization?

## 一句话结论

在 8 个 PMLB 表格分类任务、5 个 split seeds 和统一搜索空间上，LLM-OptFlow 的“一次评估强 warm-start”实际是任何 LLM 调用之前固定评估的 random-forest 默认配置；把同一 default 给经典搜索后，LLM 的早期优势在 5 次评估时消失、12 次时反转，且相对 default 没有可测的 held-out test 改善。

## 书目信息与证据边界

- arXiv ID：`2606.21641v2`；v1 2026-06-19，v2 2026-06-26；当前核验为 arXiv 预印本，未发现 DOI 或正式 venue。
- 作者：Carson Rodrigues、Oysturn Vas、Isaiah Abner DCosta、Nithish Kumar Prabhakaran。
- 一手来源：[arXiv metadata](https://arxiv.org/abs/2606.21641)、[PDF](https://arxiv.org/pdf/2606.21641)、[HTML](https://arxiv.org/html/2606.21641v2)。
- PDF SHA-256：`60f9eb61783e91d3386787dbfda7b8b83fc2d2417ea368096403dc797f60d74e`；10 页。
- 论文多次声称释放 harness 与 `significance.py`，但 arXiv 页面/PDF 未给项目 URL；本轮 GitHub repository search 对标题、arXiv ID 和 `LLM-OptFlow` 均未找到仓库。因此代码/数据可复现性证据不足，`code_url` 保持空白。
- 置信度：论文内方法、表格和统计为中高；代码公开状态为低；未执行作者脚本，复现实验结论为中。

## 研究问题、真实搜索对象与搜索空间

- 研究问题：LLM HPO advisor 的低预算优势究竟来自模型的任务先验，还是来自 loop 预置的手工 default；在 matched evaluations、multi-seed 和强经典基线下，LLM 的边际价值是多少？
- 数据：8 个 PMLB 分类任务：`credit-g`、`spambase`、`phoneme`、`churn`、`satimage`、`vehicle`、`ionosphere`、`hypothyroid`；每个任务 5 个 stratified 70/30 train/test split seeds。（§4）
- 搜索空间：logistic regression、random forest、gradient boosting、SVC 四种模型族，以及各自标准参数；例如 RF `n_estimators∈[50,500]`、GB `learning_rate∈[10^-3,0.3]`。（§3）
- 因为模型族本身也变化，本笔记分类为 `mixed-search-space`；它是很有价值的 LLM-guided HPO 对照，但不能作为“固定架构 HPO”直接证据。

## Agent / LLM 决策循环

1. LLM-OptFlow 首先评估一个固定 default：RandomForest、`n_estimators=100`、`max_depth=16`、`min_samples_leaf=1`；这发生在任何 LLM 调用之前，并占预算曲线第 1 次 evaluation。
2. 此后 Claude Haiku 接收数据集描述、incumbent 配置与 3-fold CV、历史 attempts，提出下一组配置和简短理由。
3. 规则 confidence filter 按共同空间 `S` 校验 model、数值范围、enum 和 type；非法提案不训练，保留 incumbent，且不消耗 evaluation。
4. 优化目标是 train split 上的 3-fold CV accuracy；最终报告选中配置的 held-out test accuracy。canonical advisor 共 12 evaluations，即 default + 11 个 LLM proposals。（§3–4）
5. 另用一个 OpenRouter pipeline 对七个模型做同一 12-iteration panel：Claude Haiku 4.5/Sonnet 4.6、GPT-5-chat/GPT-4o-mini、Gemini 2.5 Flash、DeepSeek-V3、Qwen3.7-max。（§5.4）

## 目标、候选、训练、GPU 与 LLM 预算

- 每个 full-fidelity evaluation 以 3-fold CV accuracy 选择配置；最终 test 只评所选配置。总体统计单元为 `8 tasks × 5 seeds = 40` paired units。
- LLM-OptFlow：12 evaluations；random、Optuna-TPE、GP-BO：40 trials，并在 1/3/5/12/40 次预算上比较 running best-CV。（§4、Table 1）
- successive halving 用 training-set size 作 fidelity，约消耗 6 个 full-fidelity-equivalent evaluations；因计费口径不同，不放在 per-evaluation curve，只放 final table。（§4、Table 2）
- TPE 与 GP-BO 使用默认 10 个 random startup trials，因此 10 次以内曲线主要反映各 sampler 的 startup，而不是 surrogate 的已学习优势。（§4）
- 七模型 panel 均经 OpenRouter；论文给 model slugs，但未给 request/token、货币成本、延迟、失败重试、GPU/CPU 硬件或 wall time。不能据此比较总成本。

## 基线、公平性与统计

- 基线：fixed default、random search、完整 Optuna-TPE、Optuna GP-BO、successive halving；所有 full-fidelity 方法共享相同搜索空间与 CV objective。
- 关键 exact control：default-seeded random search。由于后续 random draws 与 seed 独立，这能精确隔离“赠送 default”与 LLM proposals 的差异。
- seeded TPE/GP-BO 只是近似控制，因为 enqueue default 会改变 surrogate 后续 draws；论文同时报告 unseeded TPE/GP-BO 在 12 次已追平、40 次超过 LLM，以避免只靠该近似。（§7）
- 统计：对 40 个 `(task, seed)` 单元做 paired two-sided t-test、Wilcoxon signed-rank 和 20,000 次 bootstrap 95% CI。（§4）
- 公平性优点：evaluation budget、搜索空间、objective、split seeds 明确；关键问题被 default-seeded control 直接隔离。
- 公平性限制：Table 2 的 final budget 不相等（经典方法 40、LLM 12、SH 约 6 FFE），因此它回答“各自最终方案”而非等预算最终排名；matched-budget 结论应以 Table 1 的相同横坐标为准。

## 核心结果

- fixed default 的 mean best-CV 为 `88.7%`；这也是 LLM-OptFlow 的 1-evaluation 点，不是 LLM proposal。（Table 1）
- LLM proposals 相对自身 default 在 12 evaluations 只增加 `+0.40 pp` CV（95% CI `[0.22,0.62]`，`p<0.001`），held-out test 为 `-0.01 pp`（95% CI `[-0.22,0.19]`，`p=0.92`）。（§5.1）
- 相对 default-seeded random：LLM 在 2 evaluations 领先 `+0.20 pp`，5 次时为 `-0.09 pp` 且不显著，12 次时落后 `-0.37 pp`（95% CI `[-0.82,-0.02]`）。（§5.1）
- 即使不向经典方法赠送 default，12 evaluations 时 TPE 与 GP-BO 已与 LLM 统计持平；到 40 次，TPE/random/GP-BO 从 12 次继续增加约 `+0.62/+0.76/+0.61 pp`。（§5.1）
- `vehicle` 是唯一真正拉开差距的任务：random/TPE/GP-BO/SH test accuracy 为 `82.4/81.4/79.8/79.3%`，default/LLM 为 `73.5/73.3%`；其余 7 个任务 LLM 与 TPE 的差为 `+0.20 pp` 且不显著。（Table 2、§5.2）
- confidence filter 在正常 proposal 上不触发；合成 0.40 corruption 时 reject rate 0.38，把 failed evaluations 从 1.5 降到 0、浪费时间从 13.2s 降到 8.8s，但最终 accuracy `0.889 vs 0.890` 不变。价值是执行可靠性，不是模型质量。（§5.3）
- 七模型 panel 的第一点都由同一 default 产生；只有 Sonnet 4.6 与 Qwen3.7-max 在 `vehicle` 逃离 default basin，论文明确把它写成单任务观察而非 scaling law。（Table 3、§5.4）

## 可复现性、代码与数据

- 论文给出数据集、split、搜索空间轮廓、default、预算、统计检验与主要模型标识，方法描述足以重建一个近似 harness。
- 但声称“释放 harness/script”与当前可发现性不一致：未提供代码 URL，GitHub repository search 也未找到标题、ID 或项目名；无法核对精确空间、prompt、原始 proposals、per-seed records 和 `significance.py`。
- PMLB 数据公开；OpenRouter 模型 slug 可能重定向或版本漂移。没有冻结 provider response、token/cost 或运行时间，七模型 panel 无法严格重放。

## 局限与威胁

- 搜索对象包含四种模型族，不是固定架构 HPO；结论限于 tabular mixed model/HPO space。
- “LLM 是否值得”主要由 8 个任务决定，而模型之间的探索差异几乎完全由单个 `vehicle` 任务驱动。
- 多个 paired tests 没做 multiple-comparison correction；论文称 load-bearing 的 `p≤10^-4` 结论可过 Bonferroni，但边缘显著项不应放大。
- seeded TPE/GP-BO 是近似而非 exact control；TPE/GP 前 10 次还是 random startup，低预算曲线不是训练后 surrogate 的纯能力对比。
- confidence-filter 故障实验用合成 corruption；对真实 provider failure 分布的外推有限。
- 没有 deep-learning HPO、4–10 层 Transformer、Conv1d、真实 latency/memory/energy 或 Pareto 目标。

## 与当前 AgenticNAS 的直接关联

- 必须把“评估 0 的 hand-picked/default architecture”和“LLM 提案”分开计账；任何 warm-start 声明都要对 default-seeded random/TPE 做 matched-budget control。
- 搜索结果应同时画 attempted/accepted/evaluated 的 best-so-far 曲线，并报告 seeds × iterations；只报一次默认候选会把 prior 混成 Agent 能力。
- schema validator 的价值应单独记为 validity、失败率和节省计算，不应写成质量收益。
- 本论文的 exact-control 思路可直接用于 AgenticNAS：固定 typed architecture space 后，让 random/evolution/BO 与 Agent 获得同一初始 architecture、相同训练 proxy 和相同候选数。
- 由于论文混合模型族，它不能替代 `architecture-only` 与严格 `training-HPO-only` 两条独立实验；`quality_proxy` 与 `latency_proxy_ms` 仍只是流程占位符。

## 最小复现建议

- 先在一个固定 4–10 层 Transformer 架构上只调 training HPO：同一 default、5 seeds、12 trials，比较 default-seeded random/TPE 与 metric-only LLM。
- 再在同预算的 architecture-only lane 比较 default-seeded random/evolution 与 Agent；两条 lane 不混变量。
- 统一记录 evaluation 0、每次 proposal、拒绝原因、tokens/费用、GPU-hours、validation best-so-far，并仅对最终 incumbent 做一次 test。
- 若作者代码仍不可获得，应把复现标为 independent reimplementation，而不是 paper-exact reproduction。

## Citation-ready note

Rodrigues 等在 8 个 PMLB 任务和 5 个 seeds 上发现，LLM-OptFlow 的低预算 warm-start 实际来自任何模型调用之前的固定 random-forest default。给 random search 同一 default 后，LLM 优势在 5 次评估时消失、12 次时反转，且 LLM 相对 default 没有显著 held-out test 改善。该结论为 Agent 搜索提供了关键的 default-seeded matched-budget 对照，但其搜索空间跨四种模型族、代码链接不可发现，不能直接作为固定架构 HPO 的最终证据。
