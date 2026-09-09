---
title: "ATHENA: Knowledge-guided agentic neural architecture search for AutoFormer-based electronic health record modeling"
authors: "Deyi Li, Qi Xu, Lingyao Li, Tiansheng Wang, Muxuan Liang, Mei Liu"
year: "2026"
venue: "arXiv:2608.21712v2"
doi: "10.48550/arXiv.2608.21712"
paper_url: "https://arxiv.org/abs/2608.21712"
source_pdf: "https://arxiv.org/pdf/2608.21712"
code_url: "https://github.com/GatorAIM/ATHENA"
source: "arXiv v2 metadata/PDF and author code, accessed 2026-09-09"
parser: "Codex"
parsed_on: "2026-09-09"
status: codex_draft
tags: [llm-nas, transformer, multi-agent, knowledge-transfer, weight-sharing, ehr]
---

# ATHENA: Knowledge-guided agentic neural architecture search for AutoFormer-based electronic health record modeling

> 本笔记基于 arXiv v2 的 26 页 PDF 与作者代码仓库。所有结果均为作者报告，尚未独立运行；临床数据受访问限制，当前代码仓库没有论文冻结 tag。

## 一句话结论

ATHENA 在固定的 256 个 Transformer 子网空间中，用检索到的跨医院优胜架构、SHAP 架构效应先验和 Proposal/Critic/Strategy 三类 LLM 角色指导搜索；同一 AutoFormer 超网、五个随机种子和 5/20/30 个候选预算下，它在 12 个站点-任务比较中取得最优平均排名，但论文的搜索成本没有计入构建 4 个源站点知识库的前置评估，也未报告 LLM calls/tokens/费用或真实 latency/memory。（pp. 1, 4–15, 19）

## 书目信息与来源核验

- arXiv ID：2608.21712v2；v1 提交于 2026-08-22，v2 修订于 2026-08-25；arXiv DOI：10.48550/arXiv.2608.21712。
- 作者：Deyi Li、Qi Xu、Lingyao Li、Tiansheng Wang、Muxuan Liang、Mei Liu；当前可核验 venue 为 arXiv，论文标题页标注 preprint submitted to Elsevier。
- PDF：https://arxiv.org/pdf/2608.21712 ；26 页；本次读取副本 SHA-256：`806db276f48a6cfcb2e024452975bd8777cd4fe7c2394515e6cd6d7ff8e7ccfa`。
- 代码：https://github.com/GatorAIM/ATHENA ；本次只读审计 HEAD 为 `f419c3b4fdfc520e1345a8f145bd8a4542d2b148`，无 tag/release。
- 置信度：书目信息 high；方法与表格 high；跨医院泛化 medium；完整成本与独立可复现性 medium-low。

## 研究问题与贡献

- 问题：EHR Transformer 的合适宽度、深度、attention heads 与 MLP ratio 随任务和医院变化；逐候选独立预训练昂贵，已有 LLM-NAS 又通常不复用历史架构证据。（pp. 1–3）
- 方法：每个医院只预训练一个 AutoFormer-style weight-sharing supernet；候选继承对应切片后做下游 fine-tuning。（pp. 4–5）
- 跨医院先验分两层：按 task descriptor 检索源医院 top-K 架构；再用 XGBoost + SHAP 和医院随机截距汇总各结构字段的方向性效应及交互。（pp. 5–6）
- Agentic loop 把提案、批评/修订、实验和 exploration/exploitation 决策分开，并用 target validation 结果更新结构化 archive。（pp. 6–7）

## 方法拆解

### 搜索或优化对象

- 搜索对象是真实 Transformer encoder 子网，结构向量为 `(embed_dim, depth, mlp_ratio, num_heads)`，不是 Agent 工作流。（pp. 4, 7）
- `embed_dim ∈ {32,64,128,256}`；其余三个字段均取 `{1,2,4,8}`，Cartesian space 共 256 个候选。合法性要求 `embed_dim % num_heads = 0` 且参数量不超过 4M。（pp. 4, 7, 19）
- 深度候选包含 4 和 8 层，与本仓库关注的 4–10 层 Transformer 区间直接相交；没有 Conv1d、cell/op 或 attention primitive 级搜索。
- 固定项包括 tokenizer、pre-normalization Transformer 结构、训练 optimizer/schedule/dropout、数据划分和同医院超网。搜索只改变上述四个结构字段，属于 `LLM × NAS`，不是固定架构 HPO。（pp. 4–7, 19）
- 目标是 Accuracy、F1、AUROC、AUPRC 的平均 rank；参数量是硬约束及 Pareto 描述，不含 latency、peak memory、energy 或货币成本 objective。（pp. 4, 12–13）

