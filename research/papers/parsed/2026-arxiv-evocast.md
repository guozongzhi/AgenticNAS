---
title: "EvoCast: Reliable Autonomous Research Agents for Iterative Forecasting Architecture Evolution"
authors: "Kaipeng Xu, Xianli Yan, Yan Wang, Xiang Liu, Shan Liu"
year: "2026"
venue: "arXiv:2610.04517v1"
paper_url: "https://arxiv.org/abs/2610.04517"
source_pdf: "https://arxiv.org/pdf/2610.04517"
code_url: "https://github.com/18e0-x/EvoCast"
parser: "Codex"
parsed_on: "2026-10-09"
status: codex_draft
tags: [llm-nas, time-series, architecture-evolution, research-agent, memory, failure-ledger]
---

# EvoCast

> 基于 arXiv v1 的 26 页 PDF 与作者代码仓库核验。所有结果均为作者报告，不是本仓库实测。

## 一句话结论

- EvoCast 在固定数据、runner、metric、训练预算和 promotion gate 下，让 LLM 对已有 forecasting repository 做开放式模型源码修改；accepted/rejected/unstable/failed 四类结果写入跨轮 evidence/failure memory，属于真实 LLM-guided architecture evolution，而不是固定架构 HPO。
- 最有价值的是 cognition-authority separation：LLM 负责假设和代码，确定性程序负责边界、canonical evaluation、多 seed promotion 与状态写回；但结构空间不 typed，训练配置仍允许由 agent workflow 保留，不能直接当作本仓库固定配方 Conv1d NAS 的等预算证据。

## 搜索对象、固定项与闭环

- 每轮只选择一个 research direction，从当前 incumbent 的 live source path 生成 bounded architecture change；允许新模块、跨模块信息流和 main-path 重组。数据 split、lookback/horizon、metric、runner、training budget、research-round budget 与 promotion logic 固定（PDF pp.3–6、13–18）。
- 状态包含 incumbent、task/diagnosis/prior-round evidence、accepted 与 valid-negative 结果、unstable gains、repair trace 和 failure memory。accepted 更新模型；valid rejection 写科学负证据；unstable 只作弱线索；engineering failure 只约束实现路径（pp.4–6、18–20）。
- 正式 stage 最多 20 rounds，每轮最多 3 次 repair；source boundary/protocol violation 不进入科学比较。停止条件是 round budget 耗尽（pp.19–20）。

## 预算、失败与核心结果

- RQ1：30 个预定义 architecture-edit tasks，统一 MiniMax-M3、temperature 0.1、相同 repository snapshot 和 build/smoke pipeline；EvoCast success 96.7%，高于 mini-SWE-agent 90.0%、AutoResearch 86.7%、AIDE 83.3%（pp.19–21）。这是实现可靠性，不是模型质量。
- RQ2：Air Quality、Melbourne Pedestrian T33、Steel Industry 三任务采用 7:1:2 chronological split，batch 32、最多 10 epochs、patience 3；最终 artifact 用 fixed seed 2027 正式比较，并保留 2026/2027/2028 三 seed promotion references（pp.21–25）。
- 完整 agent-side ledger 报 LLM calls、input/output tokens、API USD 与 active seconds；MiniMax-M3 价格为 uncached input 0.30、cache-hit 0.06、output 1.20 USD/M tokens。论文没有报告训练 GPU-hours、energy、真实设备 latency 或全局 duplicate/OOM 统计（pp.19、22–25）。
- 公开仓库本轮 `HEAD=a47d628b2017dd3c60cc8ed0c8479521285bf4f9`；代码可访问，但本轮未执行作者实验。

## 公平性、局限与当前价值

- 形式 stage 的 20-round cap 相同，但不同 workflow 有不同 pre-formal stage，论文也明确指出 end-to-end resource 不等价；最终模型超越基线不能解释为严格相同总计算预算下的 proposer 优势。
- 搜索空间是开放式 repository code，无法直接计算 action validity/duplication，且不是 4–10 层 Conv1d Transformer；迁移时应把动作收敛为 typed depth/width/block/op/connectivity，固定 recipe，并比较 native evolution、stateless LLM 与 memory-aware LLM 的 attempted/valid/trained/GPU/token/wall-time 预算。
- evidence taxonomy 和 deterministic promotion gate 可直接用于 memory-aware policy：失败不伪装成负科学结果，unstable improvement 不更新 incumbent，test 不进入搜索反馈。

## 链接

- 论文：https://arxiv.org/abs/2610.04517
- 代码：https://github.com/18e0-x/EvoCast
