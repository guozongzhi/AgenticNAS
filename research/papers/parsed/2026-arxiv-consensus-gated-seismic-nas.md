---
title: "Consensus-gated Multi-Agent Neural Architecture Search for Seismic Fault Segmentation"
authors: "Shehram Baig, Ahmad Mustafa"
year: "2026"
venue: "arXiv:2608.13889v1"
doi: "10.48550/arXiv.2608.13889"
paper_url: "https://arxiv.org/abs/2608.13889"
source_pdf: "https://arxiv.org/pdf/2608.13889"
source: "arXiv v1 metadata/PDF, accessed 2026-09-09"
parser: "Codex"
parsed_on: "2026-09-09"
status: codex_draft
tags: [llm-nas, multi-agent, code-generation, seismic-segmentation, parameter-budget, test-feedback]
---

# Consensus-gated Multi-Agent Neural Architecture Search for Seismic Fault Segmentation

> 本笔记基于 arXiv v1 的 5 页 PDF。论文在搜索期间直接用完整 test volume 评分并反馈，因此最终 test F1 不能视为独立、无偏的泛化估计；所有结果当前仅作探索性 workflow 证据。

## 一句话结论

论文让 Claude、GPT-5.1 与 Gemini 2.5 Pro 对每个真实 PyTorch 架构 mutation 达成一致后再编码、交叉审查、验证和训练，并用 450K 参数硬约束把最终搜索压到 8 个已训练候选、101 次 LLM 调用和约一个 GPU-day；但候选选择反复读取完整 test volume，且没有单 LLM、随机或经典 NAS 的 matched-budget 搜索对照，所以既不能把 F1 0.578 当作干净测试成绩，也不能隔离多模型 debate 的因果贡献。（pp. 1–4）

## 书目信息与来源核验

- arXiv ID：2608.13889v1；提交时间：2026-08-14 02:41:37 UTC；arXiv DOI：10.48550/arXiv.2608.13889。
- 作者：Shehram Baig、Ahmad Mustafa；当前可核验 venue 为 arXiv，PDF 页眉为 IEEE Geoscience and Remote Sensing Letters 稿件格式，但未见正式发表信息。
- PDF：https://arxiv.org/pdf/2608.13889 ；5 页；本次读取副本 SHA-256：`c86e883bedf46f019f6ce5fe4f04ec28cf121b3fcb4fecb0fa956c42c02fa60e`。
- 代码/数据：论文未给代码仓库；Thebe 数据集是公开来源，但本文裁剪、split、Agent transcripts、完整候选源码与训练 logs 未随论文链接发布。
- 置信度：书目信息 high；workflow 与成本 high；最终架构描述 medium-high；泛化性能 low；多 Agent 因果贡献 low。

## 研究问题与贡献

- 问题：地震断层分割标签少、正类约 5.6%、输入大且 batch size 1；通用视觉/医学分割架构可能过大，而经典 NAS 又依赖人工搜索空间和大量训练。（pp. 1–2）
- 方法：三个异构 frontier LLM 独立提案、相互点名批评并一致投票；胜出模型写完整 `network.py`，其余模型审查接口、空间尺寸、batch-1 与 timeout 风险。（pp. 1–2）
- Orchestrator 先做 AST、实例化、三种输入尺寸的 forward/backward、空间保持与 450K 参数检查，再训练合法候选；失败机制进入 hard ban list。（p. 2）
- 最终给出一个 425,177 参数的 StripPool-UNet+FPN，并完整报告 LLM calls/tokens 与近似 GPU 时间。（pp. 1, 3–4）

## 方法拆解

### 搜索或优化对象

- 搜索对象是可执行 PyTorch segmentation architecture source code；每轮只对当前 parent 做一个开放式结构 mutation，不是搜索 Agent 工作流。（pp. 1–2）
- 没有预定义 op menu；mutation 实际涉及 encoder/decoder widths、depthwise/full-rank convolutions、ASPP/strip pooling、SE gating、FPN fusion、coordinate priors、non-local attention、kernel size 与 skip/fusion routing。（pp. 2–3）
- 固定项：Adam `1e-3`、batch size 1、weighted CE + reconstruction MSE、GroupNorm、无 augmentation/scheduler/early stop，以及双输出 head contract。（p. 3）
- 参数量上限 450K 是硬约束；搜索 objective 为 proxy test F1 并附“比每个 baseline 更少参数”的目标。没有 latency、memory、energy 或严格 Pareto archive。（pp. 2–4）

