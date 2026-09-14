---
title: "Similarity-Guided Curriculum Fine-Tuning of LLMs for Neural Architecture Synthesis"
authors: "Anujaya Vijayakumar, Radu Timofte, Dmitry Ignatov"
year: "2026"
venue: "arXiv:2607.11591v1"
doi: "10.48550/arXiv.2607.11591"
arxiv_id: "2607.11591v1"
paper_url: "https://arxiv.org/abs/2607.11591"
source_pdf: "https://arxiv.org/pdf/2607.11591"
code_url: ""
source: "arXiv v1 metadata/PDF and matching files in the public NN-GPT repository, accessed 2026-09-14"
parser: "Codex"
parsed_on: "2026-09-14"
status: codex_draft
tags: [llm-nas, mixed-search-space, curriculum, code-generation, minhash, lora, single-epoch-proxy]
---

# Similarity-Guided Curriculum Fine-Tuning of LLMs for Neural Architecture Synthesis

> 本笔记基于 arXiv v1 的 15 页 PDF、关键表格渲染图和公开 NN-GPT 当前快照。arXiv 页面没有给出代码链接；公开仓库中存在与论文同名的 curriculum pipeline和 prompts，但没有 paper tag、完整轨迹或可映射论文的 frozen artifact。

## 一句话结论

该工作用 128-permutation MinHash 对 LEMUR 中的完整网络代码做 7-gram相似度分带，按 high -> medium -> low similarity顺序逐阶段 LoRA fine-tune OlympicCoder-7B，并每 epoch生成 15 个 CNN code候选；但随机顺序在 5 个 step中的 3 个达到相同 peak、1 个更高，Level 3 无 repair时 base model成功率 47%而 curriculum仅 7%，partial repair后两者均为 53%。证据更支持“interface repair和顺序稳定性需要分开控制”，不支持 curriculum提高最佳架构；又因生成同时包含结构、超参与 transform，且使用单 epoch、单 seed和 best-epoch选择，本仓库将其归为 `mixed-search-space`。（pp. 3-14）

## 书目信息与来源核验

