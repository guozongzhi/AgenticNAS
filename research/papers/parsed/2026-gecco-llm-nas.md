---
title: "LLM-NAS: LLM-driven Hardware-Aware Neural Architecture Search"
authors: "Hengyi Zhu, Grace Li Zhang, Shaoyi Huang"
year: "2026"
venue: "GECCO 2026; arXiv:2510.01472v4"
doi: "10.48550/arXiv.2510.01472"
paper_url: "https://arxiv.org/abs/2510.01472"
venue_url: "https://sigevo.hosting.acm.org/gecco-2026/Accepted%2BPosters"
code_url: "not reported"
source: "arXiv v4 HTML/PDF and official GECCO accepted-papers list, accessed 2026-07-29"
parser: "Codex"
parsed_on: "2026-07-29"
status: codex_draft
tags: [llm-nas, hardware-aware, pareto, hypervolume, zero-cost]
---

# LLM-NAS

> 此工作早期 OpenReview 标题为 “PEL-NAS”，当前 arXiv v4 标题为 “LLM-NAS”。本笔记按 arXiv ID `2510.01472` 去重，并以当前标题和 GECCO 2026 官方录用信息为准。

## 一句话结论

LLM-NAS 把离散 NAS 空间按复杂度分成多个 niches，让 GPT-4.1 在每个 niche 中基于 Pareto parents 和累积规则做 mutation/crossover，再用准确率预测器与硬件 latency lookup 更新 Pareto archive；这是本仓库当前最直接的“Agent memory + 真实架构 + quality/latency + HV/IGD”对照，但其主要 accuracy 与 latency 来自 benchmark predictor/lookup，并非每个候选现场训练和测量。（§3–4）

## 书目信息与来源核验

- arXiv ID：2510.01472v4；首次提交 2025-10-01，v4 更新 2025-12-04；arXiv DOI：10.48550/arXiv.2510.01472。
- 作者：Hengyi Zhu、Grace Li Zhang、Shaoyi Huang。
- venue：GECCO 2026；由 GECCO 官方 accepted papers/posters 页面和 TU Darmstadt 作者组 publication page 交叉确认。
- 题名演化：OpenReview withdrawn ICLR 2026 submission 使用 PEL-NAS 长标题；arXiv v4 和 GECCO 使用 LLM-NAS。二者不是两篇论文。
- 论文：https://arxiv.org/abs/2510.01472
- 代码：论文、arXiv metadata 和可核验作者页面未提供实现链接。
- 置信度：书目信息/venue high；方法 high；实验结论 medium；独立复现 low-medium。

## 研究问题与贡献

- 问题：LLM 在大规模 HW-NAS 空间中倾向产生熟悉结构，难以覆盖不同 latency 区域；静态 prompt 也无法积累前几代的经验。
- 方法：以架构复杂度划分互斥 niches，在每个 niche 内维护 Pareto archive；LLM 每代先更新规则库，再基于规则和 Pareto parents 生成新候选。
- 训练自由评估：accuracy 用 13 个 zero-cost proxies 训练的 XGBoost predictor，latency 由 HW-NAS-Bench lookup 提供。

## 方法拆解

### 搜索或优化对象

- HW-NAS-Bench：15,625 个真实 cell 架构，操作包括 `nor_conv_3x3`、`nor_conv_1x1`、pool、skip 和 none；按 3×3 conv 数量分成 6 个 niches。
- ViT 扩展：基于 AutoFormer 空间搜索 embed dimension、depth、MLP ratio、QKV dimension 和 head count；按 embed dimension 与 depth 分区。
- 目标：预测 accuracy 最大化、device latency 最小化；最终以非支配排序聚合 Pareto front。
- 搜索对象是神经网络架构，不是 Agent 工作流；但主 CNN 实验受固定 cell/op 空间限制，不是开放代码级搜索。

### Agent 与优化闭环

- Stage 1：LLM 读取上一代候选、accuracy、latency、rationale 和 niche constraint，更新正/负设计规则库。
- Stage 2：输入当前 Pareto parents、规则库和 niche 约束；LLM 选择 crossover 或 mutation，并输出 JSON-like `architecture_code` 与 rationale。
- validator 检查新颖性、合法性和 niche 约束；合法候选由 predictor/lookup 评估，再更新各 niche Pareto archive。
- 10 generations、6 niches、120 次 GPT-4.1 API calls；crossover probability 0.5。算法正文未完整给出每次 call 的 child 数、token/费用和随机 seed 数。

### 评估与预算

