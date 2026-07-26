---
title: "Data-Local Autonomous LLM-Guided Neural Architecture Search for Multiclass Multimodal Time-Series Classification"
authors: "Emil Hardarson, Luka Biedebach, Ómar Bessi Ómarsson, Teitur Hrólfsson, Anna Sigridur Islind, María Óskarsdóttir"
year: "2026"
venue: "arXiv:2603.15939"
paper_url: "https://arxiv.org/abs/2603.15939"
source_pdf: "../pdfs/2603.15939-data-local-llm-nas.pdf"
parser: "Codex"
parsed_on: "2026-07-26"
status: codex_draft
tags: [llm-nas, data-local, privacy, time-series]
---

# Data-Local Autonomous LLM-Guided NAS

> 本笔记由 Codex 基于本地 PDF 生成；该 2026 年工作是较新的 arXiv 预印本。

## 一句话结论

论文把 LLM 控制器与本地训练执行器隔离，控制器只接收聚合 trial summaries，在不暴露原始样本或中间特征的条件下进行长周期架构和预处理搜索。（PDF pp.1, 6–7）

## 研究问题与贡献

- 面向敏感、多模态时间序列，将每个类别和模态拆成 one-vs-rest binary experts，再用轻量 MLP 融合。
- LLM 联合提议 expert architecture 和 modality-specific preprocessing。
- 所有数据、训练和评估留在本地；远端控制器仅看到 descriptors、metrics、learning curves、runtime 和 failure logs。（PDF pp.1, 6–7）

## 方法拆解

- Agent 输入：匿名化 pipeline 描述、超参、固定预算下的验证指标、学习曲线摘要和失败信息。
- Agent 输出：新候选结构与预处理代码。
- Executor：在固定 split、loss、optimizer 和训练预算下运行候选。
- 记录：proposal、execution、outcome 和 repair attempt 以 artifact 方式持久化，可恢复和审计。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| SleepEDFx 明显改善 | 30 cycles 后 test accuracy 84.7%→87.9% | staged expert-fusion baseline | p.10, Sec. 4.3 | high |
| 弱基线可被修复 | EthanolConcentration 60 cycles，32.0%→44.1% | 初始 expert architecture | p.10, Sec. 4.3 | high |
| 收益非普遍 | 部分数据集无提升或略降，作者归因于可能过拟合 | 多个 UEA30 数据集 | p.10, Sec. 4.3 | high |

## 公平性与可信度检查

- 单次 search run 内固定协议，有利于候选比较。
- 不同数据集使用 30/60 cycles，跨数据集不应直接比较搜索效率。
- 数据不出域不等于完全隐私：metrics、learning curves 和 failure logs 仍需做泄漏审计。
- 论文是 proof-of-concept，架构和预处理代码的安全沙箱细节需要进一步核查。

## 与 AgenticNAS 的关系

- 与公司环境高度一致：内部 Archai evaluator 保持本地，Codex/内部模型只看窄的结构化摘要。
- 当前 `AgentObservation` 应禁止原始样本、特征张量、内部 op 实现和完整日志。
- failure trace 应转换成枚举错误类别，而不是原样发给模型。

## 最小复现实验

- 定义 `public_observation.json`，只包含匿名 arch_id、Pareto 指标、预算和 validator error code。
- 对同一随机种子比较完整内部日志与最小摘要对动作有效率的影响。
- 执行隐私字段单元测试，确保 observation schema 无禁止字段。

## 局限与风险

- 数据集特定收益波动大，不能概括为 LLM 搜索始终改善。
- 试验摘要可能成为侧信道；论文未给出形式化隐私保证。
- controller 输出代码会扩大执行风险，当前项目应继续使用声明式动作。

## 可引用摘要

该工作提出数据本地化的 LLM-guided NAS，训练执行器保留原始数据并仅向控制器返回 trial-level 聚合摘要。SleepEDFx 和部分 UEA30 数据集显示改进，但收益具有明显数据集依赖性，且“原始数据不出域”并不替代对指标和日志侧信道的隐私审计。

## 检索与人工核验记录

- 解析问题：数据隔离接口、固定协议、周期预算和收益稳定性。
- 使用片段页码：1–4, 6, 7, 10–13。
- [x] 数据边界字段已核对
- [x] SleepEDFx/EC 关键数字已核对
- [ ] 其余数据集结果已逐项核对
- [ ] 已由人工决定 `retained` / `discarded`
