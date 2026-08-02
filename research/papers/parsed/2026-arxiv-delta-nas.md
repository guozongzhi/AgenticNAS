---
title: "Delta-Based Neural Architecture Search: LLM Fine-Tuning via Code Diffs"
authors: "Santosh Premi Adhikari, Radu Timofte, Dmitry Ignatov"
year: "2026"
venue: "arXiv:2605.04903v1"
doi: "10.48550/arXiv.2605.04903"
paper_url: "https://arxiv.org/abs/2605.04903"
source_pdf: "https://arxiv.org/pdf/2605.04903"
code_url: "https://github.com/ABrain-One/nn-gpt"
source: "arXiv v1 metadata/PDF, public code repository, model artifacts, and nn-dataset PR, accessed 2026-08-02"
parser: "Codex"
parsed_on: "2026-08-02"
status: codex_draft
tags: [llm-nas, delta-editing, lora, code-generation, cnn, single-epoch-proxy]
---

# Delta-Based Neural Architecture Search: LLM Fine-Tuning via Code Diffs

> 本笔记基于 arXiv v1 的 19 页 PDF、公开代码仓库、模型页和 `nn-dataset` PR。所有实验数字均为作者报告，尚未独立复现。

## 一句话结论

论文不让 LLM 重写完整模型，而是对 LEMUR 中可运行的 CNN 基线生成 unified diff，再以 patch、语法、实例化、forward、单 epoch accuracy 和 MinHash novelty 逐层过滤；它在三种 7B LLM 上缩短输出并提高 patch 成功率，但与 full-generation baseline 的训练语料和数据覆盖并不完全一致，主要质量指标仍是一 epoch代理，且只有一个 search seed。（pp. 3–13, 18–19）

## 书目信息与来源核验

- arXiv ID：2605.04903v1；提交日期：2026-05-06；arXiv DOI：10.48550/arXiv.2605.04903。
- 作者：Santosh Premi Adhikari、Radu Timofte、Dmitry Ignatov；当前可核验 venue 为 arXiv。
- 论文：https://arxiv.org/abs/2605.04903
- 代码：https://github.com/ABrain-One/nn-gpt ；仓库 2026-08-02 可访问，默认分支 `main`，MIT license。
- 架构数据：https://github.com/ABrain-One/nn-dataset/pull/204 ；197 个 `del-<md5>` 候选的 PR 已合并。
- 模型权重：论文列出三种 Delta-NAS LoRA merged 模型的 Hugging Face 页面。
- 置信度：书目信息 high；方法与预算 high；作者报告结果 medium-high；跨语料 baseline 因果归因 medium-low。

## 研究问题与贡献

- 问题：开放代码级 LLM-NAS 若每次生成完整 Python 文件，输出长、冗余且容易产生不可执行代码；能否只生成对现有可运行模型的局部 diff。
- 核心贡献：把动作表示为标准 unified diff；使用 LEMUR 工作模型作为基线；用静态 LEMUR corpus 做逐 cycle LoRA；用 accuracy 与 code-level novelty 控制候选入库。（pp. 1–4）
- 论文比较 DeepSeek-Coder-7B、Qwen2.5-Coder-7B 与 Mistral-7B-Instruct，三者使用相同 22-cycle、每 cycle 50 candidates 的内部协议。（pp. 4–6）

## 方法拆解

### 搜索或优化对象

- 搜索对象是真实 PyTorch 图像分类 CNN 的架构代码，不是 Agent 工作流；每个动作是对一个可运行基线源文件的 unified diff。
- diff 可改变层、通道数、kernel、normalization、activation、regularization 和连接相关代码；论文没有有限的 block/cell/op schema 或 4–10 层约束。（pp. 3–4, 11–12）
- 候选沿用基线在 LEMUR 中的 optimizer、hyperparameters 和 data transforms；LLM 输出的 `<hp>`/`<tr>` 仅是结构化上下文，不进入评估，因此正文实验按作者协议属于 architecture-only NAS。（p. 3）
- 任务覆盖 CIFAR-10、CIFAR-100、MNIST、SVHN、ImageNette、CelebA，未覆盖 Conv1d Transformer。

### Agent 与优化闭环