- 数据：CIFAR-10、CIFAR-100、ImageNet16-120；设备：Jetson TX2、Raspberry Pi 4、Edge TPU、Pixel 3、Eyeriss、FPGA。
- accuracy predictor：XGBoost ensemble 输入 13 个 zero-cost proxies，作者报告与 ground truth 的 Spearman 约 0.90。
- latency：HW-NAS-Bench 预计算 lookup；因此是公开 benchmark 的设备数据，不是本次搜索逐候选现场测速。
- ViT/ImageNet-1k：accuracy 来自 ViT-Bench-101 Auto-Proxy predictor；latency 在单张 NVIDIA A6000 上直接 profile。
- 搜索成本：作者报告每 dataset/device 约 3 分钟、120 API calls；未计入 predictor 的离线训练、LLM token/费用和 benchmark 数据生成成本。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| Pareto front 质量 | 3 数据集×6 设备均报告更高 HV、更低 IGD | LLMatic、FairNAS、PRP-NAS | §4.2, Table 3 | medium |
| 低延迟候选 | Edge GPU 1.78 ms；FPGA 1.65 ms，后者比 PRP-NAS-BL 低约 54% | PRP-NAS-BL | §4.2, Table 2 | high |
| 关键消融 | Full HV 0.978±0.017；无 partition 为 0.516±0.155 | partition/LLM/ZC ablations | §4.3, Table 5 | medium |
| 调用预算 | 10 generations，120 GPT-4.1 calls，作者报告约 3 分钟 | GPU-days 基线表 | §4.1–4.2, Table 4 | high |
| ViT 扩展 | Base 82.5% predicted top-1、5.4 ms、20.2M params | AutoFormer 83.4%、8.4 ms、23M | §4.4, Table 6 | low-medium |

## 公平性与可信度检查

- HW-NAS-Bench 提供完整 15,625 空间的 ground-truth accuracy/latency，因此可计算 true Pareto front、HV 和 IGD；但搜索期间 accuracy 使用 predictor，需复算 predictor training split 是否泄漏测试候选。
- LLMatic、FairNAS、DARTS、PRP-NAS 的“GPU days”与本方法“3 minutes API calls”未包含同样的离线资产成本；不能直接解释为端到端同预算速度提升。
- LLM-NAS 与 LLMatic 的候选、LLM、训练方式不同；只按最终 front 比较，未严格统一 LLM token 或候选评估数。
- Table 2 的 latency 是 benchmark lookup；ViT 的 accuracy 也是 predictor 输出。除非完整训练/实测，否则不能把这些数字当作新硬件部署结论。
- 主文未明确多随机种子协议、GPT-4.1 token/费用、invalid/duplicate rate 或公开 traces。

## 可复现性与代码/数据

- 论文给出 algorithm、完整 prompt skeleton、niche 规则、10-generation 配置和主要表格。
- HW-NAS-Bench 与 NAS-Bench-Suite-Zero 是公开资产；但作者实现、predictor checkpoint、API logs、seeds 和 Pareto traces 未链接。
- GECCO 2026 录用已核验；ACM DOI 尚未从可访问的一手页面确认，因此只记录 arXiv DOI。

## 与 AgenticNAS 的关系

- 可复用“复杂度分区 + 每区 Pareto archive”：4–10 层 Conv1d Transformer 可按 layer count、width、kernel、memory tier 或真实 latency band 分层，防止 LLM 只生成中等规模候选。
- 规则库可对应 memory-aware policy，但 memory 应只存公开 schema、已评估结果、错误码和可审计摘要，不暴露内部端点、日志或私有架构细节。
- 当前仓库可直接沿用 HV/IGD、action validity、duplicate rate 和 seed variance；同时必须把 predictor/lookup 结果标为 surrogate，而非真实测量。
- LLM-NAS 生成离散架构 code；本仓库应让 Agent 输出 `MutationAction`，由 validator 和 evaluator 决定真实模型构造。

## 最小复现实验

- 将 4–10 层空间分成 layer-count 或真实 latency niches；每个 niche 独立保持 Pareto archive。
- 对照 global random、global stateless LLM、partition-only evolution、partition + memory-aware LLM。
- 固定每 niche 候选数、总训练 steps、GPU 时间、LLM calls/tokens、seeds 和设备；统一实测 quality/latency/memory。
- 报告全局/分区 hypervolume、IGD、覆盖率、validity、duplicate rate、规则库命中率和总成本。

## 局限与风险

- complexity partition 依赖人工选取 3×3 conv count；作者也把自动分区列为未来工作。
- predictor/lookup 可大幅降低搜索成本，但也可能放大 surrogate ranking error；ViT 结果尤其没有完整训练 accuracy。
- 未公开代码、predictor split、trace 和 token 账，难以验证 3 分钟、120 calls 的端到端含义。
- 只优化 accuracy/latency，没有 memory、energy、LLM monetary cost 或部署稳定性。

## 可引用摘要

LLM-NAS 将硬件感知搜索空间按复杂度分区，在每个 niche 中维护 Pareto archive，并让 LLM 根据历史 accuracy/latency 和设计 rationale 更新规则、生成 mutation/crossover。作者在 HW-NAS-Bench 上报告更高 HV、更低 IGD 和低延迟候选，并由 GECCO 2026 录用；但搜索依赖 accuracy predictor 与 latency lookup，未公开完整实现、trace、随机种子和 LLM token 成本。因此它最适合作为“分区覆盖 + memory-aware Pareto policy”的研究对照，而不是已完成的真实硬件端到端复现。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2510.01472
- 正文：https://arxiv.org/html/2510.01472v4
- GECCO：https://sigevo.hosting.acm.org/gecco-2026/Accepted%2BPosters
- 已核对：当前标题、作者、版本日期、arXiv ID/DOI、GECCO venue、搜索空间、10 generations、120 API calls、主要 HV/IGD/latency 表和 prompts。
- 未核对：ACM DOI、官方代码、predictor split/checkpoint、token/费用、独立复现。
- [ ] 已由人工决定 `retained` / `discarded`
