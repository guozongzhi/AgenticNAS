---
title: "TacEvo: Self-Evolving Architecture Discovery for Robotic Tactile Perception via LLM-Driven Quality-Diversity Search"
authors: "Mohammed AbuSadeh, Lan Wei, Dandan Zhang"
year: "2026"
venue: "arXiv:2606.30109v1"
doi: "10.48550/arXiv.2606.30109"
paper_url: "https://arxiv.org/abs/2606.30109"
code_url: "https://github.com/LannWei/TacEvo"
source: "arXiv v1 metadata/PDF and author-linked code repository, accessed 2026-07-30"
parser: "Codex"
parsed_on: "2026-07-30"
status: codex_draft
tags: [llm-nas, quality-diversity, map-elites, code-generation, tactile-perception]
---

# TacEvo

> 本笔记基于 arXiv v1 的 8 页 PDF 和论文直接链接的公开代码库。所有指标均为作者报告，尚未独立复现。

## 一句话结论

TacEvo 让 Claude 3 Haiku 对真实 CNN 代码做 mutation/crossover，用语法、实例化和前后向计算验证过滤无效候选，再由双 CVT MAP-Elites archive 保留结构多样的网络和提示词结果；它为“代码级动作合法性 + quality-diversity memory”提供了直接对照，但搜索 fitness 仍是单一 validation loss，Efficiency Ratio 只是 archive descriptor，并非真实 latency、memory 或 Pareto 目标。（pp. 3–5）

## 书目信息与来源核验

- arXiv ID：2606.30109v1；提交日期：2026-06-29；arXiv DOI：10.48550/arXiv.2606.30109。
- 作者：Mohammed AbuSadeh、Lan Wei、Dandan Zhang；当前可核验 venue 为 arXiv。
- 论文：https://arxiv.org/abs/2606.30109
- 代码：https://github.com/LannWei/TacEvo；论文 PDF 直接给出该地址，仓库公开 supplementary materials，但没有 release。
- 置信度：书目信息 high；方法 high；作者报告的结果 medium；端到端可复现性 medium-low。

## 研究问题与贡献

- 问题：开放代码级 LLM 搜索容易产生不可训练候选、重复结构和单一模式收敛；触觉感知又需要任务/传感器特定架构。
- 方法贡献：用 LLM 作随机代码级进化算子，CVT MAP-Elites 作质量多样性选择，并并行维护 network archive 与 prompt archive。
- 两个 descriptor：Architectural Diversity 汇总 op entropy、connection density 和 layer heterogeneity；Efficiency Ratio 以 `FLOPs / (Params × width-to-depth ratio)` 表示计算—结构区域。（p. 4）
- 论文用 ViTacTip 的三轴力回归和七类纹理分类验证搜索闭环。（pp. 5–7）

## 方法拆解

### 搜索或优化对象

- 搜索对象是可执行、可训练的神经网络代码，不是 Agent 工作流。
- seed 是三个卷积 block 加全连接 head 的人工 CNN；所有候选固定输入分辨率、输出维度、task loss 和 I/O contract。
- 候选可改变 depth、width、connectivity、pooling、attention、normalization 和 activation block；top variants 出现 2–4 个卷积 block、spatial attention、strided convolution、residual、GELU 和 BN/LN 等变化。（pp. 3, 7）
- 搜索空间并非本仓库的 4–10 层 Conv1d Transformer，也没有声明式 block/cell/op schema；Agent 直接编辑 Python 代码。

### Agent 与优化闭环

- 每代先以 0.85/0.15 概率选择 mutation 或 crossover，且该代所有 proposal 共用同一种 operator。
- mutation 从 network archive 选一个 elite parent，并从当代随机 prompt pool 选 instruction；crossover 选两个 elite parents 和固定 instruction。
- LLM 输出候选代码后依次检查语法、实例化和在 task loss 下的 forward/backward；无效候选直接丢弃，不重采样。
- 合法候选训练 10 epochs，以最终 validation loss 为 scalar fitness；在 descriptor space 中进入空 niche 或替换更差 elite。
- prompt archive 记录 `(prompt index, temperature)` 是否产生 archive insertion，并计算 curiosity；正文明确 mutation prompt 仍从当代 pool 均匀随机抽样，未用 prompt archive 作选择，因此不能把它解释成已验证的 adaptive prompt policy。（pp. 3–5）

### 评估与预算

- 数据：ViTacTip force prediction 3,000 张图；grating classification 3,507 张图、7 类；统一 resize 到 256×256，按 80%/10%/10% 划分。
- 搜索：每任务 20 generations、每代最多 50 个 LLM proposal，即每任务最多 1,000 个 proposal；合法候选各训练 10 epochs。
- LLM：Claude 3 Haiku；论文未报告 snapshot、sampling seed、每个 proposal 的 API call 映射、token 或费用。
- 高保真：baseline 与四个 TacEvo variants 各用 20 个 training seeds；正文未给出完整高保真 epochs、optimizer schedule、GPU 型号、总 GPU-hours 或 wall time。
- 目标：validation loss 是唯一 fitness；FLOPs/Params/width/depth 只形成 QD descriptor，不是多目标 Pareto 优化，也没有真实 latency 或 memory measurement。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 搜索期 best fitness | 20 代后 force MSE 改善 56.1%，grating cross-entropy 改善 96.1% | 各任务初始 archive fitness | p. 6, Fig. 3 | medium |
| 动作合法性 | 平均可训练率 force 96.0%，grating 94.5% | 每代最多 50 个 proposal | p. 6, Fig. 4 | high |
| QD 覆盖 | final network archive coverage 88.0% / 92.0% | CVT niches | p. 6, Figs. 5–6 | medium |
| 力回归高保真 | Variant 3/4 与 expert baseline 无显著差异，校正后 p=0.25/0.40 | 人工 CNN，20 seeds | pp. 6–7, Table I | high |
| 纹理分类高保真 | 四个 variants 的 median 均高于 baseline；Variant 1/3 为 100.0%，baseline 99.7%，校正后均 p<0.05 | 人工 CNN，20 seeds | p. 7, Fig. 8/Table II | high |

