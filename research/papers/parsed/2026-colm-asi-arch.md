---
title: "Neural Architecture Discovery via Autonomous Evolution"
authors: "Weixian Xu, Yixiu Liu, Yang Nan, Lyumanshan Ye, Xiangkun Hu, Zhen Qin, Pengfei Liu"
year: "2026"
venue: "COLM 2026; arXiv:2507.18074v2"
paper_url: "https://arxiv.org/abs/2507.18074"
source_pdf: "https://arxiv.org/pdf/2507.18074"
code_url: "https://github.com/GAIR-NLP/ASI-Arch"
parser: "Codex"
parsed_on: "2026-10-12"
status: codex_draft
tags: [llm-nas, autonomous-research, architecture-evolution, memory, code-generation]
---

# ASI-Arch

> 基于 COLM 2026 camera-ready（arXiv v2，44 页）、OpenReview 引用与作者仓库核验。所有数值均为作者报告，不是本仓库实测。

## 搜索对象、闭环与固定项

- ASI-Arch 让 Researcher 直接提出并实现 linear-attention layer 代码，经 novelty/sanity gate、真实训练、debug agent、Analyzer 和 Experience Repository 形成 research–experiment–analyze–update 闭环。它改变 operator、routing、gating、information flow 与 connectivity，属于开放式 LLM-NAS；不是固定架构 HPO（PDF pp.3–4）。
- memory 包括全部实验、top-50 candidate pool、parent/sibling 关系、失败日志、Analyzer insight，以及约 100 篇论文蒸馏出的约 150 条 cognition。每轮从 top-10 取一个 parent、从 11–50 取四个 references；前 200 次 exploration 冻结 pool，之后批量更新（p.4）。
- 20M exploration、340M verification 与 1.3B final validation 使用固定数据、训练协议和 evaluator；20M 为 8 层、hidden 256、8 heads、2,000 steps、batch 256、1B FineWeb-Edu tokens。340M 为 24 层、hidden 1024、1B tokens；最终 1.3B 用 15B tokens（pp.4–5、15）。

## 预算、合法性与停止机制

- 主搜索 attempted 1,773 个 20M experiments，约 10,000 GPU-hours；其中 1,350 个同时通过 quantitative/qualitative filters，约 150 个进入 340M verification，105 个达到论文定义的受控 340M SOTA，top 5 进入 1.3B validation。论文导言给出整个研究约 20,000 total GPU-hours（pp.1、5）。
- proposal 先做 embedding top-5 motivation 去重和 LLM novelty judgement，再做 complexity、causal mask 与实现 sanity check；训练失败由 debugging agent 修复重试。monitor 在异常低 loss、编译过慢或训练速度慢于 baseline 2 倍时终止（p.3）。论文没有公开主搜索 attempted→novelty reject→sanity reject→debug retry→trained 的完整逐类账本，也未报告 LLM calls、tokens、费用、wall-time 或 energy。
- matched 120-attempt 比较中，ASI-Arch 与 OpenEvolve 使用相同 DeepSeek-V4-Flash proposer 和 20M/1B-token evaluator；valid database result rate 为 37.4% vs 8.3%。这是 raw-attempt legality 证据，但两套系统的内部 agent/tool 成本没有匹配（p.10, Table 5）。

## 核心结果与效率

- 1.3B top-5 在 10 个 development 与 6 个额外 generalization benchmarks 上比较；作者报告最佳模型相对 DeltaNet overall average +0.97 points，Mamba2 为 +0.34。105 个模型中 900 次以后发现者约 78% 的 parent 来自前 900 次，支持 archive reuse，但不等于独立消融证明 memory 因果贡献（pp.5–7, Figures 2–4）。
- 两次 120-result DeepSeek-V4-Flash rerun 的 best-score-curve AUC 为 281.3209 与 280.0682，差 0.45%；这是短跑 evolution trend 的重复性，不是 1,773 次主搜索的多 seed 重复（pp.7、15–16, Table 6）。
- 1.3B 同机测量中，ASI-Arch-1–5 peak memory 为 16.28–22.75 GB，训练 throughput 3,426–4,168 tok/s；DeltaNet 为 11.44 GB、5,063 tok/s。论文有真实性能/显存测量，但没有 latency、energy 或 Pareto/hypervolume search（p.10, Table 4）。
- 作者仓库本轮 `HEAD=3113c51b04a1d4a7520a3b0238c6a08d3194d58f`，含 framework、cognition base 与 model gallery；本轮未运行代码。

## 公平性、风险与当前价值

- fitness 同时使用 loss、development benchmarks 与 LLM judge；后期 sigmoid 压平 quantitative differences 后 LLM-judge 权重相对增大。主结果不能拆出 memory、cognition、judge、debugger 和 compute 各自贡献，且 subjective judge 存在 reward-shaping 风险（pp.4、7）。
- 开放式源码生成可同时改变实现细节，不能直接当作 4–10 层 typed Conv1d Transformer 的 matched-budget policy 证据。迁移时应固定 recipe/evaluator，把 action 限制为 depth/width/block/op/connectivity，并记录 attempted、invalid、duplicate、trained、GPU、LLM、wall-time。
- 最可迁移的是 cognition/experience 分层、pre-training legality gate、failure-triggered debugging 与 multi-scale verification；当前仍缺真实设备 latency/energy、Pareto archive 和完整成本组合。

## 链接

- 论文：https://arxiv.org/abs/2507.18074
- 代码：https://github.com/GAIR-NLP/ASI-Arch
