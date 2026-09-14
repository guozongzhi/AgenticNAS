---
title: "Device-First Feedback: Toward Mobile-Native LLM-Driven Neural Architecture Search"
authors: "Saif U Din, Muhammad Ahsan Hussain, Radu Timofte, Dmitry Ignatov"
year: "2026"
venue: "arXiv:2608.00078v1"
doi: "10.48550/arXiv.2608.00078"
arxiv_id: "2608.00078v1"
paper_url: "https://arxiv.org/abs/2608.00078"
source_pdf: "https://arxiv.org/pdf/2608.00078"
code_url: "https://github.com/ABrain-One/nn-gpt"
source: "arXiv v1 metadata/PDF and paper-linked public repository, accessed 2026-09-14"
parser: "Codex"
parsed_on: "2026-09-14"
status: codex_draft
tags: [llm-nas, mixed-search-space, mobile, hardware-aware, int8, tflite, device-feedback, test-feedback]
---

# Device-First Feedback: Toward Mobile-Native LLM-Driven Neural Architecture Search

> 本笔记基于 arXiv v1 的 11 页 PDF、关键表格渲染图和论文链接的公开仓库快照。论文把真实设备指标闭环进 LLM 生成过程，但只报告单设备、单 seed、未完成的 0-6 cycle；当前公开代码与论文所述数据集及延迟单位存在可复现性冲突。

## 一句话结论

该工作让架构生成 LLM 每轮提出最多 20 个 PyTorch CNN，经单 epoch GPU 训练、INT8 TFLite 导出和 Samsung SM-P613 三 delegate 实测后，以量化准确率/延迟比决定训练语料是否扩充；CIFAR-10 的 cycle 1 相对 cycle 0 报告 25.6 倍 mobile score，而 CIFAR-100 的最佳点仍是未微调 baseline。由于反馈直接使用 256 张 test-split 图像、cycle 1 的 gate 没有 prior reference、训练代码/超参可随模型变化、没有 matched-budget baseline 或多 search seeds，且当前仓库无法忠实重建 CIFAR-100 与毫秒延迟，该结果只能支持“GPU proxy 与端侧结果会分离”，不能支持一般 LLM-NAS 优势或设备 Pareto。（pp. 3-10）

## 书目信息与来源核验