## 公平性与可信度检查

- 搜索只与人工 CNN 最终结果比较；没有 matched-budget random mutation、传统 evolution、MAP-Elites without LLM、single archive 或 prompt-memory 消融，无法隔离 LLM、QD 和 prompt tracking 的贡献。
- “20 seeds”用于 top variants 的重新训练，不等于用 20 个独立搜索 seeds；论文只展示每任务一次 20-generation search，search variance 未报告。
- 高可训练率证明 validation gate 之后的执行可靠性，但没有报告 syntax/compile/trainability 各类失败数、duplicate rate 或无效 proposal 消耗的 API/GPU 成本。
- 纹理数据较小且 baseline median 已达 99.7%；虽有 seed-wise 统计检验，仍需要独立 dataset、split 和外部传感器验证。
- Efficiency Ratio 不是设备效率测量；不能从 archive coverage 推导 latency、energy 或 memory Pareto 改善。

## 可复现性与代码/数据

- 公开仓库包含 architectures、descriptors、LLM mutation、MAP-Elites、prompts、training 和配置目录，且论文提供核心算法、数据规模、split、20×50 搜索上限和 10-epoch 低保真预算。
- 仓库没有 release；正文没有完整 LLM 配置、硬件/总 GPU-hours、完整高保真 recipe、dataset 获取与授权说明。
- 若无法重建论文的固定 prompt library、temperature schedule 和 CVT centroids，archive coverage 结果可能不可直接复现。

## 与 AgenticNAS 的关系

- 可复用 dual archive 的思想，但应把 network archive 存为声明式 `ArchitectureSpec`/`MutationAction`，prompt/memory 只保存公开 action/result/error 摘要，避免任意代码和内部信息越界。
- Architectural Diversity 可拆成更可审计的 block/cell/op coverage、connectivity pattern、layer count 和 duplicate rate；Efficiency Ratio 应替换或补充真实设备 latency/memory。
- TacEvo 是 scalar fitness + QD descriptors，不是 Pareto NAS；本仓库仍需在相同候选、训练、GPU 和 LLM budget 下报告 hypervolume、validity、duplication 和 seed variance。
- `quality_proxy` 与 `latency_proxy_ms` 只能用于控制流，不能用来复述 TacEvo 的真实高保真结论。

## 最小复现实验

- 固定 4–10 层 Conv1d Transformer、训练 recipe、数据 split、每任务 proposal 数、LLM calls/tokens、GPU-hours 和三组 search seeds。
- 对照 native random mutation、stateless LLM、LLM + scalar archive、LLM + QD network archive、LLM + dual archive。
- Agent 只输出合法 schema action；validator 分开记录 syntax/schema、shape、OOM、divergence、duplicate 和成功率。
- 指标：真实质量、真实 latency/memory、hypervolume、archive coverage、action validity、duplicate rate、best-so-far 和总成本。

## 局限与风险

- 论文实验只覆盖一个 tactile sensor、两个小数据集和一个 CNN seed，不能证明跨任务或 Transformer 泛化。
- 未报告搜索 seed variance、LLM token/费用、GPU/时间总预算和完整高保真训练 recipe。
- prompt archive 当前主要是记录/分析机制；正文算法没有用它来选择下一代 mutation prompts。
- 代码级开放搜索扩大表达力，也扩大安全、重复、隐式 recipe 漂移和复现风险。

## 可引用摘要

TacEvo 将 Claude 3 Haiku 作为代码级 mutation/crossover 算子，并用 CVT MAP-Elites 在结构多样性与计算—结构 descriptor 上维护网络和提示结果档案。作者在两个 ViTacTip 任务的一次搜索中报告较高可训练率和 archive coverage，并在 20-seed 高保真重训中得到与人工 CNN 相当或更好的 top variants。其主要缺口是缺少 matched-budget 搜索基线、搜索 seed variance、硬件与 LLM 成本；Efficiency Ratio 也不是实际部署指标。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2606.30109
- PDF：https://arxiv.org/pdf/2606.30109
- 代码：https://github.com/LannWei/TacEvo
- 已核对：标题、作者、日期、arXiv ID/DOI、搜索空间、双 archive、validation gate、20×50 上限、10 epochs、主要结果与统计检验。
- 未核对：独立运行、dataset 获取/授权、硬件与总成本、完整高保真 recipe、prompt archive 的复现实效。
- [ ] 已由人工决定 `retained` / `discarded`
