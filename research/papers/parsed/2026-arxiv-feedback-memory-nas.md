---
title: "Resource-Efficient Iterative LLM-Based NAS with Feedback Memory"
authors: "Xiaojie Gu, Dmitry Ignatov, Radu Timofte"
year: "2026"
venue: "arXiv:2603.12091v1"
doi: "10.48550/arXiv.2603.12091"
paper_url: "https://arxiv.org/abs/2603.12091"
source_pdf: "https://arxiv.org/pdf/2603.12091"
code_url: "https://anonymous.4open.science/r/Iterative-LLM-Based-NAS-with-Feedback-Memory-E7D6/"
source: "arXiv v1 metadata/PDF and paper-linked anonymous code snapshot, accessed 2026-08-01"
parser: "Codex"
parsed_on: "2026-08-01"
status: codex_draft
tags: [llm-nas, memory, code-generation, cnn, single-gpu, failure-feedback]
---

# Resource-Efficient Iterative LLM-Based NAS with Feedback Memory

> 本笔记基于 arXiv v1 的 10 页 PDF 和论文脚注链接的匿名代码快照。所有指标均为作者报告，尚未独立复现。

## 一句话结论

论文让冻结的代码 LLM 在开放 PyTorch CNN 代码空间中生成候选，并由另一个 Prompt Improver 把最近 5 次“问题—修改建议—结果/错误”作为有界反馈记忆；它为失败轨迹记忆和低成本闭环提供了直接对照，但证据仅是单 epoch 代理、主要 baseline 只是同一 LLM 的首次成功生成，且没有多 search seed、完整 LLM 调用成本或真实 latency/memory 测量。（pp. 1, 4–8）

## 书目信息与来源核验

- arXiv ID：2603.12091v1；提交日期：2026-03-12；arXiv DOI：10.48550/arXiv.2603.12091。
- 作者：Xiaojie Gu、Dmitry Ignatov、Radu Timofte；当前可核验 venue 为 arXiv。
- 论文：https://arxiv.org/abs/2603.12091
- 代码快照：https://anonymous.4open.science/r/Iterative-LLM-Based-NAS-with-Feedback-Memory-E7D6/ ；2026-08-01 可访问，README 描述运行入口、输出日志与消融开关，但仍是匿名快照而非有版本 release 的作者仓库。
- 置信度：书目信息 high；方法 high；作者报告的单 epoch 结果 medium；端到端可复现性 medium-low。

## 研究问题与贡献

- 问题：小型、冻结 LLM 能否在单张消费级 GPU 上，利用结构化历史反馈持续改进真实神经网络架构，而不是一次性生成代码。
- 方法贡献：Code Generator、validator/evaluator 和 Prompt Improver 构成闭环；Prompt Improver 维护固定 `K=5` 的诊断三元组窗口，并把执行失败也作为下一轮信号。（pp. 1, 4–5）
- 资源主张：DeepSeek-Coder-6.7B 和 Qwen2.5-7B 各运行最多 2,000 iterations，论文称一次完整 2,000-iteration search 约需 18 GPU-hours、使用单张 RTX 4090 24GB。（pp. 5, 7–8）

## 方法拆解

### 搜索或优化对象

- 搜索对象是完整、可执行的 `Net(nn.Module)` CNN 代码，不是 Agent 工作流；候选必须满足固定数据集输入与分类输出接口。
- LLM 每轮可重写完整模型类，因而能改变 depth、width、operator、connectivity 和 pooling 等结构；论文没有给出有限的声明式 operation set、4–10 层约束或 block/cell/op schema。（pp. 1, 3–4）
- 训练协议、数据增广、optimizer、batch size 和一 epoch evaluator 固定，因此属于 NAS 而非训练配方 HPO。
- 搜索面向 CIFAR-10、CIFAR-100 与 ImageNette 的 2D CNN，不是本仓库的 Conv1d Transformer。

### Agent 与优化闭环

