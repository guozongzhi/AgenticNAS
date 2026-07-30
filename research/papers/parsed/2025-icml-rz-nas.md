---
title: "RZ-NAS: Enhancing LLM-guided Neural Architecture Search via Reflective Zero-Cost Strategy"
authors: "Zipeng Ji, Guanghui Zhu, Chunfeng Yuan, Yihua Huang"
year: "2025"
venue: "ICML 2025; PMLR 267:27237-27254"
paper_url: "https://proceedings.mlr.press/v267/ji25a.html"
source_pdf: "https://raw.githubusercontent.com/mlresearch/v267/main/assets/ji25a/ji25a.pdf"
code_url: "https://github.com/PasaLab/RZ-NAS"
source: "official PMLR proceedings/PDF and author software repository, accessed 2026-07-30"
parser: "Codex"
parsed_on: "2026-07-30"
status: codex_draft
tags: [llm-nas, reflection, zero-cost, nas-bench-201, darts, mobilenet]
---

# RZ-NAS

> 本笔记基于 ICML 2025 PMLR 正式论文和 PMLR 直接链接的作者代码库。所有实验数字均为作者报告，尚未独立复现。

## 一句话结论

RZ-NAS 用结构化的文本/代码 prompt 让 GPT-4o 在 micro cell 与 macro backbone 空间中变异真实架构，再把执行异常和代码计算的 zero-cost score 反馈给反思模块；它提供了“错误反馈 + score reflection + 多空间复用”的强对照，但最终选择依赖 proxy，主要比较也未统一候选、LLM token 和完整训练预算，因此不能把其 GPU-day 表直接解释成端到端优势。（pp. 3–9）

## 书目信息与来源核验

- 作者：Zipeng Ji、Guanghui Zhu、Chunfeng Yuan、Yihua Huang。
- venue：Proceedings of the 42nd International Conference on Machine Learning（ICML 2025），PMLR 267:27237–27254。
- PMLR paper ID：pmlr-v267-ji25a；PMLR 页面未列 DOI。
- 论文：https://proceedings.mlr.press/v267/ji25a.html
- 代码：https://github.com/PasaLab/RZ-NAS；由 PMLR “Software” 直接链接，仓库公开实现但没有 release。
- 置信度：书目信息 high；方法 high；表格结果 medium；独立可复现性 medium。

## 研究问题与贡献

- 问题：既有 LLM-to-NAS 常局限于小搜索空间、代码生成成本高，且无法充分利用 zero-cost proxies 在标准 NAS benchmark 和 macro space 中快速评估。
- 方法：向 LLM 同时提供任务、搜索空间、模型构造与 proxy 的文本/代码描述；每次变异后由代码计算 proxy，并以新旧架构、score 和 exception 驱动内部/外部 reflection。
- 范围：NAS-Bench-201 与 DARTS micro cell、MobileNetV2 macro backbone、COCO detection backbone，覆盖 CIFAR、ImageNet 和 COCO。（pp. 6–9）

## 方法拆解

### 搜索或优化对象

- 搜索对象是真实神经网络架构；LLM 输出受 prompt 定义的 operation pool 和格式约束。
- micro：NAS-Bench-201/DARTS 的 cell operation 与连接；macro：MobileNetV2 inverted bottleneck/SE block 的层堆叠，并受 FLOPs budget 和 maximal depth 约束。
- COCO 搜索 ResNet-like backbone，与 MAE-DET 的 zero-cost detection setup 对齐。
- 这不是专门的 4–10 层 Conv1d Transformer，也不是多目标 Pareto 搜索；FLOPs 是硬约束，proxy score 是单一选择目标。

### Agent 与优化闭环

- 初始化随机 population；每轮随机选 parent，GPT-4o 生成 mutation。
- validator 检查输出、架构构建和 inference budget；不合法或异常候选不进入 population，exception 发送给 reflection。
- 对合法候选由代码计算指定 zero-cost score，而不是让 LLM 预测；population 以 proxy score 排序并淘汰最低分。
- 外部 reflection 读取变异前后架构、score 和 exception，生成下一轮建议；系统 prompt 同时要求内部反思。
- 论文没有报告统一 JSON schema、invalid/duplicate rate、异常分类统计或完整 action/result trace。（pp. 4–6）

### 评估与预算

- 每个 proxy × search space 运行 1,500 evolutionary iterations。
- population：NAS-Bench-201/CIFAR-10 为 100；CIFAR-100、ImageNet、COCO 为 256；全部从随机采样初始化。
- LLM：GPT-4o，temperature 从 `{0.2,0.4,0.6,0.8,1.0}` 采样；每轮 input 约 2,300–2,600 tokens、output 约 150–200 tokens；作者报告每个 proxy 约 75 美元。
- zero-cost proxies：GraSP、GradNorm、SynFlow、Zen-NAS、ZiCo 等；表中 search cost 随空间/方法约 0.01–0.5 GPU-days。
- 最优候选按各方法 recipe 完整训练三次；论文没有把所有对照统一为相同候选数、LLM calls/tokens、GPU 型号和完整训练 wall time。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| NAS-Bench-201 | `Ours(ZiCo)` test accuracy 为 CIFAR-10 94.24±0.12、CIFAR-100 73.30±0.21、ImageNet16-120 46.24±0.23 | ZiCo 93.35/70.71/46.18 | p. 7, Table 2 | medium |
| proxy 排序相关性 | 多个 proxy 的 Kendall/Spearman 均有小幅提高；如 ZiCo ImageNet 0.60/0.79→0.64/0.81 | 原 zero-cost proxy | p. 7, Table 3 | high |
| DARTS space | `Ours(ZiCo)` test error CIFAR-10 2.41±0.13、CIFAR-100 17.49±0.08 | ZiCo 2.45/17.78 | p. 8, Table 4 | high |
| MobileNet macro | 450M FLOPs 下 `Ours(ZiCo)` ImageNet top-1 error 21.0%，表列 search cost 0.4 GPU-days | ZiCo 22.0%，DONNA 22.0% | p. 8, Table 5 | medium |
| 组件消融 | 去掉 in-context example、reflection、code/text description 均降低作者图中的最终准确率 | Full RZ-NAS | p. 8, Fig. 3 | medium |

