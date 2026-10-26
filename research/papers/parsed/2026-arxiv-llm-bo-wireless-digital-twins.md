---
title: "Large Language Models Meet Bayesian Optimization: Towards Self-evolving Wireless Digital Twins"
authors: "Yingzhuo Sun, Haoyun Li, Ming Xiao, Francisco J. Ferrao, Berna Ozbek"
year: "2026"
venue: "arXiv:2610.31192v1"
paper_url: "https://arxiv.org/abs/2610.31192"
source_pdf: "https://arxiv.org/pdf/2610.31192"
parser: "Codex"
parsed_on: "2026-10-27"
status: codex_draft
tags: [agentic-bo, llm, kernel-discovery, evolutionary-search, feedback, wireless]
---

# Large Language Models Meet Bayesian Optimization

> 本笔记基于 arXiv v1 官方 PDF。论文搜索 BO 组件而不是神经架构或固定架构训练 recipe，归 `Agentic BO 邻接`。

## 一句话结论

- 论文提出 BO 快循环 + LLM 慢循环：BO 持续更新 surrogate 和候选解，LLM 仅在需要时改变 initialization、GP kernel 或 acquisition function；proof-of-concept 把可变项锁定为 GP kernel program。（PDF pp. 3–5, Figs. 2–3）
- 两岛 archive 保存 kernel code、design idea 和 BO performance，LLM 通过 local modification、cross-island combination 或 global exploration 生成 kernel，真实 BO 表现回写 archive；但论文未披露 kernel proposal 数、LLM model/calls/tokens/费用或失败分母。（PDF pp. 4–6）

## 搜索对象与闭环

- 下游任务是在 Sionna urban scenario 中为 10 users 从 64 beams 选择配置；每个配置映射为 20-D 输入，目标为 sum spectral efficiency。（PDF p. 5）
- 固定：10 random initial observations、40 BO iterations、GP fitting、expected improvement acquisition、candidate set。可变：GP covariance kernel program；因此不是 NAS，也不是 training HPO。（PDF p. 5）
- Memory/archive：两 islands 保存 code、idea、observed performance；prompt 可检索历史 task–algorithm–performance records。（PDF pp. 3–5）
- Proposal/feedback：LLM 在受限 kernel API 中输出 executable `build_kernel`；BO engine 评价后把 performance 写回 population。生成 kernel 在评价前会检查，但 interface/numerical/invalid/retry 的数量未报告。（PDF pp. 4–6）

## 实验与预算

- 50 个 wireless tasks：30 用于 kernel discovery/training comparison，20 held-out test；每个 task 10 initial + 40 BO evaluations，所有 kernels 使用相同 initialization/acquisition/evaluation budget。（PDF p. 5）
- 对照为 Matérn-1/2、Matérn-3/2、Matérn-5/2、RBF。LLM-discovered kernel 的 normalized final objective 为 training 0.7046、test 0.6482；最强标准 kernel 为 0.5885/0.5962，对应作者报告 +19.7%/+8.7%。（PDF pp. 5–6, Fig. 5, Table I）
- 未报告：LLM 型号与 sampling settings、候选 kernel attempted/valid/evaluated 数、island population/停止条件、tokens/USD、GPU-hours、wall-time、peak memory、energy、duplicate/compile/numerical failure ledger。
- 论文没有公开代码链接；本轮未运行框架。

## 可信度与边界

- 优点：only-kernel ablation 把 initialization、EI 和 task budget 固定，能把性能差异定位到 kernel；held-out 20 tasks 避免只报告 discovery tasks。（PDF pp. 5–6）
- 风险：30/20 tasks 来自同一 system model/distribution，尚不能证明对 channel、traffic、scale 或 objective 变化的适应；正文也把这些列为 future work。（PDF p. 6）
- 最大公平性缺口是 discovery budget 不透明：标准 kernels 不承担 LLM/island search 成本，无法判断 +8.7% test gain 是否在 matched end-to-end budget 下成立。

## 对本仓库的价值

- 可复用：将 Agent 动作限制为 typed component API；保存 code/idea/performance 三元组；把快 evaluator loop 与慢 proposal-policy adaptation 分层。
- 不可转移：kernel program search 不是 Conv1d architecture search，也不能作为 fixed-architecture HPO 证据。
- 最小实验：在固定 Conv1d architecture space 的 surrogate/acquisition 层做同样 two-timescale 控制，只允许改变 acquisition component；与固定 EI、random acquisition 和无 archive LLM 在相同 calls/tokens/wall-time 下比较 invalid rate、regret 与 time-to-target。

## 检索与人工核验记录

- 官方 PDF：7 页，SHA-256 `2873aeb8488a76ae595e5cbb474c9dd5af5ce366a06ef9504397eb6d56863796`。
- 重点核对：PDF pp. 3–6，Figures 2–5、Table I。
- [x] 标题、作者、版本已核对
- [x] 核心结果已对照表图
- [x] 未报告预算已明确标注
- [x] 未把 Agentic BO 写成 NAS/HPO
- [ ] 人工决定 `retained` / `discarded`
