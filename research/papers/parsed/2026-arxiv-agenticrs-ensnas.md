---
title: "AgenticRS-EnsNAS: Ensemble-Decoupled Self-Evolving Architecture Search"
authors: "Yun Chen, Moyu Zhang, Jinxin Hu, Yu Zhang, Xiaoyi Zeng"
year: "2026"
venue: "arXiv:2603.20014v1"
doi: "10.48550/arXiv.2603.20014"
arxiv_id: "2603.20014v1"
paper_url: "https://arxiv.org/abs/2603.20014"
source_pdf: "https://arxiv.org/pdf/2603.20014"
code_url: ""
source: "arXiv v1 metadata/PDF and TeX source, accessed 2026-09-15"
parser: "Codex"
parsed_on: "2026-09-15"
status: codex_draft
tags: [llm-nas, theory, ensemble, cost-model, acceptance-criterion, unvalidated]
---

# AgenticRS-EnsNAS: Ensemble-Decoupled Self-Evolving Architecture Search

> 本笔记基于 arXiv v1 的 14 页 PDF、关键算法页渲染和 TeX source。稿件的公开离散 LLM-NAS 证据是算法方案而非已完成实验；内部 pilot 没有数据或代码，不能独立核验。

## 一句话结论

论文试图用两个独立 proxy learners 估计单模型误差、预测方差与相关性，以判断把整个同构 ensemble 替换成某个 LLM 生成架构是否会降低 ensemble MSE；思路适合把“单模型质量”和“ensemble diversity”同时纳入候选 gate，但摘要阈值依赖未公开验证的 variance-stability 假设，Algorithm 1 的 `Delta E` 符号与定理定义相反，且所有离散 topology/block LLM-NAS、公开 benchmark、代码和实测加速仍是未来工作。（pp. 1-9, 11-14）

## 书目信息与来源核验

- arXiv ID：`2603.20014v1`；提交日期：2026-03-20；arXiv DOI：`10.48550/arXiv.2603.20014`。
- 作者：Yun Chen、Moyu Zhang、Jinxin Hu、Yu Zhang、Xiaoyi Zeng；当前可核验 venue 为 arXiv preprint，正文写 `Under review`，未给具体 venue。
- PDF：https://arxiv.org/pdf/2603.20014 ；14 页；本次副本 SHA-256：`92a995f233d1323e710be4334799171481dd4710f95355ef88b86055f11077a8`。
- source tar 只含 `main.tex`、style 与 manifest；正文代码位置仍是字面量 `[GitHub Repository Link]`。GitHub repository search 未找到作者发布的 paper-exact implementation。
- 置信度：书目信息 high；公式/伪代码转录 high；通用理论保证 low-medium；内部 pilot、成本加速与 industrial impact low。

## 研究问题与贡献

- 问题：若线上系统部署的是同一架构、不同 seed/data ordering 的 `M=50-200` 个模型，逐候选训练完整 ensemble 会使架构迭代成本按 `M` 放大；能否只训练常数个实例预测系统级改进。（pp. 1-2）
- 方法：用 error-ambiguity decomposition 把同构、等权 ensemble MSE 写成 `E(pi) - sigma^2(pi) * (M-1)/M * (1-rho(pi))`，再用候选与旧架构的误差/方差/相关性差决定是否替换。（pp. 3-4）
- 解法分三类：feature retention 等可解析连续变量、复杂连续变量的约束优化，以及离散 convolution/layer/attention/block choice 的 LLM proposal + iterative acceptance。（pp. 5-7）
- 公开稿真正推导的是同构 ensemble MSE 与 feature-bagging toy/model case；NAS-Bench-201 离散搜索、公开 CTR 数据和 production A/B 均列在 `Experimental Validation Plan`。（p. 8）

## 方法拆解

### 搜索或优化对象

- 概念上的离散对象是真实神经架构 `pi`：convolution type、layer count、attention mechanism、network topology 或 block choice；论文没有给有限 op set、shape contract、prompt、4-10 层限制或 Conv1d Transformer space。（p. 6）
- 实际闭式 case 的 `pi = alpha` 是 feature retention ratio；base learners 仍使用同一架构，只随机采样特征。它更接近 data/ensemble diversity control，而非已执行的神经 topology search。（pp. 7-8）
- 目标是等权同构 ensemble 的 MSE，不是显式多目标 Pareto；没有 latency、peak memory、energy 或部署成本目标。
- 论文同时称 continuous `pi` 可包含 dropout/regularization/neural hyperparameters；因此这些连续例子不能支持 architecture-only NAS 的效果结论。

