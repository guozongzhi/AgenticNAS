---
title: "GraphIR: Architecture-Level Search States for LLM-Guided Neural Architecture Evolution"
authors: "Zhen Liu, Wanqi Zhou, Shuanghao Bai, Yuhan Liu, Jinjun Wang, Jingwen Fu"
year: "2026"
venue: "arXiv:2608.01633v1"
doi: "10.48550/arXiv.2608.01633"
paper_url: "https://arxiv.org/abs/2608.01633"
source_pdf: "https://arxiv.org/pdf/2608.01633"
source: "arXiv v1 metadata/PDF, accessed 2026-08-04"
parser: "Codex"
parsed_on: "2026-08-04"
status: codex_draft
tags: [llm-nas, architecture-ir, code-evolution, action-validity, open-evolve, qwen3-plus]
---

# GraphIR: Architecture-Level Search States for LLM-Guided Neural Architecture Evolution

> 本笔记基于 arXiv v1 的 17 页 PDF。所有结果均为作者报告，尚未独立复现；截至 2026-08-04，论文和 arXiv 页面未提供作者代码链接。

## 一句话结论

GraphIR 不让 LLM 只看可执行网络代码，而是额外提供 computation skeleton、mutation surface 与 validity envelope 三种架构状态；在 OpenEvolve + Qwen3-Plus 的受控表示对照中，它提高 MNIST1D-Shuffle 的 accuracy/OOD accuracy，并显式记录 invalid、shape mismatch 与端到端 GPU-hours，但其跨 CLRS 方法表并非全部 matched-budget 重跑，且没有 LLM calls/tokens/费用或真实 latency/memory Pareto 证据。（pp. 1–6, 12–15）

## 书目信息与来源核验

- arXiv ID：2608.01633v1；提交时间：2026-08-03 03:06:58 UTC；arXiv DOI：10.48550/arXiv.2608.01633。
- 作者：Zhen Liu、Wanqi Zhou、Shuanghao Bai、Yuhan Liu、Jinjun Wang、Jingwen Fu；当前可核验 venue 为 arXiv。
- 论文：https://arxiv.org/abs/2608.01633
- PDF：https://arxiv.org/pdf/2608.01633 ；17 页；本次读取副本 SHA-256：`1be92e4cfa42962901370ef42435a6d6fea32b2d451f6f29583a673e91fef2bb`。
- 代码：正文、arXiv 页面及精确标题检索未找到作者公开仓库；不能把 OpenEvolve/SPARK 的仓库当作 GraphIR 实现。
- 置信度：书目信息 high；方法 high；受控 MNIST1D 结果 medium-high；跨任务比较 medium；独立可复现性 low-medium。

## 研究问题与贡献

- 问题：开放代码级 LLM-NAS 把 tensor dependencies、可编辑组件、接口约束和 shape propagation 隐藏在实现细节中，导致语法正确但架构不兼容或无效的 mutation。（pp. 1–2）
- GraphIR 通过静态分析与 execution tracing 从父网络提取架构状态，源代码仍是执行和编辑对象；GraphIR 只作为 mutation prompt 的补充上下文。（pp. 2–4）
- 三个视图分别描述 tensor flow、可变 modules/operations，以及 I/O contracts、propagated shapes、dimension coupling 和 downstream dependencies。（pp. 1, 3–4）
- 论文另建 NAS-Dependency：从 MNIST1D-Shuffle CNN 演化轨迹构造 120 个依赖推理问题，并在六个下游架构搜索 benchmark 上测试表示是否改善搜索。（pp. 2, 5, 9–13）

## 方法拆解

### 搜索或优化对象

- 搜索对象是真实、可执行的神经网络程序，不是 Agent workflow；OpenEvolve archive 选择已评估父程序，Qwen3-Plus 生成子程序，validator/evaluator 再更新 archive。（pp. 2–4）
- mutation 可改变 modules、branches、tensor operations、normalization、residual paths、gating、pooling 与 output heads；搜索空间是开放程序空间，而非预定义 cell grammar。（pp. 1–3）
- 下游覆盖 CLRS、MNIST1D-Shuffle、20 Newsgroups、CartPole-v1、Yeast 和 Breast Cancer Wisconsin Diagnostic；MNIST1D 还分 CNN、MLP、GRU、linear 四类。（pp. 2, 12–13）
- 训练/evaluator 在受控对照中固定，变化是架构程序和提示中的状态表示，因此主实验属于 `LLM × NAS`；它不是固定架构 HPO。

