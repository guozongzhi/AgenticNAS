---
title: "LM-Searcher: Cross-domain Neural Architecture Search with LLMs via Unified Numerical Encoding"
authors: "Yuxuan Hu, Jihao Liu, Ke Wang, Jinliang Zheng, Weikang Shi, Manyuan Zhang, Qi Dou, Rui Liu, Aojun Zhou, Hongsheng Li"
year: "2025"
venue: "EMNLP 2025 Main"
doi: "10.18653/v1/2025.emnlp-main.478"
arxiv_id: "2509.05657v3"
paper_url: "https://aclanthology.org/2025.emnlp-main.478/"
source_pdf: "https://arxiv.org/pdf/2509.05657"
code_url: "https://github.com/Ashone3/LM-Searcher"
model_url: "https://huggingface.co/Ashenone3/LM-Searcher"
data_url: "https://huggingface.co/datasets/Ashenone3/LM-Searcher-Trajectory-228K"
source: "ACL Anthology, arXiv v3 PDF, author GitHub and Hugging Face artifacts, accessed 2026-09-12"
parser: "Codex"
parsed_on: "2026-09-12"
status: codex_draft
tags: [llm-nas, ranking, numerical-encoding, cell-search, lora-rank, transformer, cross-domain, one-epoch-proxy]
---

# LM-Searcher

> 本笔记基于 ACL Anthology、arXiv v3 的 14 页 PDF与作者公开 artifact 快照。所有结果均为作者报告，尚未独立训练；公开 GitHub 是带占位 reward 的最小示例，不是论文全部实验流水线。

## 一句话结论

LM-Searcher 把不同领域的离散架构选择编码为数字串 `NCode`，以 228K 条“历史性能 + 候选池 → 最优候选”轨迹全量微调 LLaMA-3.1-8B，并在每轮从 10 个随机候选中选一个真实评估。它覆盖 NAS-Bench cell、DARTS、32 个 LoRA rank、1–6 层 Transformer 与语音 DAG 等真实结构变量；但不同任务的候选/训练预算不统一，传统基线是否完全 matched-budget 未交代，LLM token、训练 GPU-hours、搜索 wall-time 和 latency 设备未报告，因此可复用的核心是统一的 typed-index ranking interface，而不是跨任务 headline 数值。（pp. 1–9, 12–14）

## 书目信息与来源核验