- Code Generator 接收任务、当前 best code 和上一轮改进建议，输出完整 PyTorch model class；sampling 为 temperature 0.7、top-p 0.9、最多 2,048 new tokens。（p. 4）
- validator 先实例化候选并做 dummy forward，检查输出为 `B × C`；失败候选的错误消息直接送入 Prompt Improver。（p. 4）
- 合法候选训练一 epoch；若准确率更好就替换 best code。Prompt Improver 同时读取 best、当前候选与最近 5 个诊断三元组，生成 reason、inspiration 和下一轮修改建议。（pp. 4–5）
- 三元组记录 `problem`、`suggestion`、`outcome`；outcome 可以是 accuracy gain 或错误类型。窗口固定为 5，用于控制上下文长度。（p. 5）
- 论文称使用 dual-LLM specialization，但实验表述更接近同一模型分别扮演 generator/improver 角色；没有给出两角色逐轮调用数、失败重试账或 token/费用总账。

### 评估与预算

- 数据：CIFAR-10、CIFAR-100、ImageNette；标准 crop、flip、normalization。（p. 5）
- 低保真：每个合法候选只训练 1 epoch，SGD、momentum 0.9、weight decay `5e-4`、初始学习率 0.01 + cosine、batch size 128。（pp. 4–5）
- LLM：DeepSeek-Coder-6.7B-Instruct、Qwen2.5-7B-Instruct 各 2,000 iterations；GLM-5 只做 100 iterations，原因是经济成本，三者因此不是 matched trial budget。（p. 5）
- 训练固定 seed 43、deterministic CUDA；每个候选有 30 分钟 timeout，LLM 与视觉模型共享 RTX 4090 24GB。（p. 5）
- baseline：每个 LLM 的第一次成功候选，即 single-shot generation；没有等预算 random/native mutation、传统 evolution、stateless iterative LLM 或 population baseline。（p. 5）
- 高保真：没有把 top candidates 按统一完整训练 schedule 重训；论文把这项工作列为未来验证。（p. 8）
- 硬件：共享显存只是隐式可运行约束；没有实测 latency、peak memory、energy，也没有质量—硬件 Pareto 目标。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| CIFAR-10 best-so-far | DeepSeek 28.2%→69.2%；Qwen 50.0%→71.5%；GLM-5 43.2%→62.0% | 各模型第一次成功候选 | pp. 6–7, Table 2 | medium |
| 执行成功率差异很大 | CIFAR-10：76.0% / 18.8% / 91.0%；ImageNette DeepSeek 仅 13/2000（0.7%） | 所有 proposal | pp. 6–7, Table 2 | high |
| 反馈记忆消融 | 去掉反馈或 reference 后搜索停滞/退化；图中偶发 spike 不被保留 | Full loop | pp. 6–7, Fig. 3 | medium-low |
| 搜索成本 | 单次 2,000-iteration search 约 18 GPU-hours | 单张 RTX 4090 24GB | pp. 1, 7–8 | medium |
| 失败也是主要信号 | 不同 runs 的 failure rate 约 5%–99% | 诊断三元组记录 error | pp. 7–8 | high |

## 公平性与可信度检查

- 主要对照只是 single-shot first success；它不能隔离“多尝试本身”、保留 best、Prompt Improver、`K=5` memory 和失败诊断各自的贡献。
- Figure 3 有 no-feedback/reference 消融，但正文未给出 matched search seeds、方差、逐设置成功候选数和完整预算表。
- 固定训练 seed 43 提高单次运行确定性，却不等于至少三组独立 search seeds；不同 LLM 又使用 2,000 与 100 iterations，跨模型比较不公平。
- p. 4 把 evaluator 指标写为 top-1 test accuracy，p. 5 又称 true validation accuracy；若实际搜索反复读取 test set，会构成 test-feedback leakage。必须从代码和数据 split 核对后才能引用泛化结论。
- 作者报告的是一 epoch best-so-far，而非统一完整训练后的最终模型；不能把这些数与 fully trained NAS 结果直接比较。
- 趋势相关性使用 iteration index 与 accuracy；best preservation 和搜索非平稳性会使相关性不等同于 memory 的因果贡献。

