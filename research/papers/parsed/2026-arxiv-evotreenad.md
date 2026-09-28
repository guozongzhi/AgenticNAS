---
title: "EvoTreeNAD: Genealogy-Guided Evolution for LLM-Driven Neural Architecture Discovery"
authors: "Lishan Yu, Derek Jiu, Qizhen Lan, Xiaoqian Jiang"
year: "2026"
venue: "arXiv:2609.29016v1"
paper_url: "https://arxiv.org/abs/2609.29016"
source_pdf: "https://arxiv.org/pdf/2609.29016"
parser: "Codex"
parsed_on: "2026-09-28"
status: codex_draft
tags: [llm-nas, neural-architecture-discovery, evolution, genealogy, memory, code-generation]
---

# EvoTreeNAD

> 本笔记基于 arXiv v1 PDF。论文结果均为作者报告，不是本仓库实测；作者声明代码未来发布，核验时没有找到官方实现仓库。

## 一句话结论

- 核心主张：EvoTreeNAD 从空根开始维护持久化架构谱系，用后代的 top-percentile family value 选 lineage；Idea Agent 根据该 lineage 的设计/结果历史提出变体，Code Agent 生成完整可训练模型，真实短训反馈再写回谱系。
- 这是开放式 LLM-driven NAS/NAD：任务接口、数据、split、evaluator 和阶段训练协议固定，内部模块、连接、forward 以及 model-defined loss 可变；它比仓库 typed `MutationAction` 空间更开放，也把 loss 纳入架构规格。
- 证据位置：PDF pp.3–8、21–23、27–28，Algorithm 1、Tables 1–2、6、10。

## 搜索对象、变量与固定项

- 搜索对象是完整可执行神经网络。可变项包括内部模块、连接、forward computation 和模型定义的 loss；没有预设 seed architecture 或手工限定的 architecture search space（PDF pp.3–5）。
- 固定项是 task input/output contract、supervised target、data split、discovery evaluator，以及 discovery/full-fidelity 训练协议。CIFAR-10/100 用 42k/8k discovery train/validation 和官方 10k test；MedMNIST-v2 用官方 split（PDF pp.3、7）。
- 每次从 root 按 family value 路由到尚有 child capacity 的节点；Idea Agent读取所选 lineage 的近期架构与分数，Code Agent据此实现一个完整模型。该谱系同时承担 archive、反馈历史和有限上下文 memory 的作用（PDF pp.3–5、21–22）。
- 这不是 HPO：训练/evaluator 由 task protocol 固定，但允许模型代码和 loss 改变。它也没有显式 Pareto archive；reward 主要由 validation metric 经 sigmoid 映射，并可加很小的 parameter-size 项（PDF pp.4、21–22）。

## Agent 闭环、停止与失败处理

- 主配置用 GPT-4.1 作 Idea Agent、`gpt-oss-20b` 作 Code Agent；后者以 `gpt-oss-20b-mxfp4.gguf` 在两张 V100 本地运行。补充实验还使用 GPT-5（Azure OpenAI）（PDF pp.7、23）。
- 生成代码先过 task-interface smoke test；通过者在固定短预算上训练。较差候选按历史强候选轨迹自适应 early-stop，已有 validation 记录仍用于 discovery reward（PDF pp.5、21–22）。
- 无有效分数会把诊断反馈给 Code Agent；每个 proposal 最多 1–3 次实现尝试。每个 parent 前 4–8 个失败 expansion 可跳过，不加 child；之后的持续失败以固定负 reward 写入谱系。中间 retry 不作为独立 child（PDF p.22, Table 6）。
- 论文报告 reject/early-stop，但未单独报告 duplicate 架构、OOM、divergence 或语义等价率；没有 action-validity schema，因为 Agent 直接生成模型代码。
- 预设 iteration budget 停止。最终沿同一路由规则抽取 principal lineage，取 discovery reward 最高的 3 个架构，固定候选集后再从头完整训练并只在最后使用 test（PDF p.5）。

## 预算、候选数与成本