### Agent 与优化闭环

- Algorithm 1 每轮随机采样 complexity bin，prompt LLM 生成与当前 best 不同的候选；没有明确 LLM 名称、system prompt、temperature、token cap、retry 或 invalid action 处理。（p. 6）
- 每个候选训练两个独立 seed 的 proxy models，在 validation batch 上估计平均 error、prediction variance 与二者 prediction correlation。（p. 6, Appendix C）
- 若满足 headline threshold 就把候选作为新 baseline；最终只对 winner 训练 `M` 个实例组成新 ensemble。（p. 6）
- 论文称 complexity bin 与“diverse from best” prompt 会探索低相关区域，但 prompt-level diversity 不保证低 prediction correlation，也没有 novelty/canonicalization 或结构合法性 validator。
- 失败、duplicate、shape/OOM/timeout 与无效 proposal 如何计预算均未定义。

### 评估与预算

- 离散 LLM-NAS：只给符号预算 `N`；计划在 NAS-Bench-201 对比 random/evolution，没有已报告 candidates、seeds、LLM calls/tokens、training recipe、GPU 或结果。（p. 8）
- 成本算例：设 `M=100`、`N=1000`、每模型 `C_learner=1 GPU-hour`，传统 100,000 GPU-hours、方案约 1,100 GPU-hours，得约 90x。它是代数代入，不是 benchmark measurement。（p. 5）
- 内部 pilot：正文只称 Criteo subset、`M=50` 上 alpha optimum 在理论值 5% 内，gate 接受约 85% improving、拒绝约 70% degrading；没有样本数、seed、表/图、raw outputs、hardware 或 artifact。（p. 8）
- 公开代码、数据 snapshot、experiment manifest 与 paper tag 均无；论文写完整验证和代码将在 journal version 发布。

## 理论与实现一致性审计

- 精确比较式 Eq. 22 是 `sigma_new^2(1-rho_new) > sigma_old^2(1-rho_old) + M/(M-1) Delta E`；headline Eq. 5 只有在 `sigma_new^2 ~= sigma_old^2` 时才能化简。论文称 variance stability 在 Section 6 empirically verified，但 Section 6 没有公开实验，只是 future plan/internal pilot。（pp. 4, 8, 11-12）
- 全文定义 `Delta E = E(new) - E(old)`，改善时为负；Algorithm 1 第 8 行却写 `Delta E_i = E_best - E(pi_i)`，随后第 9 行按 Eq. 5 代入。对于更低 error 的候选，这会把本应放宽的 correlation threshold 错写为收紧；伪代码与定理不能同时成立。（p. 6, p. 14）
- `O(1)` 只表示成本不随 `M` 增长，不等于一次 learner training；正文实际需要两个 proxy instances，另有 validation/statistics/LLM 成本。`90x/100x` 不包含估计误差导致的 full-ensemble false accept/reject 成本。
- independent seeds/data ordering 并不使 base learners 独立：论文又显式估计正相关 `rho`。更准确的假设是 exchangeable/homogeneous moments，而非统计独立。
- bibliography 把 LLMatic 写成 `arXiv:2305.12345`，与可核验条目 `2306.01102` 不一致；相关工作元数据需要再次清洗。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 同构 ensemble error decomposition | `E - sigma^2 (M-1)/M (1-rho)` | error-ambiguity identity | pp. 3-4, Appendix A | medium-high under equal-weight homogeneous moments |
| headline monotonic gate | correlation threshold Eq. 5 | old architecture ensemble | p. 4 | low-medium; requires unverified variance stability |
| feature-retention optimum | closed-form `alpha*` under quadratic error, linear correlation, constant variance | assumed analytic model | pp. 7-8, Appendix B | low for practice; model assumptions not public-calibrated |
| 90x search saving | 100,000 vs 1,100 hypothetical GPU-hours | `M=100`, `N=1000` arithmetic | p. 5 | high for arithmetic, low as empirical claim |
| gate classification | internal pilot claims ~85% accept of improving and ~70% reject of degrading | undisclosed Criteo subset | p. 8 | low |

## 公平性与可信度检查

- 没有一次公开执行的离散 LLM-NAS，因此没有 matched-budget random/evolution/stateless LLM 对照、multi-seed variance 或 best-so-far curve。
- 不同候选的 proxy prediction correlation 只用两个 seed 估计；论文没有置信区间，两个点对稳定估计 pairwise correlation/variance 很脆弱。
- acceptance threshold 的估计误差没有进入保证；用 noisy `E/rho/sigma^2` 代入真值定理不能保留确定性 guarantee。
- 理论只处理把整个 ensemble 从同构 `pi_old` 换成同构 `pi_new`，不处理混合旧/新架构、加权 ensemble、online member replacement 或 heterogeneous production ensembles。
- 内部 pilot 属公开文字但缺失可核验 artifact；只能记录为 author claim，不能作为 clean-room 实验基线或规模商业事实。

