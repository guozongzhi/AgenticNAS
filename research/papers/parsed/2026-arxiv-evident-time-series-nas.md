---
title: "Evidence-Guided Neural Architecture Selection under Uncertainty for Subject-Specific Blood Glucose Forecasting"
authors: "Md Azharul Islam, Dwyer Deighan, Tarunraj Singha, Danial Faghihi"
year: "2026"
venue: "arXiv:2606.05373v2"
paper_url: "https://arxiv.org/abs/2606.05373"
source_pdf: "https://arxiv.org/pdf/2606.05373"
code_url: "https://github.com/PCELab/EVIDENT"
parser: "Codex"
parsed_on: "2026-11-16"
status: codex_draft
tags: [nas, bayesian-evidence, conv1d, time-series, uncertainty, traditional-baseline]
---

# EVIDENT

> 本笔记基于 arXiv v2 官方 PDF。它是不用 LLM 的 Bayesian evidence 传统 NAS/selection 基线，直接覆盖 Conv1d 时间序列小模型。

## 搜索空间与停止机制

- 搜索 TCN block 数、filters、dilation base、encoder/decoder channels 与拓扑；训练/验证协议和 Bayesian evaluator 固定。主候选池 61 个架构、6 个容量等级，其中正文主要搜索 3–7 个 temporal blocks。（PDF pp.4–8）
- 每个等级先做 population training，再以 subject-specific evidence 排序并验证；首个通过 tolerance 的等级即停止。Level2Arch4 有 47,779 参数、5 blocks、`b=3`、`f=9`、channels `[2,4,8,16,32]`。（PDF pp.8–12）
- 10 个 in-silico subjects 做 5-fold protocol；tolerance 14.5 是经验选择，不是临床校准阈值。

## 结果与成本

- 正文展示的 19 个架构子集包含 EVIDENT 选择结果，不能解释成对任意 random search 的无偏胜出。对独立 day-6 windows，Level2Arch4 对 P3 的 NLPD/RMSE 为 8.44/9.33，RandArch8 为 8.52/13.51；P4 则为 7.98/7.98 对 6.86/5.28，说明并非所有指标都占优；validation rejected 为 0/24 对 1/24。（PDF pp.10–13）
- OhioT1DM 用 4 个病人训练、1 个目标病人适配，level-4 的 26,729 参数模型通过；该 validation 参与选择，不是独立 test。synthetic ECG 搜 41 个架构，level-2 的 3,964 参数模型在 13/13 subjects 通过。（PDF pp.13–15）
- Appendix F 报告 A100 40GB、32 CPU、16GB host：level 1–2 共 19 candidates，总墙钟 24:49:25；population training 15:56:21、evidence 00:40:28、四次 adaptation 分别 1:32:16/1:40:21/2:24:14/2:31:45，validation 约 4 min。50 samples 推理约 1.226 GFLOPs、1.12 s/window。（PDF Appendix F）
- 未报告 energy、真实终端 latency、peak GPU memory、invalid/duplicate/retry ledger；作者数字不是本仓库实测。

## 复现与课题价值

- 作者代码在 2026-11-16 可访问，核验 HEAD 为 `c81878736678bb7e162da45fd90798b4ae756c1a`；本轮未运行。仓库未包含 UVA/OhioT1DM 数据，仍有数据许可复现缺口。
- 可作为 4–10 层 Conv1d 的非 Agent baseline：保留 evidence gate 与容量分级停止，并与 random/evolution/Agent 在相同 attempted trials、GPU-hours、wall-time 和设备测量下比较。
- 官方 PDF：63 页，SHA-256 `57dc8a8ec4f6b54183504b5b5ded17a059250b688ab48c925592fd5afe608bcb`。

- [x] 架构字段、证据阈值与成本附录已核对
- [x] selection validation 与独立 test 边界已区分
- [ ] 人工决定 `retained` / `discarded`