### Agent 与优化闭环

- 固定 context 包含 target task descriptor、检索到的 5 个源架构和 SHAP-based effect prior；动态状态包含 ordered transcript、validation archive、当前 leader、剩余预算和 exploration/exploitation 指令。（pp. 5–7, 19）
- Proposal Agent 输出结构化 JSON 候选与理由；Critic 检查合法性、重复与先验冲突，最多修订 3 次；确定性 evaluator fine-tune 合法子网并写入 validation archive；LLM Strategy module 决定下一轮探索或利用。（pp. 6–7, 19）
- 参数超限和重复是 hard rejection；违背 effect prior 只是 soft concern。连续 3 轮无合法非重复候选时提前停止，失败轮不消耗 architecture-evaluation budget，但仍消耗 LLM 调用。（pp. 6–7, 19）
- 论文实验声明所有 LLM 方法使用 `anthropic/claude-3.5-haiku`。当前代码默认参数却是 `google/gemini-2.5-flash-lite`，LLM client 示例又出现 `anthropic/claude-haiku-4.5`；没有冻结 tag 时必须显式覆盖模型才能接近论文设置。（p. 19；作者代码 `mas_search.py`/`utils/llm_client.py`）

### 评估与预算

- 数据：OneFlorida+ 四个 source sites、一个 held-out target site，以及外部 MIMIC-IV target；六项任务覆盖三项 binary 与三项 multilabel clinical prediction。（pp. 7–8）
- Source prior 每个 `source-hospital × task` 使用 100 个不同架构；按四站点、六任务计算，前置 metadata 最多涉及 2,400 个架构-任务评估，但论文的 target-search cost 不包含这部分 upfront compute。（pp. 14, 19）
- Target search 最大 30 个已评估架构，并报告 budget 5/20/30；每个方法五个 search seeds。LLM 方法可能因候选饱和提前停止。（pp. 10–13）
- MIMIC-IV 另抽 150 个合法架构，对比超网继承与独立 pretrain+fine-tune 的排名相关；最低 Spearman 是 Readmission AUPRC 的 0.412。（pp. 8–9）
- 单张 NVIDIA L4 上，30 候选的 shared-weight 估算为 OneFlorida+ 90 GPU-min、MIMIC-IV 59 GPU-min；从头评估分别为 960/900 GPU-min。（p. 9）
- 论文未汇总 LLM calls、input/output tokens、API 费用、失败重试成本或 source-prior 总 GPU-hours；代码能记录 `llm_calls` 与 wall clock，但未提供论文实验的完整 traces。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 同超网、budget 5 | ATHENA 12 项平均 rank 1.17，10/12 项第一 | Random、EA、GENIUS、CoLLM-NAS；均用同一超网 | pp. 10–11, Table 5a | high |
| 同超网、budget 30 | ATHENA 平均 rank 1.42，9/12 项第一 | 同上 | pp. 11–12, Table 5c | high |
| 严格等 target compute | ATHENA test AUPRC mean 在 10/12 项最高，9/12 对全部基线显著 | 从头 pretrain+finetune 的四种 baseline；五 seed paired bootstrap | pp. 9–10, Table 4 | medium-high |
| 超网 proxy fidelity | Spearman 0.412–0.958，任务差异明显 | 150 个架构的 independent pretrain+finetune | pp. 8–9, Table 2 | high |
| Weight-sharing 搜索成本 | 30 候选：90 vs 960 GPU-min；59 vs 900 GPU-min | 独立预训练每个候选 | p. 9, Table 3 | high |
| prior 消融 | L1-only 与 cold-start 在若干任务退化；LOTO 有时接近或超过 exact retrieval | ATHENA full / CoLLM-NAS | pp. 13–14, Fig. 6/S4 | medium |

## 公平性与可信度检查

- 搜索策略质量的最干净证据是同一 pretrained supernet、同搜索空间、同 5/20/30 evaluation budget 和五 seeds 的 Table 5；它控制了每候选训练成本。
- 等 compute 表把 baseline 的候选数压到能在同 GPU 预算内完成的数量，EA 在该预算下退化为 initialization/random；该表支持有限算力下的 pipeline 效率，但不能单独证明搜索策略普遍优于充分预算经典 NAS。（pp. 9–10）
- source prior 的 2,400 个 source-hospital-task 架构记录及 SHAP/meta-regression 计算没有计入 target-search cost；只有多次复用时才可能摊销。（pp. 14, 19）
- L1-only、LOTO、cold-start 能隔离 prior 的部分贡献，但没有逐一移除 Proposal/Critic/Strategy 的消融，不能把全部提升归因于“多 Agent”组织方式。
- target test 只在 validation-selected leader 上评估一次；论文与 `mas_search.py` 均显示搜索阶段为 val-only，未发现 test feedback 进入提议 prompt 的证据。
- 论文报告五个 seeds 和 paired bootstrap，但没有完整 LLM calls/tokens、API failures、候选 proposal 数与 prompt sampling 配置；evaluation budget 不是完整 Agent budget。

