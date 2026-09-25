---
title: "An LLM-Assisted AutoML Framework for Intrusion Detection in IoT Networks"
authors: "Li Yang"
year: "2026"
venue: "arXiv:2609.23097v1; submitted to an IEEE journal"
paper_url: "https://arxiv.org/abs/2609.23097"
source_pdf: "https://arxiv.org/pdf/2609.23097"
parser: "Codex"
parsed_on: "2026-09-25"
status: codex_draft
tags: [automl-agent, hpo, cash, bounded-policy, intrusion-detection, adjacent-method]
---

# An LLM-Assisted AutoML Framework for Intrusion Detection in IoT Networks

> 本笔记基于 arXiv v1 PDF。该工作同时改变数据平衡、特征工程和模型/超参数策略，属于广义 AutoML Agent 邻接证据，不是固定架构 HPO，也不是 NAS。

## 一句话结论

- 核心主张：本地 Llama 3.1 8B 根据训练集统计生成一次性、受 schema 和边界约束的 AutoML policy，随后由 Optuna BO-TPE 在固定 LightGBM 分支内执行 10 个 trial；它提供了“小预算、可验证 policy”的实例，但没有 LLM proposal-feedback/reflection/memory 闭环。
- 证据位置：PDF pp.3–12，Fig. 1、Algorithm 1、Tables II–V。

## 搜索对象、变量与固定项

- LLM 可决定 AutoDP 的 sampler、目标分位数和 oversampling cap；AutoFE 的 mutual-information width、importance/correlation thresholds、feature caps；以及 CASH 的候选集、条件超参数范围和 trial budget（PDF pp.4–7）。
- 主实验的可执行分支把模型族固定为 LightGBM，再搜索树数、深度、learning rate、leaves、child samples、subsample、feature fraction、L1/L2 等字段；传统 CASH 对照还可在 LightGBM、Random Forest、Extra Trees 间选择（PDF p.7）。
- 固定项：两份预先选定的数据子集、80/20 outer split、12,000-sample search subset、3-fold CV、同一预处理规则和 hold-out test protocol（PDF pp.9–10）。
- 因数据平衡与 feature space 也由 LLM 改变，本工作不满足仓库“只改训练 recipe、架构/数据处理固定”的 HPO 边界；它也没有搜索 neural depth/width/op/connectivity。

## LLM/优化闭环与停止机制

- Llama 3.1 8B 只读取 aggregate dataset profile，以 temperature 0 输出 JSON；raw output 不直接执行，invalid/missing field 会被 allowlist、数值 clipping 和 deterministic default 修复（PDF pp.4–5）。
- LLM 不读取 trial score，也不在 BO-TPE 的 10 个 trial 间提出新配置；真正的 sequential feedback loop 属于 TPE，而不是 LLM。没有 reflection、memory、archive 或 LLM retry loop。
- 停止条件是预设 trial budget；最终配置按 validation F1 选择，hold-out test 只在最后使用（PDF pp.7–9）。

## 预算、失败与成本记账

- 主对比：proposed 10 trials；Traditional AutoML-TPE 10 trials（直接预算匹配）和 30 trials（较宽搜索参照）。两个数据集各执行一次 policy generation；耗时 6.88 s 和 4.99 s，输出均为 valid JSON，未触发 fallback（PDF p.9）。
- 实验机：Intel Core Ultra 7 255HX、NVIDIA RTX 5070、32 GB RAM；Python、Scikit-learn、Imbalanced-learn、LightGBM、Optuna、Ollama（PDF pp.8–9）。
- random seed 固定为 0；没有多 search seeds。LLM input/output tokens、费用、峰值显存/内存、GPU utilization、总训练能耗均未报告。
- attempted-trial budget=10；completed/evaluated、valid/failed/OOM/divergence/duplicate trial 数没有被单独报告。policy-level invalid 输出在主实验为 0，但论文没有给出更一般的 invalid rate。

## 核心结果

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 等 trial 下提高 test F1 | CICIDS2017 99.680% vs 99.532%；IoTID20 99.186% vs 98.844% | Traditional AutoML-TPE, 10 trials | PDF pp.9–10, Table IV | high |
| 等 trial 下并不更快 | 46.55 s vs 37.41 s；36.28 s vs 29.66 s | Traditional AutoML-TPE, 10 trials | PDF pp.9–10, Table IV | high |
| 对 30-trial TPE 有墙钟优势 | optimizer time 低 63.7%/49.9%，但候选空间与 trial 数不同 | Traditional AutoML-TPE, 30 trials | PDF pp.9–10, Table IV | high |
| CASH policy 是主要性能贡献 | A3 的增益最大；完整 A5 分别保留 41/19 features | 10-trial ablations A0–A5 | PDF pp.11–12, Table V | medium |

## 公平性、复现性与局限

- 10-vs-10 匹配 attempted trials，但 proposed 只执行 LightGBM compact envelope，传统 CASH 可选三种模型族；candidate space 并不相同，LLM policy generation 也不是传统对照的共同成本。
- 单 seed、两个经过 representative subset 处理的 IDS 数据集、已很强的 tree baselines，使 0.016–0.341 percentage-point 的增益难以外推。
- 报告的是最终模型 prediction latency，不是搜索目标中的真实 device latency；peak memory、energy 和 deployment cost 只列为未来工作（PDF p.12）。
- GitHub 仓库在核验时只有占位 README；`main` 为 `2da5aa7e278aec29e27aa201c7e266f29c483c3f`，说明“代码将于接收后发布”，尚不能复现。

## 与当前 AgenticNAS 的关系

- 可借鉴 bounded schema、allowlist、invalid fallback 和“LLM policy cost 与 optimizer cost 分开”的协议。
- 不能作为 memory-aware Agent 优于 stateless LLM 的证据，也不能与 Conv1d Transformer NAS 结果混合；若纳入 HPO 轨道，应先固定数据处理、feature space 和目标模型，再与 random/TPE/CMA-ES/pure LLM 在相同 attempted-trial/token/wall caps 下比较。

## 链接

- 论文：https://arxiv.org/abs/2609.23097
- 作者代码占位仓库：https://github.com/LiYangHart/LLM-Assisted-AutoML-For-Intrusion-Detection
