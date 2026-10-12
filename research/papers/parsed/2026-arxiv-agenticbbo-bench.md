---
title: "A Closer Look at Agentic BBO: Benchmarking LLM Agents for Black-Box Optimization"
authors: "Ming Chen, Rong-Xi Tan, Ke Xue, Yu-Jie Zhou, Taiye Lu, Zhi-Xuan Gao, Peng Xie, Zijun Shen, Chen Lu, Haopu Shang, Chao Qian"
year: "2026"
venue: "arXiv:2610.12183v1"
paper_url: "https://arxiv.org/abs/2610.12183"
source_pdf: "https://arxiv.org/pdf/2610.12183"
code_url: "https://github.com/lamda-bbo/agentic-bbo"
parser: "Codex"
parsed_on: "2026-10-12"
status: codex_draft
tags: [agentic-bo, benchmark, hpo, fixed-budget, failure-handling, cost]
---

# AgenticBBO-Bench

> 基于 arXiv v1 的 33 页 PDF 与作者仓库核验。它是跨域 Agentic black-box optimization 基准；HPO 只是五个 task families 之一，且包含结构字段，不能直接当作本仓库 fixed-architecture HPO 证据。

## 对象、Agent loop 与公平协议

- benchmark 含 24 BBOB、25 Bayesmark HPO、6 DBTune、12 BBOPlace、10 GuacaMol tasks，共 77 tasks。每个 task/seed 对所有方法共享 initial observations 与 objective-evaluation budget；只有 host 接受并实际评估的 candidate 消耗 budget，LLM inference、Bash/Python、tool calls、surrogate/acquisition 与 validation 不计 objective budget（PDF pp.5–6、20–21）。
- Agentic 使用 persistent Codex workspace，可读 search state、执行代码、调用 optimizer tools、提交 candidate、观察反馈并决定下一动作。invalid submissions 返回同一 round 修订，不消耗 objective evaluation；论文保留 termination status/completed evaluations，并对 incomplete trajectory 用最后 incumbent 填充 scoring checkpoints（pp.5、16–19）。
- HPO family 使用 Bayesmark mixed spaces；frontier HPO task 固定 Optical Digits/MLPClassifier，但八个变量含 `hidden_layer_sizes`，同时还有 alpha、batch size、learning rate、tol、momentum 等。因此该 aggregate 不是严格固定结构 HPO（p.22）。

## 预算、基线与结果

- broad budget：BBOB 20+100、HPO 5+25、DBTune/BBOPlace/GuacaMol 50+200；每 task 两次独立 run。diagnostic 通常四 runs；frontier 每 model/task 一 run（p.20, Table 4）。numerical baselines 包括 GP-BO、TuRBO、CMA-ES、TPE、GIT-BO、Sobol、Random；共享 initialization、search space 与 objective count（pp.20–21）。
- default DeepSeek V4.1 Flash+Codex Agentic 相对 Direct 在五类 task family 均更高；HPO normalized score 0.554 vs Direct 0.519，GP-BO 0.432，TPE 0.344。跨域 Agentic 在四类超过最佳 numerical baseline，DBTune 由 TuRBO 领先（p.7, Table 2a）。这是 family-average benchmark score，不是某个固定 backbone 的 HPO 最优值。
- 增加 GP tools 的 mean score 反而从 base Agentic 0.589 降为 +GPSuggest 0.574、+GPTools 0.538；semantics mean 0.465→0.595，full prior 为 0.569。Agent→TuRBO handoff 0.570 与持续 Agentic 0.569 接近，说明 agent warm-start 可以与经典 optimizer 分工（pp.7–9）。
- frontier challenge 比较 7 个模型、5 tasks、每组合仅一 run；作者报告 GPT-6 Astra mean 0.591、DeepSeek V4.1 Flash 0.584。Figure 1 只以官方 list price 展示每 task token cost 的对数尺度；正文没有给每模型 exact calls/input-output tokens/费用表，也未报告 wall-time、GPU cost 或 energy（pp.2、9）。

## 失败、重复与复现边界

- candidate validation/revision 与 incomplete-trajectory scoring 是重要 failure semantics；但论文未在主结果中给每方法 invalid attempts、retries、duplicates、early termination 的完整表。objective-budget 相同不等于总 LLM/tool/wall-time compute 相同。
- HPO 中包含 architecture-like field，五类 family 又跨数据库、芯片和分子设计，不能把 overall Agentic 优势转写为 fixed-architecture HPO 结论。当前项目若采用，应锁定 model structure，并同时匹配 attempted trials、accepted evaluations、tokens、wall-time 与 failed-trial ledger。
- 作者仓库本轮 `HEAD=6a08b735cc4e9514ddbcea5c9a1f5f7864b7370b`，含 1,280 个 tree entries、agentic harness、traditional/model-based baselines 与 task configs；本轮未运行实验。

## 当前价值

- 最可迁移的是统一 host evaluation budget、invalid 不吞 evaluation、best-so-far trajectory score、Agent→classical handoff 与 persistent workspace audit。
- 它没有 NAS search、真机 latency/peak memory/energy 或 Conv1d evidence；对本仓库只作为 Agentic BO/HPO protocol 邻接证据。

## 链接

- 论文：https://arxiv.org/abs/2610.12183
- 代码：https://github.com/lamda-bbo/agentic-bbo
