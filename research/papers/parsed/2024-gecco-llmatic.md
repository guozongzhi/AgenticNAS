---
title: "LLMatic: Neural Architecture Search via Large Language Models and Quality Diversity Optimization"
authors: "Muhammad U. Nasir, Sam Earle, Christopher W. Cleghorn, Steven James, Julian Togelius"
year: "2024"
venue: "GECCO 2024"
paper_url: "https://arxiv.org/abs/2306.01102"
source_pdf: "../pdfs/2306.01102-llmatic.pdf"
parser: "Codex"
parsed_on: "2026-07-26"
status: codex_draft
tags: [llm-nas, evolution, quality-diversity, benchmark]
---

# LLMatic

> 本笔记由 Codex 基于本地 PDF 生成，关键数字仍需人工抽查。

## 一句话结论

LLMatic 用 CodeGen-6.1B 生成网络代码，并用独立的 prompt archive 与 network archive 保持搜索多样性，在 2000 次评估预算内得到竞争性架构。（PDF pp.1–2, 8）

## 研究问题与贡献

- 解决 LLM 单次提示难以稳定做 NAS、传统演化变异又缺乏语义的问题。
- 使用 CVT-MAP-Elites 管理 prompt 行为描述和 network 的 FLOPs、宽深比。
- prompt curiosity 根据生成网络能否进入 archive 更新，兼顾可训练性与多样性。（PDF pp.3–5）

## 方法拆解

- Agent 输入：选中的 prompt、父代网络和 archive 状态；输出：网络代码 mutation/crossover。
- 搜索对象：CIFAR-10 网络及 NAS-Bench-201 cell。
- 选择：network archive 随机选父代，prompt archive 偏向 curiosity 高的个体。
- 默认 LLM temperature 0.7；搜索总评估数限制为 2000。（PDF pp.4–5, 8）

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 找到多样的竞争模型 | CIFAR-10 archive 中超过 20 个竞争网络 | EfficientNet-B0、消融变体 | pp.6–8, Figs. 2–3 | medium |
| NAS-Bench-201 接近最优 | 优于 GPT-4-based GENIUS，接近 DARTS 系方法 | GENIUS、random、DARTS、Lambda-DARTS | p.7, Table 1 | high |
| 各组件有贡献 | 完整 LLMatic 的最好精度高于 archive/mutation/crossover 消融 | 5 类消融 | pp.5–6 | medium |

## 公平性与可信度检查

- CIFAR-10 消融运行 30 seeds；NAS-Bench-201 结果平均 10 runs。
- 2000 evaluations 是明确预算，但真实 CIFAR-10 候选训练和 LLM 推理总成本未统一换算。
- NAS-Bench-201 的查询成本与真实训练成本不能直接等同。

## 与 AgenticNAS 的关系

- 当前 Pareto archive 可增加行为描述维度，形成 Pareto + QD 双重保留机制。
- prompt archive 可替换为“策略/提示词版本 archive”，但第一阶段不必引入复杂 MAP-Elites。
- 最有价值的对照是：同样 200 个候选下，Pareto-only 与 Pareto+novelty 的覆盖度和 hypervolume。

## 最小复现实验

- 定义两个行为描述：深度、平均 FFN ratio，按网格记录每格最好 Pareto 候选。
- 对比 random mutation、LLM mutation 和 LLM mutation + novelty archive。
- 固定候选训练、LLM 调用和随机种子预算。

## 局限与风险

- 使用代码生成导致合法性和执行安全边界较弱。
- 6.1B CodeGen 与更强模型的结论不可直接互换。
- QD 行为描述需要人工设计，可能把搜索偏向容易量化但不重要的结构差异。

## 可引用摘要

LLMatic 将代码 LLM 的架构变异能力与 CVT-MAP-Elites 质量多样性档案结合，同时维护 prompt 和 network 两类 archive。论文在 CIFAR-10 与 NAS-Bench-201 上以 2000 次评估获得竞争结果并提供多项消融，但真实训练成本与 QD descriptor 选择仍限制了可比性。

## 检索与人工核验记录

- 解析问题：QD archive、候选预算、NAS-Bench-201 和消融。
- 使用片段页码：1–9。
- [ ] Table 1/2 数值已逐项核对
- [x] 2000 evaluations 和模型规模已核对
- [x] seeds 信息已核对
- [ ] 已由人工决定 `retained` / `discarded`
