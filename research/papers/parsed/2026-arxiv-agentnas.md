---
title: "Agentic Neural Architecture Search"
authors: "Seokhoon Jeong, Mijung Kim, Taehwan Kim"
year: "2026"
venue: "arXiv:2607.07984v1"
doi: "10.48550/arXiv.2607.07984"
paper_url: "https://arxiv.org/abs/2607.07984"
code_url: "https://github.com/alroimfebruary/AgentNAS"
source: "arXiv HTML/PDF/TeX and official code repository, accessed 2026-07-29"
parser: "Codex"
parsed_on: "2026-07-29"
status: codex_draft
tags: [llm-nas, slotted-architecture, evolution, nas-bench-360, unseen-nas]
---

# Agentic Neural Architecture Search

> 本笔记基于 arXiv v1 正文、源码和作者链接的官方代码库。所有实验数字均为作者报告，尚未独立复现。

## 一句话结论

AgentNAS 先让 LLM 生成并迭代训练真实神经网络，再把最优 seed 拆成带可替换 module/glue/learning-rate slots 的有界搜索空间，最后用 regularized evolution 做组合搜索；它是当前与本仓库“LLM 定义结构空间、传统 NAS 搜索组合”最直接的对照，但论文并非多目标硬件感知 NAS，且不同任务的实际候选预算和计算量并不完全一致。（§3，§6，Appendix A.7）

## 书目信息与来源核验

- arXiv ID：2607.07984v1；提交日期：2026-07-08；arXiv DOI：10.48550/arXiv.2607.07984。
- 作者：Seokhoon Jeong、Mijung Kim、Taehwan Kim；当前可核验 venue 为 arXiv，未在正文中确认会议录用。
- 论文：https://arxiv.org/abs/2607.07984
- 代码：https://github.com/alroimfebruary/AgentNAS；仓库说明论文复现应使用 `v1.0-reproducible` tag，`main` 是后续开发版本。
- 置信度：书目信息和方法结构 high；表格结果 medium；独立可复现性 medium。

## 研究问题与贡献

- 问题：LLM 可在开放代码空间生成架构，传统 NAS 擅长有界组合搜索；如何把“构造搜索空间”和“探索搜索空间”分开，并分别测量贡献。
- 三阶段：Phase 1 由 Planner、Code Generator、Data Explorer 生成和训练 seed；Phase 2 将 seed 模块化并合成为 slotted architecture；Phase 3 在 slot 组合上执行 NAS。（§3）
- 核心主张：LLM seed 与组合 NAS 互补；作者在 NAS-Bench-360 和 Unseen NAS 共 17 个任务上报告 11 个任务达到其定义的最新最佳结果。（Abstract，§4.4）

## 方法拆解

### 搜索或优化对象

- 搜索对象是真实、可训练的 PyTorch 神经网络及其训练 recipe，不是 Agent 工作流。
- Phase 1 在开放代码空间同时改变 backbone、深度、宽度、模块、优化器、学习率、schedule、augmentation、batch size 和 epochs。
- Phase 2 大体保留 seed 的宏观结构，将其拆为最多 20 个 slots、每个最多 8 个 alternatives；slot 包括 module-level replacement、identity-default 的 additive glue，以及学习率倍率 `{0.25, 0.5, 1, 2, 4}`。（§3.2，Appendix A.7.1）
- 搜索空间跨 1D/2D 分类、音频、多标签、回归和分割；不是专门的 4–10 层 Conv1d Transformer 空间，也没有 block/cell/op 的固定 JSON schema。

### Agent 与优化闭环

- 观察：数据探索报告、候选代码、proxy validation 指标、leaderboard、训练失败和预算状态；test 指标不暴露给搜索循环。
- 动作：Planner 选择 `<EXPLORE>`、`<EXPERIMENT>` 或 `<STOP>`；Code Generator 直接生成模型代码，Slot Planner 单次生成 slotted architecture。
- 记忆：leaderboard、self-generated summary 和 checkpointed evaluation state；论文没有报告 duplicate rate 或统一的显式 memory ablation。
- Phase 3 默认 regularized evolution；另比较 random search 和 GDAS。失败状态 `rejected/oom/error/timeout` 消耗候选预算，但不增加 no-improvement patience。（§3.3，Appendix A.7.2）

### 评估与预算

- 数据：NAS-Bench-360 的 10 个任务和 Unseen NAS 的 7 个可再分发任务；后者对 LLM 隐藏任务身份和领域元数据。
- Phase 1 最多 160 次架构评估，连续 64 个成功候选无提升则停止；Phase 3 独立最多 160 次、population 16、最多 10 generations、patience 64。
- proxy 使用完整 recipe 的 30% epochs，每个候选最多 60 分钟 GPU time、11,264 MB VRAM；每阶段 top-8 再完整训练，单次最多 24 小时。（§3.1，Appendix A.7.2）
- 硬件：每个候选单张 RTX 2080 Ti；整套实验使用 8 张 11 GB RTX 2080 Ti。论文报告各任务 GPU-hour 和 wall-clock，但未报告完整 LLM token/API 费用。
- 目标：各任务的单一 validation metric；参数量、FLOPs 和 GPU time主要作透明度/约束报告，不进入统一 Pareto 目标。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 跨任务总体结果 | 17 个任务中 11 个达到作者定义的 SOTA；NAS-Bench-360 平均 rank 1.50 | WRN16-4、GAEA DARTS、Expert、einspace | §4.4, Tables 1–2 | medium |
| NAS 对 seed 的增益 | Spherical error 45.08→38.71；CIFARTile 11.20→8.48 | AgentNAS-LLM vs AgentNAS-Full | §4.4 | high |
| 多随机种子 | 6 个代表任务、seeds `{42,43,44}`，标准差 0.38–2.10 个百分点 | 同一 pipeline 不同 seed | §5.2, Appendix A.4 | medium |
| 计算成本 | NAS-Bench-360 单任务 P1+P3 报告 9–698 GPU-hours；方法高于 GAEA | GAEA、einspace | Appendix A.1, Tables 4–7 | high |

