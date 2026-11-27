---
title: "Can AI Design a Better nnU-Net? A Hypothesis-Driven Architecture Discovery Loop from Failures to Design Rules"
authors: "Songtao Jiang, Yuan Wang, Fucheng Niu, Hualiang Wang, Jian Wu, Zuozhu Liu"
year: "2026"
venue: "arXiv:2611.32384v1"
paper_url: "https://arxiv.org/abs/2611.32384"
source_pdf: "https://arxiv.org/pdf/2611.32384"
parser: "Codex"
parsed_on: "2026-11-27"
status: codex_draft
tags: [llm-nas, hypothesis-driven, memory, failure-analysis, medical-segmentation, pareto]
---

# Hypothesis-driven nnU-Net architecture discovery

> 本笔记基于 15 页 arXiv v1 PDF 与官方 arXiv source bundle。所有结果均为作者报告；仓库尚未复现。source bundle 中未编入 PDF 的自动生成账本只作诊断，不当作已分页发表的稳定证据。

## 一句话结论

- 这是结构变量与训练配方分离较清楚的 `LLM × NAS`：四类 Agent 从 profiling 与结构化失败中提出可证伪假设，在冻结的 nnU-Net pipeline 内只改变 topology，并把通过反事实对照的机制沉淀为 trigger→action 规则（PDF pp.2–4）。
- 最有价值的不是 LeanNeXt 的单点 Dice，而是 **hypothesis→预审→full-budget→fresh-seed→跨任务规则** 漏斗；但 LLM token/费用、端到端 wall-time 与可执行代码均未公开，顺序波次对照也不是独立的等预算多 seed search（PDF pp.3–8；官方 source bundle）。

## 研究问题、搜索对象与固定变量

- 研究问题：能否把 NAS/LLM evolution 中通常被丢弃的失败，转成可证伪的结构假设和跨模态设计规则，而不是只按 validation score 保留单点架构（PDF pp.1–3）。
- 可变项是 3D U-Net topology：decoder convolution 数与 skip 形式、mid-encoder residual depth、coarse-stage `7^3` ConvNeXtV2 blocks，以及由 coarse prediction 驱动的 masked region-contrast module（PDF pp.4、7、9，Fig. 2，Table 5，Table 7）。
- 固定项包括 dataset fingerprint、experiment plan、preprocessing、splits、optimizer、loss、1000-epoch schedule、12 GB memory cap 与 evaluator；候选须完整训练 1000 epochs，因此分类为 architecture-only NAS，而不是训练 recipe HPO 或 mixed-search-space（PDF p.3, Sec. 3.1）。
- 搜索空间不是 4–10 层 Conv1d Transformer；论文证据只能迁移其反馈/记忆/预算 gate，不能迁移 3D segmentation 的效果结论。

## Agent 闭环、记忆与停止机制

- 四类角色由作者报告的 `qwen3.8-flash-next` 驱动并运行在 Claude Code scaffold：coordinator 写 wave brief，ideator 产出 hypothesis card，independent reviewer 在 GPU 分配前审查前提与预算，experimenter 实现、profile、训练（PDF p.3, Sec. 3.2）。
- 观察包括 stage-wise MAC/memory/step-time profile、class/clinical-stratum error decomposition 与历史 wave failures；动作必须在训练前写明 observation、mechanism、intervention、预期改善/退化 strata、compute bound 与 falsification condition（PDF pp.3–4）。
- 反馈分层为 fold-0 screen、fresh-seed replication、4-fold CV、unseen benchmarks、locked test sets 与 matched counterfactual controls；验证机制才沉淀为带 pre-training trigger 的 executable rule，供后续 wave 使用（PDF pp.3–7）。
- 论文按八个 discovery waves 组织，但未给出基于预算、plateau 或置信区间的自动停止规则；停止更像预设研究阶段完成，而非可复现的 policy termination。

## 候选、失败与成本账本

- 111 个 hypotheses 中，reviewer 在 GPU 前拒绝 59 个：12 个被已有测量否定、18 个被更简单设计支配、5 个超过 memory cap；28 个 search designs 接受 full-budget training，其中 14 个在 fresh-seed replication 或 ACDC check 被否定，最终留下 R1–R4 四条规则（PDF p.3, Sec. 3.3）。
- Fig. 6 的完整 lineage 包含 38 个 full-budget trained arms；其中既含 search designs，也含 control/reference/attribution arms。论文还报告 21 个通过 screen 的 Agent designs 用两个 fresh seeds 复核，13/21 的增益缩小（均值 −0.34 Dice points，95% CI [−0.60, −0.08]）（PDF pp.4、8, Figs. 3、6）。
- attempted hypotheses、GPU 前 rejected、full-budget designs 和 fresh-seed designs 有清楚层级；但没有逐项 invalid/duplicate/retry、实现失败/OOM/divergence 的发布账本。这里的 5 个 memory rejection 不能替代运行期失败率。
- 主 PDF 报告 1000 epochs、12 GB cap、候选数和实测 step/memory，但未报告 search GPU-days、总 wall-time、LLM calls、tokens 或费用。官方 source bundle 的未分页自动生成文件写有 `68 device GPU-days / 140 allocated GPU-days / 138 design runs`，但这些数字未进入 15 页 PDF，故只记为待作者确认的 source diagnostic，不作为已发表成本结论。
- 未找到与标题或 LeanNeXt 对应的作者 GitHub repository；官方 arXiv source 含论文生成数据与图表，不等于可执行训练/search code。

## 基线公平性与实验协议

