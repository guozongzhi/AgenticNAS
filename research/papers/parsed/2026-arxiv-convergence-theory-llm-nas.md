---
title: "Convergence Theory for Iterative LLM-Based Neural Architecture Search: A Parametric Cross-Entropy Framework with Closed-Form Proxy Reliability"
authors: "Santosh Premi Adhikari, Radu Timofte, Dmitry Ignatov"
year: "2026"
venue: "arXiv:2605.30103v1"
doi: "10.48550/arXiv.2605.30103"
arxiv_id: "2605.30103v1"
paper_url: "https://arxiv.org/abs/2605.30103"
source_pdf: "https://arxiv.org/pdf/2605.30103"
code_url: ""
source: "arXiv v1 metadata/PDF, TeX source, cycle_data.csv, and proxy_full_pairs.csv, accessed 2026-09-15"
parser: "Codex"
parsed_on: "2026-09-15"
status: codex_draft
tags: [llm-nas, theory, cross-entropy-method, delta-editing, proxy-fidelity, convergence]
---

# Convergence Theory for Iterative LLM-Based Neural Architecture Search: A Parametric Cross-Entropy Framework with Closed-Form Proxy Reliability

> 本笔记基于 arXiv v1 的 13 页 PDF、关键表格渲染、TeX source 与随文两份 CSV。论文含可复算的新 proxy/full-training 小实验，但大部分 22-cycle/3,300-architecture 数据复用 Delta-Based NAS；收敛结论依赖强假设，当前证明与公开数据不足以支持无条件“单调/几何收敛”。

## 一句话结论

论文把在累计 elite corpus 上 LoRA fine-tune 的开放代码级 LLM-NAS表述为 parametric cross-entropy projection，并为 delta validity、novelty 与一 epoch proxy reliability 给出条件化模型；其中“同任务内先测 proxy SNR”是有用诊断，但 LoRA projection 的质量单调性被直接作为未验证假设，有限样本允许下降却又调用单调收敛，公开 CSV 的 raw/普通 3-cycle mean 也多次下降，因此不能把 smoothed case study 当作一般收敛保证。（pp. 2-8, 11-13）

## 书目信息与来源核验

- arXiv ID：`2605.30103v1`；提交日期：2026-05-28；arXiv DOI：`10.48550/arXiv.2605.30103`。
- 作者：Santosh Premi Adhikari、Radu Timofte、Dmitry Ignatov；当前可核验 venue 为 arXiv preprint，正文写 `Under review`，未给具体 venue。
- PDF：https://arxiv.org/pdf/2605.30103 ；13 页；本次副本 SHA-256：`48ab7473da5914620da0cc4b7bac47ee45137a24e4fa3939458d2c7f0f55ebbf`。
- source：https://arxiv.org/src/2605.30103 ；含 `main.tex`、`cycle_data.csv`（66 行）与 `proxy_full_pairs.csv`（43 行），没有独立代码仓库。
- 关联实证：Delta-Based NAS（`2605.04903`）；其 22 cycles、三种 LLM、3,300 proposals 已在本仓库单独解析。
- 置信度：书目信息/CSV high；proxy pair 重算 high；理论结论 medium-low；向其他 search spaces/LoRA settings 泛化 low。

## 研究问题与贡献

- 问题：iterative LLM fine-tuning 是否等价于 CE update、是否单调/收敛、delta 为何比 full code 更合法、MinHash novelty 是否防 mode collapse，以及一 epoch proxy 何时能排序 full-training quality。（pp. 1-2）
- 搜索过程：对能定义 `torch.nn.Module` 的开放 Python programs 采样；一 epoch validation accuracy 达 threshold 且过 MinHash-Jaccard novelty 的候选加入累计 corpus，再在累计 corpus + 静态 LEMUR prior 上 LoRA fine-tune。（pp. 2-3）
- 理论：MLE loss 可以写成对 uniform corpus empirical distribution 的 KL projection；后续 quality/concentration 结果额外依赖 bounded quality、positive elite mass、finite/expressive elite support 与 `quality-monotone projection`。（pp. 3-5）
- 新实证：对 Delta-NAS 每种 LLM 的 top-20 尝试 50-epoch full training，得到 43 个成功 pairs，用于估计 one-epoch/full-training correlation 与 SNR。（pp. 6, 12）

