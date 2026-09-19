---
title: "LLM-Driven Composite Neural Architecture Search for Multi-Source RL State Encoding"
authors: "Yu Yu, Qian Xie, Nairen Cao, Li Jin"
year: "2025"
venue: "NeurIPS 2025 LAW Workshop; arXiv:2512.06982v2"
doi: "10.48550/arXiv.2512.06982"
paper_url: "https://arxiv.org/abs/2512.06982"
source_pdf: "https://arxiv.org/pdf/2512.06982"
code_url: "not found"
source: "arXiv v2 metadata/PDF, OpenReview, and author publication page, accessed 2026-09-19"
parser: "Codex"
parsed_on: "2026-09-19"
status: codex_draft
tags: [llm-nas, composite-architecture, transformer, reinforcement-learning, multi-source, feedback]
---

# LLM-Driven Composite Neural Architecture Search for Multi-Source RL State Encoding

> 本笔记基于 arXiv v2 的 15 页 PDF、OpenReview 论文页和作者主页。所有实验结论均为作者报告；本次未发现作者公开代码、冻结配置或完整搜索轨迹。

## 一句话结论

LACER 让 LLM 在约束的多模块空间中迭代选择真实状态编码器结构，并把任务指标、RL reward 与中间表示信息共同反馈给下一轮；在交通控制任务的 50-candidate、8-seed 比较中，论文图示的 LACER 曲线高于专家设计、三种传统 NAS 和 GENIUS，但主实验先用同一任务选择了更强的 Claude Sonnet 4.0/temperature 1.0，而 GENIUS 使用 GPT-4，且论文没有给显著性检验、完整 LLM 成本或可运行代码。（PDF pp. 3–5, 9–15）

## 书目信息与来源核验

