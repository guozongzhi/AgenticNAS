---
title: "AutoMCU: Feasibility-First MCU Neural Network Customization via LLM-based Multi-Agent Systems"
authors: "Penglin Dai, Zijie Zhou, Xincao Xu, Junhua Wang, Xiao Wu, Lixin Duan"
year: "2026"
venue: "arXiv:2605.21560v1"
doi: "10.48550/arXiv.2605.21560"
paper_url: "https://arxiv.org/abs/2605.21560"
source_pdf: "https://arxiv.org/pdf/2605.21560"
source: "arXiv v1 metadata/PDF, accessed 2026-09-10"
parser: "Codex"
parsed_on: "2026-09-10"
status: codex_draft
tags: [llm-nas, multi-agent, hardware-aware, mcu, deployment, cnn, edge]
---

# AutoMCU: Feasibility-First MCU Neural Network Customization via LLM-based Multi-Agent Systems

> 本笔记基于 arXiv v1 的 14 页 PDF。所有结果均为作者报告，尚未独立运行；论文没有给出代码仓库、训练配置表或 STM32Cube.AI 版本，实机表也没有 latency/energy。

## 一句话结论

AutoMCU 用 DeepSeek-V3.2 Proposal Agent 生成可构造 CNN 结构，先通过 STM32Cube.AI 检查 SRAM/Flash/operator feasibility，再训练可行候选并把验证准确率与部署摘要反馈给下一轮；它完成了两款 STM32 上的编译与执行验证，并在十次运行中报告约 0.1–0.5M tokens 与 1–2 GPU-hours 的定制成本，但主表与 μNAS/ColabNAS 不同搜索空间、训练 recipe 和候选预算，且未报告实测 latency/energy，因此只能证明“部署可行性前置过滤”值得复现，不能证明全面优于 HW-NAS。（pp. 3–12）

## 书目信息与来源核验

- arXiv ID：2605.21560v1；提交于 2026-05-20；arXiv DOI：10.48550/arXiv.2605.21560。
- 作者：Penglin Dai、Zijie Zhou、Xincao Xu、Junhua Wang、Xiao Wu、Lixin Duan；当前可核验 venue 仅为 arXiv。
- PDF：https://arxiv.org/pdf/2605.21560 ；14 页；本次读取副本 SHA-256：`2c1e611ec3e93030ea95b266f9bacf327bd409803d2b8ea971070fbfc7e9aa2f`。
- 论文未列代码或数据链接；按标题/AutoMCU + STM32Cube.AI 检索公开 GitHub 也未找到可确认的作者实现。
- 置信度：书目信息 high；方法与表格 high；baseline 公平性 medium-low；独立可复现性 low。

## 研究问题与贡献

- 问题：参数量/MACs 等 proxy 不能保证 MCU 后端能转换、分配内存或支持算子；在训练后才发现不可部署会浪费候选训练成本。（pp. 1–3）
- 方法：把可构造 JSON 架构、供应商 toolchain 预筛、受控训练、部署复核和历史反馈放进 proposal–screen–train–evaluate 闭环。（pp. 3–7）
- 多 Agent 设计：Supervisor 调度 Proposal、Training、Evaluation/Conversion 模块；每个模块状态隔离，只通过结构化摘要共享结果，避免公共长上下文。（pp. 3, 6）
- 作者贡献主张：在 CIFAR-10/100 的 MCU 约束下更快找到可部署模型，并用 NAS-Bench-201、组件消融和两款 STM32 实机验证搜索能力、稳定性和适配性。（pp. 7–12）

## 方法拆解

### 搜索或优化对象

- 搜索对象是真实 CNN：`a=(B,H)`，其中 backbone 是有序层序列、head 是任务分类头；每层由原子 module type 与参数集合组成。（pp. 3–4）
- 论文示例包含 conv、depthwise、downsample、pointwise、ghost、bottleneck，参数可含 channels、kernel、stride、padding、expansion、activation/BN；允许改变 depth、width 与 operator composition。（pp. 4–5）
- 候选以 JSON-like schema 表示，必须通过字段约束、层间 tensor shape 与 builder 构造检查；不是自由文本代码生成。（p. 4）
- 论文没有给出完整 module 白名单、所有离散参数取值或搜索空间基数，因此无法从正文重建同分布 search space。
- RAM/Flash/operator support 是先于训练的 hard feasibility gate；在可行区域内主要以 validation accuracy 选择候选。作者明确称目标不是求完整 accuracy–efficiency Pareto frontier。（pp. 2–5, 7）

### Agent 与优化闭环