### Agent 与优化闭环

- Claude、GPT-5.1、Gemini 2.5 Pro 各自输出 design delta、topology、机制、预估参数、与 ban list 的区别和风险。（p. 2）
- 最多 4 轮 debate；三者必须全部 approve 且 endorse 同一 spec。死锁最多重启 6 次；仍无一致时本轮不训练。胜出者写完整实现，另两者最多审查/修订 2 轮。（pp. 2–3）
- 每轮 prompt 包含完整 JSON history、当前 parent source、ban list、历史教训、baseline scoreboard 与双轴目标。候选 F1 不胜 parent 就 revert，并把核心机制加入 ban list。（p. 2）
- 最多 15 个 mutation runs；当最近 3 个完成 run 都超过 baseline 且 running-best mean F1 改进小于 0.01 时停止。本次在 run 9 停止，run 6 因 provider transport failure 中止。（pp. 2–4）

### 评估与预算

- 数据为 Thebe 训练/测试两个不相交 volume，各裁出 100 张 `600×1500` vertical sections；约 5.6% fault pixels。（p. 2）
- 搜索 proxy：每候选只训练 5 张固定训练 sections，但每次在完整 test volume 上评分；`3 trials × 5 fresh-weight cycles × 300 epochs`，每个 trial 取五次 restart 中最佳，再以三个 trial 的 mean 决定 keep/revert。（p. 3）
- 每候选约 2.3 GPU-hours；八个候选训练、一个 debate 传输失败，总体约一个 GPU-day，硬件为单台 Apple M-series laptop 的 MPS FP32。（pp. 3–4）
- LLM 成本：101 calls；1,148,853 input / 388,377 output tokens，其中 Claude 519K/151K、Gemini 330K/180K、GPT 300K/57K；论文称按当时价格为数十美元。（pp. 1, 4）
- 最终 benchmark 对所有架构使用 100 张训练 sections、60 epochs、相同 loss/optimizer，并在同一 test volume 上评估。（pp. 3–4）

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 搜索范围与成功率 | 9 个 mutation runs 中 8 个训练；2 keep、6 revert；1 个 provider failure | 单 lineage，无算法搜索对照 | pp. 3–4, Table I/Fig. 3 | high |
| 成本对账 | 101 calls；1.149M input/0.388M output tokens；约一 GPU-day | 无 matched-budget baseline | pp. 1, 4 | high |
| Proxy winner | run 3 mean F1 0.5176，baseline 0.4923；425,177 params | 1.49M reference baseline | pp. 3–4, Table I | medium |
| 最终同训练 recipe 排名 | StripPool-UNet+FPN F1 0.578、IoU 0.406、0.43M params | DeepLabV3-R50 0.516/39.63M；Attention U-Net 0.502/1.83M；U-Net 0.494/1.81M | p. 4, Table II | low-medium |
| 目标选择风险 | 早期 recall-only 搜索把 mean recall 从 0.194 提到 0.594，却保留更差模型、revert 真正最佳 F1 架构 | 后验全指标重算 | p. 3 | medium |

## 公平性与可信度检查

- 最严重问题是搜索期间每个候选都在完整 test volume 上评分，完整 history 又回馈给 LLM；这使 test 成为 optimization set。即使 final benchmark 给所有模型相同训练 recipe，winner 已针对该 test volume 选择，F1 0.578 仍有选择偏差。（pp. 2–4）
- 只有一条 search trajectory。候选内有 3 trials 和 5 restarts，但这不能替代多个独立 search seeds；hard ban 与 greedy single-lineage 会强化路径依赖。
- 没有单 LLM proposer、majority vote、无 debate、random mutation、regularized evolution 或其他经典 NAS 的相同 8-candidate/101-call/GPU-day对照，无法判断一致门控是否优于更便宜的策略。
- Baselines 只在 final architecture training 表中出现，不是搜索效率对照；论文把“经典 NAS 通常训练数百/数千候选”与本次 8 个候选并列，不能视为 matched-budget 优势。
- 每个 trial 取五个重启中的最佳会估计“优化成功时”性能，而非典型训练性能；虽然 keep/revert 再用三个 trial mean，仍保留 best-of-five 选择。
- 参数量是唯一硬件/资源约束；Apple MPS GPU-hours 不等于目标设备 latency、peak memory 或 energy。