- 每轮从 LEMUR/扩展 baseline pool 取一个模型，LLM 输出 `<delta>`，本地 patch 工具应用；context mismatch 或格式错误直接失败。（pp. 3–4）
- patch 成功后依次做语法、实例化、forward 与单 epoch 训练；accuracy 至少 40% 才进入 novelty 检查。（pp. 3–4）
- novelty 使用 256 permutations、10-character shingles 的 MinHash-Jaccard；要求相对已有 corpus 的结构不相似度至少 0.90。（pp. 3, 8）
- 合格候选加入后续 baseline sampling pool；正文明确 LoRA 数据始终是静态 LEMUR corpus，而不是把新候选加入 fine-tuning corpus。（pp. 3–4, 8）
- 每 cycle 对同一静态 corpus 做 3 个 LoRA epochs；rank 32、alpha 32、dropout 0.05，sampling temperature 0.35、top-k 50、top-p 0.9、最多 1,024 new tokens。（p. 4）
- 无效动作会消耗 proposal/LLM budget；论文把 patch 成功且完成训练的比例称 valid generation rate，shape/undefined-variable 等语义失败在后续 validator 暴露。（pp. 5, 11–12）

### 评估与预算

- 三种 7B LLM 各 22 cycles × 50 candidates = 1,100 attempted candidates，共 3,300；成功 patch 并单 epoch 训练的候选共 2,354。（pp. 5–6, 13）
- LLM fine-tuning 与视觉模型训练使用 RTX 4090 24GB 集群；每 cycle 约 15–20 分钟 LLM fine-tuning 加 60–90 分钟候选评估。（pp. 18–19）
- 作者估算每个 LLM 的 22 cycles 为约 28–35 GPU-hours，完整三 LLM 研究约 90–100 GPU-hours。（pp. 13, 18–19）
- 固定 global seed 42，未报告独立 search seeds；三种 LLM 是模型对照，不是搜索方差重复。（p. 19）
- full-generation baseline 使用 DeepSeek-Coder-7B、22 cycles、1,100 candidates，但主要 CIFAR-10 corpus/任务覆盖与本方法的六数据集 balanced pool 不同。（pp. 5–6, 12）
- Feedback Memory/iterative baseline 使用 2,000 iterations、三个数据集、冻结 LLM，且 success 定义不同；不构成完全 matched-budget comparison。（pp. 5–6）
- 高保真复核：每种 LLM 的 proxy top-20 尝试训练 50 epochs；基础设施失败后有效 N 为 Mistral 16、Qwen 15、DeepSeek 12。（pp. 13, 18）
- 没有目标设备 latency、peak memory、energy 或 quality/hardware Pareto；输出 token 节省也不等于端到端搜索 wall-time 节省。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| patch 成功率 | DeepSeek 75.3%、Qwen 72.1%、Mistral 66.6% | full generation 50.6% | pp. 5–7, Table 3 | medium |
| CIFAR-10 一 epoch best | 85.2% / 80.6% / 85.5% | full generation 63.98%；iterative 71.5% | pp. 6–7, Table 3 | medium |
| 输出长度 | 30.4 / 31.4 / 49.5 lines，作者估算总 output tokens 约 490K | full generation 约 200+ lines、同规模约 2.64M tokens | pp. 5, 7 | medium-high |
| novelty admission | DeepSeek 88/627、Qwen 51/590、Mistral 68/556 above-threshold candidates | `tau_nov=0.90` | p. 8 | high |
| 一 epoch与 50 epoch 排名 | Spearman rho：Mistral 0.926、Qwen 0.635、DeepSeek 0.495；DeepSeek p=0.10 | 各 LLM proxy top-20 | pp. 13, 18, Table 16 | medium |
| 总计算 | 约 28–35 GPU-hours/LLM，完整研究约 90–100 GPU-hours | RTX 4090 24GB cluster | pp. 18–19 | medium-high |

## 公平性与可信度检查

- DeepSeek 的 22-cycle/1,100-candidate 对照最接近 matched candidate budget，但 baseline 只用 CIFAR-10-specific data，本方法用六数据集 LEMUR corpus；作者也承认 corpus diversity 与 diff format 尚未拆分。（p. 12）
- valid rate 的定义是 patch cleanly 且本实验中完成训练；Feedback Memory 的 success rate 定义不同，不能直接横比。（pp. 5–6）
- best accuracy 对样本数敏感：full-generation 有 1,100 个 CIFAR-10 candidates，而每个 delta LLM 只有 112–135 个 CIFAR-10 trained models；这不是同分布的 best-of-N 对照。（pp. 6, 12）
- 所有 headline accuracy 都是一 epoch validation proxy。50-epoch 相关性为重要补充，但只选 top candidates、存在基础设施排除、数据集分布不平衡，且 DeepSeek 不显著。（pp. 13, 18）
- 单 seed 无法估计搜索方差；Table 3 的 `±SD` 是 22 个 cycle means 的波动，不是独立 search runs 的方差或均值置信区间。（pp. 5–6）
- 论文的约 5.4× 是 output-token 估算，不包括 LoRA fine-tuning、input tokens、失败重试或视觉模型训练，不能当作端到端成本加速。