## 方法拆解

### 搜索或优化对象

- 对象是真实、可执行的 PyTorch neural architecture programs；quality `q(a)` 定义为固定数据集的一 epoch validation accuracy，不是 Agent workflow。（pp. 2-3）
- 搜索空间来自 LEMUR image-classification subset 与 unified-diff reachable programs；开放代码可改变 CNN layer/op/connectivity，但没有 typed block/cell schema、4-10 层或 Conv1d Transformer 限制。
- 论文只研究单一 proxy quality、validity 与 novelty；没有真实 latency、peak memory、energy、cost constraint 或 Pareto archive。
- 50-epoch follow-up跨 MNIST/CelebA/SVHN；不同任务 accuracy不能直接视为同一 quality scale。

### Agent 与优化闭环

- 每 cycle 每种 LLM 生成 50 个 delta candidates；过 one-epoch threshold `tau=0.40` 与 novelty threshold `tau_nov=0.90` 的候选进入 corpus。（pp. 3, 12-13）
- LLM 为 DeepSeek-Coder-7B、Qwen2.5-Coder-7B、Mistral-7B-Instruct；22 cycles x 50 x 3 = 3,300 proposals 来自 Delta-NAS，不是本文新跑的独立 search。（pp. 1, 6-8）
- fine-tune distribution 是累计 accepted corpus 加静态 LEMUR corpus的 MLE projection；它与标准“只拟合本轮 elite conditional distribution”的 CE update weighting 不同。
- novelty filter只决定哪些样本加入 corpus，并不直接约束下一轮 generator 的最大概率或 semantic architecture diversity。

### 评估与预算

- `cycle_data.csv`：66 行，即 3 LLM x 22 cycles；每行含 `mean_acc`、`elite_rate_tau40`、`delta_apply_rate`。按既有协议每行 50 proposals，总数 3,300；delta apply rate 总均值 0.7133。
- `proxy_full_pairs.csv`：Mistral 16、Qwen 15、DeepSeek 12 个成功 pairs，共 43；原计划每种 top-20，17 个因 runtime/degenerate outputs 未完成。（p. 6）
- 新 full-training 实验：单张 RTX 4090 24GB，43 个 architectures x 50 epochs，约 4 GPU-hours；单次从不足 1 分钟到约 25 分钟。（p. 12）
- 论文没有为新分析报告额外 LLM calls/tokens；per-cycle generation/LoRA compute 直接指向 Delta-NAS。
- 统计：表中 Spearman/Bonferroni 可由 CSV复算；但按 LLM 选择 top-20 后再分析，存在 range restriction、task mixture 与 completion selection。

## 理论证据与证明边界

