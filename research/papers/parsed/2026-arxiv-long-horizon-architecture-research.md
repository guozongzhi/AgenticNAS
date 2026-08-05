---
title: "Long-Horizon Autonomous Architecture Research with a Language-Model Agent: A Behavioural Case Study"
authors: "Aon Safdar, Mohamed Saadeldin"
year: "2026"
venue: "arXiv:2608.01995v1; submitted to IEEE (paper claim)"
doi: "10.48550/arXiv.2608.01995"
paper_url: "https://arxiv.org/abs/2608.01995"
source_pdf: "https://arxiv.org/pdf/2608.01995"
source: "arXiv v1 metadata/PDF, accessed 2026-08-04"
parser: "Codex"
parsed_on: "2026-08-04"
status: codex_draft
tags: [llm-nas, long-horizon, memory, code-generation, mixed-search-space, vision-transformer]
---

# Long-Horizon Autonomous Architecture Research with a Language-Model Agent: A Behavioural Case Study

> 本笔记基于 arXiv v1 的 29 页 PDF。论文的目标是描述单次长时程行为轨迹，不是宣称通用 NAS SOTA；具体 LLM 版本、完整训练代码与 tracking export 暂因双盲未公开。

## 一句话结论

单个 CLI 型 frontier LLM 在约 10 周、约 130 次实质训练和约 2,400 GPU-hours 中，依次提出、实现、训练、解释并 commit/revert 非标准 channel-attention Vision Transformer 假设；日志揭示 greedy 单冠军流程会诱导增量搜索、饱和与失败后风险规避，但这是单 Agent、单问题、单长轨迹，结构与训练配置/协议又跨阶段变化，因此应归为 `mixed-search-space` 行为案例，而非纯 NAS 的 matched-budget 效果证据。（pp. 1–7, 15–17, 21–25）

## 书目信息与来源核验

- arXiv ID：2608.01995v1；提交时间：2026-08-03 09:56:34 UTC；arXiv DOI：10.48550/arXiv.2608.01995。
- 作者：Aon Safdar、Mohamed Saadeldin；当前 venue 为 arXiv，PDF/metadata 只称已投稿 IEEE，不能写成已接收。
- 论文：https://arxiv.org/abs/2608.01995
- PDF：https://arxiv.org/pdf/2608.01995 ；29 页；本次读取副本 SHA-256：`6ac9d5a26a9eabe9e19b7d7daf2ec8e61b3e6db47cdb8ad385d2de14b202b5ea`。
- 代码/数据：匿名 supplementary 声称包含 brief、instructions、研究日志、CSV、figure scripts、Slurm templates 和 champion YAML；完整训练代码与 tracking export 计划在 acceptance 后以永久 DOI 发布。（pp. 21, 24）
- 置信度：书目信息 high；闭环与成本 high；headline accuracy medium；行为归因 low-medium；独立可复现性 low。

## 研究问题与贡献

- 问题：当单个通用 LLM 同时承担 proposer、implementer、executor、interpreter 与 archivist，长时程真实架构研究会出现什么行为模式，workflow 又如何塑造这些行为。（pp. 1–3）
- 研究对象是非标准 Vision Transformer 的 pure channel-attention 设计；Agent 直接编辑模型代码/配置并在 CIFAR-10、CIFAR-100、ImageNet-1K 上训练。（pp. 2, 6–7）
- 主要贡献是完整 per-hypothesis trace 与行为分析：快速早期收益、长饱和墙、扩大 action surface 后恢复、greedy/anchoring/risk aversion，以及跨 scale anti-transfer。（pp. 7–16）
- 作者明确不声称替代人类研究者，也不把最终架构数字作为独立 SOTA 主张。（pp. 2, 6, 16, 24）

## 方法拆解

### 搜索或优化对象

- Agent 每轮只提出一个 single-variable hypothesis，可修改配置或代码；accepted diff 成为新的 champion，失败则 revert。（pp. 3–4, 21–23）
- Phase 1/1b 为 CIFAR-10、约 5.8M 参数；Phase 2 为 CIFAR-100、22M；Phase 3 为 ImageNet-1K、22M budget 并允许双 GPU distributed configs。（p. 6）
- 可变项包括 block counts、embedding widths、normalization、positional encoding、attention mechanism、training configuration 等；阶段之间还改变 dataset、parameter budget、augmentation/epoch protocol。（pp. 6–7, 17, 23–29）
- 因结构与训练字段共同变化，且 evaluator/protocol 跨阶段不固定，本笔记归为 `mixed-search-space`；它不能直接支撑仓库固定 recipe 的 NAS 或固定 architecture 的 HPO。

