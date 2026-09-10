---
title: "CoLLM-NAS: Collaborative Large Language Models for Efficient Knowledge-Guided Neural Architecture Search"
authors: "Zhe Li, Zhiwei Lin, Yongtao Wang"
year: "2026"
venue: "CVPR 2026 Workshops, Sixth Workshop on Neural Architecture Search (Oral); arXiv:2509.26037v2"
doi: "10.48550/arXiv.2509.26037"
paper_url: "https://arxiv.org/abs/2509.26037"
source_pdf: "https://arxiv.org/pdf/2509.26037"
official_version: "https://openaccess.thecvf.com/content/CVPR2026W/CVPR-NAS26/html/Li_CoLLM-NAS_Collaborative_Large_Language_Models_for_Efficient_Knowledge-Guided_Neural_Architecture_CVPRW_2026_paper.html"
source: "arXiv v2 metadata/PDF and CVF Open Access final paper, accessed 2026-09-10"
parser: "Codex"
parsed_on: "2026-09-10"
status: codex_draft
tags: [llm-nas, multi-agent, weight-sharing, cell-search, transformer, imagenet, nas-bench-201]
---

# CoLLM-NAS: Collaborative Large Language Models for Efficient Knowledge-Guided Neural Architecture Search

> 本笔记基于 arXiv v2 的 21 页 PDF、CVF Open Access 终版页面与 10 页正式论文。所有结果均为作者报告，尚未独立运行；论文和官方页面没有给出作者代码仓库。

## 一句话结论

CoLLM-NAS 用有状态 Navigator 把历史候选与验证反馈压缩成搜索策略，再由无状态 Generator 在既有 MobileNet、ShuffleNet、AutoFormer 或 NAS-Bench-201 空间中生成结构化候选，Coordinator 负责合法性、去重和共享超网评估；在宏观空间的三次运行中，作者以 250 个候选对比进化搜索的 1,000 个候选，并报告 search-phase GPU days 降低 4.6–10 倍，但该成本排除了超网训练，也没有分离 LLM 推理与候选验证成本或报告 tokens/完整 traces。（pp. 3–8, 11–21）

## 书目信息与来源核验

- arXiv ID：2509.26037v2；v1 提交于 2025-09-30，v2 修订于 2026-05-17；arXiv DOI：10.48550/arXiv.2509.26037。
- 作者：Zhe Li、Zhiwei Lin、Yongtao Wang；arXiv 注释为 “Accepted as Oral at CVPR 2026 Workshop on Neural Architecture Search (NAS)”。
- CVF Open Access：CVPR Workshops 2026，pp. 3273–3282；CVF 页面给出与 arXiv 相同的标题、作者和终版 PDF。
- 本次读取的 arXiv v2 PDF 共 21 页，SHA-256：`64d74addc5350fd1a321dfa57a30edb3eee09a3364d3c51057c0900809271914`；CVF 终版 PDF 共 10 页，SHA-256：`5fd2313d54b299f777801c84ef3d492257b4f3d22e2a0959c601278d9f479a39`。
- 论文、arXiv/CVF 页面均未提供代码链接；按标题检索公开 GitHub 仓库也未找到可确认的作者实现。
- 置信度：书目信息 high；方法/表格 high；端到端成本 medium；可复现性 low。

## 研究问题与贡献

- 问题：两阶段/one-shot NAS 虽复用超网权重，但第二阶段的随机、RL 或进化搜索仍可能评估大量候选；开放代码生成式 LLM-NAS 又容易产生无效结构并要求逐候选训练。（pp. 1–3）
- 方法：保留成熟超网及其离散结构表示，只用 LLM 替换第二阶段搜索器。Navigator 负责从历史轨迹抽象策略，Generator 负责把策略翻译为候选，Coordinator 执行合法性、资源约束、去重与验证。（pp. 3–5）
- 作者主张：在三类宏观超网与 NAS-Bench-201 上，以更少架构评估找到更高准确率候选；通过单 LLM、记忆布局、prompt 改写、温度和模型替换消融检查协作设计。（pp. 5–8, 11–12）

## 方法拆解

### 搜索或优化对象

- 搜索对象是真实神经网络子结构，不是 Agent 工作流；训练好的超网、数据处理和每个空间的候选评估方式固定，LLM 改变结构向量。（pp. 2, 4–5）
- MobileNet：输入分辨率 `{160,176,192,208,224}`，五个 stage 的深度各取 `{2,3,4}`，20 个 block 的 kernel 各取 `{3,5,7}`、expansion ratio 各取 `{3,4,6}`，组合规模约 `10^19`。（p. 11）
- ShuffleNet：20 个 block 各选 3×3/5×5/7×7 ShuffleNetV2 unit 或 Xception module，共 `4^20`。（p. 11）
- AutoFormer：Tiny/Small 深度 `{12,13,14}`，Base 深度 `{14,15,16}`，同时逐层改变 embedding dimension、heads 和 MLP ratio，统一空间超过 `10^16`；深度不落在本仓库重点 4–10 层区间，也没有 Conv1d。（p. 11）
- NAS-Bench-201：4-node/6-edge cell，每条 edge 取 `none/skip/1×1 conv/3×3 conv/3×3 avg-pool`，共 15,625 个预计算架构。（pp. 5, 12–14）
- 资源约束是 FLOPs 或参数量阈值；论文没有真实 latency、peak memory、energy 或货币成本的多目标 Pareto 搜索。（pp. 4–6）

