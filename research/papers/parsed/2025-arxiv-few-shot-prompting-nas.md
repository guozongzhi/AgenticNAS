---
title: "Enhancing LLM-Based Neural Network Generation: Few-Shot Prompting and Efficient Validation for Automated Architecture Design"
authors: "Raghuvir Duvvuri, Chandini Vysyaraju, Avi Goyal, Dmitry Ignatov, Radu Timofte"
year: "2025"
venue: "arXiv:2512.24120v2"
doi: "10.48550/arXiv.2512.24120"
paper_url: "https://arxiv.org/abs/2512.24120"
source_pdf: "https://arxiv.org/pdf/2512.24120"
code_url: "https://github.com/ABrain-One/NN-GPT"
data_url: "https://github.com/ABrain-One/NN-Dataset"
source: "arXiv v2 PDF and public NN-GPT/NN-Dataset repositories, accessed 2026-09-11"
parser: "Codex"
parsed_on: "2026-09-11"
status: codex_draft
tags: [llm-nas, code-generation, few-shot, prompt-ablation, cnn, one-epoch-proxy, deduplication]
---

# Enhancing LLM-Based Neural Network Generation

> 本笔记基于 arXiv v2 的 14 页 PDF与公开仓库快照。所有结果均为作者报告，尚未独立运行。论文研究的是一次性 architecture generation 的 prompt-example-count 消融，而不是带性能反馈的多轮 Agent 搜索；headline 只基于 1-epoch validation proxy。

## 一句话结论

该工作在 NNGPT/LEMUR 上固定 DeepSeek Coder 7B 与单轮训练协议，把 prompt 中 supporting architectures 数量从 n=1 扫到 n=6；作者在 n=1..5 的 1,900 个训练候选中报告 n=3 的六数据集 balanced mean 最高，但主要显著正结果仅是 CIFAR-100 的 26.1% 对 14.5%，同时 n=1 与 n=3 样本量为 1,268 对 103、没有多重比较校正、完整 GPU/LLM 成本或多 epoch 复核。因此最可靠的启示是“prompt 例子数会同时改变有效率与早期 proxy，必须与 attempted/valid/trained 预算联报”，而不是通用的 n=3 最优法则。（pp. 3–8, 14）

## 书目信息与来源核验

- arXiv ID：2512.24120v2；v1 提交于 2025-12-30，v2 更新于 2026-04-16；arXiv DOI：10.48550/arXiv.2512.24120。
- 作者：Raghuvir Duvvuri、Chandini Vysyaraju、Avi Goyal、Dmitry Ignatov、Radu Timofte；当前可核验 venue 为 arXiv。
- PDF：https://arxiv.org/pdf/2512.24120 ；14 页；本次读取副本 SHA-256：`c6625e7768718b650c69ef7ffbe20812b3aee0514224ecff76c2f7030914e961`。
- 论文指向 NN-GPT 与 NN-Dataset/LEMUR。2026-09-11 审计时：NN-GPT HEAD 为 `904437058a274f3d25840017094789af58ee2590`，NN-Dataset HEAD 为 `fc9c0e3681d5fe84d15bc3ffc579e9de122b4b8f`；NN-Dataset 中可检索到 `alt-nn1` 至 `alt-nn4` 等产物。
- 论文没有冻结用于实验的 commit/tag。当前 NN-GPT 的 supporting-model 代码仍存在，但现有 `ds_7B.py` 使用 DeepSeek-R1-Distill-Qwen-7B、temperature 0.8，而论文写 DeepSeek Coder 7B、temperature 0.6；当前树也未检索到论文所述 whitespace-normalized MD5 实现，说明 HEAD 不能直接视为 paper artifact。
- 置信度：书目信息 high；表格与 prompt high；统计归因 medium-low；代码可获得性 medium；paper-exact reproducibility low。

## 研究问题与贡献

- RQ1：supporting example 数 n 如何影响生成有效率与 1-epoch validation 表现。（pp. 1–3）
- RQ2：多例 prompt 是否产生单例 prompt 未见的组合式结构模式。（pp. 1–3, 6–7）
- RQ3：去空白后做 MD5 hash 能否在训练前快速拦截格式重复。（pp. 2–4, 7–8）
- 方法不是迭代 Agent loop：从 LEMUR 取一个 reference 与 n 个 supporting models，单次生成完整 PyTorch `Net`，通过去重后训练 1 epoch并写回数据集。（pp. 3–5, Algorithm 1）

## 方法拆解

### 搜索或优化对象

- 搜索对象是真实 PyTorch 图像分类网络代码；prompt 要求完整 `Net`，允许组合 residual、DPN、AlexNet 等模块与 channel/depth/topology。（pp. 3–4, 6, 12–14）
- supporting pool 来自目标数据集上已有高表现 LEMUR 架构；选择一个 reference，再从剩余候选随机抽 n 个 supporting examples，并附带 accuracy。（pp. 3–4, Algorithm 1）
- 训练接口固定要求 `supported_hyperparameters() -> ['lr', 'momentum']`；正文称所有 prompt variants 使用相同 1-epoch SGD+momentum protocol。主实验因此更接近 architecture-only prompt ablation，而不是联合 HPO。（pp. 4–5, 11–12）
- 没有封闭的 op 候选表、depth/width 上限或参数/显存硬约束；输出是开放 PyTorch code，不是固定 cell/block 枚举空间。
- 论文只覆盖 Conv2d 视觉网络，没有 Conv1d 或明确 4–10 层 Transformer。

