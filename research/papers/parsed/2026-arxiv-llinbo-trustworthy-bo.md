---
title: "LLINBO: Trustworthy LLM-in-the-Loop Bayesian Optimization"
authors: "Chih-Yu Chang, Milad Azvar, Chinedum Okwudire, Raed Al Kontar"
year: "2026"
venue: "arXiv:2505.14756v3"
paper_url: "https://arxiv.org/abs/2505.14756"
source_pdf: "https://arxiv.org/pdf/2505.14756"
parser: "Codex"
parsed_on: "2026-11-11"
status: codex_draft
tags: [agentic-bo, llm, gaussian-process, reliability, physical-experiment]
---

# LLINBO

> 本笔记基于 arXiv v3 官方 PDF；论文数字均为作者报告，不是本仓库实测。该工作优化通用黑箱，不是 NAS，也不能直接作为固定架构 HPO 证据。

## 一句话结论

- LLINBO 用 GP posterior 对 LLM 候选做接受、拒绝或退回 classical BO 的控制，三种机制在理论上保留 GP-UCB 的次线性 cumulative-regret 量级；主要实验显示混合方法比 standalone LLM optimizer 稳定。（PDF pp.3–8, Theorem 1, Figures 2–4）
- v3 增加真实 3D 打印 proof-of-concept：每种方法仅一条 10-evaluation trajectory，LLINBO-Transient 最终 stringing 最低；单轨迹不能证明总体优越。（PDF pp.8–9, Figure 5）

## 搜索对象、变量与闭环

- 搜索对象是连续黑箱变量。BBO 使用 2–6D 函数；HPT 调 RF、SVR、XGBoost 的训练超参；3D 打印调 nozzle temperature、Z-hop、retraction、wipe 与 coasting volume。神经架构不是搜索对象。（PDF pp.6, 8, Appendices D–E）
- 每轮同时得到 GP-UCB candidate 与 LLM candidate。Transient 依 schedule 决定是否查询 LLM；Justify 让 LLM 给理由后由 GP 条件模型判断；Constrained 把 LLM 建议纳入 constrained acquisition。观察历史是反馈，GP posterior 是显式统计记忆。（PDF pp.3–5）
- 没有 invalid/OOM/duplicate ledger；拒绝 LLM candidate 是算法动作而非执行失败。停止由总 evaluation budget 控制。

## 评估、预算与成本

- BBO budget 为 `T=10D`，HPT 为 `T=5D`，主图各 10 个独立重复；主实验用 GPT-3.5-Turbo，附录另用 GPT-5 mini，并加入 LLM-initialized BO 等对照。（PDF pp.6–8, 19）
- Rastrigin-2D / Robot-RF 的作者报告平均 wall time：BO 12/49 s，LLAMBO 907/3628 s，LLINBO-Transient 93/278 s；硬件是 5 个 dual-Xeon、512 GB RAM 节点。（PDF p.8, Table 1）
- 3D 打印每法 budget 10，LLM 方法用 2 个 warm-start designs；每次打印数小时。作者明确说明每法只有一条 trajectory，不做统计复现。（PDF pp.8–9）
- tokens、API 费用、单轮 LLM calls/retries 与能源未报告；wall time 也未把不同服务端 LLM 计费口径统一为 matched cost。

## 公平性与局限

- 数值实验 matched objective-evaluation budget，但 LLM calls 与 CPU/LLM wall time 不匹配。LLAMBO 每轮 20 candidates×20 surrogate queries，和 LLINBO 的调用结构不同。（PDF p.8）
- 主实验的 LLM 方法使用 LLM warm start，而 BO 随机初始化；附录的 LLMiBO 对照缓解但没有消除所有模型/调用成本差异。
- 真实打印单轨迹、单打印机，无 seed variance；不能把 Figure 5 写成等预算统计胜出。
- 代码仓库 `UMDataScienceLab/LLM-in-the-Loop-BO` 于 2026-11-11 核验 HEAD `6fb48b200a422244b6e29f3b389adb2b10465f2d`；本轮未运行。

## 对本仓库的价值

- 归类：`Agentic BO 邻接`。可复用的是“LLM proposal 必须通过 uncertainty-aware gate，且随预算衰减到 classical optimizer”的 no-harm 思路。
- 在 typed Conv1d 中应把 Agent candidate 与 evolution candidate 交给同一真实 evaluator，并匹配 attempted candidates、LLM calls/tokens、GPU 与 wall time；不能把通用 BO regret 保证直接迁移为 NAS 收敛保证。
- 最小实验：random/native evolution、stateless LLM、无 gate 与 uncertainty-gated LLM 四组，固定真实训练和设备预算，报告 reject、invalid、duplicate、hypervolume 与 seed variance。

## 检索与人工核验记录

- 官方 PDF：31 页，SHA-256 `411c36833770dd28c73af16182ccaad8edccbb8cecfba08e54e3594790fb80d8`；所有页可解析。
- v3 submitted 2026-10-29、OAI datestamp 2026-11-02；主要表图与物理实验已核对。
- [x] 搜索对象与预算边界已核对
- [x] 真实实验的单轨迹限制已标记
- [x] 作者结果与仓库实测已区分
- [ ] 人工决定 `retained` / `discarded`