- arXiv ID：`2608.00078v1`；提交时间 2026-07-29；当前可核验 venue 为 arXiv。
- 作者：Saif U Din、Muhammad Ahsan Hussain、Radu Timofte、Dmitry Ignatov。
- DOI：[10.48550/arXiv.2608.00078](https://doi.org/10.48550/arXiv.2608.00078)。
- PDF：https://arxiv.org/pdf/2608.00078 ；11 页；本次读取副本 SHA-256：`2584064b5a66e6da77dc89691c032e122f830fc2eac776cd25fd1c045f63061b`。
- 代码：https://github.com/ABrain-One/nn-gpt ；2026-09-14 只读审计 HEAD 为 `904437058a274f3d25840017094789af58ee2590`，没有 paper tag/release。
- 置信度：书目信息 high；PDF 表格数值 high；25.6 倍相对比 medium；绝对延迟/score 单位与 CIFAR-100 paper-exact 复现 low。

## 研究问题与贡献

- 问题：LLM 生成的 CNN 即使在 GPU 上有较高单 epoch accuracy，也可能无法 INT8 导出、无法使用 Android delegate，或在真实设备上出现差的 accuracy-latency trade-off。（pp. 1-2）
- 方法：把 QLoRA、候选生成、GPU 训练、INT8 TFLite、Android CPU/GPU/NNAPI benchmark、基于 mobile score 的 gate 和训练语料扩充串成可恢复的 cycle。（pp. 3-4, Fig. 1）
- 主要价值：不是只用 FLOPs/latency predictor，而是把物理设备测量写回后续 LLM prompt。（pp. 2-4）
- 论文的负结果同样重要：CIFAR-100 的 GPU best 到 cycle 6 升至 26.2%，但端侧最佳仍是 cycle 0，说明 workstation proxy 不足以代表部署进展。（pp. 7-8）

## 方法拆解

### 搜索或优化对象

- 真实对象是完整 PyTorch `Net` CNN code；mobile prompt允许 Conv2d、depthwise/pointwise conv、pool、residual、Linear、Dropout，禁止 attention/Transformer 和非标准算子。
- 每个候选包含 `supported_hyperparameters()`、`train_setup()` 与 `learn()`；当前 prompt至少允许 `lr`、`momentum`，并可条件加入 `weight_decay`、`dropout`。模型可改变网络结构，也可改变 optimizer 相关训练代码。
- 因此这是实际神经网络架构生成，但不满足本仓库“NAS 固定训练配方”的严格边界，保守归入 `mixed-search-space`；不能把质量差异全部归因于 architecture。
- 搜索空间是受 prompt 约束的开放 CNN code，不是枚举 cell/op；没有 Conv1d、Transformer、4-10 层或显式 block/cell schema。
- 目标是单一比值 `INT8 top-1 accuracy / best latency`，另有 novelty 与 deployability 条件；不是显式 Pareto/HV，也不测 energy 或 peak memory。

### Agent 与优化闭环

- cycle 0：未经 QLoRA 的 `ABrain/NNGPT-UniqueArch-Rag` 生成 `K=20` 个候选；成功候选单 epoch 训练、INT8 导出并在设备上测量，只作 baseline，不扩充训练集。（pp. 3-4）
- cycle 1-6：上一轮训练池上做 3 epochs QLoRA，生成最多 20 个新模型，checksum 去重；达到 GPU accuracy threshold 的模型进入移动端流程。（pp. 4-5）
- 设备阶段：对 256 张图像测 INT8 top-1；CPU、GPU、NNAPI 各 20 次 timed runs；论文称记录成功 delegate 的最小中位延迟。（p. 4, Table 1）
- gate：当 cycle best score 至少为 reference best 的 `0.99` 且至少 2 个 valid mobile models 时接受；接受后把 GPU accuracy、量化准确率、延迟和 score 写入 chat example。（pp. 4-5）
- 关键缺陷：论文结果说明 cycle 1 没有 prior gated reference，因此 CIFAR-100 cycle 1 虽低于 cycle 0 仍被接受并加入 19 个样本；严格 baseline gate 应从 cycle 1 生效。（p. 7）
- 测试泄漏：score 的 `a_int8` 明确来自 active dataset test split，且被写回后续 prompt；这使同一 test subset参与多轮选择，最终 accuracy 不是独立 held-out test。（p. 4）

### 评估与预算

- 数据集：CIFAR-10、CIFAR-100；每个候选 GPU 训练 1 epoch；GPU accuracy threshold 分别 0.40/0.20。（p. 5, Table 1）
- 设备：Samsung Galaxy Tab SM-P613，Android 14；CPU/GPU/NNAPI；每 delegate 20 次 timed runs。（p. 5, Table 1）
- LLM：`ABrain/NNGPT-UniqueArch-Rag`；每 cycle QLoRA 3 epochs；论文未报告参数量、token 数、每轮训练样本数明细或 QLoRA/GPU wall-time。
- 候选预算：每数据集 cycle 0-6、每 cycle 最多 20 个，即最多 140 proposal；两数据集合计最多 280。论文原计划 8 cycles，但只报告到 6。（p. 5）
- 单 seed：42，同时用于 generation/data shuffling；没有独立 search-seed 重复。（p. 5）
- GPU：Linux workstation 上未指明型号/数量；没有总 GPU-hours、LLM calls/tokens、能耗、货币成本或失败重试总账。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| CIFAR-10 mobile score 峰值 | cycle 0 `1.090e-7`；cycle 1 `2.786e-6`，报告 25.6x；cycle 1 mean INT8 acc 46.9% | 同一 base LLM 的 ungated cycle 0 | pp. 5-6, Tables 2-3 | high for table; medium for absolute score |
| GPU 与端侧分离 | CIFAR-10 GPU best cycle 2 为 67.6%，但 mobile best低于 cycle 1，cycle 2-6 均 rejected | cycle 1 champion | p. 6, Table 3 | high |
| CIFAR-100 未超过 baseline | cycle 0 mobile best `9.657e-8`；cycle 1-6 均未超过；cycle 6 GPU best 26.2% | cycle 0 | p. 7, Table 4 | high for report; low for code reproduction |
| deployability | 各轮 valid samples 的部署成功率接近或达到 100% | 无固定空间 HW-NAS baseline | pp. 6-8 | medium; surviving candidates only |
| gate 防止后续回归 | cycle 2-6 均未继续扩充训练池 | 非递减 gate | pp. 6-8 | high for recorded trajectory |

## 公平性与可信度检查

- 没有 random search、regularized evolution、固定空间 HW-NAS、frozen LLM 或无设备反馈 ablation；无法隔离 QLoRA、prompt、gate 与真实设备反馈各自贡献。
- 每数据集只有一个 adaptive trajectory。cycle 内候选共享模型和 history，Student-t CI across models 不是跨 search seeds 的方法不确定性。
- cycle 0 与 cycle 1 不只是“是否反馈”的受控对比：后者经历 QLoRA，训练池、候选分布和筛选路径均变化。
- CIFAR-100 cycle 1 无条件接受低于 baseline 的候选，导致后续训练池污染；论文讨论承认更严格 gate 应在首次迭代就比较 cycle 0。（pp. 7-8）
- accuracy/latency scalar在低准确率时偏好极快但不可用模型；没有 accuracy floor、Pareto front、HV 或独立 latency constraint。（p. 8）
- 256 张 test-split 图像反复进入 gate 和 prompt，构成选择泄漏；没有最终 untouched test set。
- 报告 0-6 而非计划 8 cycles，不能视为完整预注册预算；停止后的行为和恢复能力未被完整实验验证。

## 可复现性与代码审计

- 公开仓库包含 `MobileDeploymentFinetuner`、mobile prompt、INT8 converter、ADB benchmark和 resume路径；但没有论文称随文提供的 `data/experiment_protocol.json`、两个 `progress_metrics_*.json`、per-cycle records、模型清单或 paper tag。
- 当前 HEAD 的 `_evaluate_tflite_accuracy()` 无条件实例化 `torchvision.datasets.CIFAR10`，没有 CIFAR-100 分支；因此不能按公开代码重建论文的 CIFAR-100 quantized accuracy。
- 当前 `_parse_benchmark_output()` 注释说明 benchmark 输出单位为微秒，却把数值乘以 `1000`；字段仍命名 `best_duration_ms`。代码还在 delegate 间选择 `avg`，而论文写“minimum median latency”。
- 上述实现冲突不一定证明论文运行时使用相同 commit，但 paper-exact commit/metrics未公开，因此绝对 score、单位与 CIFAR-100 结果目前不可独立验证。
- 当前 prompt与论文口径都允许模型生成训练方法/超参，不是固定训练 recipe；复现应由 evaluator 覆盖 training config，不能信任 prompt 约束。

## 与 AgenticNAS 的关系

- 最可复用的是 device-in-the-loop evaluation contract：每个 architecture action在独立 validation 上训练，再在目标设备记录 quantized quality、latency、delegate failure和 peak memory。
- scalar ratio应改成显式多目标 archive：quality floor + measured latency + peak memory + energy/成本，并报告 Pareto/HV；不同单位先标准化。
- architecture-only action必须只输出 typed graph；optimizer、lr、batch、augmentation由 evaluator固定。HPO 另开独立实验，不把 mixed search收益写成 NAS。
- 从 cycle 1 起就以 cycle 0 为 gate reference；rejected cycle保留探索记录但不得把 test反馈写回训练语料。
- 设备 validation 与最终 test必须分离；每轮只用 validation device subset，最终一次在完整 untouched test/device run 上确认。
- `quality_proxy` 与 `latency_proxy_ms` 只能作流程占位符；本论文的真实设备数值也不能直接移植到不同模型、设备或本仓库内部实现。
- clean-room 复现只使用公开论文、代码和自建 typed space，不读取或披露内部 Archai、模型端点、日志或私有架构。

## 最小复现实验

- 在公开 4-10 层 Conv1d Transformer typed space固定训练 recipe、量化方式和数据划分；比较 random、regularized evolution、frozen LLM、LLM + validation feedback、LLM + device feedback。
- 每组 5 个 search seeds，固定 attempted/evaluated candidates、LLM calls/tokens和 GPU/device测量预算；无效 proposal同样计预算。
- 每候选记录 measured latency distribution、delegate/设备、batch、warmup/timed runs、peak memory、energy和 quantized quality；不使用单位不明的单一字段。
- 只用 validation feedback更新 archive；search结束后对每组相同数量的 Pareto candidates做一次 untouched test。

## 局限与风险

- 单 tablet、单 seed、两个小型 vision datasets、未完成 cycle budget，外推很窄。
- 训练 recipe随生成 code变化，不能把结果纯归因于架构。
- test feedback、首次 gate例外和 adaptive候选内相关性削弱统计解释。
- 绝对 score单位、median/mean口径和 CIFAR-100 公开实现不一致；paper-exact artifacts缺失。
- 没有参数量/FLOPs、energy、peak memory、完整成本或 matched-budget baseline。

## 可引用摘要

Din 等把 LLM 生成 CNN 的单 epoch GPU评估、INT8 TFLite导出和 Samsung SM-P613 实测串成闭环，并以量化准确率/延迟比控制训练语料扩充；作者在 CIFAR-10 单 seed轨迹中报告 cycle 1 相对 baseline 的 25.6 倍 score，而 CIFAR-100 最佳仍是未微调 baseline。该证据直接展示 GPU proxy与设备结果可能分离，但搜索使用 test-split反馈、mixed training code、单 seed和 scalar ratio，且当前公开仓库无法忠实重建 CIFAR-100与延迟单位，因此不能视为一般 LLM-NAS 或设备 Pareto优势。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2608.00078
- PDF：https://arxiv.org/pdf/2608.00078
- 代码：https://github.com/ABrain-One/nn-gpt （审计 commit：`904437058a274f3d25840017094789af58ee2590`）
- 已核对：标题、作者、日期、arXiv ID/DOI、PDF Table 1-4、cycle/gate、test feedback、设备/预算、当前 mobile prompt、accuracy evaluator和 benchmark parser。
- 未核对：独立运行、paper-exact commit、原始 metrics/模型、真实 ADB 输出、完整 QLoRA/LLM/GPU成本、CIFAR-100 paper运行代码。
- [ ] 已由人工决定 `retained` / `discarded`
