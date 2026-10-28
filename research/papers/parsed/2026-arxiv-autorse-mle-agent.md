---
title: "AutoRSE: Evaluating LLM Agents as Recommendation Engineers for Self-Evolving Recommender Systems"
authors: "Rui Tian, Yi Fang, Yejin Hua, Du Wang, Yuzhe Wang, Minxuan Shan, Zirui Ren, Xinyu Lin, Chongming Gao, Wenjie Wang, Fuli Feng"
year: "2026"
venue: "arXiv:2610.37228v1"
paper_url: "https://arxiv.org/abs/2610.37228"
source_pdf: "https://arxiv.org/pdf/2610.37228"
code_url: "https://github.com/Ray-Tiann/AutoRSE"
parser: "Codex"
parsed_on: "2026-10-28"
status: codex_draft
tags: [mle-agent, automl-agent, hpo, recommender, trajectory, benchmark]
---

# AutoRSE

> 本笔记基于 arXiv v1 官方 PDF。Agent 可改代码、模型、训练流程与 ensemble，归 `MLE/AutoML Agent` 邻接基准，不是固定架构 HPO。

## 任务、闭环与预算

- 六个 recommendation tasks 各提供完整 baseline code、train/validation data 和隐藏 test labels。Agent 循环执行 Explore→Ideate→Implement→Experiment→Analyze，可按 stdout、error traces 和 validation metrics 保留、修订或放弃代码修改；联网和外部检索被禁止。（PDF pp.2–3, Fig.2, Table 1）
- 评测 3 个 frontier LLM、3 个 harness 的 7 个可用组合；每 task×agent 做 3 次独立运行，每次固定 1×H200、16 vCPU、32GB RAM、12h。按协议共 126 runs，即 1,512 H200-hours 的固定时限分配；论文未报告实际 utilization、energy、peak memory、LLM calls/tokens/API 费用。（PDF pp.3–5）
- 完整 trajectories 被切成 4,425 个 training/evaluation experiments；分析时会过滤 file reads 和 failed tool calls，因此没有可复用的 attempted/invalid/failure/retry 完整账本。（PDF pp.3, 5–6）

## 结果与准确分类

- 作者把动作分为 parameter tuning、ensemble、training strategy、feature modeling、architecture 和 objective。91.7% segmented experiments 属工程优化，其中 ensemble 59.0%、parameter tuning 26.2%、training strategy 6.6%；architecture 仅 3.1%。（PDF pp.4–6, Fig.4）
- 七个 Agent 在六任务上的作者报告平均相对提升为 16.1%，但 IntSR 多数组合低于 baseline，且同一组合三次运行方差明显。（PDF pp.5–6, Table 2, Fig.3）
- HSTU case 中固定 architecture 的 cosine schedule/warmup 从 0.06770 提升到 0.06997；加入 content projection 的结构/表示变更到 0.07216。该 case 可展示 HPO 上限，但全 benchmark 并未锁定 architecture/data/code，因此不能转为 fixed-HPO 总体结论。（PDF p.6）
- idea-injected 使用顶会论文、竞赛方案和专家 ideas；平均比 standard/self-generated 高 14.23%/13.35%，但这是外部知识条件变化，并存在 benchmark familiarity/idea leakage 风险。（PDF pp.7–8, Table 3）

## 对本仓库的价值

- 可复用：固定 wall-clock 与单 GPU、隐藏 test、完整 trajectory、best-so-far 曲线、跨 seeds 方差、按实际动作分类。
- 必须修正：保留 failed tool/training attempts，而不是分析前过滤；拆出 architecture-only 与 recipe-only action contract；同时匹配 attempted、GPU、LLM token 和 wall-time。
- 官方代码本轮可访问，`HEAD=80d6164614277eccf2fbcf3c291efb13ae9e068f`；未运行。

## 检索与人工核验记录

- 官方 PDF：12 页，SHA-256 `53d2000b03080d990e9ca2764e57d31aa770646fefcaa3fc1e9e553f800a1f01`。
- [x] 任务、硬件、重复数、trajectory 分布和主要表图已核对
- [x] MLE Agent 与 fixed-HPO 边界已区分
- [ ] 人工决定 `retained` / `discarded`
