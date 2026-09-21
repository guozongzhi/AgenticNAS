---
title: "GenomeHarness: Harnessing AI Agents for Reliable Adaptation of Genome Language Models"
authors: "Weicai Long, Yusen Hou, Houcheng Su, Junning Feng, Yanlin Zhang"
year: "2026"
venue: "arXiv:2608.21916v1"
paper_url: "https://arxiv.org/abs/2608.21916"
source_pdf: "https://arxiv.org/pdf/2608.21916"
parser: "Codex"
parsed_on: "2026-09-22"
status: codex_draft
tags: [hpo, fixed-architecture, genome-language-model, mcts, agent-harness]
---

# GenomeHarness

> 本笔记基于 arXiv v1 PDF；它是本轮最清晰的 fixed-architecture recipe-HPO 证据。

## 一句话结论

- 核心主张：在冻结 DNABERT2/NTv2-100M-Multi 骨干和任务协议后，Agent 通过 MCTS 选择 lineage、提出/修复 fine-tuning recipe，在一小时 launch budget 内完成几十个单 GPU trial，并在 freeze 后用三 seeds 做 test evaluation。
- 证据位置：PDF pp.1–8，Tables 1–3、Figs. 1–4。

## 搜索对象与固定变量

- 可变 recipe：learning rate、warmup、weight decay、layerwise decay、epochs 等训练字段。
- 固定：pretrained backbone、模型结构、task/data split、label、metric、搜索预算和 final evaluation policy；Agent 被限制为 recipe-level decisions，不能改架构。
- 层级：task → root recipe → parent/child recipe edits；每个 node 是一次完整 train-validation trial。

## Agent 闭环与失败处理

- MCTS 选择待扩展 recipe lineage；Agent 输出 patch 或根据 invalid/unstable/failed trial 修复；harness 执行、记录 status/runtime/parent/repair，并隔离 test。
- 并行 pending lineages 使用 virtual-loss 类惩罚避免重复占用同一未完成分支。
- 具体 invalid/OOM/divergence/repair rates 和重复率：未报告。

## 预算、硬件与公平性

- 每 task 固定 1h **launch budget**；到点停止启动，但 drain 已运行 trials 后再 freeze。
- 4× NVIDIA L20 46GB；最多并行四个 single-GPU trials。平均 completed trials：43/57（DNABERT2 的 NT/Genomic），36/54（NTv2 的 NT/Genomic）；累计 GPU 分钟 193/166/189/192。
- 搜索 seed=42；freeze 后 root 与 selected recipe 均用 3 seeds 做 final test。
- 没有 random/TPE/CMA-ES/pure-LLM 的同预算基线；LLM 型号、prompt、tokens 和费用在核验正文中未报告。

## 核心结果

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 多数任务改善 | 47/52 model-task settings mean test MCC 提升 | literature-derived root recipe | PDF pp.1, 8 | high |
| 改善覆盖两骨干 | DNABERT2 24/26；NTv2-100M-Multi 23/26 | same frozen backbone | PDF pp.1, 8 | high |
| 一小时内形成密集 evidence | 平均 36–57 completed trials/task，166–193 cumulative GPU-min | fixed launch budget | PDF p.6, Fig. 2 | high |

## 复现性与局限

- 代码和数据链接公开；本轮未运行代码，故仍为 `codex_draft`。
- validation-only selection 与 freeze 后三 seeds 是优点；搜索过程本身只有 seed 42，无法估计 Agent/MCTS search variance。
- 缺 classical HPO 和 stateless/pure LLM matched-budget baseline，无法隔离 Agent、MCTS 与扩大并行试验的贡献。
- 预算按 launch window 而非 hard wall clock；drain 后总墙钟未报告。

## 与当前 AgenticNAS 的关系

- 适合作为独立 HPO 轨道的 protocol 模板：架构锁定、attempted/completed trial、GPU time、failure repair、freeze 后多 seed test。
- 下一步应在同一 fixed Conv1d Transformer 上加入 random/TPE/CMA-ES/pure LLM/hybrid，并统一 trial/token/wall caps。

## 链接

- 论文：https://arxiv.org/abs/2608.21916
- 代码：https://github.com/ai4nucleome/GenomeHarness
