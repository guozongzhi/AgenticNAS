---
title: "Bayesian Optimization with Rich Auxiliary Information via LLMs"
authors: "Tejus Gupta, Efe Mert Karagözlü, Rohit Sonker, Barnabás Póczos, Jeff Schnieder"
year: "2026"
venue: "arXiv:2609.19437v1"
doi: "10.48550/arXiv.2609.19437"
paper_url: "https://arxiv.org/abs/2609.19437"
source_pdf: "https://arxiv.org/pdf/2609.19437"
code_url: "not found"
source: "arXiv v1 metadata/PDF/HTML, accessed 2026-09-19"
parser: "Codex"
parsed_on: "2026-09-19"
status: codex_draft
tags: [hpo, bayesian-optimization, llm-prior, auxiliary-information, mixed-search-space]
---

# Bayesian Optimization with Rich Auxiliary Information via LLMs

> 本笔记基于 arXiv v1 的 17 页 PDF 和 HTML。论文同时评估固定模型 HPO 与含隐藏层宽度的 MLP 空间，因此按本仓库边界归入 `mixed-search-space`；所有结果均未独立运行。

## 一句话结论

论文显示，把 LLM 用作 GP 的 function/argmax prior 接口，比让 LLM 直接充当 optimizer 或 surrogate 更稳定；在 HPOBench 的四个展示面板中，两种 prior-augmented BO 曲线最强，额外训练统计也改善 LLINBO。但论文未披露所用 LLM、temperature、prior 查询数、tokens/费用或代码，且 MLP 示例搜索 `n_units_1/2`，不能作为严格固定架构 HPO 的直接证据。（PDF pp. 5–13, 16–17）

## 书目信息与来源核验