- 主 discovery 每个任务 3 个独立 run；CIFAR-10/100 最多 300 iterations，MedMNIST-v2 为 80 iterations。策略和 Agent 配置消融用 CIFAR-10、每个方法 3 个独立 100-iteration run（PDF p.7）。
- iteration 是目标谱系扩展预算，不等于 Code-Agent 调用数。以 `GPT-4.1 + OSS20B` 的 100-iteration 配置为例，平均 144.0 次 Code realizations（含 retry），reject 37.5%，early-stop 28.0%，0.37 GPU-days，Idea/Code output tokens 0.30M/1.61M，Idea API 成本 0.84 USD、Code API 成本 0（PDF p.28, Table 10）。
- 同表其他配置平均 115.3–144.0 次 realization、0.27–0.37 GPU-days；GPT-5 作 Code Agent 时总代价约 3.10–3.74 USD。每个 CIFAR-10 candidate 最长短训 10.5 分钟（PDF p.28）。
- 每个 discovery run 使用一张 A100 评价候选；full-fidelity 训练使用 A100 或 V100。论文只给部分 run 的 discovery GPU-days，没有给全部任务总 GPU-hours、总墙钟或能耗（PDF pp.8、23）。
- 每个 run 最终 3 个 full-fidelity candidates；Table 1 的最终 accuracy/error 对每个架构用 4 个训练 seed 报均值和标准差（PDF p.8）。

## 核心结果

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| CIFAR 主结果 | CIFAR-10 error `2.05±0.06%`，CIFAR-100 `15.09±0.22%`；对应 discovery cost 0.63/1.02 GPU-days | 论文汇总的 classical NAS 与 LLM-NAD | PDF p.8, Table 1 | medium |
| 小模型结果 | CIFAR-10 2.25M 参数架构 error `2.38±0.06%` | DARTS/P-DARTS 等发表值 | PDF pp.7–8, Table 1 | medium |
| 路由规则受控比较 | EvoTreeNAD 三个 run 最佳 full-fidelity accuracy 97.39/97.26/97.11，均高于 repeated direct generation、best-of-N greedy、family mean 的各自 run | 相同生成/评价 pipeline、OSS20B、3×100 iterations | PDF pp.7–8, Table 2 | high |
| 跨任务结果 | 六个 MedMNIST-v2 任务均高于表中 strongest listed baseline | 论文引用的公开 baseline | PDF pp.10–11, Tables 3–4 | medium |

## 公平性、复现性与局限

- Table 2 是最可信的 matched-budget 证据：四种策略共享 pipeline、Agent 模型和 100-iteration budget；但没有 random/native evolutionary NAS、stateless LLM 和 memory-aware LLM 四方统一对照。
- Table 1 的外部 NAS/NAD 数字来自各论文，search space、训练 recipe、GPU/LLM budget 和 seed 均不统一；不能据此断言 EvoTreeNAD 在等预算下优于 classical NAS。
- Open-ended code generation让搜索空间很难计数或去重，也允许 model-defined loss；对当前仓库来说必须把结构动作与 recipe/loss 变更分离后再比较。
- 论文屏蔽数据集名称以降低 benchmark-specific prior，但 LLM 预训练污染仍无法排除；没有报告完整 prompt/corpus provenance 或不同 base LLM 下的外推。
- 作者写明“Code will be released on GitHub”；本轮 GitHub 搜索未找到官方仓库，因此 prompts、运行脚本和 trajectories 尚不能独立复核。

## 与当前 AgenticNAS 的关系

- 最直接的可借鉴点是 persistent genealogy：保留 parent-child、proposal、evaluation 和失败结果，用 family-level statistic 决定后续 lineage，可作为 memory-aware policy 的一种 archive 设计。
- 不能直接把其开放式 code generation 接入当前 Conv1d Transformer：应先把动作收敛为 4–10 层范围内的 typed depth/width/block/op/connectivity 变更，固定 loss/recipe，并与 random/native evolution/stateless LLM 在相同 attempted/valid/trained/GPU/LLM budget 下比较。
- 当前论文只优化 quality/size，没有真实 latency、peak memory、energy 或 deployment cost；若迁移，应把真实设备 Pareto 目标和 hypervolume、action validity、duplication、seed variance 同时纳入。

## 链接

- 论文：https://arxiv.org/abs/2609.29016
- 代码：作者声明未来发布；截至 2026-09-28 未找到官方仓库