### Agent 与优化闭环

- 每轮从 archive 选父程序 `P`，把源代码、GraphIR 状态 `z` 与历史反馈 `H` 放入 mutation prompt，LLM 产生子程序；子程序经验证、评估和 archive update 后重新抽取 GraphIR。（pp. 2–4）
- computation skeleton 记录从输入到输出的 executed tensor flow；mutation surface 暴露 modules、tensor ops 和可改字段；validity envelope 记录 shapes、I/O contracts、coupling 与 downstream consumers。（pp. 3–4）
- 架构级状态来自 static analysis + runtime tracing；它不替代本地 validator，也不保证每个 LLM edit 合法，论文仍单独统计 invalid 与 shape mismatch。（pp. 3–5）
- 全部架构演化使用 OpenEvolve 和 Qwen3-Plus；NAS-Dependency 的模型设置为 `qwen-plus` alias、temperature 0、最大 1,536 output tokens、120 秒 timeout、API failure 最多两次 retry。（pp. 5, 12）

### 评估与预算

- MNIST1D-Shuffle 的 representation matched-budget 对照固定 OpenEvolve、Qwen3-Plus、prompt、evaluator 与 100 evolution iterations，只替换 CodeRAG-style、CPG-style、GraphCode-style 或 GraphIR context。（p. 6）
- 该对照中三种 generic representation 各 3 seeds，GraphIR 10 seeds；GraphIR 信息消融为 3 seeds。四类 backbone 的 robustness 使用 CNN 10 seeds，其余各 6 seeds。（pp. 5–6）
- GPU-hours 是 candidate generation、program analysis、validation 和 evaluation 的端到端时间，运行在单张 NVIDIA RTX 3090；论文未给完整 LLM calls、input/output tokens、API 费用或 wall-time cap 对账。（p. 5）
- NAS-Dependency 共 `120 × 5 = 600` predictions，论文只报告 76 个 held-out questions；使用 deterministic JSON parser/scorer，不用 LLM judge。（p. 12）
- CLRS 30-task 表中 EvoPrompting 与 Triplet-GMPNN 数字来自原论文；OpenEvolve、SPARK 与 GraphIR 只在 CLRS-DFS 下按 SPARK 设置评估，不能把整张表解释为所有方法同候选/GPU/LLM 预算。（pp. 5, 14–15）
- 没有目标设备 latency、peak memory、energy 或 LLM cost objective；model size 与 GPU-hours 不能替代多目标 Pareto 测量。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 受控 representation 对照 | GraphIR 71.55±2.14 accuracy、68.68±2.53 OOD；CPG-style 70.10±3.47 / 67.95±3.12 | 同 OpenEvolve/Qwen3-Plus/100 iterations，仅表示不同 | p. 6, Table 6 | high |
| 失效与成本账 | GraphIR 19.80 invalid、6.80 shape errors、1.639±0.089 GPU-h | CodeRAG/CPG/GraphCode-style | pp. 5–6, Table 6 | high |
| GraphIR 内容消融 | full 73.53±0.83；无 edge relations 71.53±0.40；无 node facts 67.13±3.20 | 3 seeds | p. 6, Table 5 | high |
| 四类 backbone robustness | CNN/MLP/GRU/linear accuracy 为 71.55/70.42/66.18/56.38，均报告 seed 方差 | 独立 evolution runs | p. 5, Table 3 | medium-high |
| CLRS aggregate | GraphIR 89.21 average、22/30 wins；SPARK 83.91、5/30 wins | 非全部 matched-budget 的跨论文/重跑混合表 | pp. 5, 14–15, Tables 2/17 | medium |
| 跨任务相对效率 | GraphIR mean relative performance 100、relative NAS GPU-hours 1.379 | EOH/FunSearch/OpenEvolve/EvoPrompting | p. 13, Table 15 | medium |

## 公平性与可信度检查

- 最可信结论是 MNIST1D 的表示替换对照：固定搜索 backbone、LLM、prompt、evaluator 和 100 iterations，只改变提供给 LLM 的 representation。
- generic representations 是作者“adapted to NAS”的 `-style` 实现，而非原系统完整复现；该对照支持 GraphIR 相对这些适配实现的收益，不能自动外推到所有 code graph 方法。（p. 5）
- GraphIR 用 10 seeds，而三种表示 baseline 只用 3 seeds；均有方差，但 seed 数不相等。单独列出的 OpenEvolve 只有 1 run。（p. 6）
- CLRS aggregate 混用原论文数值和本论文重跑，候选/训练/GPU/LLM 预算并未统一；跨任务 relative GPU-hours 表也不能视为真实设备部署 Pareto。
- 论文对 failed execution 与 shape mismatch 有显式计数，这是可复用优点；但未报告 duplicate、OOM、divergence、每轮 API retry、tokens/费用和全部候选的训练 steps。
- 使用 standard test/OOD test 指标进行搜索结果报告；需从代码核对是否存在搜索期间直接使用 test feedback 的风险。

