---
title: "Hyperparameter Optimization for Large Language Model Instruction-Tuning"
authors: "Christophe Tribes, Sacha Benarroch-Lelong, Peng Lu, Ivan Kobyzev"
year: "2023"
venue: "AAAI 2024"
paper_url: "https://arxiv.org/abs/2312.00949"
source_pdf: "../pdfs/2312.00949-llm-instruction-tuning-hpo.pdf"
parser: "Codex"
parsed_on: "2026-07-26"
status: codex_draft
tags: [hpo, instruction-tuning, lora, black-box]
---

# Hyperparameter Optimization for LLM Instruction-Tuning

> 本笔记由 Codex 基于本地 PDF 生成，关键数字仍需人工抽查。

## 一句话结论

论文把 LLaMA 2 7B 的 LoRA 指令微调整体视为昂贵黑盒，对比 NOMAD/MADS 与 NNI-TPE 调整 rank、alpha、dropout 和学习率，说明验证损失最优不必然等于下游任务最优。（PDF pp.1–5）

## 研究问题与贡献

- 搜索 LoRA rank、scaling alpha、dropout 和 learning rate。
- 比较直接搜索 MADS/NOMAD 与 Bayesian model-based NNI-TPE。
- 在 Alpaca 52K 与 Dolly 15K 混合指令数据上调优 LLaMA 2 7B。（PDF pp.1–3）

## 评估与预算

- 训练使用 4 × NVIDIA A100 80GB，batch size 4。
- 第一轮 NOMAD：50 evaluations × 3 epochs；单次约 2h15m，总过程少于 5 天。
- 第二轮：NOMAD 与 NNI-TPE 各 100 evaluations × 2 epochs；NOMAD 用第一轮 cache warm-start。（PDF pp.3–4）
- 下游核验：MMLU、BBH、DROP、HumanEval。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| HPO 明显影响验证损失 | NOMAD/TPE 都找到优于默认区域的组合 | 默认 LoRA 配置 | pp.3–4, Figs. 1–2 | high |
| 高 rank 常被选中 | NOMAD top-10 中 5 个 rank 512、4 个 256、1 个 128 | 搜索空间其他 rank | p.3 | high |
| 单一验证损失不完全代表能力 | validation-loss 第一名并非所有下游任务最好 | MMLU/BBH/DROP/HumanEval | pp.4–5 | high |

## 公平性与可信度检查

- 第二轮 NOMAD 使用第一轮 cache，NNI-TPE 是否获得完全等价 warm-start 需谨慎核对。
- 只用单次/少量训练评估，seed variance 和训练噪声报告有限。
- 4×A100、100 次 trial 的成本仍高，不适合作为小型模型 Agent 的默认内环。

## 与 AgenticNAS 的关系

- 是训练参数优化的传统非 Agent 基线，应优先于 LLM Agent 比较。
- 提醒项目不要只用 validation loss：还需 downstream、稳定性、吞吐和显存目标。
- 可将 NOMAD/TPE 作为固定预算下的强对照，再测 Codex 是否改善 warm-start。

## 最小复现实验

- 固定一个候选架构，搜索 learning rate、batch size、weight decay、warmup ratio。
- 比较 random、TPE、Codex warm-start + TPE，各 20 trials。
- 用短训 loss 排序后，对 top-k 做完整训练，测 fidelity rank correlation。

## 局限与风险

- 只研究 LoRA instruction tuning，不覆盖预训练或架构搜索。
- 大量算力用于单一 7B 模型，迁移到小模型可能产生不同最优区间。
- 人类偏好证据和自动 benchmark 的一致性仍有限。

## 可引用摘要

该工作使用 NOMAD/MADS 和 NNI-TPE 对 LLaMA 2 7B 的 LoRA 指令微调进行黑盒超参优化。结果表明 rank、alpha、dropout 与学习率需要联合搜索，同时最低验证损失并不保证所有下游任务最优；其高计算预算适合作为 HPO 证据和传统基线，而非低成本 Agent 内环。

## 检索与人工核验记录

- 解析问题：LoRA 搜索空间、BBO 基线、预算和多指标风险。
- 使用片段页码：1–6, 8, 9。
- [x] GPU、trial 和 epoch 预算已核对
- [x] 搜索参数已核对
- [ ] Table 1 下游数值已逐项核对
- [ ] 已由人工决定 `retained` / `discarded`
