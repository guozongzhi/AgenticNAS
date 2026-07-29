---
title: "AutoMMLab: Automatically Generating Deployable Models from Language Instructions for Computer Vision Tasks"
authors: "Zekang Yang, Wang Zeng, Sheng Jin, Chen Qian, Ping Luo, Wentao Liu"
year: "2025"
venue: "AAAI 2025"
paper_url: "https://arxiv.org/abs/2402.15351"
source_pdf: "../pdfs/2402.15351-autommlab.pdf"
parser: "Codex"
parsed_on: "2026-07-29"
status: codex_draft
tags: [hpo, cv, deployment, edge-vision]
---

# AutoMMLab

> 本笔记由 Codex 基于 arXiv v2 PDF 的页码证据生成；在人工核验前仍是草稿。

## 一句话结论

AutoMMLab 把需求理解、数据/模型选择、HPO 和部署串成 request-to-model 流程，其中 HPO-LLaMA 由 8,000 次真实 CV 训练结果微调而成，可对固定模型连续提议训练配置；硬件约束用于选模与部署，并未成为 HPO 的联合目标。（PDF pp.1, 3–7）

## 研究问题与贡献

- 用自然语言请求驱动分类、检测、分割和关键点任务的端到端模型生产。
- HPO-LLaMA 是 LoRA 微调的 LLaMA-7B，训练数据来自四类 CV 任务的 `request-hyperparameter-performance` triplets。
- LAMP benchmark 评估 request understanding、HPO 与端到端模型生产。（PDF pp.1, 5–8）

## 方法拆解

### 搜索或优化对象

- HPO 搜索 optimizer、initial learning rate、decay policy、weight decay、batch size 和 training iterations。
- 目标架构先由 model zoo 选定；参数量、FLOPs、推理速度和性能用于模型过滤。
- 部署阶段通过 MMDeploy 输出 ONNX、NCNN、OpenVINO 等后端。（PDF pp.3–6）

### Agent 与优化闭环

- 第 1 轮输入数据/模型描述与搜索空间，HPO-LLaMA 输出训练配置。
- 后续轮次把上一次训练结果写入对话，由模型继续提议配置。
- 训练集由 4 类任务 × 100 requests × 20 随机配置形成 8,000 次实验，再构造 1–3 轮对话用 LoRA 微调 LLaMA-7B。（PDF p.6）

### 评估与预算

- 四类 CV 任务：分类、检测、分割、关键点。
- Random 使用 10 rounds，并把流程重复 1,000 次估计均值/方差；BayesianRF/GP 使用 5 rounds。
- 通用 LLM 与 HPO-LLaMA 主要比较 1 round，HPO-LLaMA 另报告 3 rounds。
- 论文将 test-set 结果直接反馈给 HPO-LLaMA；这不符合本仓库要求的 validation/test 隔离。（PDF pp.6–7, 16–17）

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| HPO-LLaMA 使用真实训练轨迹微调 | 8,000 次实验；1–3 轮对话；LoRA 微调 LLaMA-7B | 通用 LLM prompting | p.6, Sec. 5 | high |
| 一到三轮可持续改善 | Cls. 0.975→0.983，Det. 0.435→0.440，Seg. 0.854→0.856，Kpt. 0.728→0.738 | HPO-LLaMA 1 round | p.7, Table 2 | high |
| 小型部署链路可运行 | MobileNetV3-Large：5.48M、0.23 GFLOPs、174.42 FPS；三轮 HPO 后示例 accuracy 98.01% | 用户请求阈值 | p.4, Fig. 2 | medium |
| HPO-LLaMA 优于 random 曲线 | 四类任务的 mean metric 曲线更快上升 | 10-round random | p.7, Fig. 5 | high |

## 公平性与可信度检查

- Random 10 rounds、Bayesian 5 rounds、LLM 1/3 rounds 的口径不同，Table 2 不是完全等预算比较。
- HPO 闭环使用 test-set performance 作为反馈，存在测试集过拟合/泄漏风险。
- 8,000 次预训练 HPO 数据的生成成本没有计入推理时的 trial 效率。
- MobileNet 示例把选模、HPO 和部署串在一起，无法单独归因 98.01% 给 HPO-LLaMA。

## 与本仓库独立课题的关系

- HPO-LLaMA 属于固定架构的训练配方优化，可纳入 `LLM × HPO`；model zoo 选模和部署约束是相邻流程。
- 不应把按参数/FLOPs/速度选模型写成 LLM HPO 的硬件目标，也不应由此推断 hardware-aware NAS。
- 可借鉴 task/model card 输入和结构化 JSON 配置，但必须改为 validation feedback，test 只用于最终一次评估。

## 最小复现实验

- 固定 MobileNetV3 或 MobileViT 架构与数据划分，只搜索六个训练超参。
- 比较 random、TPE、通用 LLM、LLM→TPE；不把模型选择和部署时间计入 HPO 收益。
- 使用 validation best-so-far 选配置，最终 test 只评估一次，并单独报告真实设备延迟。

## 局限与风险

- 系统依赖 OpenMMLab model/dataset zoo，超出支持范围时可能失败。
- HPO-LLaMA 依赖大规模离线实验数据，迁移到新任务/新模型的泛化未充分隔离。
- 论文系统级示例没有提供边缘设备上的功耗、内存和端到端延迟优化证据。

## 可引用摘要

AutoMMLab 的 HPO-LLaMA 使用 8,000 个 CV 训练实验微调 LLaMA-7B，并在固定模型上迭代生成训练超参数。系统同时支持按参数量、FLOPs 和速度选模及部署，但这些硬件约束不属于 HPO 目标；此外，其 test-set feedback 和不等轮次基线限制了直接复用。

## 检索与人工核验记录

- 解析问题：HPO 搜索空间、训练数据、轮次基线、MobileNet 示例与部署边界。
- 使用片段页码：1, 3–7, 16–17。
- [x] 作者、AAAI 2025 状态和 arXiv v2 已核对
- [x] 8,000 experiments、六个超参、Table 2 和 MobileNet 示例已定位
- [ ] 8,000 个训练结果的数据许可与生成脚本尚未运行核对
- [ ] 已由人工决定 `retained` / `discarded`
