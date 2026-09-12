---
title: "Closed-Loop LLM Discovery of Non-Standard Channel Priors in Vision Models"
authors: "Tolgay Atinc Uzun, Dmitry Ignatov, Radu Timofte"
year: "2026"
venue: "ICPR 2026 / LNCS Pattern Recognition (online 2026, proceedings copyright 2027)"
doi: "10.1007/978-3-032-31920-3_42"
arxiv_id: "2601.08517v2"
paper_url: "https://link.springer.com/chapter/10.1007/978-3-032-31920-3_42"
source_pdf: "https://arxiv.org/pdf/2601.08517"
code_url: "https://github.com/ABrain-One/NN-GPT"
data_url: "https://github.com/ABrain-One/NN-Dataset"
source: "Springer ICPR page, Crossref, arXiv v2 PDF and public NN-GPT/NN-Dataset repositories, accessed 2026-09-12"
parser: "Codex"
parsed_on: "2026-09-12"
status: codex_draft
tags: [llm-nas, mixed-search-space, channel-search, code-generation, ast, feedback-loop, one-epoch-proxy, pareto-posthoc]
---

# Closed-Loop LLM Discovery of Non-Standard Channel Priors in Vision Models

> 本笔记基于 Springer ICPR 页面、Crossref、arXiv v2 的 15 页 PDF和公开仓库快照。headline 是单次 search trajectory 上的单 epoch validation proxy；公开 prompt 同时输出训练超参与 transformer code，因此本文的“channel-only”贡献尚未被 artifact 严格隔离。

## 一句话结论

该工作先以 AST/TorchFX 生成并验证 AlexNet channel variants，再让 OlympicCoder-7B 在 22 轮中根据性能反馈生成 AirNet-like CIFAR-100 候选并逐轮 LoRA fine-tune；220 次生成只有 20 个有效，最佳单 epoch validation accuracy 从 seed population 的 0.250 到 0.311（+6.1 points，+24.1% relative）。由于没有 matched-budget random/evolution/AST-only 基线、多个 search seeds、完整训练或成本账，且公共 prompt 还允许改变 hyperparameters/transform，证据只能支持“闭环在这条代理轨迹中产生了更高候选”，不能支持一般 channel prior、因果 LLM 优势或设备 Pareto。（pp. 4–13）

## 书目信息与来源核验