### Agent 与优化闭环

- 输入：task/dataset spec、一个带 accuracy 的 main/reference architecture、n 个带 code/accuracy 的 supporting architectures、格式和接口约束。（pp. 4, 11–12）
- 动作：LoRA fine-tuned DeepSeek Coder 7B 一次性生成完整 PyTorch code；temperature 0.6、top-k 50、top-p 0.95、max tokens 65,536。（p. 3）
- 没有观察新候选性能后再提案的循环、memory/reflection、Pareto archive 或 acquisition function；本研究把 prompt 中例子数本身作为自变量。
- hash gate 去除所有 whitespace 后做 MD5，并查询 LEMUR；只识别这种规范化后完全相同的文本，不处理 AST/graph/semantic equivalence。（pp. 4, 7–8, Algorithm 2）
- n=6 报告 3,394 次 query 中只有 7 个 valid model；说明 context 增大同时改变 proposal validity 与有效训练预算。（p. 6）

### 评估与预算

- 定量表覆盖 MNIST、CelebA-Gender、CIFAR-10、CIFAR-100、ImageNette、SVHN；Places365 因每 epoch 约 180 分钟被排除出性能表，只用于 hash 规模验证。（pp. 4–5）
- 每个可接受候选训练 1 epoch，SGD+momentum，batch size 按数据集为 64–4096，使用“advanced” augmentation；主要指标为第一 epoch validation Top-1。（p. 5）
- Table 1 的 n=1..5 候选数分别为 1,268、306、103、102、121，恰好合计 1,900；n=6 的 7 个 valid 候选没有进入该表。（p. 6）
- 论文另称 hash 在 4,033 个 generated architectures 上测量、约 5% 被过滤，同时称 n=6 有 3,394 queries；attempted、parse-valid、hash-unique、trained 的总账没有被一张表完整对齐。（pp. 4–8）
- 未报告 generation/fine-tuning GPU 型号、总 GPU-hours、wall time、LLM input/output tokens、search seeds、sampling seeds 或完整失败分类。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| n=3 balanced mean 最高 | n=3 53.1%，n=1 51.5%；两者 95% CI 重叠 | 同模型/协议的 n=1 | p. 6, Table 1 | medium for observed proxy; low for general rule |
| CIFAR-100 正向差异 | n=3 26.1% vs n=1 14.5%，+11.6 points，p=0.001，d=0.73 | n=1 | p. 14, Tables 3–4 | medium |
| 其他数据不支持统一 n=3 | CelebA 最佳为 n=2；CIFAR-10/ImageNette 最佳为 n=1；SVHN 最佳为 n=2 | n=1..5 | p. 14, Table 3 | high |
| n=6 validity collapse | 7 valid / 3,394 queries，即 99.8% failure | n=1..5 | p. 6 | medium; accounting incomplete |
| prompt 产生结构组合 | 展示 ResNet-AlexNet、DPN 与 hierarchical residual 例子 | 代表性 n=1 code | pp. 6–7, 12–14 | low-medium; qualitative selection |
| hash 延迟 | <1 ms；声称比 AST 10–100 ms 快 100× | 文献/实现对照 | pp. 7–8, Table 2 | low-medium |

## 公平性与可信度检查

- 优点：base LLM、LoRA、temperature 和训练协议在 n 组间按正文保持一致，主要自变量清晰。
- 关键不平衡：n=1 有 1,268 个训练样本，n=3 仅 103；Welch test 处理方差/样本量不等，但不能修复不同 prompt 组有效率导致的选择机制差异，也不能把每个生成架构自动当成独立 search seed。
- 论文对多个数据集与多个 n 做显著性检验，没有说明 family-wise/FDR 多重比较校正；只展示 p<0.05 的 Table 4 也有选择性报告风险。
- “n=3 最优”只在跨六数据集 macro mean 和 CIFAR-100 上得到正向支持；各数据集最优 n 明显不同，不能外推为通用默认。
- 1 epoch accuracy 是低保真代理；论文承认没有 multi-epoch 验证。模型早期优化动力学可能改变排序，尤其不同归一化/残差/宽度架构。
- supporting examples 来自同一 LEMUR 数据库并附 accuracy；若生成候选与 reference corpus 存在结构重复或近重复，简单 hash 不能排除 AST/graph/semantic leakage。
- “zero false positives”只是在作者生成集上的声明；去除全部 whitespace 对 Python indentation 与字符串内容并非一般语义保持，且论文没有人工标注 protocol 或置信区间。
- 论文称每个被过滤 duplicate 节省 2–3 GPU-hours，但主训练只 1 epoch且数据集耗时差异很大；没有硬件/计时分解，不能把该数字作为通用节省。

