---
title: "Bayesian Optimization in Sequence-to-Architecture Latent Space for Zero-Shot NAS"
authors: "Ondrej Tybl, Lukas Neumann"
year: "2026"
venue: "arXiv:2610.06167v1"
paper_url: "https://arxiv.org/abs/2610.06167"
source_pdf: "https://arxiv.org/pdf/2610.06167"
parser: "Codex"
parsed_on: "2026-10-09"
status: codex_draft
tags: [nas, traditional-baseline, bayesian-optimization, zero-shot, latent-space, duplicate-control]
---

# Sequence-to-Architecture latent BO

> 基于 arXiv v1 的 18 页 PDF。该方法没有 LLM/Agent，是传统 zero-shot NAS/BO 邻接基线。

## 搜索空间、闭环与成本

- 搜索 UniNAS 的 mixed convolution/transformer DAG block；prefix encoding 经 4.2M 参数 VAE 映射到 latent space，GP+expected improvement 提议，VKDNW 等零成本 proxy 标量化给反馈。结构可变、标准 UniNAS 训练协议固定，属于 NAS（PDF pp.4–10）。
- VAE 用约 96k 随机 blocks、2,048 validation blocks，50 epochs，单 A100 约 12 GPU-hours。search 从 256 个 seed architectures 开始，跑 10,000 iterations，单 GPU 8h；约束参数量，最终只 full-train 一个候选（pp.8–10）。
- decoder 用 grammar 保证 syntax，但 shape 仍可能非法；论文称少于 5% decoded samples 被丢弃。每次 latent proposal 最多扰动 retry 100 次，但没有 attempted/valid/duplicate/retry 的完整整数账本（pp.6、8）。

## 核心结果与边界

- ImageNet-1K top-1 81.51%、27.0M params、9.1G FLOPs；UniNAS-A 81.15%、search 0.5 GPU-days，本文 search 0.33 GPU-days。最终训练为 8×A100×32h，远大于表中的 search-only 成本（pp.9–10, Tables 1–2）。
- COCO/APb 42.9、APm 39.8，ADE20K mIoU 46.1；但 FPS 13.5/62.4 均不优于全部 baselines。fine-tuning 分别 4×A100×24h 与 15h（p.10, Table 3）。
- ablation 只训练每个 variant 选出的单一最终架构；graph-VAE variant 最终训练发散。没有多 search seed、显著性或真实 latency/energy/memory；proxy noise 下取 99th percentile 而非 maximum 是人工稳健性选择（pp.10–11）。

## 当前价值

- 可作为非 LLM latent-BO baseline，并提醒把 proposal validity、retry、duplicate 和 generator pretraining 单独计费；不能把 0.33 GPU-days 写成端到端成本。
- 若迁移到 4–10 层 Conv1d Transformer，应与 native evolution、random、stateless/memory-aware LLM 在相同 attempted/evaluated budget 和多 search seeds 下比较，最终候选统一训练。

## 链接

- 论文：https://arxiv.org/abs/2610.06167