- **CE equivalence 很窄。** Theorem 1 只是说明对累计 corpus 的 cross-entropy MLE 等于对同一 empirical distribution 的 KL projection；这不自动继承 classical CE 在 current elite distribution、adaptive threshold 或 unrestricted family 下的收敛结论。（pp. 3, 11）
- **单调性被写进 Assumption 2。** `quality-monotone projection` 要求投影后 mean quality 不低于当前 distribution；正文承认对 LoRA 不可验证。Theorem 2 因此是条件命题，不证明实际 LoRA update 会提高质量。（pp. 3-4, 7, 12）
- **有限样本与单调收敛有缺口。** Theorem 2/3 允许 `C_{t+1} >= C_t - epsilon_t`，序列可下降；proof 却把它称为 non-decreasing 并直接用 Monotone Convergence Theorem。除非另证 summable error/近似单调或取无限样本，当前步骤不足以推出 Part 2。（pp. 4, 11）
- **elite support 假设不足。** Assumption 1(d)只说 family含一个对每个 elite element赋正概率的 distribution；proof 随后把“elite set上的 uniform distribution属于 family”作为前提，逻辑更强。几何 rate corollary 在正文也没有独立递推证明。（pp. 3-4, 11-12）
- **novelty不等于 generator no-collapse。** corpus pairwise separation可以成立，但对 uniform corpus 的 KL projection未必禁止 parametric generator在某一点高度集中；给出的 `delta_t` 还随 corpus size衰减，没有 uniform entropy bound。论文自己承认只能防有限 cycle 的 degenerate collapse，且不防窄 architecture class。（pp. 5, 7, 11-13）
- **delta valid-rate模型是事后校准。** `lambda ~= 0.995`、length ratio约0.20给预测 2.23，实际 1.41；只能支持“更短输出通常更易合法”的方向，不能当 first-principle quantitative prediction。（pp. 4-5, 7-8）

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| delta validity direction | mean 0.713 / full-code 0.506 = 1.41 | Delta-NAS vs earlier full generation | pp. 5, 7-8; CSV | medium; reused unmatched corpus |
| elite plateau | last cycles大致 0.73-0.76 | fixed `tau=0.40` | pp. 4, 7-8 | low-medium; raw series fluctuates and Qwen范围更宽 |
| proxy/full rank correlation | Mistral 0.926, Qwen 0.635, DeepSeek 0.495 | each LLM selected top set | p. 6, Table 1; CSV | medium; task/selection confounding |
| significance | Bonferroni p: `7.7e-7`, `0.033`, `0.306` | 3 LLM family | p. 6 | high for reported calculation |
| new compute | 43 successful 50-epoch runs, ~4 GPU-hours | RTX 4090 24GB | p. 12 | medium-high |
| monotone quality | author says 3-cycle smoothed trend rises | per-cycle mean | pp. 7-8 | low; public CSV does not reproduce ordinary monotonic smoothing |

## 公开 CSV 复算

- raw `mean_acc` 在 21 个相邻 transition 中下降：DeepSeek 9 次、Mistral 12 次、Qwen 12 次。
- ordinary trailing 3-cycle mean 仍下降：DeepSeek 10 次、Mistral 10 次、Qwen 13 次；Mistral/Qwen raw 第 21 cycle（0.6249/0.6210）低于 cycle 0（0.6466/0.6421）。因此“3-cycle smoothed monotonic”至少不是随文 CSV 的普通 rolling mean 结果，论文未给 smoothing code。
- Mistral 16 pairs 混合 MNIST 9、CelebA 6、SVHN 1；overall Spearman 0.926。仅同任务重算时 MNIST N=9约0.750、CelebA N=6约0.829，样本很小；Qwen/DeepSeek均只含 MNIST。
- 跨任务 accuracy level与训练难度会同时增大 `sigma_arch` 和相关性；把这种 between-task variance解释为 architecture-level proxy signal会高估跨架构排序证据。

## 公平性与可信度检查

- 3,300 candidates 不是本文新随机重复，而是同一 Delta-NAS adaptive experiment 的 reanalysis；不能当 independent observations，也不能证明跨第三方 LLM/search space 泛化。
- 每种 LLM 只有一个 22-cycle trajectory；不同 cycles共享 corpus与 LoRA history，不能用 cycle rows替代 search seeds。
- top-20 selection压缩 proxy范围，17 个失败又非随机排除；相关性只描述 surviving selected pool。
- Mistral跨三数据集、Qwen/DeepSeek只在 MNIST，LLM ordering与 dataset composition混杂。
- proxy theorem假设 bivariate Normal、additive independent noise；Qwen accuracy ceiling已经明显违背模型，论文也承认 predicted 0.10 vs observed 0.635。
- 一 epoch quality的条件收敛即使成立，也不能推出 50-epoch quality、真实设备目标或 Pareto improvement。

## 可复现性与代码/数据

