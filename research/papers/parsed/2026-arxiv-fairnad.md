---
title: "Structuring Open-Ended NAS: Semi-Automated Design Knowledge Structuring with LLMs for Efficient Neural Architecture Search"
authors: "Yuiko Sakuma, Masakazu Yoshimura, Marcel Gröpl, Zitang Sun, Junji Otsuka, Atsushi Irie, Takeshi Ohashi"
year: "2026"
venue: "arXiv:2605.19247v1"
doi: "10.48550/arXiv.2605.19247"
paper_url: "https://arxiv.org/abs/2605.19247"
code_url: "not reported"
source: "arXiv HTML/PDF/TeX source, accessed 2026-07-29"
parser: "Codex"
parsed_on: "2026-07-29"
status: codex_draft
tags: [llm-nas, open-ended, pareto, evolution, nas-bench-201]
---

# Structuring Open-Ended NAS / FairNAD

> 本笔记基于 arXiv v1 正文、PDF 和 TeX 源码。所有实验数字均为作者报告，未发现论文自带的公开代码链接，也尚未独立复现。

## 一句话结论

FairNAD 将论文设计知识组织成 operation、block/connectivity、network 三级属性树，再以公平抽样、Pareto-aware mutation、LLM iterative mutation 和执行/预算/结构 verifier 搜索真实 PyTorch backbone；它与本仓库的 block/cell/op、Pareto 和 validity 目标高度相关，但 500 候选搜索需约 24–30 GPU-days/数据集，且 LLM token 成本未量化。（§3–5，Appendix A）

## 书目信息与来源核验

- arXiv ID：2605.19247v1；提交日期：2026-05-19；arXiv DOI：10.48550/arXiv.2605.19247。
- 作者：Yuiko Sakuma、Masakazu Yoshimura、Marcel Gröpl、Zitang Sun、Junji Otsuka、Atsushi Irie、Takeshi Ohashi。
- 当前可核验 venue 为 arXiv；TeX 使用 NeurIPS 2026 样式不等于已录用。
- 论文：https://arxiv.org/abs/2605.19247
- 代码：正文和 arXiv metadata 未给出作者实现链接；只说明基于 OpenMMLab，并在部分实验中使用 NADER 仓库实现。
- 置信度：方法和预算 high；结果 medium；代码可用性 high（未报告）。

## 研究问题与贡献

- 问题：开放式代码 NAS 虽能突破人工搜索空间，但设计 ideas 容易受论文潮流、LLM prior 和粒度混杂影响，导致偏置、低质量或不适用的变异。
- 知识结构：用 14 个参考视觉架构和人工定义的高层模板生成 15 个 main categories、55 个 sub-categories；再从 2,353 篇摘要筛出 1,149 篇，提取 15,323 个设计 ideas。（§5）
- FairNAD 依次执行 fair idea sampling、Pareto-aware mutation 和 LLM-driven iterative mutation，并以 verifier loop 修复或缩减候选。（§4）

## 方法拆解

### 搜索或优化对象

- 搜索对象是可初始化、可微、具有 forward/backward 的多层 PyTorch 视觉 backbone，不搜索 neck/head，也不是 Agent 工作流。
- 搜索空间为开放代码级：可修改 operation、block/connectivity 和 network，包含卷积、Transformer、MLP、pooling、深度、宽度和拓扑。
- 主实验从 CIFAR 版 ResNet-32 出发，限制参数量 ≤1.5M；CIFAR-10/100 FLOPs ≤0.2G，ImageNet16-120 ≤0.05G。
- Pareto 维度是 accuracy、parameter size 和 FLOPs；不是实测设备 latency、memory 或货币成本。

### Agent 与优化闭环

- 输入：parent code、结构化设计 idea、历史中的 accuracy/HW budgets，以及 verifier 的错误或越界信息。
- 动作：LLM 直接重写完整 PyTorch model code；不是声明式 mutation schema。
- Stage I 按属性公平抽样 idea；Stage II 用 NSGA-II 风格从 Pareto frontier 选 parent，再做 scale-up 或非深宽超参调整；Stage III 从高性能历史中归纳相近/相反 idea 并重复两步 refinement。
- verifier：执行失败最多 debug 2 次；预算越界最多 downscale 4 次；结构检查要求代码确有架构变化且仍为多层模型。
- 每轮三个阶段分别生成 8、8、4 个候选，Stage III 每个候选含 2 次 iterative steps。（§4，Appendix A.2）

### 评估与预算