- 用户输入数据集、任务与 RAM/Flash 上限；Supervisor 把任务派发给三个模块，控制是否继续下一轮或返回最终架构与 C code path。（pp. 3–4, 6）
- Proposal Agent 读取约束和精选历史摘要，输出结构化 architecture spec；若 builder 或 STM32Cube.AI 判定不可构造/超资源/不兼容，则训练前拒绝。（pp. 4–5, 7）
- Training Agent 对可行候选使用统一 split、preprocess、optimizer 与有限训练/early stop，输出 validation metric、convergence 和 checkpoint；但正文没有列出具体 split、optimizer、epoch、patience 或 batch size。（p. 5）
- Evaluation/Conversion Agent 在训练前后调用 STM32Cube.AI，记录 RAM、Flash、operator status 和部署产物；历史 repository 保存 architecture、accuracy、RAM、Flash。（pp. 4–6）
- Supervisor/各 Agent 只交换 task-level structured summary，内部 reasoning/tool trace 不共享；w/o MSIM 消融改为 shared context。（p. 6）
- 主实验 Proposal 使用 DeepSeek-V3.2 API，另测 MiMo-V2-Flash 与 Qwen-Plus；温度固定为 0。温度 0 不能保证跨 API/硬件的严格确定性，但作者做十次独立重复。（p. 7）

### 评估与预算

- 训练硬件：Ubuntu 22.04、AMD EPYC 7642、单张 RTX 3090 24GB；搜索成本包含 GPU 租赁与 LLM tokens，GPU 按 `$0.21/hour`，各 API token 单价在正文列出。（pp. 7–8）
- 数据：CIFAR-10/100 原生 32×32；扩展低资源/实机实验含 MNIST 和 FashionMNIST。作者称各数据集使用同 preprocessing/augmentation，但未披露完整 recipe。（pp. 8, 10–12）
- 主表对 AutoMCU 报告十次独立重复；在 256KB RAM/512KB Flash 下，CIFAR-10 为 `1.56±1.25 GPU-hours`、`$0.45±0.37`，CIFAR-100 为 `2.43±1.15 GPU-hours`、`$0.76±0.37`。正文未明确主表每次最多生成/训练多少候选。（p. 8, Table I）
- NAS-Bench-201 与 GENIUS 使用相同 DeepSeek-V3.2、温度 0、每 run 10 个架构、10 runs，按 validation 选优后报告 validation/test。（pp. 9–10, Table III）
- 组件消融固定最多 10 iterations、10 runs；random variants 每 run 最多 10 候选。w/o MSIM/Baseline 的异常终止 run 从 accuracy/resource 统计中排除，同时另报 50%/60% failure rate。（pp. 10–11, Table IV）
- 实机为 STM32F407VET6（Cortex-M4 168MHz，192KB RAM/512KB Flash）与 STM32H723ZGT6（Cortex-M7 550MHz，564KB RAM/1MB Flash）；最终 firmware integration、flashing 与 on-device execution 由人工完成。（p. 11）

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 严约束下可找到模型 | CIFAR-10 87.62±0.52、124.84KB RAM、466.55KB Flash；CIFAR-100 58.70±0.71、138.21KB/481.49KB | μNAS、ColabNAS | p. 8, Table I | high for reported values |
| NAS-Bench-201 同候选预算 | 10 architectures/run、10 runs；AutoMCU 在 CIFAR-100 test 为 72.24±1.21，GENIUS 71.30±0.98 | 同 DeepSeek-V3.2/temperature 0 的 GENIUS | p. 10, Table III | medium-high |
| HAG 贡献 | full accuracy 87.62±0.52 vs w/o HAG 82.89±2.81；time 1.56±1.25 vs 3.81±0.85 GPU-hours | random proposal、相同 10-iteration 上限 | pp. 10–11, Table IV | medium |
| 状态隔离贡献 | full failure 0%、0.46±0.40M tokens；w/o MSIM 50%、0.99±1.13M | shared-context multi-agent | pp. 10–11, Table IV | medium-low |
| 实机可部署 | 四数据集模型在两款 STM32 上成功编译与执行，表列 accuracy/RAM/Flash | 无 matched baseline 实机表 | p. 11, Table V | medium-high for feasibility |
| 极低内存候选 | 64KB RAM/Flash 下 CIFAR-10 76.36±1.92、MNIST 99.23±0.13、FashionMNIST 91.28±0.41 | 无同约束 baseline | p. 10, Table II | medium |

## 公平性与可信度检查

- NAS-Bench-201 对 GENIUS 的比较相对干净：相同 LLM、温度、每 run 10 架构、10 runs、validation 选优；但只比较一个 LLM-NAS baseline，没有 random/evolution 同预算结果。
- Table I 的 μNAS/ColabNAS 对比不统一 search space、候选/训练预算或训练 recipe；μNAS 的长时间与不满足 RAM/Flash 的结果不能直接证明 AutoMCU 搜索器普遍更快或更优。
- 经典轻量模型被训练 200 epochs，但 AutoMCU 候选只描述为 limited budget + early stopping，具体 epoch/optimizer/patience 未给，准确率横向比较无法确认训练公平性。
- 主表报告十次 AutoMCU 重复，却没有主实验的最大 iterations、attempted/rejected/trained candidate 数，GPU-hour 无法分解为 HAG、训练和 LLM 成本。
- w/o MSIM/Baseline 把异常终止 run 排除在 accuracy/resource 均值外，表中性能是“成功运行条件下”的结果；failure rate 虽单列，但均值仍有 survivor bias。
- HAG 消融同时把 LLM proposal 替换为 random，因此混合了“硬件预筛”和“LLM 引导”两项变化，不能单独归因于 feasibility-first gate。
- STM32Cube.AI 给出的 RAM/Flash 是后端分析值；实机表确认编译和执行，但没有测量 latency、energy、峰值运行内存、重复次数或输入吞吐。