- 优点：source tar提供 66-row cycle summary与43-row proxy/full pairs；表1主要 correlation可独立重算，PDF/TeX一致。
- 缺口：没有 smoothing code、完整 3,300 candidate manifest、LoRA checkpoints、per-candidate failures、dataset splits或本论文独立 repo。
- `cycle_data.csv`只有聚合行，不能审计每轮50 proposals、novel admissions、duplicates或自适应依赖。
- 50-epoch pairs给数值但不含 architecture source/hash、training config、seed、failure原因；无法重跑具体候选。
- 与 Delta-NAS公开仓库的paper-exact commit/revision仍未绑定。

## 与 AgenticNAS 的关系

- 可直接采用的诊断是：在每个 dataset、固定 recipe与固定架构分布内估计 proxy/full residual variance；只有 `sigma_arch^2`明显大于` sigma_noise^2` 才信任低保真排序。
- 不应跨任务混算 raw accuracy SNR；可使用 task-normalized rank、hierarchical model或每任务 correlation，再做 meta-analysis。
- convergence claim必须围绕实际 typed action distribution、finite candidate budget、invalid/duplicate与多 search seeds；不能把 MLE/KL identity当作性能保证。
- novelty应基于 canonical architecture graph/action distance，并同时报告 generator entropy、unique valid rate与semantic mode coverage。
- `quality_proxy` 与 `latency_proxy_ms`只能作流程占位符；任何 proxy都必须用本仓库公开实验单独校准，不能移植本文相关系数。
- clean-room只使用论文、公开 CSV/代码和自建实验；不得推断内部 Archai、模型端点、日志或私有架构。

## 最小复现实验

- 在固定公开数据集与4-10层Conv1d Transformer typed space，预先均匀抽100个架构；每个架构跑1/3/10 epoch proxy与完整训练，至少3个training seeds。
- 分层估计within-dataset SNR、Spearman/Kendall与bootstrap CI；预注册proxy length选择，禁止用test set或top-k筛选后再报告全局相关性。
- 搜索对照：static LLM、cumulative elite LoRA、current-round elite CE、native evolution；统一attempted/evaluated candidates、LLM calls/tokens、GPU-hours，至少5个search seeds。
- 检查raw mean/best-so-far/elite mass而非只画平滑曲线；若主张convergence，发布每候选manifest、distribution diagnostic与停止规则。
- top-k在untouched test与真实设备重测quality、latency、peak memory；报告Pareto/HV及proxy选错前沿点的比例。

## 局限与风险

- 质量单调与几何收敛依赖强且未验证的 projection/expressiveness 条件；有限样本 proof 存在近似单调到单调收敛的缺口。
- 公开 empirical evidence主要复用单个 Delta-NAS trajectory，缺少独立 search seeds与第三方方法。
- proxy实验样本小、top-selected、completion-selected且跨任务混杂。
- delta validity的数值预测是事后校准，不能外推到typed actions或其他LLM。
- 没有hardware Pareto、Conv1d Transformer或4-10层受限空间证据。

## 可引用摘要

该文把累计 elite corpus 上的 LoRA fine-tuning 写成 parametric cross-entropy projection，并以 Delta-NAS 的 3,300 个 proposals及43个50-epoch surviving pairs讨论validity、novelty和proxy reliability。随文 CSV可复算三种LLM的proxy/full correlation，但Mistral跨任务混合、样本经过top/completion selection，且普通raw或3-cycle rolling mean不呈单调。由于quality-monotone projection本身未对LoRA验证，有限样本证明也不足以直接调用单调收敛，该工作更适合作为proxy-fidelity与理论假设清单，而不是无条件收敛保证。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2605.30103
- PDF：https://arxiv.org/pdf/2605.30103
- TeX/CSV source：https://arxiv.org/src/2605.30103
- 关联 Delta-NAS：https://arxiv.org/abs/2605.04903
- 已核对：标题、作者、日期、arXiv ID/DOI、theorem assumptions/proofs、Table 1-2、66/43-row CSV、候选/训练/GPU预算与关键渲染页。
- 未核对：具体 architecture code、完整 candidate manifests、smoothing implementation、paper-exact checkpoints、独立 rerun与第三方复现。
- [ ] 已由人工决定 `retained` / `discarded`
