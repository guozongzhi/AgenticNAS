---
title: "LLM-Driven AutoML for Cross-Lingual Handwritten OCR: Closed-Loop Neural Architecture Search with GPT-5, GPT-4o, and Claude Sonnet 4"
authors: "Mobina Kashaniyan, Amirhossein Ghassemi, Nasser Mozayani"
year: "2025"
venue: "2025 15th International Conference on Computer and Knowledge Engineering (ICCKE)"
doi: "10.1109/ICCKE68588.2025.11273810"
paper_url: "https://arxiv.org/abs/2607.15509"
source_pdf: "https://arxiv.org/pdf/2607.15509"
source: "IEEE accepted manuscript on arXiv v3 and Crossref DOI metadata, accessed 2026-09-11"
parser: "Codex"
parsed_on: "2026-09-11"
status: codex_draft
tags: [llm-nas, mixed-search-space, closed-loop, code-generation, ocr, cnn, vision-transformer, test-feedback]
---

# LLM-Driven AutoML for Cross-Lingual Handwritten OCR

> 本笔记基于 arXiv v3 的 7 页 IEEE accepted manuscript。所有结果均为作者报告，尚未独立运行；论文未公开代码、prompt、完整 JSON schema、随机种子、训练预算或 GPU 型号。最重要的证据限制是：每轮 test accuracy 被反馈给同一 LLM，用于生成后续候选，因此最终 test 结果不是独立 held-out 评估。

## 一句话结论

该工作让 GPT-5、GPT-4o 与 Claude Sonnet 4 分别生成包含 CNN/可选视觉 Transformer 和训练超参的 Keras JSON 配置，连续 30 轮训练后把 train/validation/test accuracy 回灌给下一轮；作者在三种文字数据集上报告 270 次训练和约 40.6–43.8 ms 的单样本 GPU 延迟，但没有 matched-budget NAS/HPO 基线、完整成本或无 test-feedback 对照，所以证据只能说明“LLM 能产出并训练多种 OCR 网络”，不能支持无泄漏的泛化、收敛或 Pareto 优越性。（pp. 2–6）

## 书目信息与来源核验

- arXiv ID：2607.15509v3；v1 提交于 2026-07-16，v3 更新于 2026-08-18；arXiv DOI：10.48550/arXiv.2607.15509。
- 作者：Mobina Kashaniyan、Amirhossein Ghassemi、Nasser Mozayani。
- accepted manuscript 首页标注 2025 15th ICCKE；Crossref 核验 DOI 为 10.1109/ICCKE68588.2025.11273810，会议日期为 2025-10-28 至 2025-10-29，页码 1–6。
- PDF：https://arxiv.org/pdf/2607.15509 ；7 页；本次读取副本 SHA-256：`8e75c158669989fb137ef5fc2d2f2c2d0cc892d8db48a479d053008485aa4fca`。
- 论文没有代码或数据产物链接；未找到可确认的作者实现。
- 置信度：书目信息 high；表格转录 high；搜索闭环 medium；可复现性 low；泛化与算法比较 low。

## 研究问题与贡献

- 问题：能否让通用 LLM 在不同书写体系上直接提出、训练并迭代改进 OCR 网络，减少人工架构设计与调参。（pp. 1–3）
- 方法：数据集元数据与上一轮指标组成 prompt，LLM 返回结构与训练配置 JSON，Keras parser 构建并训练模型，再把结果反馈到下一轮。（pp. 2–3）
- 搜索覆盖 Conv2D、BatchNorm、pooling、dropout、dense，以及可选 PatchEmbedding/TransformerBlock；同时改变 optimizer、learning rate、batch size、epochs 和 early-stopping patience。（p. 3）
- 因架构和训练字段同时变化，本笔记归类为 `mixed-search-space`，不是固定训练配方的纯 NAS，也不是固定架构的纯 HPO。

## 方法拆解

### 搜索或优化对象

- 候选是真实可训练的 Keras 网络；LLM 输出顺序层 JSON，包含 Conv2D、归一化、池化、dropout、flatten、dense 和可选视觉 Transformer 模块。（pp. 2–3）
- 候选也包含 Adam/SGD、learning rate、batch size、epochs 和 early-stopping patience，故结果混合了结构与训练策略贡献。（p. 3）
- 论文没有给 operator 白名单、每项取值范围、最大深度、参数/显存上限、无效 JSON 处理或搜索空间基数；无法重建同分布空间。
- 视觉 Transformer 以二维 patch/token 处理图像；论文没有 Conv1d，也没有给 4–10 层的离散边界。