## 可复现性与代码/数据

- 无作者代码、容器、prompt、完整 module schema、训练配置、数据 split、STM32Cube.AI 版本或实验 traces。
- CIFAR/MNIST 数据公开，但 vendor toolchain 与具体 license/version 会影响 operator support 和内存结果；复现必须冻结 toolchain、board、compiler flags 与 quantization/config。
- 论文给出硬件、LLM 名称/温度、部分 API 价格、主表 tokens/cost、NAS-Bench 与消融预算；这些有助成本审计，但不足以重建完整 pipeline。
- 实机部署仍需人工集成、flash 与运行，不是完全无人介入的 end-to-end deployment。

## 与 AgenticNAS 的关系

- 最可复用的是“双门控”：先用 typed schema/shape check 保证构造合法，再用真实 backend/toolchain 过滤 SRAM/Flash/operator feasibility，最后才付训练成本。
- 把 hardware feasibility 作为硬约束、quality 作为可行域内优化，与参数/FLOPs proxy 相比更接近部署；但如果目标是 Pareto，需要额外测 latency、peak memory、energy 和总成本并保存 non-dominated archive。
- state-isolated agents 与 concise summary exchange 可用于控制长轨迹 token；必须用成功率、token、calls 和同模型同候选预算消融，而非把“多 Agent”本身当效果来源。
- 本文搜索 CNN/MCU，没有 Transformer、Conv1d 或 4–10 层的完整离散定义；机制可迁移，精度与设备结论不可迁移。
- `quality_proxy` 与 `latency_proxy_ms` 只能保持流程占位符；本文没有真实 latency 数字，不能用其 RAM/Flash 表替这些字段背书。
- clean-room 复现只使用公开 module schema、公开 board/toolchain 和 validation summary，不接触内部 Archai、私有端点、内部日志或私有架构。

## 最小复现实验

- 固定公开 MCU 数据、4–10 层 Conv1d/CNN typed space、训练 recipe、STM32Cube.AI 版本与同一 board；每组 10 个 attempted proposals、10 runs。
- 对照 random without gate、random + backend gate、single LLM + schema gate、single LLM + schema/backend gate、state-isolated multi-agent full。
- 明确统计 attempted/schema-valid/backend-feasible/trained/deployed 数，以及每阶段 wall time、GPU-hours、LLM calls/tokens/费用和 failure taxonomy。
- 对冻结候选实测 validation quality、latency distribution、peak SRAM/Flash、energy/inference；test 只在 search 完成后一次评估。
- 再与 μNAS/ColabNAS 做同 search space、同训练 epoch、同候选和同总 GPU-hour budget 对照，避免以不同 pipeline 总时长直接下结论。

## 局限与风险

- 搜索空间、训练 recipe、主实验候选预算和代码均不完整，独立复现风险高。
- baseline 预算不匹配，数百 GPU-hour 对 1–2 hour 的 headline 不能解释为同任务同预算算法加速。
- 实机只验证两块 STM32 与四个图像分类数据集；没有真实 latency/energy，也没有跨 vendor 后端。
- 供应商分析与实际峰值运行行为可能有差异；需要板载测量而非仅依赖工具报告。
- 温度 0 并不等于 API 完全确定；缺少 model snapshot、seed、prompt 与 retry log。
- 失败 run 的条件性均值和 HAG 混合消融会夸大单组件归因，需要更细对照。

## 可引用摘要

AutoMCU 将结构化 CNN 提案、STM32Cube.AI 可部署性预筛、受控训练和实机部署复核串成闭环，并用状态隔离的 Supervisor/Proposal/Training/Evaluation 模块降低共享上下文。作者在 MCU RAM/Flash 硬约束下报告十次重复、token/成本及两款 STM32 的成功编译与执行；但缺少代码、完整搜索空间、训练 recipe、主实验候选预算和实测 latency/energy，且与 μNAS/ColabNAS 的预算不匹配，因此证据主要支持 deployment gate 的工程价值，而非全面的 HW-NAS 性能优势。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2605.21560
- PDF：https://arxiv.org/pdf/2605.21560
- 已核对：标题、作者、日期、arXiv DOI、结构表示、Agent loop、模型/温度、GPU、主要表格、token/cost、两款 STM32 与部署方式。
- 未核对：独立运行、作者代码、完整 prompt/schema、训练 recipe、主表候选预算、STM32Cube.AI 版本、真实 latency/energy/peak memory。
- [ ] 已由人工决定 `retained` / `discarded`
