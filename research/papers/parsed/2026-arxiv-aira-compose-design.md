---
title: "Agentic Discovery of Neural Architectures: AIRA-Compose and AIRA-Design"
authors: "Alberto Pepe, Chien-Yu Lin, Despoina Magka, Bilge Acun, Thomas Simon Foster, Yannan Nellie Wu, Anton Protopopov, Carole-Jean Wu, Yoram Bachrach"
year: "2026"
venue: "arXiv:2605.15871v2"
paper_url: "https://arxiv.org/abs/2605.15871"
source_pdf: "https://arxiv.org/pdf/2605.15871"
parser: "Codex"
parsed_on: "2026-10-09"
status: codex_draft
tags: [llm-nas, foundation-model, transformer, mamba, mixed-search-space, scaling]
---

# AIRA-Compose and AIRA-Design

> 本笔记核验 2026-10-07 更新的 arXiv v2（55 页）。AIRA-Compose 是结构搜索；AIRA-Design 同时写 attention module 与 training script，单列为 mixed/MLE-adjacent。作者结果不是本仓库实测。

## 搜索对象与分类

- AIRA-Compose 把 16 层 proxy 表示为 Attention/MLP 两原语（`2^16=65,536`）或 Attention/MLP/Mamba 三原语（`3^16≈43M`）序列；小模型训练后按 validation/test 指标排序，再聚类/聚合并放大到 350M、1B、3B。结构可变，训练协议固定，因此主线归 LLM-NAS（PDF pp.5–12）。
- AIRA-Design 在 LRA 中生成 novel attention code，在 Autoresearch 中直接改 GPT training script，结构、优化器与训练流程可能一起变化；这些结果不能作为固定架构 HPO 或 fixed-recipe NAS 证据（pp.6–8、13–17）。
- 搜索用 one-shot/greedy agent feedback；20 one-shot seeds、10 greedy seeds，每 run 最多 24h/500 steps，BabiStories/DCLM 为 60h；每个 agent 一张 H200。小规模每 seed 约探索 100–200 个 AIRA-Compose 架构（p.8）。

## 预算与核心证据

- 两原语搜索共 2,307 unique architectures（空间 3.17%）；三原语 2,248 unique（0.0052%）。总体报告 11 agents、340 个 24h 与 300 个 60h runs（pp.9、11、18）。attempted/invalid/duplicate 的逐候选总账本、LLM calls/tokens/USD 未报告。
- 两原语 1B 比较固定 37.5B tokens、3 training seeds：AIRAformer-D Stretched validation loss 2.734、average 0-shot 59.7%、DCLM Core 48.9；Llama 3.2 为 2.815/57.5/46.9（p.10, Table 2）。
- 三原语 1B 表只报 single seed；AIRAhybrid-D Stretched loss 2.719、average 0-shot 60.5%，但 Composer 的 DCLM Core 49.3 高于该模型 48.5（p.11, Table 3）。不能概括为所有指标全面胜出。
- 另做 350M/1B/3B ×5 FLOP budgets；latency 是 H100-profiled block latency 按层数加和，不是完整部署测量。未报告 energy、peak memory 或端到端 search GPU-hours（pp.10–12）。

## 公平性、泄漏与局限

- LRA 搜索只见 train/validation，最终 held-out test 在提交后训练评估；Autoresearch 本身优化 validation BPB。AIRA-Compose 文中存在按 test accuracy 聚合小模型的表述，可能把最终集合选择与 test 口径混在一起，复现前需要检查代码/manifest。
- agent 模型、scaffold、seed 数与搜索时长并非所有比较都一致；large-scale 三原语结果只有单 seed，foundation-model baselines 还包含 approximate Nemotron variants。
- 论文没有给可核验的统一源码仓库 URL；引用的 AIRA-dojo/AIRS-Bench 依赖与 14 个 reference repositories 需要单独锁定 commit，当前记为复现缺口。

## 对当前 AgenticNAS 的价值

- 16 层 primitive sequence 超出本仓库 4–10 层范围，但说明 typed layer sequence 可以把 Agent proposal 与确定性 decoder 分离；应缩减为 Conv1d/attention/block/op schema，并保留 canonical hash 去重。
- fixed-token、isoFLOP 与 profiled-latency 三种口径不可混用；本仓库应另外报告真实设备 latency、peak memory、energy、search GPU-hours 与 LLM 成本。

## 链接

- 论文：https://arxiv.org/abs/2605.15871