## 可复现性与代码/数据

- 论文提供 LLM/LoRA/sampling 配置、候选数、seed、software versions、600 秒 subprocess timeout、GPU 和 wall-clock 估算。（pp. 18–19）
- `nn-gpt` 公开仓库包含脚本、prompts、evaluator 和 JSON configs；三种模型权重公开；197 个 novelty-admitted CV models 已并入 `nn-dataset`。
- 论文未引用冻结 commit/tag；公开仓库仍在更新。复现前应锁定 commit、模型 revision、LEMUR snapshot 和数据 split。
- 未给逐 candidate 的统一 input/output token、失败重试与 LLM fine-tuning token 总账；作者的 token comparison 主要由平均行数换算。

## 与 AgenticNAS 的关系

- unified diff 证明“局部动作”比完整代码输出更短，但本仓库应进一步收窄为 declarative `MutationAction`，由本地 builder 生成变更，而不是让 LLM 接触任意内部源码。
- 可复用分层 validator：schema/patch、构造、shape、训练、objective；所有失败都计入 attempted candidates 和 LLM budget。
- 需要 `full-generation vs diff vs typed-action` 三组对照，并固定相同 baseline corpus、数据集、candidate/training/GPU/LLM budget 与至少三组 search seeds。
- novelty 应基于架构 canonical form/graph hash，而不是 code shingle，避免格式变化被误当结构创新。
- 单 epoch accuracy 只能作低保真筛选；top-k 必须相同完整训练，硬件目标必须来自真实 latency、peak memory 和成本测量。
- `quality_proxy` 与 `latency_proxy_ms` 继续只作控制流占位符，不能用本论文 proxy 或输出长度替代研究结论。

## 最小复现实验

- 固定 4–10 层 Conv1d Transformer、训练 recipe、数据 split、200 attempted candidates、同一 LLM 与三组 search seeds。
- 对照 full architecture generation、unified diff、typed `block/cell/op/connectivity` action 和 native random mutation。
- 所有组统一 input/output token cap、LLM calls、validation timeout、训练 steps 和 GPU-hours；失败与 duplicate 仍计预算。
- top-k 用统一完整训练；报告 best-so-far、validity、duplicate、结构 edit distance、hypervolume、seed variance、LLM/GPU cost 和真实设备 latency/memory。

## 局限与风险

- 只覆盖 LEMUR 图像 CNN，不能证明向 Conv1d Transformer 或受限声明式空间泛化。
- richer corpus 与 diff format 混杂，尚不能把全部提升归因于 action representation。
- 只有一个 search seed，且一 epoch proxy 对 DeepSeek top set 的秩相关不显著。
- code-level MinHash 可能把语法差异当结构差异，也可能漏掉语义等价重复。
- 没有真实设备多目标结果；token savings 不是 latency/memory/energy Pareto 证据。

## 可引用摘要

Delta-Based NAS 让三个 7B LLM 对 LEMUR 中的可运行 CNN 生成 unified diff，并以 patch、执行、单 epoch accuracy 和 MinHash novelty 过滤候选。作者在每个 LLM 1,100 candidates 的设置下报告比完整代码生成更高的 patch 成功率和更短输出，并对部分 top candidates 做 50-epoch 秩相关检查。结论仍受训练语料/数据覆盖不匹配、单 search seed、一 epoch proxy 和缺少真实硬件目标限制。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2605.04903
- PDF：https://arxiv.org/pdf/2605.04903
- 代码：https://github.com/ABrain-One/nn-gpt
- 数据 PR：https://github.com/ABrain-One/nn-dataset/pull/204
- 已核对：标题、作者、日期、arXiv ID/DOI、diff loop、LoRA 配置、候选/数据/GPU预算、主要表格、proxy validation、代码与模型入口。
- 未核对：独立运行、冻结 artifact、多 search seeds、逐候选 token/log 和真实设备指标。
- [ ] 已由人工决定 `retained` / `discarded`