- arXiv：2601.08517v2；v1 提交于 2026-01-13，v2 更新于 2026-05-04。
- Springer：ICPR 2026 conference paper，First Online 2026-08-03，pp. 627–641；proceedings metadata 的 copyright/publication year 为 2027。
- DOI：[10.1007/978-3-032-31920-3_42](https://doi.org/10.1007/978-3-032-31920-3_42)；Crossref 与 Springer 作者、题名一致。
- PDF：https://arxiv.org/pdf/2601.08517 ；15 页；本次读取副本 SHA-256：`c1ff50609bd6dce84bf3e7654a26204a827981bb79c5a83859d1d8915343a7d0`。
- NN-GPT 2026-09-12 HEAD：`904437058a274f3d25840017094789af58ee2590`；NN-Dataset HEAD：`fc9c0e3681d5fe84d15bc3ffc579e9de122b4b8f`；均无 paper tag。
- 置信度：书目信息 high；220/20 与 proxy结果 high；统计因果解释 low；代码可获得性 medium；paper-exact artifact completeness low。

## 研究问题与贡献

- 问题：LLM 能否在满足 tensor-shape 依赖的条件下，直接通过可执行 PyTorch code 搜索非标准 channel widths，并用新候选性能闭环更新 proposal model。（pp. 1–4）
- 冷启动：用 Python AST + TorchFX 对 seed model 建 mutation groups，同步传播 channel 依赖，做 forward/backward/optimizer-step 检查后加入 LEMUR。（pp. 5–6）
- closed loop：从数据库构造较差 baseline 到较好 addon 的 pair，条件生成更高目标 accuracy 的代码，训练候选、回写数据库、再 fine-tune LLM。（pp. 6–7）
- 解释性分析：作者考察 early/late channel allocation、非 power-of-two 宽度和 accuracy-parameter 后验前沿。（pp. 10–12）

## 方法拆解

### 搜索或优化对象

- 论文定义的主搜索变量：AirNet-based CIFAR-100 skeleton 中所有 convolutional 与 fully-connected layer widths；AST 冷启动的 channel 值范围为 `[4, 1025]`。（pp. 6, 8）
- AST seed 是 AlexNet，生成 1,129 个 verified variants；之后 AST engine 退场，LLM 在开放完整 PyTorch code 上生成 AirNet-like candidates。（pp. 5–6, 10）
- 动作不是封闭 channel vector：公开 training/test prompt要求同时输出 `<hp>` training hyperparameters、`<tr>` transformer code 和 `<nn>` model code；test prompt明确允许选择 batch、transform 以及 model `supported_hyperparameters()`。
- 因此论文叙述是 channel-only，但公开 action contract 未锁死 optimizer/lr/augmentation 等字段；在可审计 artifact 层面保守归为 `mixed-search-space`，直到有 paper manifest 证明这些输出固定。
- 没有 Conv1d、Transformer 或 4–10 层结构搜索；对象是 Conv2d/CIFAR-100。

### Agent 与优化闭环

- 初始 validation corpus：AST parser + source tracer + TorchFX graph 建依赖组，随机修改维度并同步消费者/残差分支；forward、backward、一个 optimizer step 三重验证。（pp. 5–6）
- training pair：同 dataset 中 `m_B` accuracy 高于 `m_A`；二者不要求直接 parent-child，属于 outcome-ranked pseudo-trajectory。（p. 6）
- prompt：给 baseline code、hyperparameters、transform、metric 和 observed accuracy，并给更高 target；输出完整 code/hp/transform。（pp. 6–7；公共 JSON prompt）
- 每轮采 baseline、生成 10 个候选、以单 epoch proxy 训练有效者，把成功/高性能 pair 加入下一轮 LoRA SFT；共 epoch 0–21。（pp. 7–8；公共 tune entry 的 `test_nn=10`）
- 无效候选在训练前被丢弃；论文没有 compiler/self-repair 回路，导致 200/220 的 proposal budget失效。

### 评估与预算

- 数据/模型：CIFAR-100，AirNet-based vision skeleton；每个有效候选 1 epoch，batch 64、AdamW、advanced augmentation，指标是 validation accuracy。（pp. 7–8）
- LLM：OlympicCoder-7B，论文称 context 16,384；LoRA rank 32、alpha 32、dropout 0.05，作用于 q/k/v/o projection，paged AdamW 8-bit、cosine scheduler、lr `1e-6`；temperature 0.8、top-k 70、top-p 0.9。（p. 8）
- 计算设备：NVIDIA RTX 3090/4090 24GB 的 Kubernetes cluster 和 dedicated workstation；没有卡数、总 GPU-hours、wall-time 或 LLM tokens。（p. 7）
- proposal 预算：22 rounds × 10 = 220，valid 20，invalid 200，validity 9.09%。（p. 8）
- 冷启动：论文称 1,129 verified AlexNet variants；当前 NN-Dataset HEAD 只含 1,126 个 `ab/nn/nn/ast-dimension-AlexNet-*.py`，没有 frozen 1,129 manifest。
- 未报告 full-training、独立 test、search seeds、candidate generation seeds、每轮 SFT examples/steps、LLM calls/tokens、完整 failure taxonomy或成本。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| best-so-far 改善 | 0.250 → 0.311 at epoch 19；+0.061 points，+24.1% relative | 初始 AST population best | pp. 8–9, Figs. 3–4 | high for trajectory; low for method advantage |
| proposal validity | 20/220 valid = 9.09%；200 verification failures | 无 repair/constrained decoding | p. 8 | high |
| early vs late valid means | early epochs 0–5：N=9, mean 0.226；late 16–21：N=4, mean 0.273；one-tailed t p=0.0033 | 同一 adaptive trajectory 分段 | p. 10 | medium for arithmetic; low for iid inference |
| permutation test | 100,000 label permutations，gap +0.0474，p=0.0077 | early/late groups | p. 10 | medium for reported test; low for causal claim |
| peak trend | regression slope +0.0019，p=0.083 | epoch maxima | p. 10 | high; not conventionally significant |
| prompt removal | 220 attempts 中 9 executable；5 个漂移到 CelebA，剩余 4 个 CIFAR-100 为 0.0202–0.108 | 去除 task/metric/dataset context 的联合 ablation | p. 11 | medium; components not isolated |
| channel pattern | layer 2/4 与 accuracy correlation -0.47/+0.53；best `[64,99,256,1536]`；40.9% widths 非 power-of-two | 20 个有效候选的后验分析 | p. 11 | low-medium; tiny selected sample |
| post-hoc Pareto | 20 个有效点上画 accuracy vs parameters 前沿 | seed/LLM candidates | p. 12, Fig. 5 | low-medium; no explicit second objective |

## 公平性与可信度检查

- 论文明确承认没有 random search、evolution 或标准 NAS baseline；初始 AST best 也不是与 220 次 LLM proposal matched-budget 的 AST-only controller。
- 只有一个 adaptive trajectory。early/late 候选受不断变化的 fine-tuned model、history 与选择机制影响，不满足简单 t-test/permutation 的 exchangeability/iid 解释；p-value 不能建立 LLM闭环因果优势。
- 20 个 valid 中只用 9 个 early、4 个 late 做分段检验，剩余候选的分组/处理未形成完整独立账目。
- 单 epoch validation proxy没有 full-training rank correlation；0.311 不能写成最终 CIFAR-100 generalization accuracy。
- parameter Pareto 是事后画图，搜索目标只有 accuracy；没有显式 parameter constraint/HV、matched parameter baselines、latency、energy 或 peak memory。
- 非 power-of-two 可能增加真实硬件 kernel inefficiency；“非标准”不是硬件效率证据。
- 公开 prompt允许改变 hp/transform，与正文 standardized recipe/channel-only scope 有冲突；若实际 evaluator没有强制覆盖，accuracy差异不能只归因于 channel widths。

## 可复现性与代码/数据

- NN-GPT 公开了 AST mutator、source tracer、dimension planner、channel prompts 和 OlympicCoder tune entry；NN-Dataset 公开大量 AST variants，优于只有伪代码的工作。
- 当前 tune entry 是 `test_nn=10`、`context_length=8192`，LLM config default 也是 8192；论文写 16,384。没有 paper commit/tag解释该漂移。
- 论文称 1,129 AST variants，当前 HEAD 只有 1,126 个对应 model files；未找到可直接映射论文 20 个 AirNet valid LLM candidates、22-round trajectory、seeds、checkpoints或每轮 metrics 的 manifest。
- 当前 NN-Dataset 仍在快速更新，HEAD 时间晚于论文；文件数量不能替代 paper snapshot。
- 代码/数据存在，但 paper-exact trajectory 和 0.250→0.311 仍不可从公开 artifacts 独立重建。

## 与 AgenticNAS 的关系

- AST/TorchFX dependency grouping 可迁移成 typed validity preprocessor：在 proposal 前同步修复 Conv1d channel/head/residual constraints，而不是接受 90.91% 无效率。
- outcome pair 不必 parent-child，会混淆“哪个 edit 导致改善”；当前 4–10 层空间更适合保存 parent action、child graph、validity reason 和 delta reward。
- 必须把 architecture 与 HPO action contract 分开：architecture-only 固定 optimizer/lr/batch/augmentation；HPO-only 固定 graph；joint 作为第三组。
- one-epoch proxy需要 full-training rank calibration；应报告所有 attempts、valid、unique、trained和selected层级。
- 参数量后验前沿可以作探索图，但设备研究必须测 target hardware latency/memory/energy；`latency_proxy_ms` 与 `quality_proxy` 仍只能是流程占位符。
- clean-room 复现只读取公开 NN-GPT/NN-Dataset 与论文，不接触内部 Archai、端点、日志或私有架构。

## 最小复现实验

- 在公开 4–10 层 Conv1d Transformer typed space 固定 220 proposal calls × 5 seeds；比较 closed-loop LLM、frozen LLM、AST/typed random、regularized evolution和随机候选 + surrogate rerank。
- architecture-only 组强制锁死 training config/augmentation，所有生成输出经 schema + shape + short-train validator；另设 HPO-only/joint 组，禁止混写贡献。
- 每轮保存 parent、action、child、failure reason、tokens、wall-time和 evaluator cost；对无效候选是否消耗预算预先定义。
- 先 1-epoch proxy，再对每组相同 top-k/full-random sample 做完整训练，报告 proxy-to-full correlation 与独立 test。
- 若做多目标，显式优化 validation quality + measured latency + peak memory，固定真实设备并报告 Pareto/HV，不把 post-hoc scatter 当搜索目标。

## 局限与风险

- 一个 dataset、一个 CNN skeleton、一个 search trajectory、20 个 valid samples，外推范围很窄。
- 90.91% 无效率使有效预算选择偏差显著，也使 LLM方案的边际成本高。
- statistical tests 没有处理 adaptive dependence、winner selection 与多轮 fine-tune；显著性弱于标题表达。
- public prompt与正文 scope 不一致，paper artifact不冻结；现有代码不足以重建结果。
- 没有 full-training、test、经典基线或完整 cost；后验参数前沿不是硬件感知 Pareto。

## 可引用摘要

Uzun 等以 AST/TorchFX 生成可执行 channel variants 冷启动 LEMUR，再用 OlympicCoder-7B 在单 epoch CIFAR-100 validation反馈下迭代生成和 fine-tune；作者在 220 次 proposal 中得到 20 个有效候选，best proxy 从 0.250 提升到 0.311。该结果来自单条 adaptive trajectory，缺 matched-budget random/evolution、full-training、多 search seeds 和成本账，且公开 prompt同时生成训练超参与数据变换，因此它更适合作为 validity-first closed-loop 原型，而不是 channel-only LLM优势或设备 Pareto 证据。

## 检索与人工核验记录

- Springer：https://link.springer.com/chapter/10.1007/978-3-032-31920-3_42
- arXiv：https://arxiv.org/abs/2601.08517
- Code：https://github.com/ABrain-One/NN-GPT
- Data：https://github.com/ABrain-One/NN-Dataset
- 已核对：标题、作者、ICPR/DOI、arXiv history、PDF方法/预算/Fig. 3–5、公共 prompts、tune entry、LLM config、AST code与公开 dataset文件计数。
- 未核对：独立运行、paper commit、22-round manifest、20 个有效候选映射、完整 SFT/generation cost、full-training 与 test。
- [ ] 已由人工决定 `retained` / `discarded`