### Agent 与优化闭环

- Navigator LLM 有持续对话状态：初始接收目标准确率与资源上限，后续读取已访问候选、当前最优和本轮评估结果，输出总结、模式、导航方向与具体建议。（pp. 3–4, 15–19）
- Generator LLM 无跨轮记忆，只接收当前 Navigator 策略与空间约束，每轮生成 10–20 个结构化候选。（pp. 4, 19–20）
- Coordinator 是确定性编排层：检查结构合法性与资源成本、跳过已访问候选、用超网继承权重评估 validation performance，并把结果写入 history。（pp. 3–5）
- 循环在达到目标准确率或 iteration limit 时停止；论文未给出完整的 attempted/invalid/duplicate proposal 数、每轮实际接收数、重试数或所有运行 traces。（Algorithm 1, pp. 3–4）
- 基础模型为本地 vLLM 部署的 Qwen3-30B-A3B，Navigator/Generator 温度均为 0.6；补充实验另测 Qwen3-32B 和两种 DeepSeek-R1 distill 模型。（pp. 5, 8, 12）

### 评估与预算

- 宏观空间：复用 OFA/SPOS/AutoFormer 预训练超网；同一空间中传统 baseline 用进化搜索。OFA 与本文最终都在完整 validation set 上直接评估子网，未使用原始 OFA accuracy predictor。（p. 5）
- 宏观搜索每种方法报告三次独立运行的最佳子网；baseline 候选预算 1,000，CoLLM-NAS 为 250。（p. 5, Table 2）
- 搜索阶段在单张 NVIDIA A100-80GB 上计时，并称包含 LLM inference；MobileNet 为 `0.42→0.09` GPU-day、ShuffleNet `0.32→0.07`、AutoFormer `1.0→0.1`。这些数字明确排除超网训练。（p. 5, Table 2）
- NAS-Bench-201 每次最多评估 100 个架构、结果汇总十次独立运行；检索反馈使用 benchmark 的 validation accuracy，最终同时报告 validation/test。（pp. 5–7）
- 论文没有报告 LLM calls、input/output tokens、vLLM 并发与吞吐、单独 LLM GPU-hours、失败成本或超网训练 GPU-hours。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 宏观空间以更少候选取得更高 Top-1 | 250 vs 1,000 candidates；提升最高 0.7 point | OFA/SPOS/AutoFormer 的 EA search | p. 5, Table 2 | medium-high |
| search-phase 时间下降 | 0.09/0.07/0.10 vs 0.42/0.32/1.00 GPU-day，即 4.7×/4.6×/10× | 同超网传统搜索 | p. 5, Table 2 | medium |
| ImageNet 候选 | 77.9% Top-1、93.8% Top-5、320M FLOPs | 论文汇总的人工、DARTS、two-stage 与 LLM-NAS 结果 | p. 6, Table 3 | medium |
| NAS-Bench-201 | CIFAR-10/100/ImageNet16-120 test 为 94.37±0.01 / 73.44±0.15 / 46.79±0.28 | RS/RL/EA、GENIUS、LLMatic、RZ-NAS、LM-Searcher | p. 7, Table 4 | high for reported table |
| 双 LLM 协作 | 十次运行中 CoLLM-NAS best-so-far 曲线高于合并角色的 SiLLM-NAS | 单 LLM reflection→generation | p. 7, Fig. 5 | medium |
| 记忆布局 | 复杂任务以 Navigator stateful + Generator stateless 最好；简单任务无记忆可接近最优 | 四种 memory setting | pp. 7–8, Fig. 6 | medium |

## 公平性与可信度检查

- Table 2 的干净比较是同一已训练超网、同一 validation evaluator、同一资源上限下的 250-vs-1,000 candidate search；它支持 sample efficiency，但不是同候选预算的算法质量比较。
- 4–10× 是 search phase wall/GPU time 比，不含建立超网的共同前置成本；也没有分离 LLM serving 和子网 validation，因此不能外推为端到端 4–10× 或 API 成本优势。
- 宏观结果只有三次运行，且只报告每次最佳子网；没有候选级轨迹、显著性检验或同 250-candidate EA/RS 曲线。
- NAS-Bench-201 对比最多 100 个候选并做十次运行，预算较清楚；但部分 LLM-NAS baseline 数字标为转引，不能确认全部方法使用相同模型、prompt、候选与调用预算。
- 作者主动承认 Qwen 的预训练语料可能见过 NAS-Bench-201 架构；prompt 不提供 benchmark performance mapping，但仍无法排除记忆污染。（p. 3）
- 单 LLM消融保留 reflection→generation，只合并角色；它能检验角色分离，但不能隔离“第二个模型调用数”与上下文长度差异。
- Table 3 是跨论文 SOTA 汇总，不是统一训练 recipe 的 matched-budget 实验；77.9% 不应单独解释为搜索器普遍优越。