### Agent 与优化闭环

- 每轮读取研究日志和可选 synthesis，检索文献，提出有动机的单变量假设，编辑 code/config，检查 parameter/compute budget，提交一个训练 job 并结束该 turn。（pp. 3–4）
- job 完成后 Agent 解析主指标、记录相对 champion 的 delta；改善则 commit，否则 revert。该规则等价于 greedy hill climbing，论文把它视为行为偏差的一部分来源。（pp. 3–4, 15–17）
- persistent memory 是固定模板研究日志，记录 identifier、motivation、literature basis、exact diff、parameter/FLOP/wall-clock budget、result 与 Git status；上下文过长后加入 Agent 自写 compact synthesis。（pp. 3, 16, 22–24）
- Phase 1b 起通过 MCP 增加 arXiv full text、GitHub repository QA 与 model/dataset hub；多个变化同时发生，因此不能单独归因给 literature access。（pp. 5, 17, 21）
- 具体 LLM 只描述为 terminal-oriented frontier instruction-tuned model；模型 identifier/version 在未公开 supplementary 中，主文没有可核验名称，也未 fine-tune 或加 RAG/domain scaffold。（p. 21）

### 评估与预算

- 四个 phase marker 共 42 + 25 + 32 + 18 = 117 个列明 hypotheses；约 150 个 submitted jobs，约 130 个不少于 5 分钟的实质训练。（pp. 4, 6）
- 总跨度约 10 周、约 2,400 aggregate GPU-hours，median substantive run 约 2.5 小时、最长约 6 天；shared cluster 混合多代 GPU，论文未给逐型号成本。（p. 4）
- small-scale job 单 GPU，ImageNet phase 每 job 双 GPU；parameter/FLOP/wall-clock 在提交前重算。人类另有每日约 1–2 小时 passive oversight。（pp. 21, 23–24）
- LLM token consumption 只估计为数千万，未系统记录，也未报告费用、逐假设 calls、sampling、seed 或 retry 账。（p. 24）
- 没有 matched random/evolution/stateless LLM/memory-aware LLM baseline，也没有相同 compute/hypothesis budget 的 human control；每个 accepted hypothesis 未做多 seed replication。（pp. 16–17, 24）
- 没有多目标 Pareto、真实 latency、peak memory 或 energy；parameter/FLOP/wall-clock 是预算检查，不是部署设备测量。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| CIFAR-10 trajectory | baseline 69.67%；Phase 1 champion 95.10%；Phase 1b champion 96.59% (100ep) / 97.25% (300ep) | 单条 greedy champion chain | pp. 6–8, Table 4/Fig. 2 | medium |
| CIFAR-100 trajectory | Phase 2 champion 83.37% (100ep) / 85.07% (300ep) | 同一 Agent 的 sequential hypotheses | p. 7, Table 4 | medium |
| ImageNet-1K trajectory | baseline 77.65% (100ep) / 79.00% (300ep)；champion 77.91% (100ep) | 18 hypotheses，只有 2 次 accepted improvement | pp. 6–8 | medium |
| phase success rate | 36%、38%、32%、12% | 各 phase accepted/attempted | p. 6, Table 3 | high |
| 计算规模 | ≈130 substantive runs、≈2,400 GPU-hours、≈10 weeks | 无 matched control | p. 4, Table 1 | high |
| 行为主张 | 快速收益→饱和→恢复；greedy bias/risk aversion | 单 Agent/单问题/单轨迹定性分析 | pp. 8–17 | low-medium |

## 公平性与可信度检查

- 论文的主要可信价值是审计轨迹与 workflow failure modes，不是与其他 NAS 算法比较后的性能优势。
- 没有 classical evolution、random mutation、stateless LLM、memory-aware LLM 或 human researcher 的相同 hypothesis/GPU/LLM 预算对照，无法隔离 Agent 能力与“117 次尝试 + champion preservation”的收益。
- 单冠军 commit-or-discard 直接强制 greedy hill climbing；tool expansion 同时伴随 instruction 与 code-authority 变化，workflow confound 没有做受控消融。（pp. 16–17）
- dataset、scale、augmentation 与 epoch protocol 跨阶段变化，cross-scale anti-transfer 可能部分来自 evaluator divergence；不能把跨阶段 accuracy delta 当作同一 search curve。（p. 17）
- 只有一条 stochastic LLM trajectory，run-to-run variance 未知；accepted hypotheses 也未逐项多 seed 重训。（pp. 17, 24）
- 具体 frontier model/version、training code 和 tracking export 暂不可访问，匿名 supplementary 是否完整需人工取得并验证。