## 可复现性与代码/数据

- 作者仓库公开超网、prior 构建、multi-agent search、seed 与 cost-audit 字段；代码 HEAD 已记录，但没有 tag/release、容器或论文实验的完整输出 artifacts。
- OneFlorida+ 不公开；MIMIC-IV 需 PhysioNet credential。仓库不附处理后数据或 checkpoints，无法开箱复现表格。
- 当前代码模型默认值与论文 `claude-3.5-haiku` 不一致，且 README 只写论文 under review；复现必须保存 commit、显式模型、prompt/temperature、seeds 和全部 traces。
- 本次 PDF 只在临时目录读取，没有提交到仓库。

## 与 AgenticNAS 的关系

- 两层 prior 可转成 clean-room 的公开架构档案：只传递 task descriptors、typed architecture vectors、公开 validation metrics 与不确定性，不传内部代码、端点或日志。
- 4/8 层、宽度、heads、MLP ratio 是本仓库 Conv1d Transformer 的可直接映射变量；但 ATHENA 不支持 Conv1d、op/cell、真实 latency/memory 或硬件 Pareto。
- 最值得验证的是“结构先验 + 本地 validation”能否在 5–30 候选预算内提高 hypervolume，而不是复用临床结论或 SHAP 因果解释。
- `quality_proxy` 与 `latency_proxy_ms` 仍只能作流程占位符；ATHENA 的 parameter Pareto 不能替代目标设备延迟、显存与能耗测量。

## 最小复现实验

- 固定 4–10 层 Conv1d Transformer、训练 recipe、数据 split 与 30 个 attempted/evaluated candidates；每组至少五个 search seeds。
- 对照 random、regularized evolution、单 LLM、Proposal+Critic、完整 Agent + retrieval prior、完整 Agent + retrieval/effect prior。
- 同时报 attempted proposals、accepted/evaluated candidates、LLM calls/tokens/费用、GPU-hours、失败类型与 prior 构建/摊销成本。
- 目标使用 validation quality、真实 latency、peak memory 与总成本的 Pareto/hypervolume；test 只做最终一次确认。

## 局限与风险

- 作者仅验证两个 target health systems 和六项任务；MIMIC-IV 仍是单一学术中心。（pp. 14–15）
- 搜索空间仅四个结构字段；attention mechanism、temporal representation、prediction head、tokenization 和训练超参均固定。（pp. 14–15）
- 超网排名 fidelity 在部分 binary tasks 较低，尤其 Readmission AUPRC 仅 0.412。（pp. 8–9, 15）
- 未计 source knowledge base upfront cost，也未给完整 LLM 成本；当前代码与论文模型配置漂移。
- 参数量不是部署硬件指标；没有 latency、memory、energy 或端侧实测。

## 可引用摘要

ATHENA 在固定的 256 个 Transformer 子网空间中，将跨医院优胜架构检索、SHAP 架构效应先验与 Proposal/Critic/Strategy LLM 角色结合，并通过共享 AutoFormer 超网评估候选。作者在同超网、五个随机种子和 5/20/30 个候选预算下报告最佳平均排名，并用外部 MIMIC-IV 检验迁移。该结果未计入构建源站点知识库的前置成本，且缺少 LLM calls/tokens/费用、冻结代码版本和真实硬件指标，因此最适合支持“可复用结构先验值得受控复现”，而非完整端到端成本优势。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2608.21712
- PDF：https://arxiv.org/pdf/2608.21712
- 代码：https://github.com/GatorAIM/ATHENA （审计 commit：`f419c3b4fdfc520e1345a8f145bd8a4542d2b148`）
- 已核对：标题、作者、日期、arXiv ID/DOI、搜索空间、Agent loop、数据 split、五 seeds、5/20/30 budgets、L4 时间、主要表格、limitations、代码可用性和模型配置漂移。
- 未核对：独立运行、受限数据与 checkpoints、完整 source prior 成本、LLM tokens/费用、论文实验 traces、目标设备指标。
- [ ] 已由人工决定 `retained` / `discarded`
