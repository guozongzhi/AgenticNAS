---
title: "Coverage You Can Steer: Online Conformal Calibration for RL-Driven Hardware-Aware NAS"
authors: "Pedro Brandimarte, Nerea Aranjuelo, Marcos Nieto, Oihana Otaegui"
year: "2026"
venue: "arXiv:2610.03127v1"
paper_url: "https://arxiv.org/abs/2610.03127"
source_pdf: "https://arxiv.org/pdf/2610.03127"
code_url: "https://github.com/Vicomtech/rl-hw-nas"
parser: "Codex"
parsed_on: "2026-10-05"
status: codex_draft
tags: [nas, hardware-aware, conformal-prediction, evaluation-filter, reinforcement-learning, adjacent-baseline]
---

# Coverage You Can Steer

> 本笔记基于 arXiv v1 的 35 页 PDF、官方 HTML 与作者 GitHub 占位仓库。论文不使用 LLM/Agent，只作为传统 hardware-aware NAS、在线校准评估过滤和 matched-budget proposer 对照的邻接基线；所有结果均为作者报告，未在本仓库运行。

## 一句话结论

- 论文把 adaptive conformal inference（ACI）放入 RL-NAS 评估前置过滤器，按用户给定风险水平在线校正 reward upper bound；在三个 CNN family 上作者报告可剪掉 25%–50% candidate evaluations，同时没有测得最终 accuracy 损失。
- 对本仓库最有价值的不是 RL controller：作者自己的 PPO 在 1,000 个真实 evaluation 下不如 random/evolution，而是“提案器无关的在线风险校准 + false-discard ledger + matched real-evaluation budget”。
- 关键限制是硬件 latency/memory 全部来自单一、未校准到设备的解析式 MCU cost model，训练只用 partial-training proxy；没有真机 latency、peak memory、energy、GPU-hours 或 wall-time。代码 URL 已存在，但截至本轮只有 README，承诺论文发表后发布源码。

## 书目、版本与来源

- arXiv ID：`2610.03127v1`；v1 submittedDate 为 2026-10-02 10:47:58 UTC，OAI datestamp 与官方 announcement 为 2026-10-05。
- 当前发表状态：arXiv preprint；未见正式会议/期刊信息。arXiv DOI 为 `10.48550/arXiv.2610.03127`（页面标注 pending registration）。
- PDF：35 页，SHA-256 `cffbc5e9a15d00dbb7b1d1cf6bb412547e170bee9d29402042dd7ef4f99de718`。
- 作者代码仓库：`Vicomtech/rl-hw-nas`，本轮 `HEAD=778ee383582b61f3f2f88658a9b69b2a7a89849c`；唯一提交是 2026-09-21 的 README，占位文本明确写源码将在论文发表后发布，故实验代码、配置与原始 traces 尚不可核验。

## 搜索对象、变量和固定项

- **实际搜索对象**：离散 CNN 架构与逐 block quantization bit-width；目标 reward 合并 partial-training accuracy、估计 latency 和估计 memory penalty，属于 hardware-aware NAS，不是 HPO（PDF pp.8–10）。
- **结构变量**：depth、base channel width、kernel `{3,5}`、skip on/off、pooling `{max,avg}`，以及每 block bit-width `{4,8}`；sequential family 还逐层改变 kernel、channels、bit-width。LeNet-like depth 2–4、MobileNet-like 4–12、ResNet-like 8–20（pp.8–9）。
- **固定项**：family 对应数据集为 MNIST/CIFAR-10/CIFAR-100；同一 experiment 内固定 proxy、数据子集、reward、cost model、controller/seed 和 filter arm。默认 proxy 为 5 epochs + 固定 10% train subset；search-quality comparison 用 15 epochs +30%（pp.9、16–17）。
- **不是 Pareto 搜索**：reward 用 `accuracy - latency penalty - memory penalty` 的固定标量化，论文没有 Pareto archive 或 hypervolume（p.8）。

## 搜索闭环、proposal 与 feedback

- Macro search 用双 actor CTDE-PPO：一个 agent 提 macro-architecture，另一个提 per-layer bit-width；每次 joint decision 形成完整架构，再把实测 proxy reward 回传。Sequential MDP 逐层构造，complete network 每 episode 只做一次真实 evaluation（pp.10–11）。
- Filter 在训练前根据 surrogate upper bound 与阈值 `tau` 接受或剪枝；只有被接受候选得到真实 reward 并用于在线更新。被拒绝候选给 controller 固定 reward `-1`（pp.11–13）。
- ACI 每个 evaluation 用 coverage error feedback 更新 offset；AgACI 聚合多个 step sizes；Mondrian ACI 按 construction depth 分组。它们是数值状态而非自然语言 reflection/memory，也没有 LLM proposal-feedback loop（pp.12–16）。
- Baselines：无 filter、calibrate-once split conformal、periodic recalibration（论文称 faithful MARCO baseline）、GP-UCB；search proposer 对照含 random、regularized evolution、PPO、greedy acquisition 与 MCTS（pp.15–17、25–27）。

## 预算、失败与成本账本

