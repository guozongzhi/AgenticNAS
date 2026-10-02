---
title: "AutoBCI: Forecast-Guided Agentic Neural Architecture Discovery for EEG-Based Brain--Computer Interfaces"
authors: "Muyun Jiang, Yi Ding, Wei Zhang, Jinbo Chen, Chenyu Liu, Zhenjie Yang, Yuxin Li, Jingyuan Chen, Yuhao Lu, Yong Li, Shuailei Zhang, Cuntai Guan"
year: "2026"
venue: "arXiv:2609.35456v1"
paper_url: "https://arxiv.org/abs/2609.35456"
source_pdf: "https://arxiv.org/pdf/2609.35456"
parser: "Codex"
parsed_on: "2026-10-02"
status: codex_draft
tags: [llm-nas, eeg, code-generation, forecasting, early-stopping]
---

# AutoBCI

> 本笔记基于 arXiv v1 PDF。所有结果均为作者报告，不是本仓库实测；截至 2026-10-02 未找到官方代码仓库。

## 一句话结论

- AutoBCI 让六个 LLM 直接生成完整 PyTorch EEG 架构，再用 PEEK 根据前 10 个 epoch 的曲线预测 40-epoch 排名；它是直接 LLM-driven NAS，但 pool/parent 反馈不等于持久会话 memory。
- 论文的亮点是把生成、筛查、训练和预测 token/GPU 成本部分量化；缺口是 288 个请求仅 269 个进入三任务 pool，19 个损失没有按 invalid/OOM/divergence/duplicate 拆账。
- 证据位置：PDF pp.3–10、15–16、20–22，Tables 2、6，Figures 2–4。

## 搜索对象与闭环

- Agent 生成完整网络代码；参数量须小于 1M，排除 recurrent architecture。每轮从前代选 2 个 parent，各做 3 个 refinement，并生成 2 个 fresh candidates；第一轮全为 fresh。训练 recipe、split 和 evaluator 对每个任务固定。
- 六个 LLM 各跑 6 轮、每轮 8 个 proposal，即每个 LLM 48 个、总计 288 个请求。代码先过静态/数值检查和两个 synthetic optimizer steps，再分别在三类 EEG 任务上训练。
- 生成 prompt 禁止复制已有 source，但论文没有报告语义重复率。每次生成读取 parent 与结果，未建立跨轮对话 session；可视为显式 population feedback，而非已证实的 memory-aware policy。

## 预算、失败与成本

- 固定训练为每任务 40 epochs、AdamW、batch 512、BF16；硬件为 RTX PRO 6000 Blackwell。主结果使用 seed 0，且 cuDNN 非确定性；外部 baseline 多为 3 seeds，公平性有限。
- 269 个架构完成全部三任务并进入 pool，共 807 个 full task runs、32,280 task-epochs、68.58 GPU job-hours。请求到 eligible pool 的差额为 19；这是由文中总数推得，具体失败阶段未报告。
- PEEK 在 epoch 10 预测终局。若每轮仅保留 3 个候选，作者估计保留 91.7% winner，用 17,790 task-epochs 和 38.85 GPU job-hours，节省 44.9%。这是 retrospective estimate，不是独立线上搜索实测。
- 36 次 forecasting calls 合计约 1.167M input 和 0.120M output tokens；generation 合计约 0.281M input 和 0.501M output tokens。论文列模型单价但未汇总总 USD，也未给端到端墙钟、OOM、divergence 或 retry 计数。

## 核心结果与局限

| Claim | Result | Evidence locator | Confidence |
|---|---|---|---|
| 最佳平均 balanced accuracy | Claude Opus 4.6 候选平均 test bAcc 64.16，REVE 为 63.87；但 REVE 在 wF1/Kappa 领先 | PDF pp.7–10, Table 6 | medium |
| PEEK 早期预测 | epoch 10 的 MAE 从直接观测 2.20 降至 1.36 | PDF pp.8–9, Fig. 4 | medium-high |
| 预测并非全程占优 | epoch 16 时 best-observed aggregate MAE 0.88，优于 PEEK 1.18 | PDF pp.8–9, Fig. 4 | high |

- 三个任务共享同一候选代码，但各自独立训练；没有真实设备 latency、peak memory、energy 或 deployment Pareto 测量。
- 外部模型和六种 LLM 的预算、seed 与预训练信息并不完全匹配；0.29pp bAcc 差异不能直接写成等预算显著优势。
- 代码和配置声明未来发布；当前无法重放 prompts、筛查失败、269 个 eligible candidates 和 PEEK selection。

## 与当前 AgenticNAS 的关系

- 可借鉴“每轮 attempted → valid → 三任务 trained → forecast/selected”的账本和 early-fidelity 评估，但需要补齐 invalid、duplicate、retry 与 seed variance。
- 迁移到 4–10 层 Conv1d Transformer 时，应把开放式代码生成收敛为 typed `MutationAction`，固定 recipe，并与 native/random、stateless LLM、memory-aware LLM 做相同 candidate/GPU/LLM 预算比较。

## 链接

- 论文：https://arxiv.org/abs/2609.35456
- 代码：作者声明未来发布；截至 2026-10-02 未找到官方仓库
