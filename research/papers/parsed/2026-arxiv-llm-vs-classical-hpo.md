---
title: "Can LLMs Beat Classical Hyperparameter Optimization Algorithms? A Study on autoresearch"
authors: "Fabio Ferreira, Lucca Wobbe, Arjun Krishnakumar, Frank Hutter, Arber Zela"
year: "2026"
venue: "arXiv:2603.24647v5"
paper_url: "https://arxiv.org/abs/2603.24647"
source_pdf: "../pdfs/2603.24647-llm-vs-classical-hpo.pdf"
parser: "Codex"
parsed_on: "2026-07-29"
status: codex_draft
tags: [hpo, benchmark, hybrid, mixed-search-space, transformer]
---

# Can LLMs Beat Classical Hyperparameter Optimization Algorithms?

> 本笔记由 Codex 基于 arXiv v5 PDF 的页码证据生成。该论文的固定空间含结构变量，按本仓库分类只能作为相邻方法证据。

## 一句话结论

论文在 nanochat 小型 LM 上以 24 小时、3 seeds 比较 9 种方法：经典 TPE/CMA-ES/SMAC 在固定 14-HP 空间中优于纯 LLM，CMA-ES 与 LLM 共享状态的 Centaur 最强；但搜索空间包含 `DEPTH`、`HEAD_DIM` 和 attention window，不能作为本仓库“固定架构训练 HPO”的直接实验。（PDF pp.1, 3–8）

## 研究问题与贡献

- 在同一训练 testbed 下比较经典 HPO、固定空间 LLM、自由代码编辑 LLM 和 hybrid。
- 用 AST 自动提取 14 个全大写配置项，并手工设置范围。
- 提出 Centaur：CMA-ES 保留全量更新，约 30% trials 让 LLM看到均值、步长、协方差、top-5 和最近 20 个 trials 后覆盖提议。（PDF pp.3–5）

## 方法拆解

### 搜索或优化对象

- 目标是约 50M 参数 nanochat decoder-only Transformer 的 validation bits-per-byte。
- 14 个字段同时包含结构变量（depth、aspect ratio、head dim、window pattern）与训练变量（batch、多个 learning rates、weight decay、warmup/warmpdown）。
- Code-editing Agent 可直接修改 `train.py`，超出固定结构化空间。（PDF pp.1, 4–5）

### Agent 与优化闭环

- 固定空间 LLM 接收目标、数据、硬件/OOM 警告、搜索边界和成功/失败历史。
- Centaur 在 30% turns 提供 CMA-ES 内部状态；所有结果都回写 CMA-ES。
- OOM trial 记为 `val_bpb=100.0`，让代理模型学习避开不可行区域。（PDF pp.3–5）

### 评估与预算

- 每个 trial 在单张 H200 上训练 5 分钟；每个方法 24 小时、3 seeds。
- 训练 VRAM 统一限制为 80GB；Qwen3.5-0.8B/27B 自托管，另测 Gemini/Claude。
- LLM inference overhead 从 24 小时 wall-time 中排除，因此训练预算匹配但总成本并不匹配。
- 共比较 4 classical、4 LLM-based、1 hybrid 方法。（PDF pp.3–5）

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 固定空间经典 HPO 优于纯 LLM | TPE 0.9768±0.0019；最强 fixed-space pure LLM LLAMBO(Paper) 0.9862±0.0041，越低越好 | LLAMBO、Karpathy Agent 14 HPs | pp.5–6, Table 3 | high |
| Centaur 是主实验最佳类别 | Qwen-27B Centaur 0.9763±0.0005；Opus Centaur 0.9739±0.0012 | TPE、CMA-ES、SMAC、pure LLM | pp.6–8, Table 3/Fig. 2 | high |
| 小 LLM 足以做 hybrid | Qwen-0.8B Centaur 0.9766±0.0008 | Qwen-27B Centaur 0.9763±0.0005 | pp.6–8 | high |
| 自由代码编辑需要模型规模 | Qwen 0.8B 0.9910 vs 27B 0.9814；Opus 0.9770，仍略差于 TPE 0.9768 | TPE、CMA-ES | pp.6–7 | high |
| OOM avoidance 比多样性更关键 | TPE OOM 11%，LLAMBO(Paper) 48%，Random 56% | 多样性统计 | pp.5–6, Table 3 | high |

## 公平性与可信度检查

- 24 小时和 3 seeds 的训练预算设计较强，但排除了 LLM inference 时间/费用。
- 快速 OOM 会产生更多 attempted trials；论文同时报告 wall-time 和 trial 数，并惩罚 OOM。
- 只评估一个 LM 训练任务，论文明确要求更多 benchmark 才能判断泛化。
- 固定 14-HP 空间含架构字段，不符合本仓库训练-only HPO 的固定架构要求。
- 自由代码编辑与结构化 HPO 的动作权限、搜索空间和安全风险不同，不应合并成一个方法排名。

## 与本仓库独立课题的关系

- 可用于设计经典/纯 LLM/hybrid 的公平预算与 OOM 记账，不可直接作为训练-only HPO 结果。
- `DEPTH`、`HEAD_DIM`、`WINDOW_PATTERN` 必须在本仓库 HPO 复现实验中固定；若搜索它们，应归入 NAS 或 mixed track。
- Centaur 比简单的前 5 次 LLM warm-start 更紧密地共享优化器状态，值得作为第二阶段 hybrid baseline。
- 自由源码编辑不符合当前声明式 action 与 clean-room 边界。

## 最小复现实验

- 固定 nanochat 架构字段，只保留 batch、learning-rate、weight-decay 和 schedule 变量。
- 同预算比较 random、TPE、CMA-ES、纯 LLM、5+15 LLM→TPE 和 Centaur。
- attempted trials、每 trial time cap、失败惩罚一致；同时报告训练 wall-time 与 LLM inference 成本。

## 局限与风险

- 单任务与新发布模型版本限制外推。
- 论文中的 best method 会随 frontier API 更新变化。
- 混合方法的收益可能依赖 CMA-ES 状态是否容易转成自然语言；TPE/GP 状态未必同样适用。
- 搜索结构字段造成的收益无法与纯训练配方收益分离。

## 可引用摘要

Ferreira 等在 nanochat 上以统一训练 wall-time 和三随机种子比较经典、LLM 与 hybrid HPO。固定 14-HP 空间中经典方法优于纯 LLM，Centaur 通过向 LLM 暴露 CMA-ES 状态取得最好结果；不过该空间混合了架构和训练字段，且排除了 LLM inference 成本，因而只能作为本仓库 HPO 方法设计的相邻证据。

## 检索与人工核验记录

- 解析问题：搜索字段、24h/3-seed 预算、OOM 处理、Centaur 和模型规模。
- 使用片段页码：1, 3–8, 14–20。
- [x] arXiv v5、作者、14 HP、9 methods、24h/3 seeds 与 Table 3 已核对
- [x] mixed structural fields 与 LLM inference exclusion 已定位
- [ ] 官方代码尚未运行，完整复现实验未执行
- [ ] 已由人工决定 `retained` / `discarded`