- arXiv ID：`2512.06982v2`；v1 提交于 2025-12-07，v2 修订于 2025-12-11；arXiv DOI：`10.48550/arXiv.2512.06982`。
- 作者：Yu Yu、Qian Xie、Nairen Cao、Li Jin。
- Venue：arXiv Comments 与作者主页均标为 NeurIPS 2025 Workshop on Bridging Language, Agent, and World Models for Reasoning and Planning（LAW）；不能写成 NeurIPS 主会论文。
- 一手来源：[arXiv](https://arxiv.org/abs/2512.06982)、[PDF](https://arxiv.org/pdf/2512.06982)、[OpenReview](https://openreview.net/forum?id=cjeisJBijK)、[作者主页](https://qianjanexie.github.io/)。
- 本次读取 PDF SHA-256：`016c3a8cdf0327ded3a976aed7bf0a64afb3c1389f357a1b1a5fe4c512cfaf8e`；15 页。
- 代码/数据：arXiv、OpenReview、作者主页与 GitHub repository title search 均未发现作者代码；未发现公开搜索日志、prompt、checkpoint 或交通仿真配置快照。
- 置信度：书目信息 high；搜索空间与预算 high；结果曲线 medium-high；公平性与可复现性 medium-low。

## 研究问题与贡献

- 问题：多源 RL 需要为传感器、时间序列、图像或文本分别设计编码模块，再由 fusion 模块组合；候选必须经过昂贵的 RL 训练，传统单模块 NAS 不能直接利用每个中间表示的质量信号。（pp. 1–3）
- 方法：以专家架构为初始点，LLM 根据历史候选与反馈生成单个或批量结构；每个候选与固定 PPO policy 端到端训练，评估后把 task metric、average reward、mutual information/redundancy 等 feature information 回填。（pp. 3–4, 8–9）
- 实证：主文只对 mixed-autonomy traffic control 给出完整搜索比较；附录还定义 MiniGrid 与 ManiSkill 的复合搜索空间，但没有同等完整的结果表，因此不能把它们写成已验证结论。（pp. 4–5, 12–14）

## 方法拆解

### 搜索或优化对象

- 搜索对象是真实 composite state encoder，而不是 Agent 工作流：traffic/time/sequence 三个输入模块与 fusion 模块的结构字段共同变化；RL policy、PPO 训练流程和环境固定。（pp. 3–4）
- 交通任务中，time 与 sequence encoder 为 `MHSA + FFN`，各搜索 heads `{2,4,8}`、dimension `{8,16,32}`、ratio `{1,2,4}`、depth `{1,2,3}`；traffic 与 fusion 为 FFN，各搜索 activation `{relu,gelu,swish}`、dimension、ratio、depth。（p. 9, Table 1）
- 论文称总空间约 2600 万；按 Table 1 的直接 Cartesian product 是 `81^4 = 43,046,721`。正文未说明把空间缩到约 2600 万的额外合法性约束，复现前需作者澄清。（p. 9）
- MiniGrid 的 image encoder 搜索 CNN op/channel/pooling/depth 2–5，text encoder 搜索 embedding/GRU/dropout/depth 1–4，fusion 搜索 merge type/width/activation；ManiSkill 仅给结构示意，主实验未形成同等证据。（pp. 12–14）
- 它没有 Conv1d，也没有 4–10 层单体 Transformer；交通任务的单模块 depth 仅 1–3，不能直接支撑本仓库目标搜索空间。
- 目标是平均车速；reward 与 feature information 是反馈信号，不是独立 Pareto objectives。没有真实 latency、peak memory、energy 或货币成本约束。

### Agent 与优化闭环

- 输入：task description、typed search space、expert initial architecture/score、完整对话历史，以及历轮候选的 task metric、average reward 和表示互信息/冗余。（pp. 3, 8）
- 动作：LLM 输出一个或一批模块配置；正则和 pattern matching 抽取 heads、dimension、ratio、depth 等字段并实例化网络。（pp. 3, 10–11）
- 评估：候选与 PPO agent 端到端训练，固定 RL policy architecture，只替换 state encoder；结果写回下一轮 prompt。（pp. 3–5）
- 论文没有给 schema validation、越界值修复、重复候选、解析失败或训练崩溃的完整处理与计数。Algorithm 2 返回 raw values，没有展示 hard validity gate。（p. 11）
- 模型选择实验比较 Claude Sonnet 4.0/GPT-4 与 temperature 0/1，随后以同任务表现最好的 Claude Sonnet 4.0、temperature 1.0 作为主实验配置。（p. 11, Fig. 9）

### 评估与预算

- 主任务：SUMO mixed-autonomy traffic control，CAV penetration ratio 0.9；输入为 temporal traffic evolution、current traffic state 与 vehicle-sequence history。（pp. 4–5）
- 每个候选 PPO 训练 200k interaction steps，再评估 50k steps；每种方法总计 50 candidates。LACER-5/传统 batch NAS 各 10 轮，LACER-1/GENIUS 各 50 轮。（p. 5）
- 每个配置 8 random seeds；误差条为 `2 × standard error`。（pp. 5, 9）
- 硬件：单张 Quadro RTX 8000 48GB 或 Tesla V100 32GB，16 CPU cores、32GB RAM。时间消融另在 Intel Core i7 + RTX 4070 上运行。（pp. 9, 15）
- Baselines：expert architecture、DARTS、ENAS、PEPNAS、GENIUS。DARTS/ENAS/PEPNAS 从视觉 NAS 映射到 RL 的实现细节不足；GENIUS 明确使用 GPT-4，与主实验的 Claude Sonnet 4.0 不同。（pp. 4, 9–10）
- 未报告 tokens、每轮 LLM calls、API 费用、总 GPU-hours、失败候选或各方法 wall time 的数值表。Fig. 14 只给相对组成，称 LLM query 约占 LACER 总时间 1%，evaluation 对各法超过 97%。（p. 15）

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 50-candidate 主结果 | Fig. 2 末端 LACER-5 约 5.08、LACER-1 约 5.07 average speed；高于图中 GENIUS/传统 NAS | Expert、DARTS、ENAS、PEPNAS、GENIUS | p. 5, Fig. 2（读图近似） | medium-high |
| 早期 sample efficiency | LACER-1 在约 5–10 candidates 达到约 5.04–5.06，随后保持高位 | 同上 | p. 5, Fig. 2 | medium |
| richer feedback 消融 | 去掉 feature information、再去掉 reward、再去掉 initial evaluation 后曲线依次退化 | LACER-1 prompt ablations | p. 14, Fig. 13 | medium |
| LLM/temperature 影响 | 四种组合中 Claude Sonnet 4.0、temperature 1.0 曲线最好，被用于主实验 | GPT-4/Claude × temperature 0/1 | p. 11, Fig. 9 | medium |
| 时间构成 | 作者图示 LLM query 约 1%，候选 evaluation 对全部方法超过 97% | traditional/LLM NAS | p. 15, Fig. 14 | medium-low |

## 公平性与可信度检查

- 候选数、候选 RL 步数与 8 seeds 基本匹配，是论文最强的公平性设计。
- GENIUS 用 GPT-4，而 LACER 先在目标任务上挑出 Claude Sonnet 4.0/temperature 1.0；缺少同一 base LLM/temperature 的 LACER-vs-GENIUS 对照，不能把差距全部归因于反馈设计。
- “significantly outperform”只由带标准误的曲线支撑；正文没有 p-value、置信区间差异检验或逐 seed 原始值。
- DARTS/ENAS/PEPNAS 的 RL 映射没有公开代码和充分算法细节；尤其将视觉任务的梯度/样本数概念映射到 average speed/interaction steps 后，未证明它们仍是强实现。
- 50 candidates 相同不等于总成本完全相同：LLM calls、失败提议、prompt 构建与传统搜索开销未统一计量。
- prompt ablation 是嵌套移除，不能单独识别 reward、feature information 与 initial evaluation 的独立效应。

## 可复现性与代码/数据

- 没有公开代码、environment snapshot、完整 prompts/responses、候选 manifests、逐 seed 结果或 LLM token/cost logs。
- SUMO、PPO 和硬件类别已给出，但版本、traffic scenario、训练超参、解析失败处理与模型 API 版本不足以 paper-exact 复现。
- Claude Sonnet 4.0 与 GPT-4 是服务型模型；未记录确切 API snapshot，后续行为可能漂移。
- 本次 PDF 与渲染页只存在于临时目录，没有提交到仓库。

## 与 AgenticNAS 的关系

- 可复用点是“typed composite modules + richer intermediate feedback”：对多分支 Conv1d/Transformer 可分别记录每个 block 的合法性、表示质量与最终 validation 质量，再由 LLM 提议组合结构。
- 不能直接迁移其平均车速提升到分类/时序任务，也不能把 mutual information/redundancy 当作质量因果解释。
- 最值得验证的是，在同一 base LLM、相同 attempted/evaluated candidate budget 与相同 GPU-hours 下，feature-level feedback 是否比只给 validation metric 提高 Pareto hypervolume。
- `quality_proxy` 与 `latency_proxy_ms` 仍只能作为流程占位符；本文没有真实设备延迟、内存或能耗证据。
- clean-room：只能复用公开 typed fields、算法思想与公开结果，不能引入内部 Archai、内部端点、日志或私有架构细节。

## 最小复现实验

- 固定一个公开多输入时序任务、typed 结构空间、训练 recipe 和 validation/test split；每法 50 evaluated candidates、至少 8 search seeds。
- 同一 LLM/temperature 比较 metric-only、metric+training dynamics、metric+module feature statistics，以及 random/regularized evolution/TPE。
- 同时报 attempted/valid/unique/evaluated、LLM calls/tokens/费用、GPU-hours、wall time、解析/训练失败和重复率。
- 目标使用 validation quality、真实 latency、peak memory 和总成本的 Pareto/hypervolume；test 只在最终候选上确认一次。

## 局限与风险

- 论文只完整证明单一交通控制环境；MiniGrid/ManiSkill 是扩展空间描述，不是同等完成的实验结论。
- 搜索空间规模与 Table 1 的直接乘积不一致；无公开实现可解释差异。
- LLM 选择、baseline LLM 不一致和嵌套消融削弱因果归因。
- 缺代码、模型快照、失败记账与完整成本；无法独立确认结果曲线。
- 单目标平均车速不是 Pareto/hardware-aware 证据。

## 可引用摘要

LACER 将多源 RL 状态编码器表示为多个 source-specific module 与 fusion module 的组合搜索空间，并用 LLM 在候选训练后吸收 task metric、average reward 与中间表示信息。作者在交通控制任务上以每法 50 candidates、8 seeds 报告优于专家、传统 NAS 和 GENIUS 的曲线。由于主实验使用了预先选择的 Claude Sonnet 4.0，而 GENIUS 使用 GPT-4，且论文没有公开代码、完整显著性检验或 LLM/GPU 成本，该结果更适合作为“中间反馈可能提升复合 NAS”的待复现假设。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2512.06982
- PDF：https://arxiv.org/pdf/2512.06982
- OpenReview：https://openreview.net/forum?id=cjeisJBijK
- 作者页：https://qianjanexie.github.io/
- 已核对：标题、作者、日期、workshop、arXiv ID/DOI、搜索对象、Table 1、Agent loop、50-candidate/8-seed 预算、硬件、主要图、消融与代码缺失。
- 未核对：独立运行、原始逐 seed 数据、完整 prompt/response、API snapshot、总 GPU/LLM 成本、Table 1 空间规模差异。
- [ ] 已由人工决定 `retained` / `discarded`