## 可复现性与代码/数据

- 主文给出 Algorithm 1、phase/hypothesis counts、human interventions、compute footprint、per-hypothesis 表、log schema、MCP tools、Slurm 约束与已知 autonomy failures。
- supplementary 声称含完整 research log、CSV、figure scripts、brief/instructions、Slurm/watch scripts 与 champion YAML；当前 arXiv 入口没有独立可下载代码仓库。
- 完整 model/training code、failed-run configs、tracking export、具体 LLM identifier/version 暂未公开；因此不能独立复现 champion 或审计所有 prompts/calls。
- 作者称用待发布代码重跑可在 run-to-run variance 内复现 champion，但没有预算为每个 accepted hypothesis 做多 seed；此主张当前仍是作者报告。（p. 24）

## 与 AgenticNAS 的关系

- 最可复用的是“每次一个 typed hypothesis + pre-run budget check + post-run result + commit/revert + compact synthesis”，但应把开放 diff 收窄到声明式 `MutationAction`。
- 单 champion 会导致路径依赖和风险规避；本仓库应保留 Pareto archive、多样性分支与少量显式 exploration budget，并与纯 greedy policy 做 matched-budget 对照。
- memory 只记录 clean-room action、公开结构字段、typed failures 和 measured objectives；不得保存内部架构代码、端点或日志。
- 跨 dataset/scale 时必须重新验证 top findings，并固定或显式记录 evaluator changes；NAS 与 HPO 继续分轨，不共享 archive/reward/manager。
- 论文没有真实 latency/memory/energy；`quality_proxy` 与 `latency_proxy_ms` 仍只能是控制流占位符。

## 最小复现实验

- 固定同一个 4–10 层 Conv1d Transformer search space、training recipe、data split、200 attempted trials、GPU 和 LLM budget。
- 对照 native evolution、stateless LLM greedy single champion、memory-aware greedy、memory-aware Pareto archive、Pareto + 10% diversification；每组至少三 search seeds。
- 每次只发一个 `block/cell/op/connectivity` typed action；所有 invalid/duplicate/OOM/timeout/divergence 计入主预算。
- 指标：best-so-far/hypervolume、accepted rate、diversity、risk-taking proxy、plateau length、seed variance、LLM tokens/费用、GPU-hours、真实 latency/memory。

## 局限与风险

- 单 Agent、单架构问题、单长轨迹；行为模式是否跨模型/任务复现未知。
- 无 matched human/algorithm baseline，workflow、tool access、instruction changes 与 scale transition 均有混杂。
- 结构与训练 config 混合变化，且阶段间 evaluator 不同，不属于固定 recipe 的纯 NAS。
- 具体模型、完整训练代码与 token/call 账未公开；2,400 GPU-hours 也未按 GPU 型号细分。
- 仅检查 parameter/FLOP/wall-clock budget，没有部署 latency、peak memory、energy 或 Pareto。

## 可引用摘要

该案例让单个 CLI 型通用 LLM 在约 10 周内执行真实 Vision Transformer 架构研究：每轮提出一个假设、修改 code/config、提交训练、记录结果，并以 commit/revert 维护单一 champion。作者公开报告约 130 次实质训练和约 2,400 GPU-hours，并分析出快速收益、饱和、恢复、greedy anchoring 与失败后风险规避等模式。由于只有单 Agent/单问题/单轨迹，缺少 matched human/算法对照，且结构与训练配置及跨阶段协议混合变化，这些观察应作为 workflow 设计假设，而非纯 NAS 的普遍效果结论。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2608.01995
- PDF：https://arxiv.org/pdf/2608.01995
- 已核对：标题、作者、日期、arXiv ID/DOI、闭环、phase/hypothesis counts、GPU-hours、headline results、memory、human interventions、limitations 与 code availability。
- 未核对：具体 LLM/version、匿名 supplementary 实物、完整训练代码、independent rerun、LLM calls/tokens/费用与多 seed variance。
- [ ] 已由人工决定 `retained` / `discarded`