## 可复现性与代码/数据

- 可复现材料只有 PDF/TeX 与公式；没有 code URL、dependency lock、prompt、LLM、NAS space、seed、dataset split 或 raw pilot results。
- source tar 没有正文声称的 supplementary calibration plots/worksheet；`[GitHub Repository Link]` 仍是占位符。
- 不能重建 `r>0.95` proxy/full-ensemble correlation、5% optimum gap、85%/70% gate accuracy 或 variance-stability 假设。
- 当前最小可复核部分仅是符号推导和成本 arithmetic；实现 Algorithm 1 前必须先解决 sign mismatch。

## 与 AgenticNAS 的关系

- 可复用目标：若最终产品确实部署多 seed ensemble，不应只优化单模型质量；可把 task quality、prediction correlation、latency、memory、energy/成本放进 archive。
- gate 应使用精确 variance-change 式或带置信区间的 conservative bound，不能静默假设不同 architecture 的 prediction variance 相同。
- LLM 只输出 typed `block/cell/op/connectivity` action，本地 builder/validator 决定 legality；prompt 中的“diverse”不能替代 canonical graph distance 与实际 prediction diversity。
- 每个 candidate 的两个 seed 都计入 training budget；必须与相同 total learner-runs 的 random/evolution 做公平对照。
- clean-room 实验只用公开 benchmark、自建 search space 和公开模型；不得读取或复述作者未公开 internal pilot，更不得联想到内部 Archai、端点、日志或私有架构。
- `quality_proxy` 与 `latency_proxy_ms` 只能作流程占位符，不能被本文的理论量或内部 pilot 数值替代。

## 最小复现实验

- 在 NAS-Bench-201 或公开 4-10 层 Conv1d Transformer typed space，固定训练 recipe、validation/test、`M=5` 与 total learner-runs。
- 对照 random、regularized evolution、stateless LLM、LLM + quality-only gate、LLM + exact diversity gate；至少 5 个 search seeds。
- 每候选训练 2/3/5 个 proxy seeds，bootstrap `E/rho/sigma^2`；只在 lower confidence bound 满足时接受，并记录 false accept/reject。
- winner 才训练完整 `M` ensemble；在 untouched test 上检查 predicted delta 与 actual ensemble delta，并报告 learner-runs、GPU-hours、LLM calls/tokens、quality、latency、peak memory 与 Pareto/HV。
- 停止条件：若 gate 的 95% CI 覆盖随机 gate，或总预算下 final ensemble 不优于 matched random/evolution，则不扩大到昂贵设备实验。

## 局限与风险

- 离散 LLM architecture search、公开数据实验和代码尚未完成；论文标题中的 self-evolving search 目前主要是方案。
- headline guarantee 依赖同构/equal-weight ensemble、MSE、moment estimates 与 variance stability；不覆盖异构或加权 ensemble。
- Algorithm 1 sign mismatch 会直接改变候选接受逻辑。
- 两个 proxy instances 对相关性与方差的估计可能不稳，且没有 uncertainty-aware threshold。
- 没有 Conv1d Transformer、4-10 层、真实 latency/memory/energy 或 Pareto evidence。

## 可引用摘要

AgenticRS-EnsNAS 提出用少量独立 proxy learners 估计候选架构的单模型误差、预测方差与相关性，从而在不为每个候选训练完整同构 ensemble 的情况下决定是否替换部署架构。其离散 LLM-NAS 仍是算法与未来实验计划，公开稿没有代码或 benchmark；摘要阈值依赖未验证的 variance-stability 假设，且伪代码的 `Delta E` 符号与定理定义相反。因此该工作目前更适合作为 ensemble-aware acceptance 的待验证理论候选，而非已证明的成本或性能结果。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2603.20014
- PDF：https://arxiv.org/pdf/2603.20014
- TeX source：https://arxiv.org/src/2603.20014
- 已核对：标题、作者、日期、arXiv ID/DOI、公式、Algorithm 1、成本算例、Section 6 roadmap、source tar 与代码占位符。
- 未核对/不可核对：内部 pilot、supplementary plots/worksheet、paper-exact implementation、离散 NAS benchmark、LLM/GPU预算和 production A/B。
- [ ] 已由人工决定 `retained` / `discarded`