- Bandit experiments：50 iterations ×20 trials = **1,000 proposed candidates**，前 100 个作 warm-up；sequential experiments 为 150 construction episodes（p.17）。
- Calibration sweeps 主要为 3 seeds；depth-conditional audits 为 8 seeds。PPO/random/evolution 和 directed search 都以 1,000 个 real evaluations、3 seeds 比较（pp.16–17、25–27）。
- evaluation saving 以 prune rate 报告；offline replay 记录 prune、false-discard 和 realized coverage。论文未给每个 run 的 attempted/accepted/trained/pruned 原始整数 ledger，也未报告 invalid architecture、duplicate、OOM、training divergence 或 retry 数。
- 训练/GPU/wall-time、energy、主机型号未报告；没有 LLM calls/tokens/费用，因为方法不使用 LLM。
- 作者把“未训练就剪枝”称为 evaluation saving，但每个被接受 candidate 的 proxy training 成本仍未换算为 GPU-hours 或 wall time；full training 与部署复验也未计入。

## 硬件目标与测量口径

- reward 的 latency `T(a)`、weights + peak-activation memory `M(a)` 均由作者自建解析式 MCU oracle 计算；默认 budget 为 `T_B=0.3 ms`、`M_B=512 kB`，directed-search testbed 将 memory 收紧到 256 kB（pp.8–9、17）。
- cost model 对 design knobs 单调，但**没有校准到任何物理设备**。论文明确把 GPU/NPU/edge target 的 measured-cost validation 留作未来工作（pp.28–29）。
- 因此本文不能作为真实 latency、peak memory、energy 或 deployment Pareto 证据；只能作为预算约束下的控制流与排序实验。

## 核心结果

| Claim | Author-reported result | Comparator | Evidence locator | Confidence |
|---|---|---|---|---|
| 在线 coverage 可控 | ResNet/CIFAR-10 的 ACI mean calibration error 0.001、max std 0.002；requested 0.95/0.90/0.80/0.70 对应 realized 0.949/0.900/0.798/0.701 | split、periodic split、GP-UCB | PDF pp.18–19, Tables 2–3 | high |
| 节省可按风险调节 | LeNet prune 30.3%→39.5%，ResNet 26.8%→36.3%（delta 0.05→0.3） | 静态 filters | pp.20–21 | medium-high |
| 校准过滤未测得 quality 损失 | ACI/AgACI 在全部 family/delta/seed 找到与 unfiltered 相同 best architecture，同时作者概括剪掉 25%–50% evaluations | unfiltered | pp.21–22、28 | medium-high |
| 静态 recalibration 可误删 optimum | ResNet best accuracy 0.481 vs 其余 arm 0.505；作者日志称每个 seed 都剪掉最佳架构 | other filter arms | p.21 | medium |
| PPO 不是更强 proposer | 1,000 evaluations 后 random/evolution/PPO best reward 为 0.7252/0.7148/0.7040 | matched real-evaluation budget | p.25, Table 6 | high |
| calibrated acquisition 有窄场景收益 | constrained ResNet testbed 1,000 evaluations 后 calibrated acquisition reward 0.695、accuracy 0.734；random 为 0.656/0.673 | random、PPO、uncalibrated/mean acquisition | pp.26–27, Table 7 | medium |

## 公平性、复现性与局限

- 同一表内 proposer/filter 使用相同 real-evaluation budget、code version 和 seeds，预算公平性比只报搜索轮数强；但 proxy-training 计算量、surrogate/refit/MCTS 计算与端到端 wall time没有计量。
- directed-search 证据只覆盖一个 constrained ResNet-like testbed、3 seeds；固定 optimism 已带来大部分收益，online calibration 只再增加 0.004 reward，不能泛化成所有 NAS search 都更优（pp.26–28）。
- weak proxy 的 landscape 会退化为“warm-up 偶然命中”的 needle；作者因此换 strong proxy 做 search-quality comparison。校准结论可对 proxy outcome 成立，但最终 full-training 排序 fidelity 未验证（pp.9、25、28–29）。
- PPO 学到更高 mean proposal reward，却错过 argmax；这是“expected reward 与 NAS best-so-far objective 不一致”的直接负结果，不能把 policy learning 本身写成搜索效率提升（pp.25–28）。
- 代码、原始 per-trial trace 和配置尚未公开，论文数值当前不可独立复现。

## 对当前 AgenticNAS 的价值

- 将 ACI/Mondrian 视为 evaluator-side risk controller，而不是 Agent memory：它可为 low-fidelity early rejection 提供 `requested risk → realized false-discard/coverage` 的可审计协议。
- 在 4–10 层 Conv1d Transformer 上应保留 native/random evolution、stateless LLM、memory-aware LLM 的相同 proposed/accepted/trained/evaluated 预算；若使用 filter，必须同时报告被剪枝数、事后 false-discard audit、best-so-far 与 seed variance。
- 真正进入本仓库 hardware Pareto baseline 前，需要把解析式 `T/M` 换成目标设备真实 latency、peak memory、energy，并保留 Pareto archive/hypervolume，而不是固定加权 reward。

## 链接

- 论文：https://arxiv.org/abs/2610.03127
- PDF：https://arxiv.org/pdf/2610.03127
- 代码占位仓库：https://github.com/Vicomtech/rl-hw-nas
- 核验 commit：https://github.com/Vicomtech/rl-hw-nas/commit/778ee383582b61f3f2f88658a9b69b2a7a89849c