## 可复现性与代码/数据

- arXiv 补充材料公开宏观搜索空间和 prompt 示例，但未提供运行代码、环境锁、超网 checkpoint 链接、完整候选轨迹或 seeds。
- NAS-Bench-201 数据公开，OFA/SPOS/AutoFormer 有上游实现；然而缺少作者搜索器实现仍阻碍严格复现。
- 论文给出基础模型、vLLM、温度、候选预算、GPU 与部分运行次数，但没有 LLM sampling seed、token/call 预算、GPU partition、stop targets 或无效候选日志。

## 与 AgenticNAS 的关系

- typed structure vector + deterministic legality/evaluator 是最直接可复用设计；相比开放代码 mutation，更容易记录 attempted/accepted/evaluated 三层预算。
- stateful strategy / stateless generator 的分工值得在 block/cell/op 级动作上复现，并与单 LLM、无策略压缩及经典 evolution 做同候选、同 LLM-token、同 GPU-hour 对照。
- MobileNet 与 ShuffleNet 展示 block/op 级搜索；AutoFormer 展示 Transformer 宽度、深度、heads、MLP ratio，但其 12–16 层和二维视觉任务不能直接支撑 4–10 层 Conv1d Transformer 的质量结论。
- FLOPs/params 不是实测硬件 Pareto；`quality_proxy` 和 `latency_proxy_ms` 仍只能是流程占位符，不能从本文赋予研究含义。
- clean-room 复现只使用论文公开搜索空间、prompt、validation metrics 与公开超网，不传入内部 Archai、私有端点、内部日志或私有架构。

## 最小复现实验

- 固定一个公开 4–10 层 Conv1d Transformer 超网、训练 recipe、data split、真实设备和 250 个 evaluated candidates；每组至少五个 search seeds。
- 对照 random、regularized evolution、单 LLM direct generation、单 LLM strategy→generation、stateful Navigator + stateless Generator。
- 同时报 attempted/valid/unique/evaluated 数、LLM calls/tokens、LLM GPU-hours、candidate evaluation GPU-hours、超网训练/摊销成本与 wall time。
- 目标用 validation quality、实测 latency、peak memory、energy/cost 的 Pareto/hypervolume；test 只对冻结前沿做一次最终确认。

## 局限与风险

- 无代码与 traces；宏观任务只有三次运行，完整 stop condition、seeds 与失败行为未披露。
- 成本比较改变候选预算，不能区分 LLM 引导质量和更多/更少 evaluation 的预算效应；也没有同 250-candidate 经典 baseline。
- AutoFormer 深度为 12–16，非本仓库重点 4–10；没有 Conv1d 或真实 device metrics。
- NAS-Bench-201 可能存在 LLM 预训练污染，论文的 reasoning 样例不能排除记忆效应。
- 参数/FLOPs 约束与 A100 搜索耗时都不能替代部署端 latency、memory、energy 测量。

## 可引用摘要

CoLLM-NAS 将两阶段 NAS 的搜索阶段拆成有状态 Navigator、无状态 Generator 与确定性 Coordinator，在固定超网和结构化搜索空间中迭代生成、过滤和验证候选。作者在 MobileNet、ShuffleNet 与 AutoFormer 空间中以 250 个候选对比进化搜索的 1,000 个候选，报告 search-phase GPU days 降低 4.6–10 倍并略升准确率；该成本排除超网训练，且没有独立报告 LLM tokens/GPU 成本、同预算经典基线或公开代码，因此证据更适合支持“策略压缩与结构化生成可能提高候选效率”，不支持端到端加速或真实硬件 Pareto 结论。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2509.26037
- arXiv PDF：https://arxiv.org/pdf/2509.26037
- CVF 终版：https://openaccess.thecvf.com/content/CVPR2026W/CVPR-NAS26/html/Li_CoLLM-NAS_Collaborative_Large_Language_Models_for_Efficient_Knowledge-Guided_Neural_Architecture_CVPRW_2026_paper.html
- 已核对：标题、作者、版本日期、venue、arXiv DOI、搜索空间、Agent loop、模型/温度、候选预算、GPU、主要表格、消融与代码缺口。
- 未核对：独立运行、完整超网成本、LLM tokens/独立 GPU-hours、候选 traces、显著性、作者代码与真实设备指标。
- [ ] 已由人工决定 `retained` / `discarded`