- arXiv ID：`2609.19437v1`；提交于 2026-09-16 21:15:43 UTC，在 2026-09-18 新稿列表发布。
- 作者：Tejus Gupta、Efe Mert Karagözlü、Rohit Sonker、Barnabás Póczos、Jeff Schnieder。
- 当前可核验 venue 为 arXiv；无会议/期刊声明。arXiv DOI 为 `10.48550/arXiv.2609.19437`，页面标注 DataCite registration pending。
- 一手来源：[arXiv](https://arxiv.org/abs/2609.19437)、[PDF](https://arxiv.org/pdf/2609.19437)、[HTML](https://arxiv.org/html/2609.19437v1)。
- 本次读取 PDF SHA-256：`482df0a0eb20bf22d918cdd944bdcd3a45497013094eb4c4ccd7ac9cb92ef754`；17 页。
- 代码/数据：arXiv 未链接代码，GitHub repository title search 无结果；HPOBench 是公开基准，DIII-D 的 281 条历史实验及 operator logs 未见随文数据链接。
- 置信度：书目信息 high；方法 high；图示相对排名 medium-high；完整成本与可复现性 low。

## 研究问题与贡献

- 问题：标准 BO 只接收 `(x,y)`，丢弃训练曲线、诊断日志、图片或专家先验等富辅助信息；直接让 LLM 预测数值又往往校准差。（pp. 1–3）
- 方法一：在 Sobol query points 上让 LLM 把候选分成五档 ordinal quality，数值化后用 RBF 插值得到 GP mean function `mu_LLM(x)`。（pp. 5–6）
- 方法二：重复让 LLM 提议可能的 maximizers，拟合等权 Gaussian mixture `pi_LLM(x)`，以 `alpha(x;D_t) * pi_LLM(x)^(beta/t)` 调制 acquisition，随迭代衰减先验影响。（pp. 6–7）
- 方法三：把每个已评估点的 auxiliary observations 附加到 LLM prompt，用于 LLM-E2E、LLINBO 或 prior elicitation。（p. 7）

## 方法拆解

### 搜索或优化对象

- HPOBench 从离散 lookup table 返回 validation F1；论文声明评估 SVM、logistic regression、XGBoost、random forest、neural network 五类模型，覆盖 German Credit、Vehicle Silhouettes、KC1、Phoneme、Blood Transfusion 五个 OpenML 数据集。（pp. 7–8）
- SVM/LR/XGBoost/RF 是固定模型字段调参，可作为严格 HPO 邻接证据；MLP prompt 示例同时搜索 `learning_rate`、`batch_size`、`n_units_1`、`n_units_2`、`dropout_1`、`dropout_2`，其中两个隐藏层宽度是结构变量。（pp. 16–17）
- 因为同一论文把训练字段和结构宽度放入 neural-network benchmark，整体归类为 `mixed-search-space`，不能直接进入本仓库固定架构 `LLM × HPO` 主表。
- DIII-D 任务搜索三维 Gaussian ECH deposition profile，并以 `beta_N` 为 context；它是科学控制 BO，不是神经架构或训练 HPO。（pp. 8–9）
- 目标：HPOBench 最大化 validation F1；fusion task 最小化相对最佳历史 shot 的 instantaneous/cumulative regret。没有神经网络 latency、memory、energy 或部署成本目标。

### Agent 与优化闭环

- Function-prior 输入包括 dataset、model family、search-space description 和某个 Sobol point；输出五档 ordinal score，映射到 `{0.1,0.3,0.5,0.7,0.9}` 后插值。（pp. 5–6, 16）
- Argmax-prior 让 LLM 返回 `K=5` 个合法配置和 predicted score，多次 query 后对 locations 拟合 Gaussian mixture。（pp. 6–7, 17）
- Auxiliary-feedback 版本把训练/验证 accuracy、balanced accuracy、F1、precision 以及训练/验证 loss curve 的 final values 追加到 history，使 LLM判断 over/underfitting。（pp. 7–8）
- Baselines：Random Search、GP-UCB、LLM-E2E、LLAMBO、LLINBO；新方法保留 GP uncertainty，而不是完全用 LLM 替代 surrogate。（pp. 9–10）
- 论文没有说明 base LLM、API/version、temperature、randomness、retry/invalid-output handling，也未给 `N` 个 function-prior queries、`n` 次 argmax queries、`beta`、`sigma` 的实验取值。

### 评估与预算

- HPOBench prior 主图：3 个 initialization points，最多 30 function evaluations，每配置 100 seeds；展示 SVM/NN × German Credit/Vehicle Silhouettes 四个面板。（pp. 10–11, Fig. 2）
- Auxiliary LLINBO 图：SVM on German Credit 与 XGBoost on Vehicle Silhouettes，50 seeds。（pp. 12–13, Fig. 4）
- Fusion：281 个 2012–2023 DIII-D historical experiments；每轮按 `beta_N ± 0.05` 过滤候选，最多 250 evaluations，20 seeds。（pp. 8, 12, Fig. 3）
- HPOBench 使用 tabular lookup，无本轮候选训练 GPU 成本；论文没有报告主机、GP/RBF 计算、LLM calls/tokens、API 费用或 wall time。
- 文本称评估 5×5 model/dataset 组合，但主结果只显示四个 prior panels和两个 auxiliary panels，没有完整 aggregate table；“consistent across”不能理解为公开了全部 25 个任务的逐项数值。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| LLM prior 改善 BO | 四个 Fig. 2 面板中 function-prior GP-UCB 与 argmax-prior piBO 最快接近零 simple regret | Random、GP-UCB、LLM-E2E、LLAMBO、LLINBO | pp. 10–11, Fig. 2 | medium-high |
| 直接 LLM optimizer 较弱 | LLM-E2E 在展示面板中接近 Random；LLAMBO 随任务波动较大 | Random/GP-UCB | pp. 10–11 | medium-high |
| richer HPO feedback 有效 | LLINBO + auxiliary feedback 在两个 Fig. 4 面板均低于无辅助版本 | LLINBO | pp. 12–13, Fig. 4 | medium |
| fusion logs 有效 | LLM-E2E + auxiliary feedback 的 cumulative regret 曲线最低；约 250 evaluations 时明显低于无辅助版本 | Random、GP-UCB、LLINBO、LLM-E2E | p. 12, Fig. 3 | medium |
| argmax prior 比直接数值更稳 | 四个 SVM landscape 中 argmax mixture 与 optimum 区域重叠较好，function prior cell-level 噪声更大 | ground-truth table | pp. 9–10, Fig. 1 | medium |

## 公平性与可信度检查

- Function-evaluation budget与 seeds 较清楚，但各 LLM 方法的 calls/tokens 不透明：function prior 可能需要对大量 Sobol points 逐点询问，LLAMBO/LLINBO/LLM-E2E 的 query pattern 又不同，因此不是完整成本匹配。
- 新方法的 `N/n/beta/sigma` 和 base LLM 未报告，无法确认性能/成本或重复结果。
- 仅给曲线，无终点数值表、逐任务显著性检验或完整 25-task appendix；结论应限定在展示面板。
- HPOBench objective 写作 validation F1，但 Appendix prompt 要求预测 “held-out test set” F1；这至少是 prompt/metric 口径不一致，复现时应改成 validation-only 并冻结 test。
- DIII-D logs 先由另一个 LLM 扩写缩写，作者承认会引入错误；预处理成本、模型和误差率未报告。（p. 8）
- HPOBench 可能出现在 LLM 预训练语料中；论文没有做 contamination audit。先验成功可能反映通用经验，也可能含 benchmark familiarity。

## 可复现性与代码/数据

- 没有公开代码、配置、LLM prompts 的完整版本、model/version、seeds 列表或 raw curves；仅附两个 sample prompts。
- HPOBench 可公开重建 lookup experiments，但论文未给所用版本、具体 grid、sampling API 和 stochastic draw seed mapping。
- DIII-D 历史 shots/logs 没有随文公开，且经过未说明模型的 LLM preprocessing，无法独立重现 Fig. 3。
- 本次 PDF 和渲染图只在临时目录读取，没有提交到仓库。

## 与 AgenticNAS 的关系

- 最可复用结论是把 LLM 限定为“先验/辅助信息接口”，由 GP/BO 保留校准与不确定性；这比让 LLM 独立预测 quality 更适合低预算 AgenticNAS。
- 对本仓库的严格 HPO track，应固定 `n_units_1/2` 等结构字段，只搜索 training parameters；若搜索宽度，应明确归入 NAS/mixed track。
- 在 NAS 中可把公开架构知识转换成 decaying argmax prior，并让真实 validation/device measurements 逐步覆盖错误先验。
- `quality_proxy` 与 `latency_proxy_ms` 只能是流程占位符；本文的 validation lookup 与 fusion regret 不能替代真实训练质量或设备延迟。
- clean-room：不得把内部 Archai、模型端点、日志或私有结构作为 auxiliary observations 写入公开研究记录。

## 最小复现实验

- 固定一个公开 4–10 层 Conv1d Transformer 架构，只开放 optimizer、learning rate、batch size、weight decay、schedule；另设结构宽度可变的 mixed track。
- 同一 30-evaluation/100-seed budget 比较 Random、GP-UCB、TPE、LLM-E2E、LLAMBO、LLINBO、function-prior GP 和 argmax-prior BO。
- 固定 base LLM、temperature、prompt、`N/n/beta/sigma`；同步报告 function evaluations、LLM calls/tokens/费用、wall time 和 invalid outputs。
- 使用 validation-only feedback；test 仅在最终选中配置上一次性评估。分别加入 training curve 与真实 device metrics，做独立消融。

## 局限与风险

- 作者明确承认 auxiliary information 可能噪声大、需要预处理，实验只覆盖 HPOBench 和一个 fusion application，并继承反复 LLM query 的开销与随机性。（p. 13）
- 未报告关键 LLM 与 prior hyperparameters，未发布代码或完整任务结果。
- NN 空间包含结构宽度，和固定架构 HPO 的结论混在一起。
- Appendix 的 test/validation 用语冲突会造成数据边界风险。
- 没有部署硬件、Pareto、多目标质量/延迟/内存或真实训练 GPU 证据。

## 可引用摘要

Gupta 等提出用 LLM 生成 BO 的 function prior、argmax prior，并把训练统计或实验日志作为辅助观察加入 LLM-guided optimizer。HPOBench 展示面板表明，保留 GP surrogate 的 prior-augmented 方法比直接 LLM optimizer 更稳定，辅助反馈也改善 LLINBO。由于论文未披露 base LLM、查询预算和关键 prior 超参，未开源代码，且 MLP 空间包含隐藏层宽度，该结果应视为 mixed-space BO 的待复现证据，而非严格固定架构 HPO 的定论。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2609.19437
- PDF：https://arxiv.org/pdf/2609.19437
- HTML：https://arxiv.org/html/2609.19437v1
- 已核对：标题、作者、日期、arXiv ID/DOI、方法公式、HPOBench/fusion 数据、baselines、seeds/evaluation budgets、主要图、sample prompts、代码缺失。
- 未核对：独立运行、完整 25-task 结果、base LLM/temperature、`N/n/beta/sigma`、tokens/费用、DIII-D 数据与预处理。
- [ ] 已由人工决定 `retained` / `discarded`
