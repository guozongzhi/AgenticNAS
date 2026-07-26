---
title: "LLM-Guided Neural Architecture Search for Robust Co-Design of Physical Neural Networks"
authors: "Tyler King, Timothee Leleu"
year: "2026"
venue: "arXiv:2606.10294"
paper_url: "https://arxiv.org/abs/2606.10294"
source_pdf: "../pdfs/2606.10294-uh-nas.pdf"
parser: "Codex"
parsed_on: "2026-07-26"
status: codex_draft
tags: [llm-nas, pareto, hardware-aware, robustness]
---

# UH-NAS

> 本笔记由 Codex 基于本地 PDF 生成；该 2026 年工作是较新的 arXiv 预印本。

## 一句话结论

UH-NAS 把硬件成本、约束和非理想性封装成可替换 backend，让 LLM 充当 NSGA-II 的 mutation/crossover 算子，并联合优化准确率与推理能耗。（PDF pp.1–4）

## 研究问题与贡献

- 同一搜索算法可分别面向 CPU、GPU 和光学 MZI backend 生成 Pareto front。
- 每轮依据当前 Pareto 候选和噪声退化更新硬件设计知识库。
- 针对非常规硬件，作者认为 zero-cost proxy 与 noisy accuracy 可能负相关，因此完整训练候选。（PDF pp.2–5）

## 方法拆解

- 搜索对象：MNIST 分类网络，结构通过硬件相关操作词表和约束生成。
- Agent 输入：global Pareto front、近期候选、非理想性带来的 accuracy degradation。
- Agent 输出：硬件感知 mutation/crossover 和更新后的设计 heuristics。
- 选择：NSGA-II Pareto rank + crowding distance；目标为 accuracy 最大、energy 最小。
- 评估：每候选训练 20 epochs，并计算 energy、噪声下准确率和 robustness degradation。（PDF pp.3–5）

## 评估与预算

- 30 generations × 8 candidates，population size 20。
- backends：Xeon 8380 FP32、Blackwell B200 FP16、8-bit MZI 模拟。
- LLMatic 对照使用同样代数、候选数、种子和训练条件。（PDF pp.5–6）

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 跨硬件得到不同 Pareto front | MNIST error-energy front 在 CPU/GPU/MZI 上排序不同 | 同搜索算法不同 backend | p.1, Fig. 1 | medium |
| 非理想性改变最优结构 | clean performance 不能可靠预测 noisy performance | ideal/noisy regimes | pp.2–3, Fig. 5 discussion | high |
| 光学 MAC 能耗代理更低 | Linear MAC: CPU 91.7 pJ、GPU 0.89 pJ，MZI 更低但含转换成本 | analytical cost models | p.5, Table 1 | medium |

## 公平性与可信度检查

- 候选训练条件在 LLMatic 对照中匹配，但 energy 来自解析模型而非整机测量。
- MNIST 与模拟 MZI 是 proof-of-concept，不能直接推断真实大模型部署收益。
- full noisy training 提高可信度，也显著提高搜索成本；论文未给出统一 GPU-hours/LLM token 总账。

## 与 AgenticNAS 的关系

- 可直接借鉴 backend interface：`energy(spec)`、`constraints(spec)`、`inject_noise(model)`。
- 当前 latency/quality proxy 应替换为真实设备测量，或明确标注解析 cost model。
- LLM 仍只提议动作，NSGA-II/Pareto 和硬件 evaluator 保持确定性。

## 最小复现实验

- 首先只增加两个目标：真实 latency 与 params/peak memory，不立即模拟光学噪声。
- 对 CPU/GPU 分别搜索并比较 Pareto front 的结构 motif。
- 对比相同候选在 proxy 与真实测量上的 rank correlation。

## 局限与风险

- 能耗和非理想性主要依赖模拟/解析假设。
- 搜索任务较小，硬件感知经验能否迁移到 4–10 层语言模型未知。
- 新预印本应优先核查代码、seed 和 cost-model 实现。

## 可引用摘要

UH-NAS 将硬件能耗模型、物理约束和非理想性封装为可替换 backend，并用 LLM 生成候选、NSGA-II 维护准确率–能耗 Pareto front。该框架适合作为硬件感知 AgenticNAS 的接口参考，但当前证据主要来自 MNIST 和模拟 MZI，能耗结论不能等同于真实系统测量。

## 检索与人工核验记录

- 解析问题：硬件 backend、Pareto、噪声鲁棒性和公平预算。
- 使用片段页码：1–6, 8–10, 15。
- [x] generation/candidate/population 预算已核对
- [x] NSGA-II 目标和每候选训练轮数已核对
- [ ] 主要 Pareto 数值已从图中人工读取
- [ ] 已由人工决定 `retained` / `discarded`
