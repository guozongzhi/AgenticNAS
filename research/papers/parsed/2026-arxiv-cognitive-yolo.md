---
title: "Cognitive-YOLO: LLM-Driven Architecture Synthesis from First Principles of Data for Object Detection"
authors: "Jiahao Zhao"
year: "2026"
venue: "arXiv:2512.12281v2"
paper_url: "https://arxiv.org/abs/2512.12281"
source_pdf: "https://arxiv.org/pdf/2512.12281"
parser: "Codex"
parsed_on: "2026-09-22"
status: codex_draft
tags: [llm-nas, architecture-synthesis, object-detection, react, code-generation]
---

# Cognitive-YOLO

> 本笔记由 Codex 基于 arXiv v2 PDF 的带页码文本生成；作者结果不是本仓库结果，人工核验前均视为草稿。

## 一句话结论

- 核心主张：系统把数据画像、ReAct 组件检索、LLM 拓扑组装和编译/训练串成真实检测架构生成流程；它证明了“一次性按数据合成轻量架构”的可行性，但没有给出可比较的多轮搜索预算、经典 NAS 对照或真实设备目标。
- 证据位置：PDF pp.1, 4–5, 7–10，尤其是 Fig. 1、Tables 3–5。

## 研究问题与贡献

- 问题：通用 YOLO 在垂直数据上存在 domain shift，人工定制 Backbone/Neck/Head 成本高。
- 真实搜索对象：由组件库中的卷积、注意力、融合和检测模块组成的完整目标检测网络拓扑，而不是 Agent 工作流。
- 变化：`Analyze–Synthesize–Compile` 管线先量化数据特征，再检索模块，由 LLM 输出结构描述，最后通过编译、静态检查和 pilot training 落地。
- 证据位置：PDF pp.1, 4–6。

## 方法拆解

### 搜索对象、变量与层级

- 可变：Backbone/Neck/Head 的模块选择、连接与组合；生成模型的参数量随数据集变化。
- 固定：检测任务和每个数据集的训练/评估协议；详细固定字段只在 Table 3 局部报告。
- 层级：完整模型 → Backbone/Neck/Head → 组件/op；论文不是针对 4–10 层 Conv1d Transformer。
- 空间规模、候选去重和显式边界：未报告。

### Agent 闭环

- 观察：数据画像与组件库检索结果。
- 动作：ReAct Agent 检索候选组件，LLM 生成拓扑/配置，编译器实例化并检查。
- 反馈：编译、静态检查和 pilot training；没有清晰展示多轮“结果→新候选”的迭代轨迹。
- 无效动作、重复与修复率：未报告。

### 目标与预算

- 目标：检测 mAP 与模型紧凑性；没有 Pareto/hypervolume 定义。
- 候选数、训练次数、GPU-hours、墙钟、LLM 调用/tokens/费用：未报告。
- 硬件：训练环境见 Table 3（PDF p.7）；真实设备 latency、peak memory、energy 未报告。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 合成模型保持轻量 | 四个任务的模型约 1.9M–2.7M 参数 | YOLO 系列 | PDF p.8, Table 5 | high |
| Rice Disease 上达到可用检测质量 | mAP@0.5:0.95 为 24.7%，约 2.1M 参数 | 表中 YOLO 基线 | PDF p.8, Table 5 | high |
| 跨四种垂直数据展示适配 | rail、rice、fire、student behavior | 统一训练表 | PDF pp.7–8, Tables 3–5 | medium |

## 公平性、复现性与局限

- 没有 matched attempted/evaluated candidate budget，也没有 random/evolution/classical NAS、stateless LLM 与 memory-aware LLM 对照。
- 搜索 seed、完整 prompt、组件库 manifest、失败/重复候选和 LLM 成本未报告；代码链接未在核验 PDF 中确认。
- 结果支持架构合成，不足以证明搜索效率或 Pareto 优势；未来工作才提出 NPU/FPGA latency/energy（PDF p.10）。
- 置信度：方法/表格读取为高；关于迭代搜索效率的结论为低，因为字段缺失。

## 与当前 AgenticNAS 的关系

- 可借鉴 typed Backbone/Neck/Head 中间表示和编译 gate。
- 不能直接迁移到 4–10 层 Conv1d Transformer，也不能把参数量替代真实 latency、memory 或 energy。
- 复现优先补：固定训练配方、相同候选预算、多 seed、完整失败账本，以及 random/evolution/stateless/memory-aware 四组对照。

## 链接

- 论文：https://arxiv.org/abs/2512.12281
