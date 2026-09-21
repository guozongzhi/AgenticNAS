---
title: "LEMUR 2: Unlocking Neural Network Diversity for AI"
authors: "Tolgay Atinc Uzun et al."
year: "2026"
venue: "arXiv:2607.06839v1"
paper_url: "https://arxiv.org/abs/2607.06839"
source_pdf: "https://arxiv.org/pdf/2607.06839"
parser: "Codex"
parsed_on: "2026-09-22"
status: codex_draft
tags: [llm-nas, benchmark, architecture-dataset, hardware-aware, real-device]
---

# LEMUR 2

> 本笔记由 Codex 基于 arXiv v1 PDF 生成；它主要是数据集与生成/部署基础设施论文，不应当被写成单一 NAS 算法的胜出证据。

## 一句话结论

- 核心主张：LEMUR 2 聚合 AST mutation、遗传/RL、fractal、LLM synthesis 和 NN-RAG 生成的 14k+ 架构及 750k+ training records，并提供 Android/Unity 部署测量；价值在于开放异质架构数据与设备管线，而不是严格 matched-budget 的 Agent NAS 对比。
- 证据位置：PDF pp.1–9，Tables 1–2。

## 搜索对象、空间与 Agent

- 搜索对象：跨图像 captioning、text-to-image、language modeling、image classification 的模型源码/拓扑。
- 生成路径：AST edits、genetic/RL evolution、fractal construction、few-shot LLM、masked-skeleton completion，以及从 1,289 candidate blocks/900+ usable modules 构建的 NN-RAG。
- LLM 作为代码 policy；生成候选依次经过 compilation、forward、training/accuracy 等检查，并按通过阶段/相对基线形成 reward。
- 变量与训练配方在不同子系统间不同，因此不是一个统一 fixed-recipe NAS space。

## 预算、失败与部署

- 数据规模：14,000+ architectures、750,000+ structured records（摘要）；Table 2 分解各生成/部署子系统。
- few-shot LLM 子系统报告 4,033 candidates；NN-RAG 初始大上下文方案因 context overflow 出现 99.8% failure，随后改成检索式上下文。
- 训练硬件：NVIDIA RTX 3090/4090（PDF p.7）；总 GPU-hours、墙钟和 LLM tokens/费用未报告。
- NN-Lite 报告 7,512 Android TFLite records/100% conversion；NN-VR 报告 10,244 Unity/Barracuda records/95.0% 自动 shader/memory optimization（PDF p.8, Table 2）。精确物理设备覆盖、能耗与统一测量协议需要代码/数据复核。

## 核心结果

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 数据覆盖比单一 cell benchmark 更广 | 14k+ architectures、750k+ records | NAS benchmark taxonomy | PDF pp.1–3, Table 1 | high |
| LLM 生成可产生有效候选 | few-shot LLM 4,033 candidates；best CIFAR-10 accuracy 0.3874 | 不同生成系统 | PDF p.8, Table 2 | medium |
| 提供真实部署元数据 | Android latency DB 与 Unity frame-time/memory pipeline | deployment pipeline | PDF pp.6–8, Table 2 | medium |

## 公平性、复现性与局限

- 生成方法的 candidate/training/LLM budget 不统一，不能比较“LLM 优于 GA/RL”。
- 多任务训练 recipe、数据规模和 evaluator 不同，不能形成统一 Pareto frontier。
- 作者提供项目仓库，但本轮未执行代码或验证数据库行级 provenance；状态保持 `codex_draft`。
- energy 和统一 peak-memory 数值未报告；real-device latency 记录不等于已证明 hardware-aware search loop。

## 与当前 AgenticNAS 的关系

- 可作为异构架构语料、code validity gate 与 Android/VR measurement schema 的参考。
- 不能直接支持 4–10 层 Conv1d Transformer；若复用数据，须筛出结构/训练固定且设备协议一致的子集。
- 值得借鉴 compilation→forward→train→device 的分层失败账本。

## 链接

- 论文：https://arxiv.org/abs/2607.06839
- 项目：https://github.com/ABrain-One/NN-Dataset