- 关键 within-system 对照使用同一 LLM team、scaffold、block library 与 1000-epoch evaluator：score-driven Waves 1–3 为 10 个 models、0/10 in-budget；rule-guided Waves 5–8 为 13 个 proposals、8/13 in-budget（PDF pp.5、7, Table 3, Fig. 4）。
- 该对照控制了 evaluator 与大部分系统组件，但后期 wave 继承了前期失败与 profiler calibration，候选数也为 10 vs. 13；它证明的是“累积规则记忆后的系统阶段差异”，不是独立重启、多 search-seed、完全等 attempted-budget 的 policy 消融。
- Random grammar baseline 有 15 个 valid draws；one-shot Claude Opus 5.5 只有 2 个 proposals。二者与 discovery loop 的 22 个 designs 数量不同，且 random/one-shot 都未满足 step budget，因此不能把 Table 3 解读成严格等预算算法排名（PDF pp.5、7）。
- 设计数据为 KiTS23、AMOS22、ACDC；fold 0 只作 screening，folds 1–4 做 CV，另有 locked cohorts 与八个 unseen transfer benchmarks。跨任务结果降低但不能消除 rule-selection 对设计数据过拟合的风险（PDF pp.5–7）。

## 作者报告的核心结果

| Claim | 作者报告结果 | 对照 | 证据位置 | 置信度 |
|---|---|---|---|---|
| 轻量结构 | LeanNeXt 为 31.04M params、373.5 GMAC、8.02 GB、113.1 ms/step；nnU-Net 为 31.20M、477.4 GMAC、8.51 GB、123.3 ms/step | 同一 KiTS23 plan | PDF p.5, Table 2 | high（表内作者报告） |
| KiTS23 多 seed | LeanNeXt 相对 nnU-Net +1.63 Dice，8/8 fold-seed pairs，95% CI [+0.15,+3.12] | 两 seeds×四 folds | PDF pp.11–12, Table 10 | high（表内作者报告） |
| 规则阶段预算命中 | score-driven 0/10 in-budget；rule-guided 8/13 in-budget | 同 LLM/scaffold/evaluator，不同 sequential phase | PDF pp.5–7, Table 3, Fig. 4 | medium |
| 失败驱动 stepping stone | LeanDec 与 LeanAdd-NeXt 不是各 wave 最高分，却分别暴露 thin-boundary regression 与 R2/R3 interaction，成为最终规则祖先 | lineage + fresh-seed/CV | PDF pp.7–9, Fig. 6, Table 7 | medium-high |
| 跨任务结果 | LeanNeXt+ 相对 nnU-Net 在作者汇总的 15/15 evaluations 均为正，且以 0.30× ResEnc-M 参数在 12/15 rows 更高 | nnU-Net、ResEnc-M 等 | PDF pp.5、11–12, Tables 2、9–10 | medium（多任务但未独立复现） |

这些是论文结果，不是 AgenticNAS 仓库实测；`quality_proxy` 与 `latency_proxy_ms` 仍只可作控制流占位符。

## 未报告、局限与风险

- 未报告 LLM prompt/version snapshot、temperature/seed、calls、tokens、费用和 Agent wall-time；`qwen3.8-flash-next` 与 Claude Code scaffold 也没有公开可执行环境快照。
- 未发布逐候选 action/result trace、canonical architecture hash、duplicate ledger、implementation failure、runtime OOM/divergence/retry 统计。
- 表内 memory/step 是真实 profiling，但主 PDF 未标明 profiler GPU 型号，energy 与部署端 latency 均未报告；不能称为真实设备 deployment Pareto。
- 多个 source files 引用未编入 15 页 PDF 的 Supplementary tables；source bundle 虽含宏与结果文件，但缺少可独立复现的训练/search repository，预算数字仍需作者确认。
- 论文把规则驱动后期波次与前期 score-driven 波次比较；由于后期显式继承早期 observations、failures 和 cost calibration，收益同时包含 memory accumulation 与 policy change，尚不能隔离二者。

## 对本仓库的价值与最小复现实验

- 可复用：把 `proposal` 与 `hypothesis` 分开计数；训练前写 falsification card；memory 只保存通过反事实或 fresh-seed gate 的 mechanism；在 GPU 前以真实 profiler 审核 memory/step budget；将失败按 premise/dominated/infeasible/runtime 分类。
- 最小验证：在固定 4–10 层 Conv1d Transformer typed space 中，对 random/native evolution、stateless LLM、score-memory LLM、principle-memory LLM 做至少 3 search seeds；统一 attempted proposals、valid unique candidates、trained candidates、GPU/LLM/wall-time caps。
- 固定 dataset split、training recipe 与 evaluator；只允许 depth/width/operator/connectivity typed actions。报告 hypervolume、action validity、duplication、seed variance、真实 latency/peak memory/energy，并把 rejected-before-training 与 failed-during-training 分开。
- 最值得验证的假设：在相同 attempted 和 trained budget 下，**经 fresh-seed/反事实 gate 的 principle memory** 是否比保存 top-score architectures 的 archive 更能提高后续 valid-and-in-budget yield，而不是只提升单一 best score。

## 核验记录

- 官方 PDF：15 页，9,581,342 bytes，SHA-256 `c7882c2fed7361895ddaef4322471189f943af5db60b5865328808fa74353cc6`；HTTP 200、EOF、页数与逐页文本解析均通过。
- 官方 arXiv source bundle：9,732,661 bytes；用于核对未分页 funnel/GPU 宏，但未把其中未编入 PDF 的数字升级为稳定论文结论。
- GitHub exact-title/LeanNeXt repository search 未找到作者仓库；代码状态记为“未找到公开可执行实现”，不是“证明不存在”。
- 使用 PDF pp.1–12，重点核对 Tables 2–5、7、9–10 与 Figs. 3–6、10–11。
