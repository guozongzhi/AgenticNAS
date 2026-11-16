---
title: "NeoResearch: Literature- and Experience-Guided Autonomous Time Series Model Discovery"
authors: "Ze Guo, Mingyue Cheng, Xiaoyu Tao, Shuo Yu, Shangtong Ye"
year: "2026"
venue: "arXiv:2611.18235v1"
paper_url: "https://arxiv.org/abs/2611.18235"
source_pdf: "https://arxiv.org/pdf/2611.18235"
code_url: "https://github.com/Kawai1Angel/NeoResearch"
parser: "Codex"
parsed_on: "2026-11-16"
status: codex_draft
tags: [mle-agent, automl-agent, mixed-search-space, time-series, memory, reflection]
---

# NeoResearch

> 本笔记基于 arXiv v1 官方 PDF。系统会改预处理、模型代码与训练配方，属于 `MLE Agent / mixed-search-space`，不能当作固定架构 HPO 证据。

## 搜索对象与闭环

- 外层 research loop 从文献与历史经验提出方向，并生成新的模块组合；内层 optimization loop 固定一个设计后继续改变 loss、optimizer、learning rate、batch size、regularization 与 schedule。数据集和统一评测协议固定，但 architecture、recipe、代码与部分数据处理都可变。（PDF pp.2–5）
- planner、experimenter、reviewer 构成 proposal–execution–feedback loop；memory 保存成功、失败和 inconclusive 经验，重复设计会被拒绝。默认 DeepSeek-V4.1Flash、temperature 0.2、每次调用最多 32k tokens，失败最多重试 3 次。（PDF pp.3–5）
- 每个任务最多 25 个 research iterations；单 RTX 4090、模型不超过 10M 参数。连续 7 次无提升、达到目标、planner 主动停止或连续 3 次重复均可终止。（PDF pp.5–6）

## 预算与结果

- Optuna-TPE 与 AIDE 也给 25 次预算；作者在 10 个数据集、两个指标上报告 19/20 个比较最好，Windy 是例外。消融显示 dual-loop 与 experience memory 均有贡献，但表格只报告最终指标，没有逐次 proposal ledger。（PDF pp.6–8, Tables 1–3）
- 每个目标任务的 memory 由其余 9 个数据集的 cold-start research 构建；这不是目标测试集直接泄漏，但给 Agent 提供了跨任务先验，和从零开始的基线存在资源边界差异。
- attempted/valid/trained/evaluated 数、失败/OOM/duplicate/retry 总数、GPU-hours、wall-time、LLM calls/tokens/费用均未报告；25 iterations 不能直接等同于 25 次成功训练。

## 复现与课题价值

- 作者仓库在 2026-11-16 可访问，核验 HEAD 为 `d3354cb65fe871eb23cb44bd1d6463794775025a`；本轮仅静态核对，未运行实验。
- 对本课题最有价值的是“跨任务经验库 + 失败记忆 + 双层停止条件”；最小复现应冻结 typed Conv1d architecture-only 或 fixed-backbone recipe-only 其中一轨，并匹配 attempted trials、GPU-hours、tokens 与墙钟。
- 官方 PDF：13 页，SHA-256 `7986d925aa2eac76a937087a804b0c7fdad519d3cf8aac8e17efa9b36cb9f2d5`。

- [x] 搜索变量与固定变量已区分
- [x] memory、停止与重复控制已核对
- [ ] 人工决定 `retained` / `discarded`