## 可复现性与代码/数据

- 论文提供算法、prompt 角色、训练 recipe、iterations、seed、timeout、GPU 和 per-run success counts；匿名快照 README 给出 `run.sh`、消融 flag、`summary.json`、逐轮日志和生成模型目录。
- 公开入口仍是 anonymous 4open snapshot；未见永久作者仓库、tag/release、依赖锁定或所有论文 runs 的不可变 artifact。
- 未报告 LLM serving stack、精度/量化、实际显存占用、每轮两角色是否分别调用、token/费用和全部实验的 GPU-hours。
- 最关键复现缺口是 validation/test split 实现、top candidates 的完整训练和多 search seed 方差。

## 与 AgenticNAS 的关系

- 可复用固定大小 memory，但条目应是 clean-room 的 `MutationAction + validation result + typed error + measured objective`，不能保存任意内部代码、端点或日志。
- 失败应计入 attempted-candidate 和 LLM budget；同时分别报告 schema、shape、OOM、timeout、divergence、duplicate，避免只看成功候选。
- 本仓库可以对照 `K=0/1/5/all`、只记成功、成功+失败、stateless LLM 和 native evolution，并保持候选/LLM/GPU budget 一致。
- “在同一张 GPU 上能运行”不是 hardware-aware objective；最终仍需真实 latency、peak memory 和 cost 的 Pareto/hypervolume。
- `quality_proxy` 与 `latency_proxy_ms` 只能是控制流占位符，不能用本论文的一 epoch accuracy 或共享 VRAM 代替本仓库实测结果。

## 最小复现实验

- 固定 4–10 层 Conv1d Transformer、声明式 action space、训练 recipe、数据 split、200 attempted trials、LLM calls/tokens 和三组 search seeds。
- 对照 native random mutation、stateless LLM、LLM + best-only、LLM + recent success、LLM + recent success/error；memory window 比较 1/5/all。
- 所有失败计入主预算；top-k 候选用相同完整训练，并在隔离 test set 与同一目标设备上复核。
- 指标：best-so-far、regret/hypervolume、validity、duplicate、失败类型、seed variance、GPU-hours、LLM tokens/费用和真实 latency/memory。

## 局限与风险

- 搜索只覆盖三个小型图像分类数据集和开放 CNN 代码，不能证明向 Conv1d Transformer、结构化 schema 或多目标 NAS 泛化。
- 代码生成成功率最低达 0.7%，但没有 constrained decoding、duplicate rate 或完整失败成本分析。
- single-epoch proxy 尚未用 full training 验证；validation/test 表述不一致带来潜在数据泄漏风险。
- 缺少 matched-budget 强基线、多 search seeds、完整 LLM 调用账和实测硬件指标。

## 可引用摘要

该工作用冻结 LLM 在开放 PyTorch CNN 代码空间中执行多轮生成—验证—单 epoch 评估—改进，并用最近 5 次问题、建议和结果/错误构成固定长度反馈记忆。作者在 CIFAR-10、CIFAR-100 和 ImageNette 上报告 best-so-far 单 epoch accuracy 提升，并给出单张 RTX 4090 上一次 2,000-iteration search 约 18 GPU-hours的估算。证据仍受 single-shot 弱基线、单 search seed、代理未做完整训练验证、validation/test 表述不一致和缺少真实硬件测量限制。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2603.12091
- PDF：https://arxiv.org/pdf/2603.12091
- 匿名代码快照：https://anonymous.4open.science/r/Iterative-LLM-Based-NAS-with-Feedback-Memory-E7D6/
- 已核对：标题、作者、日期、arXiv ID/DOI、闭环、`K=5` memory、模型/数据、iterations、training recipe、GPU、成功率、主要结果与正文限制。
- 未核对：独立运行、validation/test split 实现、完整训练、永久代码 release、LLM token/费用、全部实验成本和多 search seeds。
- [ ] 已由人工决定 `retained` / `discarded`