- ACL Anthology：EMNLP 2025 Main，pp. 9408–9421，DOI [10.18653/v1/2025.emnlp-main.478](https://doi.org/10.18653/v1/2025.emnlp-main.478)。
- arXiv：2509.05657v3；v1 提交于 2025-09-06，v3 更新于 2025-09-25；arXiv 页面与 ACL 作者表一致。
- PDF：https://arxiv.org/pdf/2509.05657 ；14 页；本次读取副本 SHA-256：`c1828be6c53afdef0daf2a7ef6a9d7d8fee779af7332e9c959282ca83ba57dec`。
- 作者 GitHub 2026-09-12 HEAD：`557f1e7cde24526f2e65ddb03a05c57a693c0f89`；无 tag，只有 10 个 tracked files。
- Hugging Face 模型和 228K dataset 可访问；API 返回模型 revision `31d41d76dbfeaed6dd8fe2404700882142de6d0f`、数据 revision `31de389cbdc6b175dfb6018628e9b27bf828b4b7`。
- 置信度：书目信息 high；PDF 表格 high；方法/搜索空间 high；matched-budget 公平性 medium-low；paper-exact code reproducibility low。

## 研究问题与贡献

- 问题：能否训练一个无需目标域额外 fine-tuning 的通用 LLM search model，在不同离散架构空间里利用历史性能对候选池排序。（pp. 1–2）
- `NCode`：每一位是某个 typed choice 的索引；例如 NAS-Bench-201 六条 edge 的五类 op 形成六位数字串。（pp. 2, 4）
- 任务重构：不让 LLM自由生成全局最优架构，而是给 history 与 candidate pool，要求选出预测最优的一个。（pp. 2, 4–5）
- 训练数据：对完整空间的 edge 和 option 分别以 50% 概率剪枝得到子空间，每个子空间随机采 100–200 个架构构造排序样本，共 228K 条 optimization trajectories。（pp. 2, 4–5）

## 方法拆解

### 搜索或优化对象

- NAS-Bench-201：六条 DAG edge，每条从 zero、skip、1×1 conv、3×3 conv、3×3 average pool 五个 op 选一，属于 cell/op 搜索。（pp. 2, 4）
- CIFAR-10/ImageNet：DARTS 大空间；CIFAR-10 搜 500 个 unique architectures，ImageNet 从 surrogate benchmark 搜 1K 个。（p. 12）
- SAM segmentation：32 个 LoRA modules，各自 rank 从 `[3, 6, 12, 24]` 选一，组合空间为 `4^32`，文中约写 `10^19`。（p. 6）
- Stable Diffusion：把 UNet LoRA 分为 48 组，各组 rank 从 `[4, 8, 16]` 选一。（pp. 6–7）
- IWSLT'14 De-En：embedding `[512, 640]`、hidden `[1024, 2048, 3072]`、head `[4, 8]`、decoder layers `[1..6]`；这是与当前 4–10 层 Transformer 最接近的结构变量，但只覆盖 1–6 层且不是 Conv1d。（p. 7）
- NAS-Bench-ASR：四节点 DAG，每个节点选择 primary op（linear、不同 kernel/dilation conv 或 zero）及 skip op。（pp. 7–8）

### Agent 与优化闭环

- 训练输入：历史 `NCode-performance` 对与候选 `NCode` 列表；答案是候选中真实性能最高者。（pp. 4–5, Table 1）
- 推理循环：前几轮建立 history；之后每轮编码 history 和 10 个随机候选，LM-Searcher 返回一个候选，真实/代理 evaluator 评估后写回 history。（p. 5；公开 `search.py`）
- 没有多 Agent、自然语言 reflection、Pareto archive 或自由 code mutation；LLM 的核心动作是 typed candidate ranking。
- 公共示例将历史截断到最多 200 条、默认 192 trials，并以前 5 轮 random warm-up；这些值未在正文形成跨任务统一预算。
- `NCode` 依赖每个位置的 option mapping；它统一了接口，但会丢失 kernel、连接和模块语义，跨域能力不能等同于理解同一种架构语义。

### 评估与预算

- LLM SFT：LLaMA-3.1-8B，228K trajectories，1 epoch，论文称 8×40GB 总 320GB GPU memory、lr `1e-5`、warmup ratio 0.1、batch size 8、gradient accumulation 2、mixed precision、ZeRO-2。（p. 5）
- 公开 YAML 为 per-device batch 1、gradient accumulation 2、8 GPU；与正文“batch size 8”的口径没有完全对齐，也没有 frozen training run manifest。
- CIFAR-10：每个候选 10 epochs，搜 500 unique，top 5 再训 200 epochs；ImageNet：搜 1K surrogate candidates，top 1 再训 250 epochs。（p. 12）
- SAM：200 search iterations，每候选 1 epoch proxy，top 1 再训 30 epochs；最终架构训练随机性按五次训练报告 standard error，但不等于五个独立 search seeds。（pp. 6–7）
- Stable Diffusion：每个 search candidate 训练 1,000 iterations，在 11 prompts × 8 images 上评价；搜索轮数未报告。最终测试为每 concept 20 prompts × 50 images。（p. 7）
- Translation：先训练 super-transformer，再采评 3K sub-transformers，并施加 500 ms GPU latency constraint；未写明 GPU、batch、warmup、测量重复数或 latency predictor 误差。（p. 7）
- 未报告：228K 轨迹生成成本、SFT GPU-hours、LLM calls/tokens、各 OOD 任务完整 search wall-time/GPU-hours、统一失败账与 inference latency。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 跨任务 headline | CIFAR-10 error 3.10%；CIFAR-100/ImageNet Top-1 72.96/75.5；Kvasir Sα 92.35；ISIC Jac 77.60；generation CLIP-T/I/DINO 0.668/0.737/0.416；BLEU 34.02；PER 21.44 | Random、regularized evolution 与任务专用方法 | p. 6, Table 2 | high for table; medium-low for unified comparison |
| NAS-Bench-201 | test 94.20/72.96/46.51 on CIFAR-10/100/ImageNet16-120 | GENIUS、LLMatic 与专用 NAS | p. 13, Table 9 | high for reported numbers |
| 训练策略消融 | full 为 94.20/72.96/46.51；无 pruning sampling 为 93.39/70.98/43.98；无 ranking reformulation 为 92.16/69.51/42.53 | 同 LLaMA-3.1-8B 的数据/任务消融 | p. 8, Table 7 | medium-high |
| history-performance mapping 有用 | shuffle 后 test 为 93.87/71.89/46.25，对照 94.20/72.96/46.51 | corruption ablation | p. 8, Table 6 | medium |
| 模型规模趋势 | 1B/3B/8B 在 CIFAR-100 为 72.31/72.60/72.96，ImageNet 为 73.52/73.93/75.5 | 同 pipeline 不同 base size | p. 8, Table 5 | medium |
| OOD segmentation | 搜得架构在 11 个指标中多数优于 Conv-LoRA；五次 final training 报 standard error | BitFit/Adapter/VPT/LST/SAM-Adapter/SSF/LoRA/Conv-LoRA | p. 7, Table 3 | medium |
| 设备约束 Transformer | 3K sub-transformers 中在 500 ms GPU constraint 下选 validation loss 最低者，BLEU 34.02 | random 33.00，evolution 33.45 | pp. 6–7, Table 2 | medium-low; profiling incomplete |

## 公平性与可信度检查

- NAS-Bench-201 报五个独立 runs；但 Table 2 的跨任务随机/进化对照没有逐任务列出完全相同的 proposal、candidate training、supernet、final retraining 与 LLM-pretraining成本。
- CIFAR-10 500-candidate DARTS 搜索与其他论文已发表数字并非统一预算；作者只明确重实现 GENIUS，不能把整张 Table 2 当 matched-budget leaderboard。
- 228K 轨迹来自既有 NAS benchmark/training logs。in-domain 结果验证了在相似 metadata 分布上的搜索，OOD LoRA/translation/audio 才更接近迁移证据。
- Table 6 的 shuffled performance mapping 说明模型使用了 context signal，但不是因果“推理能力”证明；attention correlation 同样只是诊断。
- OOD final architecture 的五次训练衡量 training initialization，不替代多 search seeds；只有一个 search trajectory 时 winner's curse 未量化。
- latency constraint 缺设备与测量协议；没有 energy、peak memory、美元成本或质量/延迟/内存 Pareto。

## 可复现性与代码/数据

- 优点：GitHub、Hugging Face 8B model 和 228K dataset 均公开，且可记录 revision；训练 YAML、DeepSpeed config、template 与 vLLM launch 命令可见。
- GitHub 只有 10 个 tracked files，没有数据构建、NAS-Bench/DARTS/SAM/Stable Diffusion/HAT/ASR evaluator 或完整 experiment manifests，也没有 license 文件/tag。
- `search.py` 的 reward 是 `random.uniform(0, 100)` 占位；`utils.py` 在第五轮后把历史 cell 字符串列表误传给 `generate_random_cell(search_space)`，按当前代码会在 `range(option_number)` 处类型错误。因此示例不能直接复现正文闭环。
- 公开 YAML 的 effective batch 口径与正文不完全一致；模型/数据 revision 可冻结，但论文的端到端 search scripts、seed lists 和 logs 未公开。
- 结论：artifact availability 为 medium-high，paper-exact end-to-end reproducibility 为 low。

## 与 AgenticNAS 的关系

- `NCode` 可映射成 typed 4–10 层 Conv1d Transformer action vector：layer count、block type、kernel/dilation、width、heads、skip，每一位都需保存显式 schema 与版本。
- candidate ranking 比自由 code generation 更容易保证动作合法，也适合作为 random/evolution proposals 的 learned reranker；必须对完全相同的 candidate pool 做盲选比较。
- 论文的 1–6 层 translation space提供邻近证据，但 BLEU/500 ms 数字不能迁移到 4–10 层 Conv1d、不同设备或不同 batch。
- 228K 历史先验的构建成本不能隐去；应分别报告 amortized pretraining/SFT 成本和 per-search marginal cost。
- `quality_proxy` 与 `latency_proxy_ms` 只能作为流程占位符；本论文的 1-epoch accuracy、validation loss 和未指定 GPU latency 不能赋值给本仓库代理结论。
- clean-room 复现只使用公开 NAS benchmark、公开 artifact 与自建公开搜索空间，不接触内部 Archai、模型端点、日志或私有架构。

## 最小复现实验

- 在公开 4–10 层 Conv1d Transformer typed space 预生成相同的 10-candidate pools；比较 LM-Searcher reranker、random choice、regularized evolution score 和轻量 surrogate。
- 每方法固定 200 evaluator calls、相同 5+ search seeds、相同 1-epoch proxy 和 top-k full training；禁止把 SFT dataset 中的目标任务条目泄漏到测试。
- 报告 best-so-far、regret、valid/unique 候选、proxy-to-full Spearman/Kendall、LLM calls/tokens、SFT GPU-hours、search GPU-hours、wall-time、peak memory。
- 在相同 schema 下分别做 numeric-only、semantic typed labels、randomized option mapping 和无 history 消融，验证 `NCode` 的真正贡献。
- 若加设备目标，用真实 target device、固定 batch/warmup/重复次数，报告 latency distribution 与 Pareto/HV，而非未指定 GPU 的单阈值。

## 局限与风险

- 论文承认 metadata availability、专用方法性能差距和 NCode 语义损失；跨域不代表任意开放 code space 可搜索。
- 完整训练/搜索脚本缺失，使候选预算、失败重试、数据划分与基线同预算性无法独立核验。
- 多任务表把不同 evaluator、search space 和最终训练协议并列，不能横向解释为统一倍率优势。
- 预训练轨迹与 benchmark 重叠、单 search trajectory 和 finalist selection 都可能使结果偏乐观。
- latency/内存/成本证据不足，不支持硬件感知 Pareto 结论。

## 可引用摘要

Hu 等提出 LM-Searcher，以数字串 `NCode` 统一表示多类离散架构，并把 NAS 重构为基于历史性能从候选池选优的排序任务；LLaMA-3.1-8B 在 228K 轨迹上微调后被用于 cell、LoRA rank、Transformer 和语音 DAG 搜索。论文在 NAS-Bench-201 和多个 OOD 任务报告了相对随机/进化搜索的改善，但不同任务预算不完整、LLM/SFT 成本未核算，且公开仓库不包含 paper-exact evaluator 与可运行端到端闭环，因此最稳妥的贡献是 typed numerical ranking interface，而非统一的跨域效率结论。

## 检索与人工核验记录

- ACL Anthology：https://aclanthology.org/2025.emnlp-main.478/
- arXiv：https://arxiv.org/abs/2509.05657
- Code：https://github.com/Ashone3/LM-Searcher
- Model：https://huggingface.co/Ashenone3/LM-Searcher
- Data：https://huggingface.co/datasets/Ashenone3/LM-Searcher-Trajectory-228K
- 已核对：标题、作者、venue、DOI、arXiv history、PDF Table 2/3/4/5/6/7/8/9、搜索空间、主要候选/训练预算、GitHub tree、HF revisions 与示例代码。
- 未核对：独立训练、228K 生成流水线、完整 OOD scripts、seed manifests、tokens/GPU-hours、所有基线的 matched-budget 条件。
- [ ] 已由人工决定 `retained` / `discarded`