## 可复现性与代码/数据

- 论文给出 GraphIR 结构、演化公式、prompt、NAS-Dependency task/scorer、模型生成参数、seeds、100-iteration budget、硬件和主要表格。
- 截至读取日未见 GraphIR 作者仓库、冻结 commit、requirements、NAS-Dependency 数据下载或完整 evolution traces；因此无法独立核验 extractor、random-start、training recipe 与失败分类。
- OpenEvolve、SPARK 等公开项目只能作依赖/基线线索，不能代替本论文实现。
- PDF 本地读取成功，但未把 reading copy 提交到仓库；状态保持 `codex_draft` 等待人工与代码复核。

## 与 AgenticNAS 的关系

- GraphIR 的 mutation surface/validity envelope 可映射到本仓库 `block/cell/op/connectivity` typed action、shape contract 和 downstream dependency；本地 builder 仍负责生成 Conv1d 代码。
- 最小接口应只暴露 clean-room 的 schema、tensor shape、合法范围、objective 与 typed error；不得传入内部架构代码、端点或日志。
- 可比较 raw code、code + generic dependency facts、code + GraphIR-like state 与纯 typed action；所有组固定 attempted candidates、LLM calls/tokens、training steps、GPU-hours 和至少三组 search seeds。
- 对失败分别记录 schema、shape、interface、OOM、timeout、divergence 与 duplicate；GraphIR 的 invalid/shape accounting 可直接作为设计参考。
- model size 和 NAS GPU-hours 不是实测 deployment latency/memory/energy；`quality_proxy` 和 `latency_proxy_ms` 仍只能是控制流占位符。

## 最小复现实验

- 固定 4–10 层 Conv1d Transformer、训练 recipe、data split、100 attempted trials 与单张目标 GPU。
- 对照 native mutation、raw-code LLM、raw code + generic shape facts、GraphIR-like 三视图、typed `MutationAction`；每组至少三 search seeds。
- LLM 固定模型、temperature、max tokens、timeout/retry 和 call budget；所有 invalid/duplicate/OOM/timeout 计入 attempted trials。
- 指标：best-so-far/hypervolume、action validity、shape/interface failure、duplicate、GPU-hours、LLM tokens/费用、真实 latency 与 peak memory。

## 局限与风险

- 无作者代码和冻结 artifact，无法核实 extractor、training recipe、random-start 与完整 traces。
- 最强受控证据集中于 MNIST1D；向 CLRS、文本、RL、tabular 与 Conv1d Transformer 的外推口径不完全一致。
- 部分 baseline 来自原论文，且 representation baseline 是作者适配版；整表不是严格 matched-budget benchmark。
- 没有完整 LLM 成本、duplicate/OOM/divergence、多目标 Pareto 或真实部署指标。

## 可引用摘要

GraphIR 通过 computation skeleton、mutation surface 和 validity envelope，把可执行神经网络程序中的 tensor flow、可编辑组件与接口/shape 约束显式提供给 LLM，同时保留源代码为编辑对象。作者在 OpenEvolve + Qwen3-Plus 的 MNIST1D-Shuffle 受控 100-iteration 对照中报告更高 accuracy/OOD accuracy，并记录 invalid、shape error 与 RTX 3090 端到端 GPU-hours。跨 CLRS/跨任务结果混合原论文数字与本论文重跑，且缺少作者代码、完整 LLM 成本和真实设备 Pareto，因此当前只支持“架构状态表示值得 matched-budget 复现”的结论。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2608.01633
- PDF：https://arxiv.org/pdf/2608.01633
- 已核对：标题、作者、日期、arXiv ID/DOI、三视图、OpenEvolve/Qwen3-Plus、100 iterations、seeds、RTX 3090、主要表格、失效计数与跨表公平性。
- 未核对：作者代码、独立运行、完整 training recipe、LLM tokens/费用、test-feedback 实现、真实设备指标与所有 baseline 的 matched budget。
- [ ] 已由人工决定 `retained` / `discarded`