## 公平性与可信度检查

- Table 2/4/5 混合使用论文复现和已发表结果，搜索空间、operation set、训练 recipe 与 search method cost 口径并非完全一致；不能把“62× faster”当作严格 matched-budget 结论。
- 作者明确报告每 proxy 的 LLM token 范围与约 75 美元，是良好成本证据；但未报告 reflection 是否额外一次调用、失败调用数、总 API calls 和不同模型价格快照。
- NAS-Bench-201 最优候选训练三次，但 1,500-iteration 搜索自身的多 seed variance 未清楚报告。
- zero-cost proxy 可用于快速排序，却不等同于真实训练质量；相关性提升幅度在部分设置较小，仍需最终真实训练。
- FLOPs budget 不是设备 latency、energy 或 memory；论文不支持本仓库的多目标硬件 Pareto 结论。

## 可复现性与代码/数据

- PMLR 提供正式 PDF，作者仓库公开 micro/macro search space、zero-cost proxies、prompt 和 evolution implementation。
- 论文提供 1,500 iterations、population size、temperature、token 范围、proxy 与数据集配置；公开 benchmark 可降低数据复现门槛。
- 仓库没有 release；README 只给简要运行入口，未见完整依赖锁定、GPT-4o snapshot、search seeds、原始 traces 或所有表格的一键复现协议。

## 与 AgenticNAS 的关系

- 最可复用的是 reflection payload：`parent action + validated result + score + typed exception`。本仓库可把它限制为 clean-room JSON，而不是向 LLM 发送任意内部代码、日志或 endpoint。
- micro/macro 统一 prompt 可映射到 4–10 层 Conv1d Transformer 的 block/cell/op 层级，但 Agent 应只发 `MutationAction`，由本地 validator 构造模型。
- 应将 RZ-NAS 的 zero-cost score 作为 proposal/ranking 消融，而不是研究终点；所有最终 Pareto claims 仍需真实 quality/latency/memory 测量。
- `quality_proxy` 与 `latency_proxy_ms` 继续只作控制流占位符，不能引用 Table 2–5 为仓库结果。

## 最小复现实验

- 固定同一 4–10 层 search space、训练 recipe、候选数、GPU-hours、LLM calls/tokens 和三组 search seeds。
- 对照 native random mutation、stateless LLM、LLM + error reflection、LLM + error/score reflection；另比较 random parent 与 highest-score parent。
- proxy 只用于搜索排序；top-k 候选统一完成真实训练和设备测量。
- 指标：真实质量/latency/memory、hypervolume、proxy rank correlation、validity、duplicate rate、seed variance 和总成本。

## 局限与风险

- 单 proxy 优化可能奖励与最终质量相关性不足的结构；跨 search space 的 proxy 可靠性并不恒定。
- 论文未报告严格 matched-budget LLM baselines、搜索 seed variance、失败/重复率和完整调用账。
- structured prompt 包含大量代码与描述，约 2.3k–2.6k input tokens/轮；迁移到私有系统必须经过窄接口和 clean-room 审查。
- FLOPs 与 GPU-day 表不能替代目标设备实测 latency、memory、energy 和端到端成本。

## 可引用摘要

RZ-NAS 在 micro cell 与 macro backbone 空间中用 GPT-4o 生成结构变异，以代码计算的 zero-cost proxy 评估候选，并把 score 与执行异常反馈到内部/外部 reflection。作者在 NAS-Bench-201、DARTS、MobileNet 和 COCO 上报告优于对应 proxy 的最终模型，并公开代码与单 proxy 约 75 美元的 LLM 费用估算。其证据仍受 proxy 排序、未统一的对照预算和缺少搜索 seed/失败统计限制，不能直接支持真实硬件多目标结论。

## 检索与人工核验记录

- PMLR：https://proceedings.mlr.press/v267/ji25a.html
- PDF：https://raw.githubusercontent.com/mlresearch/v267/main/assets/ji25a/ji25a.pdf
- 代码：https://github.com/PasaLab/RZ-NAS
- 已核对：标题、作者、venue、页码、micro/macro search space、reflection loop、1,500 iterations、population、token/费用和主要表格。
- 未核对：独立运行、GPT-4o snapshot、完整 API call 账、搜索 seed variance、所有 baseline 的统一重跑。
- [ ] 已由人工决定 `retained` / `discarded`
