---
title: "Automated deep learning by recurrent hyperparameter optimization"
authors: "Zhanzhan Cheng, Yuyi Cheng, Chenbo Zhang, Xingbo Li, Jihong Guan, Fei Wu, Shuigeng Zhou"
year: "2026"
venue: "Nature Communications"
paper_url: "https://doi.org/10.1038/s41467-026-72413-9"
source_pdf: "../pdfs/2026-nature-rocket-hpo.pdf"
parser: "Codex"
parsed_on: "2026-07-29"
status: codex_draft
tags: [hpo, llm-policy, reinforcement-learning, tinyvit, edge-vision]
---

# Automated deep learning by recurrent hyperparameter optimization

> 本笔记由 Codex 基于 Nature 官方 article-in-press PDF 生成；数字是论文报告，尚未运行公开代码复现。

## 一句话结论

Rocket 把 Qwen2.5-0.5B-Instruct 训练成循环强化学习 HPO policy，在 8 类任务、32 个 benchmark 上搜索高维混合型训练超参；TinyViT/ImageNet 的最佳 75.34% 高于 GPT-4o/DeepSeek-R1 直接提议，但低于论文引用的 expert 76.25%，且没有优化端侧延迟、内存或能耗。（PDF pp.2, 6–8, 33）

## 研究问题与贡献

- 避免依赖人工离散网格或历史最优配置，直接生成连续与离散混合的 HP JSON。
- 通过 recurrent group policy optimization、动态 reference model 和 experience pool 自我改进。
- 用数据子集近似 reward，论文报告最高 80× policy-learning 加速。
- 在 EZVIZ 工业案例中报告优化周期缩短 13.4×、成本降低 73%。（PDF pp.2, 5–6, Sec. 2.7）

## 方法拆解

### 搜索或优化对象

- 每个目标网络架构固定，搜索 task-specific 的 20+ 训练超参，包括连续和离散变量。
- 目标函数是任务质量指标；结构、延迟、内存和能耗不在同一 HPO objective 中。
- 大数据集先在 split/subset 上评估，再用 learning-rate scaling 做全量训练。（PDF pp.3, 6–8）

### Agent 与优化闭环

- Qwen2.5-0.5B-Instruct 同时作为 policy/reference 的基础架构。
- Agent 根据历史 `(HP Config, performance)` 生成新配置；目标模型训练结果形成 reward。
- 每个阶段更新 policy、experience pool 和下一阶段 reference model。
- 输出需满足 JSON schema；语法合法是初始 policy 的最低要求。（PDF pp.25–29, 33）

### 评估与预算

- 8 类任务、32 个 benchmark，覆盖图像、文本、时间序列和音频。
- 默认 policy 0.5B；消融还比较 1.5B 和 7B。
- 实验平台为 NVIDIA A800 80GB；论文称 2 GPU 即可运行，一张生成配置、一张评估目标任务。
- 各目标任务的完整 GPU-hours、总候选数与统一 trial 预算未在主表中汇总，难与传统 HPO 做完全等成本比较。（PDF pp.7–8, 30–33）

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| TinyViT 上优于通用 LLM 直接提议 | ImageNet Top-1：Rocket max 75.34，GPT-4o 72.47，DeepSeek-R1 74.05 | GPT-4o、DeepSeek-R1 | p.7, Table 1 | high |
| TinyViT 尚未超过 expert proxy | Rocket 75.34 vs public expert result 76.25 | OpenMMLab/public result | pp.7–8, Table 1 | high |
| 覆盖多任务 | 8 类任务、32 benchmarks | BOGP、BOHB、DPO、GRPO、LLMs、public expert records | pp.6–8 | high |
| 工业部署降低周期与成本 | 13.4× optimization-time reduction，73% cost reduction | manual expert workflow | p.2, Sec. 2.7 | medium |
| Reward approximation 降低 policy 学习成本 | 最高 80× | full-data reward evaluation | pp.2, 6, Sec. 2.4 | medium |

## 公平性与可信度检查

- “Expert”是公开项目结果，不是相同硬件、trial 数和训练预算下重跑的专家对照。
- GPT-4o/DeepSeek-R1、BO/RL baselines 与 Rocket 的预训练/强化学习成本未统一折算。
- 大数据集使用 subset + scaling，TinyViT 75.34 带 split-data 标记；与 full-data expert 的口径不同。
- 论文称所有随机种子固定，但主文未给出每项比较的 outer-seed 数量。
- 工业效率来自作者自报案例，仍需独立账单与工作流复核。

## 与本仓库独立课题的关系

- Rocket 是目前最直接的“小 LLM policy + TinyViT HPO”证据，属于 `LLM × HPO`。
- 它固定目标网络，不应并入 NAS；TinyViT 结果也不能证明 LLM 能优化端侧硬件指标。
- 最值得验证的是训练过的 0.5B policy 是否优于通用 LLM→TPE，但其 policy-training 成本必须摊销记账。

## 最小复现实验

- 先使用公开 Rocket 代码在 mini-CIFAR/ResNet-18 上复现单/双 GPU 示例。
- 再固定 TinyViT 架构，对比 random、TPE、通用 LLM、Rocket policy 和 LLM→TPE。
- 统一 attempted trials 与每 trial 样本/time cap；分别报告 policy 训练成本、目标模型训练成本和最终设备指标。

## 局限与风险

- 论文承认高维非凸空间没有全局最优保证。
- 大模型/大数据 HPO 计算强度很高；论文称 `<100 A800` 时验证 `>1B` 模型和 `>1M` 样本可能不可行。
- 用 Rocket 调 Rocket 自身超参会带来二次方级成本。
- 论文没有展示真实边缘芯片上的 latency/energy HPO objective。

## 可引用摘要

Rocket 使用 Qwen2.5-0.5B-Instruct 构建循环强化学习 HPO policy，并在多模态任务中报告了较强结果。其 TinyViT/ImageNet 结果优于通用 LLM 直接提议但低于 public expert proxy，且采用 subset evaluation；因此它是小模型 HPO 的重要候选证据，而不是 hardware-aware NAS 或端侧多目标 HPO 的证明。

## 检索与人工核验记录

- 解析问题：TinyViT 数字、policy 架构、搜索空间、reward approximation、硬件与工业结果。
- 使用片段页码：2–8, 23–25, 30–33, 49。
- [x] 作者、DOI、TinyViT Table 1 和 Qwen2.5-0.5B 已核对
- [x] 官方 PDF 页数、代码/日志 Figshare 入口和硬件段已定位
- [ ] 公开代码尚未运行，13.4×/73% 工业账单尚未独立复核
- [ ] 已由人工决定 `retained` / `discarded`