## 公平性与可信度检查

- 论文对 LLM-only 延长采样和 NAS 追加 160 次评估做 matched-candidate 分析，这是有价值的机制对照；但主结果中的公开基线来自原论文，不是全部在相同硬件、训练 recipe、候选数和 wall-clock 下统一重跑。
- Phase 1 与 Phase 3 都可因 patience 或 LLM `<STOP>` 提前结束，实际预算跨任务/模型变化；作者在局限中明确承认并非完美控预算。
- LLM 同时搜索架构和训练 recipe，而若干基线使用固定 recipe，因此性能差异不能只归因于架构搜索。
- 论文报告三 seed 分析，但不是 17 个任务全部三 seed；完整 LLM token、费用、action validity 和 duplication rate 未报告。
- DeepSEA 出现 validation 改善但 test 退化；6 个任务仍落后各自最强公开基线。（§4.4，§6）

## 可复现性与代码/数据

- 官方仓库公开 MIT 许可实现、tests、配置和 `v1.0-reproducible` tag；这是当前三篇新增中可复现资产最完整的一篇。
- 复现仍需要 Anthropic 模型访问、NAS-Bench-360/Unseen NAS 数据和多张 GPU；模型版本、API 行为和费用可能随时间变化。
- 论文提供 prompts、预算、失败状态、slots caps 和搜索参数；未提供完整 LLM token ledger。

## 与 AgenticNAS 的关系

- 最直接可复用的是“slotted architecture”：可把 4–10 层 Conv1d Transformer 固定成 macro scaffold，再在 block/cell/op 层提供声明式 alternatives。
- 本仓库应保留更窄的 clean-room 边界：Agent 只输出可验证的 `MutationAction`，不直接写任意 PyTorch；slotted alternative 也应先转成 schema，再由内部 evaluator 执行。
- AgentNAS 是单目标任务性能搜索；本仓库需继续以真实 quality/latency/memory/cost 构造 Pareto，不能把 `quality_proxy` 或 `latency_proxy_ms` 当研究证据。
- 最值得验证：在同样的候选、训练、GPU 和 LLM 预算下，`fixed search space`、`LLM seed only`、`LLM-built slots + random`、`LLM-built slots + evolution` 的 hypervolume、validity、duplication 和 seed variance。

## 最小复现实验

- 固定 4–10 层 Conv1d Transformer macro scaffold、训练数据、候选数、GPU 时间、LLM 次数和三组 seeds。
- LLM 仅提出 slot definitions 或声明式 mutations；validator 拒绝越界 depth、shape 和非法 op。
- 对照 native/random mutation、stateless LLM、memory-aware LLM、LLM-built slots + regularized evolution。
- 指标：真实质量、真实设备 latency/memory、hypervolume、action validity、duplicate rate、每个合法候选总成本。

## 局限与风险

- 代码级生成使搜索空间强依赖 LLM 能力；弱模型有时无法构造可用 slots。
- 8×2080 Ti 和单候选时间/显存上限隐式偏向小模型；主结果不是统一硬件下的严格公平重跑。
- 宏观深宽主要由 seed 固定，Phase 3 更像 module recombination，不能自动证明覆盖本仓库希望的全部层级空间。
- 未报告端到端 LLM 成本、能耗和跨版本稳定性。

## 可引用摘要

AgentNAS 将 LLM 的开放式架构设计与传统 NAS 的有界组合搜索分开：LLM 先生成 seed，再把它改写为 slotted architecture，最后由 regularized evolution 搜索 slot 组合。作者在 17 个多模态任务上报告多数任务的进一步 NAS 增益，并公开复现代码；但主结果的基线预算和训练 recipe 未完全统一，实际候选数也会提前停止。对本仓库而言，其主要价值是 slotted search-space synthesis，而不是已经证实的多目标硬件结论。

## 检索与人工核验记录

- 原始来源：https://arxiv.org/abs/2607.07984
- 正文：https://arxiv.org/html/2607.07984v1
- 代码：https://github.com/alroimfebruary/AgentNAS
- 已核对：标题、作者、日期、arXiv ID、DOI、三阶段方法、slot caps、候选/GPU 预算、主要表格和局限。
- 未核对：端到端复现、LLM token/费用、所有 17 个任务的原始 traces。
- [ ] 已由人工决定 `retained` / `discarded`
