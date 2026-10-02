---
title: "PINNMorph: Evolving Online Adaptation Policies for Physics-Informed Neural Networks"
authors: "Xu Yang, Mingyang Yu, Jun Zhang, Keqian Li, Jing Xu"
year: "2026"
venue: "arXiv:2609.32685v1"
paper_url: "https://arxiv.org/abs/2609.32685"
source_pdf: "https://arxiv.org/pdf/2609.32685"
parser: "Codex"
parsed_on: "2026-10-02"
status: codex_draft
tags: [automl-agent, mixed-search-space, online-adaptation, pinn, evolution]
---

# PINNMorph

> 本笔记基于 arXiv v1 PDF。论文同时改变 topology、loss、sampling、gradient 和 optimizer，按本仓库规则归为 `mixed-search-space`，不是纯 NAS 或固定架构 HPO。

## 一句话结论

- PINNMorph 在同一次 PINN 训练中，每 200 steps 诊断一次，再从演化的声明式 policy 选择动作；LLM 负责生成/进化 policy，确定性 executor 校验和回滚，不直接生成模型代码。
- 它提供了完整调用/token/墙钟表，但相同 20k optimizer steps 不代表相同 GPU 工作量：模型宽度/层、采样和 loss 都可变化，且硬件、参数轨迹、invalid/rollback 分母未报告。
- 证据位置：PDF pp.3–11、15–18，Figures 2–5、Tables 1–4。

## 搜索对象、固定项与闭环

- 初始 PINN 为 4 个 hidden layers、width 128、tanh；总训练 20,000 optimizer steps，结构动作仅在 step 400–14,000 开启，population size K=5。
- 16 个高层动作映射到 23 个 primitive mechanisms，包括 widen/add/prune/redistribute、additive branch、loss/objective 权重、gradient、adaptive sampling 和 optimizer phase。结构与 recipe 混合，因此不可跨轨引用。
- DeepSeek-V4-Flash 以 temperature 0.7 生成/进化 policies，Qwen3.8-27B 以 temperature 0 评分。executor 检查类型/约束并可回滚；每次 observation 进入 policy archive。
- counterfactual feedback 由最近 7 点的局部 continuation 估计，没有并行 shadow control，不能解读为实测因果反事实。

## 预算、失败和结果

- 13 个 PDE、每项 5 seeds；所有主方法使用相同 20k optimizer-step 上限。作者报告 full PINNMorph 在 13/13 个 PDE 上平均 MSE 最佳。
- 成本表：No Morph 为 0 calls/0 tokens/1250s；Random Selection 为 30 calls/6.52e4 tokens/1273s；Random Evolution 为 33/1.06e5/1286s；PINNMorph 为 38/4.40e5/1308s。货币成本和硬件未报告，表中墙钟的汇总口径也不够明确。
- full method 的 median MSE ratio 归一为 1.0，Random Selection/Random Evolution 为 10.77/10.30。比较包含 SA-PINN、ConFIG、RoPINN、HARMONIC、PINNsAgent，但各方法动态参数量与计算量未按 GPU-hours 配平。
- validation/rollback 机制明确，invalid、OOM、divergence、duplicate、retry 的数量均未报告；代码仓库也未在论文或作者页面中找到。

## 与当前 AgenticNAS 的关系

- 可借鉴声明式 policy、executor validation 和 action/result memory；但需要把 architecture、loss、sampling 与 optimizer 分轨，避免把 mixed-space 收益写成 NAS 或 HPO 证据。
- 若迁移到 NAS，应固定 recipe/evaluator 并记录 attempted、valid、executed、rolled-back、duplicate 和真实 GPU/LLM/墙钟成本。

## 链接

- 论文：https://arxiv.org/abs/2609.32685
- 代码：截至 2026-10-02 未找到官方公开仓库