## 可复现性与代码/数据

- NN-GPT 与 NN-Dataset 公开，论文提供完整 prompt 模板、两段算法、generation hyperparameters 和代表性代码，这是相对强的 artifact 基础。
- NN-Dataset 当前 HEAD 可检索到大量 `alt-nn*` training-stat paths；但仓库规模大、持续更新，论文未冻结 commit，也未提供把 1,900 candidates/3,394 n=6 queries/4,033 hash samples 一一对齐的 manifest。
- 当前 NN-GPT HEAD 的 supporting-model path 与 prompt 存在，但默认模型/temperature 已与论文漂移，论文所述 hash 实现没有在当前树的代码搜索中定位到；需向作者索取 paper commit或从历史定位。
- 未公开或未明确：LLM fine-tune checkpoint hash、fine-tuning GPU/time、generation seeds、每组 query manifest、完整 parse/compile/OOM failure taxonomy 和 multi-epoch checkpoints。

## 与 AgenticNAS 的关系

- 可复用设计：把 prompt example count 当作 proposal-policy 超参，并同时记录 attempted、parse-valid、dedup-unique、trained 候选数；不能只按成功候选比较 accuracy。
- n=6 的 collapse 是“上下文丰富度与 action validity”冲突的直接案例，适合在 typed block/cell/op action 上做同预算 validity ablation。
- whitespace hash 可作便宜的第一层 exact-format canonicalization，但必须保留 AST/graph signature 作为第二层；Python 中不可盲目删去所有 whitespace。
- 这不是 Agent feedback loop，也没有 Pareto/设备约束；不能用来证明多轮 Agent、硬件感知或质量/延迟/内存/成本的联合优化。
- 当前研究若聚焦 4–10 层 Conv1d Transformer，应固定同一 typed search space、reference pool、训练 proxy 和 total generation attempts，再扫 n；本文的 Conv2d early-epoch 数字不可迁移。
- `quality_proxy` 与 `latency_proxy_ms` 只能继续作为流程占位符；本文只提供 1-epoch accuracy，未测 latency/memory/cost Pareto。
- clean-room 复现只使用公开 LEMUR/NN-GPT 或自建公开 reference corpus；不接触内部 Archai、私有端点、内部日志或私有架构。

## 最小复现实验

- 在公开 4–10 层 Conv1d Transformer typed space 固定 100 attempted generations/组，比较 n=0、1、3、6；相同 LLM checkpoint、temperature、seed 列表与 context token cap。
- 记录 JSON/schema-valid、build-valid、unique-graph、trained 数，并以 intention-to-generate 和 conditional-on-valid 两种口径报告。
- 固定 1-epoch proxy 后，从每组按 validation 选定相同数量候选做完整训练，测 proxy-to-full Spearman/Kendall 与 best-so-far。
- 对照 raw hash、token-normalized hash、AST/typed-graph signature；人工抽样核对 false positive/false negative，而不是只报延迟。
- 至少 5 个独立 generation/search seeds；报告 LLM calls/tokens、GPU-hours、wall time、peak memory和失败类型。

## 局限与风险

- 单 epoch、样本量严重不均、缺多重比较校正与缺独立 seed 层级，使 n=3 因果结论弱于 headline。
- 结果来自开放 Conv2d code generation；缺封闭搜索空间与复杂度约束，结构多样性不等于可部署性或 Pareto 改善。
- artifact 持续漂移，当前代码默认值不能直接复现实验。
- hash 只覆盖格式近重复且对 Python whitespace 有语义风险；没有 semantic equivalence。
- LLM 与训练总成本未报告，无法核验“resource-efficient”或与传统 NAS 的等预算关系。

## 可引用摘要

Duvvuri 等在 NNGPT/LEMUR 上控制 prompt 中 supporting architectures 数 n，并以 1-epoch validation accuracy 比较 1,900 个生成的 PyTorch 视觉网络。作者报告 n=3 的六数据集 balanced mean 最高、CIFAR-100 相对 n=1 提升 11.6 points，同时 n=6 的生成有效率几乎崩溃；但 n=1 与 n=3 样本量为 1,268 对 103，其他数据集的最优 n 不一致，且没有 multi-epoch、完整成本或多重比较校正，因此该结果更适合作为 prompt/context validity 消融，而不是通用 NAS 性能结论。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2512.24120
- PDF：https://arxiv.org/pdf/2512.24120
- Code：https://github.com/ABrain-One/NN-GPT
- Data：https://github.com/ABrain-One/NN-Dataset
- 已核对：标题、作者、arXiv history、prompt、n 扫描、模型/LoRA/generation 参数、1-epoch protocol、候选数、Table 1/2/3/4、关键 code examples 与当前仓库 HEAD。
- 未核对：独立运行、paper-exact commit、fine-tuning/generation GPU、总 tokens/cost、seed manifest、完整失败账与 multi-epoch 排序。
- [ ] 已由人工决定 `retained` / `discarded`