### Agent 与优化闭环

- 输入：类别数、图像尺寸，以及上一轮的 training、validation、test accuracy。（pp. 2–3）
- 动作：GPT-5、GPT-4o 或 Claude Sonnet 4 独立返回完整 JSON；parser 自动构建、compile、训练和评估。（pp. 2–3）
- 反馈：同一 LLM 根据前一轮 accuracy 修改 layer type、depth、width 与训练超参；正文没有描述跨多轮记忆压缩、候选 archive、去重或显式 acquisition rule。（p. 3）
- 失败处理：论文只称 JSON 可 deterministic parsing，没有报告语法错误、shape mismatch、OOM、重试或失败候选数。
- 选择逻辑：作者称目标兼顾 accuracy、inference efficiency 与 model complexity，但明确回灌字段只有三种 accuracy；没有标量化公式、Pareto archive 或约束可行性门控。（p. 3）

### 评估与预算

- 数据：EMNIST（English）、SADRI（Persian）、AHCD（Arabic）；使用 stratified split，10% 用作 validation，并用 Keras ImageDataGenerator 做 rotation、horizontal/vertical shift 和 zoom。（p. 3）
- 规模：每个 LLM × 每个 script 30 轮，即 3 × 3 × 30 = 270 次候选训练；论文把这些称为 independent trials，但又说明 trial-by-trial feedback，二者口径冲突。（pp. 3–4）
- 指标：peak train/validation/test accuracy、参数量、单样本 latency；latency 为 batch 1、FP32、NVIDIA GPU、1,000 次 forward pass 的均值。（p. 3）
- 未报告 GPU 型号、warm-up、同步方式、重复批次分布、wall time、GPU-hours、LLM calls/tokens/费用、模型 snapshot、temperature 或 retry。
- test accuracy 在每轮用于后续提案，形成 adaptive test reuse；表中的均值、best trial 与最终架构均不能解释为未参与搜索的 held-out test 结果。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| GPT-5 三脚本均值 | English 0.937、Persian 0.938、Arabic 0.954；0.88–1.35M mean params | 无 matched NAS/HPO baseline | p. 4, Table I(a) | high for transcription; low for causal claim |
| GPT-4o 三脚本均值 | English 0.936、Persian 0.944、Arabic 0.959；1.31–2.74M params | 无 matched baseline | p. 4, Table I(b) | high/low |
| Claude Sonnet 4 三脚本均值 | English 0.931、Persian 0.946、Arabic 0.921；6.76–9.28M params | 无 matched baseline | p. 4, Table I(c) | high/low |
| 单样本 GPU 延迟 | 各组合 mean 40.6–43.8 ms | 三 LLM 间内部比较 | pp. 3–5, Table I/Figs. 2,5,8 | medium-low |
| 最佳单次准确率 | GPT-5 Arabic best 0.981；其余 best 0.944–0.979 | 从各 30 轮中取 best | pp. 4–5 | high for reported value; low for generalization |
| 与既有 OCR 对比 | 表 II 只比较任务、数据和流程属性，没有同数据精度/预算 | GPT-4o 直接识别 Romanian Cyrillic | p. 4, Table II | low |

## 公平性与可信度检查

- 没有 random search、固定手工架构、传统 NAS、单轮 LLM 或 no-feedback 的同空间同训练预算对照，无法隔离 LLM 闭环贡献。
- 三个 LLM 产生的模型参数量差异可达约一个数量级；没有相同参数/FLOPs/训练预算约束，因此 accuracy 横比不是严格公平的搜索器比较。
- “30 independent trials”与连续反馈冲突；如果候选按序依赖前轮，则常规跨 trial 标准差不等于独立 search seeds。
- 将 test accuracy 回灌给下一轮造成选择泄漏；validation closely follows training 也不能证明泛化，尤其 test 已参与自适应决策。
- “no domain-specific preprocessing”与文中“tailored preprocessing/encoding”及各脚本 specialized loader 的描述不完全一致。
- 延迟集中在约 41 ms，但缺 GPU 型号、同步与 warm-up；不能据此推断“depth 主导 latency”，也不能外推到目标设备或 CPU。
- 搜索同时改变架构和训练超参；任何 accuracy 差异都不能单独归因于 neural architecture。
- 没有报告无效 JSON、shape/build/train 失败率、重复架构、LLM serving 成本或总候选成本。