- 数据：NAS-Bench-201 协议下的 CIFAR-10、CIFAR-100、ImageNet16-120。
- 训练：遵循 NAS-Bench-201 的数据 split、200 epochs 和优化设置；主结果搜索 100/500 个新架构，三次运行报告均值和标准差。
- 硬件：4×A100 40GB，每卡两个并行流，共 8 路候选评估。
- 500 候选的作者报告成本：CIFAR-10 24.22、CIFAR-100 26.56、ImageNet16-120 30.06 GPU-days。
- LLM：知识抽取和主搜索使用 Qwen3-8B；另测试 Qwen2.5-Coder 7B/32B、Qwen3 4B/32B。论文明确承认 token 需求高，但未给出 token/费用账。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 500 候选结果 | test acc 95.46±0.10 / 78.17±1.25 / 52.87±1.32 | NADER 94.62 / 76.00 / 50.52 | Table 1 | medium |
| 公平抽样贡献 | CIFAR-100 test 75.24→77.05 | uniform vs fair attribute sampling | Table 2 | high |
| Pareto + iterative 组合 | Pareto 后 77.28；加入 iterative 后 77.97；iterative 单独为 75.64 | 分阶段消融 | Table 2 | high |
| verifier 有效性 | 完整 loop pass rate 0.56；去除 budget verifier 为 0.04 | feedback-loop ablation | Table 3 | high |
| 搜索成本 | 500 候选为 24.22–30.06 GPU-days/数据集 | 无统一端到端基线成本表 | Appendix A.4 | high |

## 公平性与可信度检查

- 作者固定 NAS-Bench-201 split、训练超参、参数/FLOPs 上限，并对 500 候选报告三次运行，这是较强的协议透明度。
- 但开放代码空间并非 NAS-Bench-201 的 15,625-cell 离散空间；表中的“NAS-Bench-201 Optimal”和传统方法并不处于完全相同搜索空间，横向结论需谨慎。
- NADER 作为最接近基线也使用论文知识和代码生成，但正文没有给出统一 LLM token、wall-clock 和 API/推理成本。
- accuracy 与 FLOPs/params 的 Pareto-aware parent sampling并不等同于最终多目标报告；主表只报告 accuracy，未报告 hypervolume 或完整 Pareto front。
- 论文公开 prompts 和三 seed 结果，但未给出可核验作者代码或全部搜索 traces。

## 可复现性与代码/数据

- TeX 源包含完整 prompts、伪代码、训练设置、消融表和三个发现架构的 PyTorch listing。
- 未发现官方代码仓库；知识库的完整 15,323 ideas、筛选结果和搜索 trace 未在 arXiv 页面链接。
- 知识来源使用 CVPR 2023 open-access 论文；复现需同时核对抓取条款、具体许可和 idea extraction 版本。

## 与 AgenticNAS 的关系

- 属性树可直接映射为本仓库的 `op`、`cell/block`、`network` 三层 action taxonomy，用于测量不同粒度的覆盖率与有效率。
- fair sampling 可用于约束 Agent 不只重复 attention/常见 conv 变异；但应对“属性类别”公平抽样，而不是对未经验证的自然语言 idea 直接执行。
- Pareto-aware parent sampling适合真实 quality/latency/memory/cost 目标；本仓库不应以 params/FLOPs 或 `quality_proxy`、`latency_proxy_ms` 替代真实测量结论。
- verifier loop 的 execution/budget/structure 三类错误码值得保留到 trace；clean-room 公开层只记录声明式 action、错误码和聚合指标，不暴露内部 evaluator 或日志。

## 最小复现实验

- 在 4–10 层 Conv1d Transformer 中定义稳定的 op/block/network 属性树，并为每条 mutation 标注唯一层级。
- 对照 uniform action、attribute-fair action、Pareto-parent + fair action、memory-aware iterative action。
- 固定候选数、训练 steps、GPU 时间、LLM 调用、seeds 和硬件；所有候选通过同一 schema validator。
- 报告 hypervolume、validity、duplicate rate、各属性覆盖、预算违规率、真实 latency/memory 和 seed variance。

## 局限与风险

- LLM 直接生成整段代码，主要失败包括截断、组件幻觉、shape mismatch、downscale 失败和结构误判；作者也认为 prompt-only 修复有限。
- 主实验局限于视觉 backbone 和三个小型 benchmark 数据集，不能直接外推到 Conv1d Transformer。
- 搜索 GPU 成本高，LLM token 成本未量化；没有官方代码和 trace 降低了复现可信度。
- 结构化知识仍含人工模板与人工清洗，所谓“公平”依赖类别定义和不平衡程度。

## 可引用摘要

FairNAD 先将视觉架构知识组织为 operation、block/connectivity 和 network 层级，再通过公平 idea 抽样、Pareto-aware parent mutation、LLM iterative refinement 和 verifier loop 搜索开放式 PyTorch backbone。作者在 NAS-Bench-201 协议下报告三 seed 的 accuracy 提升和关键消融；但开放代码空间与传统 NAS-Bench-201 方法并非完全同构，500 候选需约 24–30 GPU-days，且官方代码、完整 trace 和 LLM 成本尚未公开。

## 检索与人工核验记录

- 原始来源：https://arxiv.org/abs/2605.19247
- 已核对：标题、作者、日期、arXiv ID、DOI、知识库规模、方法阶段、参数/FLOPs 约束、GPU-days、三 seed 表格和局限。
- 未核对：官方代码、完整知识库、LLM token/费用、独立复现。
- [ ] 已由人工决定 `retained` / `discarded`
