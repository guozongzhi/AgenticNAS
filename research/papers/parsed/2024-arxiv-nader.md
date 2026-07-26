---
title: "NADER: Neural Architecture Design via Multi-Agent Collaboration"
authors: "Zekang Yang, Wang Zeng, Sheng Jin, Chen Qian, Ping Luo, Wentao Liu"
year: "2024"
venue: "arXiv:2412.19206"
paper_url: "https://arxiv.org/abs/2412.19206"
source_pdf: "../pdfs/2412.19206-nader.pdf"
parser: "Codex"
parsed_on: "2026-07-26"
status: codex_draft
tags: [llm-nas, multi-agent, memory, graph]
---

# NADER

> 本笔记由 Codex 基于本地 PDF 生成，关键数字仍需人工抽查。

## 一句话结论

NADER 用 Reader、Proposer、Modifier、Reflector 四类 Agent 在开放图结构空间中迭代设计网络，并通过即时错误反馈和历史经验检索减少无效修改。（PDF pp.1–3, 5–6）

## 研究问题与贡献

- 将受固定搜索空间约束的 NAS 区分为开放的 Neural Architecture Design。
- 用 DAG 文本表示替代直接生成完整代码，节点是操作、边是数据流。
- Reflector 同时执行结构可执行性检查和成功/失败经验总结。（PDF pp.2–6）

## 方法拆解

- Reader 从论文中提取设计知识；Proposer 选择 modification tree 节点并给出建议。
- Modifier 把建议应用到 network graph，再转换为可执行代码。
- Reflector 校验图、与 Modifier 多轮纠错，并按相似建议检索 5 条历史经验。
- 搜索采用 DFS/BFS 结合，在 modification graph 中兼顾深挖与覆盖。（PDF pp.3–6）

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 即时反馈改善可执行性 | executability 0.54→0.64，quality 0.78→0.84 | 无 LIF | p.8, Table 3 discussion | high |
| 开放设计可提升初始架构 | 大规模实验得到 76.0% test accuracy，较初始高 5.14% | 初始 ResNet | p.8, Fig. 4 discussion | medium |
| 研究 Agent 都有贡献 | Reader/Proposer 消融在 CIFAR-10/100、ImageNet16-120 上下降 | 专家建议/随机建议 | p.8, Table 2 | medium |

## 评估与预算

- NAS-Bench-201：CIFAR-10、CIFAR-100、ImageNet16-120；5 次修改，3 个随机种子。
- 大规模 NAD 报告约 987K output tokens、总成本 23 美元、平均每架构 0.046 美元。
- 训练遵循 NAS-Bench-201 数据与超参，并用宽度约束参数量/FLOPs。（PDF pp.7–8, Appx. A1）

## 公平性与可信度检查

- Agent 组成、图表示和经验机制同时变化，完整系统收益不能只归因于 multi-agent。
- 开放搜索空间与固定 NAS-Bench-201 方法的可比性依赖参数量/FLOPs 约束。
- 论文 v1 首页写“代码将发布”，解析时未验证代码是否已经公开。

## 与 AgenticNAS 的关系

- DAG/声明式表示与当前 JSON `MutationAction` 的安全思路一致。
- Reflector 的失败分类可直接映射为 invalid hierarchy/value/depth/duplicate 等 validator 结果。
- Reader 不应直接接触公司源码；仅输入公开论文知识和匿名化结构摘要。

## 最小复现实验

- 为当前 validator 错误建立短期失败记忆，按 action signature 检索最近 5 条。
- 对比 stateless Agent、只用失败记忆、成功+失败记忆。
- 固定候选和 LLM token 预算，报告有效动作率、重复率、hypervolume。

## 局限与风险

- 复杂多 Agent 系统带来更多提示词和归因混杂。
- graph-to-code 转换仍是关键失败点，只是从 Agent 输出边界后移。
- 公开论文知识可能与目标内部算子不匹配，需要白名单映射。

## 可引用摘要

NADER 将开放式网络设计组织为 Reader、Proposer、Modifier 和 Reflector 的协作过程，并以 DAG 文本和经验检索约束修改。论文的消融表明即时反馈与历史经验能改善可执行性和设计质量，但系统同时改变了 Agent 分工、表示和搜索策略，贡献归因仍需更严格的同预算对照。

## 检索与人工核验记录

- 解析问题：多 Agent 分工、图表示、反思记忆、预算和消融。
- 使用片段页码：1–6, 8, 9, 11, 14。
- [ ] Table 1–3 数值已逐项核对
- [x] LIF/LDE 定义和经验检索数量已核对
- [x] LLM 成本数字已定位
- [ ] 已由人工决定 `retained` / `discarded`