## 可复现性与代码/数据

- 三个数据集公开或可取得，但论文没有代码、prompt、JSON schema、训练脚本、具体 split seed、augmentation 参数、每候选 epoch 上限、GPU 型号或 LLM API snapshot。
- 表格给出候选训练数、聚合准确率、参数量和 latency；不足以重建每轮轨迹或验证 test-feedback 的影响。
- DOI/venue 已由 arXiv accepted manuscript 与 Crossref 交叉核验；实验只依据作者 PDF，未独立运行。

## 与 AgenticNAS 的关系

- 可复用的是 typed JSON → parser/build → train/evaluate → structured feedback 的控制面，以及 CNN/Transformer 可选模块的统一表示。
- 必须把 architecture action 与 optimizer/lr/batch/epoch action 拆成正交实验；否则只能归入 mixed search space。
- 搜索反馈只能来自 validation；test 必须在搜索结束后冻结候选并一次性使用。
- 若要做多目标，需实测 quality、latency、peak memory、energy 与 total cost，保留 non-dominated archive；本文的 accuracy feedback 不是 Pareto evidence。
- 本文不支持 4–10 层 Conv1d Transformer，也不能把图像 OCR 的 40–44 ms GPU 数字外推到当前目标硬件。
- `quality_proxy` 与 `latency_proxy_ms` 只能继续作为流程占位符；本文的 test-leaked accuracy 和未说明 GPU 的 latency 不能为占位值背书。
- clean-room 复现只使用公开数据、公开 API 文档和独立 prompt；不接触内部 Archai、私有模型端点、内部日志或私有架构。

## 最小复现实验

- 固定公开 OCR 数据、固定 split/augmentation/training recipe 和 4–10 层 typed space；test 在搜索完成前不可见。
- 对照 random search、one-shot LLM、LLM + validation feedback、LLM + validation feedback + typed validity gate；每组相同 30 attempted candidates、至少 5 search seeds。
- 分别做 architecture-only、HPO-only 与 joint action，避免把联合变化归因于架构。
- 统计 attempted/JSON-valid/build-valid/trained 数、LLM calls/tokens、GPU-hours、wall time、validation best-so-far 和失败类型。
- 冻结最终候选后测 held-out test accuracy，以及目标设备上的 latency distribution、peak memory 和 energy；报告 Pareto front，而非只报 best trial。

## 局限与风险

- test feedback 是主要有效性威胁；没有独立最终评估集时，headline accuracy 不宜进入算法优越性结论。
- 没有同预算基线、消融、完整成本和失败会计。
- 搜索空间、prompt 和训练 recipe 不完整，作者声称的 reproducibility 暂不可由公开产物验证。
- latency 测量缺硬件与计时细节，且只在 NVIDIA GPU 上；无法代表 MCU、移动端或 CPU。
- 联合搜索使因果归因不清晰；不同 LLM 的参数规模分布也不受控。

## 可引用摘要

Kashaniyan 等让 GPT-5、GPT-4o 与 Claude Sonnet 4 生成包含 CNN/可选视觉 Transformer 结构及训练超参的 Keras JSON，并在 Arabic、Persian、English OCR 上进行连续反馈训练。作者报告 270 个候选训练、93% 以上的多数组合 mean test accuracy 和约 40.6–43.8 ms 的单样本 GPU latency；但每轮 test accuracy 被用于后续提案，且没有 matched-budget baseline、代码、完整搜索空间或成本，因此这些结果不能视为无泄漏的 NAS 泛化或设备 Pareto 证据。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2607.15509
- PDF：https://arxiv.org/pdf/2607.15509
- DOI：https://doi.org/10.1109/ICCKE68588.2025.11273810
- 已核对：标题、作者、arXiv history、IEEE accepted venue/DOI、Crossref 会议元数据、数据集、JSON 字段、feedback loop、候选数、Table I/II 与 latency protocol。
- 未核对：独立运行、代码、prompt/schema、split seed、训练 recipe、GPU 型号、LLM tokens/cost、失败轨迹和独立 test。
- [ ] 已由人工决定 `retained` / `discarded`
