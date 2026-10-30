---
title: "FlowGenesis: Representation-Driven Self-Organization of Neural Architectures"
authors: "Maksim A. Kazanskii"
year: "2026"
venue: "arXiv:2610.35108v1"
paper_url: "https://arxiv.org/abs/2610.35108"
source_pdf: "https://arxiv.org/pdf/2610.35108"
code_url: "https://github.com/maksimkazanskii/FlowGenesis"
parser: "Codex"
parsed_on: "2026-10-30"
status: codex_draft
tags: [adaptive-architecture, structural-plasticity, neurogenesis, pruning, recurrent-network, traditional-baseline]
---

# FlowGenesis

> 本笔记基于 arXiv v1 官方 PDF。FlowGenesis 不使用独立 architecture proposer/searcher，而是在一次训练轨迹中按 representation feedback 生长和剪枝，归“在线结构自适应邻接基线”，不能写成标准 NAS 或固定架构 HPO。

## 一句话结论

- FlowGenesis 用连续 minibatch activation mean 的变化量 Representation Flux 驱动 neuron birth，并以低 Flux+低 activity 驱动 pruning；结构变化与梯度训练形成闭环，但没有候选 population、archive 或独立 architecture-evaluation loop。（PDF pp.6–9）
- 作者在 Fashion-MNIST、CIFAR-10、AG News 的五 seed 实验中报告，不同初始 neuron count 最终收敛到较窄的 dataset-specific 范围；在 Split CIFAR-100 50-task 设置中，作者报告与 fixed-width PNN 准确率接近，同时 active parameters 减少 34.2%。这些是在线容量分配证据，不是 matched-budget NAS 胜出证据。（PDF pp.10–18, Tables 1–4）

## 搜索对象、变量与固定项

- 基础模型是 trainable sparse recurrent neural container；可变结构为 neuron population、recurrent mask/edge count 和 connectivity density。固定输入投影、relaxation dynamics、task loss、optimizer 和数据协议。（PDF pp.6–9）
- birth 复制 parent 的 input/incoming recurrent weights 并加小噪声，把 outgoing/output contribution 平分；pruning 需要 activity 与 Flux 同时落入低分位并持续满足条件。每次 change 后重建 Adam optimizer。（PDF pp.7, 9）
- `Nmin/Nmax`、warm-up、check/cooldown、birth/death persistence 与 per-check rate 限制结构变化；它们不直接指定目标 neuron count，但 birth threshold 对最终容量非常敏感。（PDF pp.8, 23–26, Table 5）

## Feedback、停止与失败处理

- observation 是 per-neuron Flux 与 activity EMA；action 是 split 或 remove neuron；feedback 是后续 activation statistics、accuracy 与 population dynamics。不存在 LLM、reflection、proposal archive 或显式 Pareto objective。（PDF pp.6–9）
- 默认训练 100 epochs；结构适配在 100k processed examples 后启动，每 10k examples 检查一次，birth/death persistence 和 cooldown 也为 10k，population 限制 10–300。（PDF p.24）
- 论文记录 cumulative births/deaths 和结构轨迹，但未单列 invalid change、optimizer-reset failure、OOM/divergence、duplicate/equivalent architectures 或 retry。训练结束是 epoch budget，而不是 architecture-search convergence。

## 评估、预算与结果

- standalone 实验覆盖 Fashion-MNIST、CIFAR-10、AG News，不同初始 size 均为 5 seeds。Fashion-MNIST 的 `N0=20/40/80/160` 最终 mean neurons 为 61.6/53.0/55.4/51.4；CIFAR-10 的 `N0=50/100/200/400` 为 60.2/60.6/62.6/64.0；AG News 为 60.2/63.8/57.0/58.4。（PDF pp.10–12, Figure 2, Table 1）
- random birth 在 Fashion-MNIST 得到更高 final accuracy 87.86% 而非原方法 86.99%，但规模为 140.8 而非 57.2 neurons；这表明 Flux ranking 的主要证据是容量控制，未证明预测质量占优。（PDF pp.15–16, Table 3）
- Split CIFAR-100 20 tasks：59.32% vs PNN 58.66%，active parameters 0.576M vs 0.650M；50 tasks：71.05% vs 71.03%，1.903M vs 2.890M。每个 task 40 epochs、5 paired seeds；best validation checkpoint 冻结。（PDF pp.16–18, Table 4）
- 未报告 GPU 型号/数量、GPU-hours、wall-time、energy、peak memory、USD；attempted architecture 也不适用，宜以 structural checks、birth/death attempts 和实际 training compute 记账。

## 公平性、代码与局限

- main initial-size 对照共享训练协议并有 5 seeds；continual-learning PNN 使用固定 width 60，作者说明它近似匹配 early FlowGenesis modules，但不等同于逐 task/参数/计算预算严格匹配。
- best-checkpoint test accuracy 存在作者明确承认的 retrospective optimistic bias；结构分析使用 final epoch，二者不可混写。（PDF p.9）
- birth/pruning selection 消融表明 shuffled signals 可达到相近结果；原方法不唯一依赖 neuron-specific Flux ranking。（PDF pp.15–16, Table 3）
- 论文声称代码位于 `maksimkazanskii/FlowGenesis`，但 2026-10-30 `git ls-remote` 返回 repository not found；当前属于代码不可访问的复现缺口。

## 对本仓库的价值

- 可复用的是把 per-block activation/gradient drift 作为 typed growth/pruning trigger，并记录 structure turnover 与 final capacity；它可成为 memory-aware policy 的局部 feedback feature。
- 不可直接迁移的是“自组织到 50–65 neurons”的数值，它来自特定 recurrent container、阈值和训练长度；作者也明确指出扩展到 convolution/Transformer 尚未验证。（PDF pp.19–20）
- 最小验证应在固定 Conv1d recipe 上比较 static、random grow/prune、Flux grow/prune 与 Agent policy，匹配 epochs/GPU/wall-time，报告 attempted structural checks、accepted birth/death、invalid/OOM、真实 latency/memory/energy 与 Pareto hypervolume。

## 检索与人工核验记录

- 官方 PDF：41 页，SHA-256 `fb248ba323ea582a6a762203b7563cc9f3f6d9280faff6f75a2f9fbfe78189e5`；首次下载截断，HTTP 206 续传完成后才通过 EOF/pypdf 校验。
- arXiv Atom 于 2026-10-30 核对为 v1；论文代码 URL 当前不可访问。
- [x] 结构更新规则、协议、Tables 1、3、4、5 已核对
- [x] seed 与 epoch 预算已核对
- [x] GPU/墙钟/energy/失败账本缺口已标记
- [x] 在线结构自适应与标准 NAS 边界已区分
- [ ] 人工决定 `retained` / `discarded`