- arXiv ID：`2607.11591v1`；提交时间 2026-07-13；当前可核验 venue 为 arXiv。
- 作者：Anujaya Vijayakumar、Radu Timofte、Dmitry Ignatov。
- DOI：[10.48550/arXiv.2607.11591](https://doi.org/10.48550/arXiv.2607.11591)。
- PDF：https://arxiv.org/pdf/2607.11591 ；15 页；本次读取副本 SHA-256：`3fb4adc298fd6da9f57d0d4f6ef8e26a1f47f6ba9eda8550ab1ff47cf8b88225`。
- arXiv页未列代码；公开 NN-GPT 2026-09-14 HEAD `904437058a274f3d25840017094789af58ee2590` 含 matching curriculum pipeline/prompts，但无 paper tag/release。
- 置信度：书目信息 high；PDF Table 2/3/6与限制 high；curriculum因果优势 low；paper-exact复现 medium-low。

## 研究问题与贡献

- 问题：当 LLM 以完整 Python code生成神经网络时，fine-tuning references应如何排序，才能兼顾 evaluator interface合法性与架构多样性。（pp. 1-3）
- 表示：将 normalized source code切成 7-token shingles，以 128-permutation MinHash近似 Jaccard；signature以 512-byte BLOB存 SQLite，查询时通过 UDF即时算相似度。（pp. 3-4）
- curriculum：围绕同一 anchor，按高相似 `[0.95,0.98)`、中相似 `[0.85,0.95)`、低/very-low-near `[0.30,0.85)` 的六个 `(level,k)` steps递进，并把每 step最佳 epoch LoRA adapter累积 merge。（pp. 4-6）
- 主要审计结论：论文自己给出的 2x2 repair ablation和单随机顺序 baseline削弱了“progressive ordering提高 best capability”的解释。（pp. 8, 12-14）

## 方法拆解

### 搜索或优化对象

- 每个 action输出完整可执行 LEMUR CNN code `<nn>`、training hyperparameters `<hp>` 和 data transform `<tr>`；prompt允许最多一个架构想法和一个超参变化。
- 候选可改变 backbone组合、FractalNet结构、卷积块、fusion topology、feature routing和spatial adapter，是真实 neural architecture synthesis，不是 Agent workflow搜索。（pp. 10-12, Fig. 4）
- 同时，公开 prompt要求 `batch/dropout/epoch/lr/momentum/transform`，evaluator使用“LLM-proposed hyperparameters”；训练配方并未固定。因此本索引归入 `mixed-search-space`，不能把 accuracy变化纯归因于 architecture。（pp. 5-6；公开 prompt）
- 没有 Conv1d/Transformer architecture search；OlympicCoder-7B是proposal model，不是被搜索目标。没有显式 4-10 层 typed space或cell/op动作集合。
- MinHash反映代码 token重叠而非语义等价：重命名、boilerplate和training code也会改变相似度，不能直接当架构距离。

### Agent 与优化闭环

- 从 13,023 个 CIFAR-10 LEMUR实现中自动选 anchor `rl-bb-init-9afa16ef`，并按相似度 band检索 `k=2/3/4` references。（pp. 4-5, Table 1）
- 当前模型每 epoch生成 `N=15` 候选；通过 evaluator的候选成为 SFT examples，训练 LoRA；step结束选 `success rate x best accuracy` 最高的 epoch merge入 backbone。（pp. 3, 5-6）
- OlympicCoder-7B以 4-bit NF4加载，LoRA为 bfloat16；每次 merge先反量化到 float16、叠加 adapter、再量化到 NF4。论文估计每 step相对 quantization error约 0.1-0.3%，累积 merge drift是潜在混淆。（p. 5）
- Level 3部分条件使用 rule-based `fix_param_usage`插入缺失 interface函数；这类 repair与 curriculum effect必须分别报告。（pp. 6-8）
- 这不是实时 LLM Agent基于每个候选结果做自然语言反思；更准确地说是阶段式生成-评估-SFT-model-merging闭环。

### 评估与预算

- LLM：OlympicCoder-7B（Qwen2-based, 7B），context 32k；generation temperature 1.0、top-k 50、top-p 0.9、最多 16,384 decoding tokens。（pp. 5-6）
- LoRA：rank/alpha 32、dropout 0.05、attention+MLP projections、paged AdamW 8-bit、lr `1e-6`、batch 1、grad accumulation 4、cosine schedule。（p. 5）
- 硬件：单 NVIDIA RTX 4090 24GB，LLM adaptation与CNN evaluation共用同卡。（p. 5）
- 候选评估：CIFAR-10、`norm_256_flip`、1 epoch、SGD但使用 LLM-proposed hyperparameters、batch最多16、每候选8分钟上限。（p. 6）
- primary curriculum Table 2共 45个记录epochs x 15 = 675 candidate generations；此外还有2x2 ablation、random ordering和SVHN观察。论文没有汇总全部LLM calls/tokens、GPU-hours、wall-time或失败成本。
- 只有一个 curriculum seed（seed 2）；random ordering只跑 seed 42；SVHN是单独 observational condition。（pp. 6, 11-13）

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 高相似 Level 1可生成合法模型 | best SR 60%，mean SR 40%，best accuracy 0.9630，score 0.578 | 无 unmodified同预算 baseline | pp. 6-7, Table 2 | high for trajectory; low for curriculum effect |
| Level 3 curriculum无repair退化 | curriculum best/mean SR 7%/7%，base 47%/26% | base model，同 references，单 seed | p. 8, Table 3 | high |
| repair主导有效率 | repair后 base 与 curriculum best SR都53%，score都0.516 | 2x2 ablation | p. 8, Table 3 | high for observed run |
| random ordering peak大多相当 | 5 steps中3个peak相同，L3 k3 random 0.387 > curriculum 0.322；仅L2 k2 curriculum 0.322 > 0.258 | 同 reference pool/merge流程，单 random seed | pp. 11-13, Table 6 | high for table; low for variance claim |
| random ordering更不稳定 | L2 k2 random某epoch 0/15 valid；mean score 0.142 vs curriculum 0.215 | 单随机顺序 | pp. 12-13 | medium; one trajectory |
| 结构相似度随level下降 | mean anchor Jaccard 0.513 -> 0.236-0.266，valid模型mean accuracy约93.19-94.97% | 同anchor后验分析 | pp. 10-11, Table 4 | medium; code similarity proxy |
| SVHN迁移较差 | base/no repair best SR 27%、best acc 60.45%，CIFAR-10为47%/96.51% | 数据集、anchor family、reference分布均不同 | p. 11, Table 5 | low for cross-dataset causality |

## 公平性与可信度检查

- central ordering claim只有一个 curriculum trajectory和一个 random permutation；不同 seed、不同顺序及 anti-curriculum均未充分覆盖。
- best-epoch在同一 evaluation set上选择，存在 winner's curse；没有 untouched test报告最终架构。
- 8分钟单 epoch proxy偏好快速收敛模型，未校准 proxy-to-full-training rank correlation。
- 2x2显示 interface repair可把 curriculum从7%提到53%，效应大于该条件下 curriculum；但没有报告非平凡repair比例或独立repair-only random generator。
- 没有 matched-budget LEMUR random search、database best、单阶段 no-curriculum fine-tuning或 unmodified OlympicCoder-7B全程 baseline。
- score把SR与best accuracy相乘，混合 proposal validity和winner quality；小样本下不同失败类型不能由单一scalar解释。
- MinHash band包含完整code/hp/transform样式信息，不能证明变化来自神经架构结构本身。
- CIFAR-10是六个数据集中唯一能覆盖完整三band的数据库；SVHN对比同时改变数据集、anchor family和reference distribution。

## 可复现性与代码/数据

- 当前 NN-GPT公开 `GenerationPipeline.py`、六组prompt、MinHash band配置、resume路径和实验结果摘要；README估计完整CIFAR-10 curriculum在单RTX 4090约7天，但这不是论文的完整测量成本。
- arXiv页没有 code URL；当前仓库HEAD晚于论文且无paper tag，无法证明当前代码就是paper-exact snapshot。
- 当前公开prompt确认输出 `<nn>/<hp>/<tr>`并允许一个hyperparameter decision，支持本笔记的mixed-search-space分类。
- 未找到论文所有 epoch tracker、adapter checkpoints、random-ordering seeds/trajectories、SVHN logs或完整LLM/GPU cost manifest；不能只凭README重建所有表格。

## 与 AgenticNAS 的关系

- curriculum可转化为 action difficulty schedule，但距离应基于 typed architecture edit/graph，而非完整source-code MinHash；training code和命名必须从距离计算中剔除。
- 先学习interface再增加结构跨度的思路可用于 block/cell/op；更稳妥的实现是schema validator保证合法性，不依赖LoRA记住boilerplate。
- adapter累积merge会把“顺序”与量化/权重漂移混在一起；应增加不merge replay、adapter composition和from-base per-stage对照。
- NAS实验必须锁死 optimizer/lr/batch/augmentation；HPO实验固定graph；joint组单列，不把mixed结果转移到任一主线。
- 报告 attempted/valid/unique/trained/full-trained、每类failure、LLM calls/tokens、GPU-hours和多seed分布，不只给best epoch。
- `quality_proxy` 与 `latency_proxy_ms`只能作流程占位符；本文不含真实latency、memory、energy或Pareto证据。
- clean-room实现仅复用公开MinHash/typed-graph思想，不导入内部Archai、端点、日志或私有架构。

## 最小复现实验

- 在公开 4-10 层 Conv1d Transformer typed space定义graph edit distance，把difficulty分为1-op、1-block、depth/head拓扑三级；固定training recipe。
- 比较 progressive、random permutation、reverse curriculum、no-curriculum replay、from-base per-stage和schema-only；每组至少5个search seeds。
- 每个stage固定15 proposals x相同epochs；不按同一validation上的best epoch做唯一结论，同时报告all-epoch AUC和最终untouched test。
- 用typed validator替代repair，再单独加入repair ablation；记录invalid原因、重复率和模型merge误差。
- 若评估设备目标，另行测真实latency/peak memory/energy并计算Pareto/HV，不从code similarity或单epoch accuracy推断。

## 局限与风险

- 单模型、单anchor、单主要数据集、单seed；central random-order baseline不完整。
- 生成同时改变架构、超参和transform；MinHash不隔离神经结构。
- best-epoch选择、单epoch/8分钟proxy和小`N=15`扩大选择偏差。
- repair与sequential quantize-merge漂移混淆curriculum效应。
- 缺paper-linked frozen code、完整轨迹、GPU/LLM成本、full training和硬件指标。

## 可引用摘要

Vijayakumar 等用128-permutation MinHash把LEMUR网络代码按与anchor的7-gram Jaccard相似度分带，并以逐阶段LoRA fine-tune与adapter merge生成CIFAR-10架构。单seed结果显示高相似阶段可达60% peak validity，但Level 3无repair时curriculum为7%而base为47%，repair后两者均为53%；一个random ordering又在多数step达到相同或更高peak。因其同时生成架构、超参和transform，且缺多seed、full training和matched quantitative baselines，该工作更适合作为“curriculum、interface validity与merge drift需分离”的证据，而非curriculum提升NAS最优解的结论。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2607.11591
- PDF：https://arxiv.org/pdf/2607.11591
- matching公开仓库：https://github.com/ABrain-One/nn-gpt （审计 commit：`904437058a274f3d25840017094789af58ee2590`；非arXiv明示code link）
- 已核对：标题、作者、日期、arXiv ID/DOI、PDF Table 1-7、MinHash/LoRA/evaluator设置、2x2 repair、random ordering、limitations、当前prompts/pipeline。
- 未核对：独立运行、paper-exact commit、完整epoch/seed/checkpoint artifacts、全部LLM/GPU成本、full-training/test。
- [ ] 已由人工决定 `retained` / `discarded`