## 可复现性与代码/数据

- 论文提供搜索 loop、验证约束、固定训练 recipe、每轮 mutation、per-trial 结果、token 用量和最终架构模块描述，成本透明度优于多数 LLM-NAS 稿件。
- 未提供代码 URL、冻结 commit、environment、完整 prompts/transcripts、八个候选源码、seeds 或 Thebe crop/split manifest；无法核验 exact implementation 与数据泄漏范围之外的执行细节。
- 使用三个商业模型，版本随服务漂移；除名称外未报告 temperature、max tokens、provider snapshot 或 retry policy。
- PDF 本地读取成功，但未把 reading copy 提交到仓库。

## 与 AgenticNAS 的关系

- 可复用设计是“先讨论 spec、后编码、再机械验证”：异构 proposer 只交换 typed architecture deltas，由本地 builder 和 shape/parameter validator 生成候选。
- 不应直接复用全量源码或内部日志作为 prompt；clean-room 接口只保留公开 schema、候选结果、typed errors、预算与公开论文机制。
- hard ban list 可转成带作用域和失效原因的短期 memory，但要设置过期/复验，避免单次噪声永久屏蔽有效机制。
- 本论文不支持 Conv1d Transformer、4–10 层、真实 latency/memory 或多目标 Pareto 结论；参数量更小也不能推导更低延迟。
- `quality_proxy` 和 `latency_proxy_ms` 仍只能作流程占位符，不能引用本文 test-feedback proxy 作为研究结果。

## 最小复现实验

- 将原始 test volume 分成独立 validation/test；所有 Agent feedback、keep/revert 与 stopping 只使用 validation，test 只在最终锁定后评一次。
- 固定 8 个 evaluated candidates、101 次总 LLM calls、相同训练 steps 与五个 search seeds；对照 random typed mutation、单 LLM、三 LLM majority、三 LLM unanimous 和 deterministic critic。
- 把开放 source edit 收窄为 `block/cell/op/connectivity` typed actions；分别记录 debate reject、schema、shape、parameter、OOM、timeout、training divergence 与 duplicate。
- 同时报告 validation/test gap、best-so-far/hypervolume、真实 latency、peak memory、energy、LLM 费用和 GPU-hours；若连续三 seed 无优势则停止扩展 debate。

## 局限与风险

- 搜索用完整 test feedback，直接破坏 held-out test 解释，是当前最关键风险。
- 单任务、单数据集、单 search trajectory、极小的 8-candidate budget，外推范围有限。
- 没有多 Agent 结构消融或 matched-budget 搜索 baseline，不能归因于 debate/consensus。
- 无公开代码、prompt 与 logs；商业模型版本和成本可能漂移。
- 单一参数约束不是 latency/memory/energy Pareto；MPS 时间无法替代部署测量。

## 可引用摘要

该工作用 Claude、GPT-5.1 和 Gemini 2.5 Pro 对真实 PyTorch 架构 mutation 做一致投票、编码与交叉审查，并在 450K 参数约束下训练八个候选，报告 101 次 LLM 调用和约一个 GPU-day。其 workflow 显示多模型讨论、机械验证和失败记忆可以把昂贵训练集中到合法候选。然而搜索期间反复使用完整 test volume，且缺少单 LLM、随机和经典 NAS 的 matched-budget 对照，因此最终 F1 只能视为探索性结果，不能证明多 Agent 共识带来无偏泛化收益。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2608.13889
- PDF：https://arxiv.org/pdf/2608.13889
- 已核对：标题、作者、日期、arXiv ID/DOI、三模型 debate、450K validator、8 个候选、训练 recipe、test feedback、per-run 表、最终 baseline 表、token/GPU 成本。
- 未核对：代码、完整 prompts/transcripts、模型 snapshot/temperature、independent search seeds、数据 crop/split manifest、独立运行与真实硬件指标。
- [ ] 已由人工决定 `retained` / `discarded`
