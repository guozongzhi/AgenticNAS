---
title: "A Physical Testbed for Self-Driving Laboratories: Comparing Bayesian and Agentic Optimization in a Minimal Closed-Loop Color Formulation Task"
authors: "Tony Qin, Ziheng Wu, Maximilian Schommer, Roya Amini-Naieni, Aldair Gongora"
year: "2026"
venue: "arXiv:2611.11690v1"
paper_url: "https://arxiv.org/abs/2611.11690"
source_pdf: "https://arxiv.org/pdf/2611.11690"
parser: "Codex"
parsed_on: "2026-11-11"
status: codex_draft
tags: [agentic-bo, physical-experiment, closed-loop, cost-reporting, adjacent-baseline]
---

# Physical Agentic Optimization Testbed

> 本笔记基于 arXiv v1 官方 PDF。优化对象是染料配方，不是神经架构或训练超参；归真实物理 Agentic BO 邻接证据。

## 一句话结论

- 系统把 candidate proposal、自动移液、吸光度测量和反馈闭成 48-iteration physical loop；Claude Opus 5 可在连续上下文中写 Python、选择模型并提出下一配方。（PDF pp.3–5, Figures 3–4）
- 三个 target 各做一次 BO 与 Agent campaign；Agent 在 10/23/11 iterations 达测量误差带，BO 为 21/34/未在 48 次内达到，但方法与 target 只有单次配对，不能视为统计优越证据。（PDF pp.5–7, Table 2, Figure 6）

## 优化对象、闭环与预算

- 四个液体体积总和固定 250 μL，测 400/600/700 nm absorbance；objective 是三输出对 target 的 MSE。硬件流程、目标、总 volume 与 48 次预算固定。（PDF p.4, Table 1）
- BO 先 12 个 random mixtures，再用 qLogEI 选 36 个。Agent 用 Claude Opus 5/high thinking，单连续 conversation 保留全部观察，可无限次调用本地 `run_python`，再 `propose_setting`。（PDF pp.4–5）
- Agent 只能用 NumPy/SciPy/pandas/scikit-learn/BoTorch sandbox，无 web/旧实验数据；完整 rationale 被保存。无 invalid proposal、hardware failure、duplicate/retry ledger，论文称六个 campaign 均无人工介入完成。（PDF pp.5–7）

## 结果与成本

- 六个 campaign，每个 48 iterations、约 4 h，合计约 24 h。Agent/BO candidate generation 平均 19/16 s；物理 loop 约 4.5 min/iteration。（PDF pp.4, 6–7）
- Agent 对 target 1/2 分别减少 52%/32% 达标 iterations，并在 target 3 的 11 次达到；BO target 3 未在 48 次达到。（PDF p.6, Table 2）
- 三个 Agent campaign 的 API 总费用 `$20.83`。模型为 Claude Opus 5；tokens、每轮 tool calls、Python executions 与失败费用未报告。（PDF pp.4, 6）
- Agent 自行尝试 linear/Hill/power-law/Michaelis–Menten、recency weighting、drift/noise correlation 和 Monte Carlo；这属于 open-ended optimizer policy，不是固定模型 HPO。（PDF p.6）

## 公平性、局限与泄漏

- physical evaluation budget matched 为 48，但 BO 有 12 个 random initial points，Agent 自选 center/vertices；proposal compute 与信息结构不完全匹配。
- 每个 target 每方法仅一次 campaign，target 与 run 不可独立估计 variance；Agent 能选择模型而 BO 固定 GP/qLogEI，因此不能分离 LLM reasoning、model selection 与 acquisition choice 的贡献。
- sandbox 隔离旧实验降低数据泄漏风险，但 prompt/model 服务不可完全复现；代码/trajectory 下载链接未在论文正文中给出。
- energy、耗材成本、peak memory、硬件失败与 API token ledger 未报告。

## 对本仓库的价值

- 归类：`Agentic BO 邻接`。最有价值的是 physical attempted-trial budget、tool isolation、rationale trace 与明确 API 费用。
- 不可把配方优化效果转为 NAS/HPO 结论。typed Conv1d 应限制 Agent 为 schema-valid action，并让 classical/Agent proposer 使用相同 initial design、真实训练/设备评价和 tool-call budget。
- 最小实验：相同 48 attempted candidates，比较 BO/evolution/stateless/memory-aware Agent；报告 candidate latency、LLM calls/tokens/USD、invalid/duplicate/retry、真实 latency/memory/energy 与 seed variance。

## 检索与人工核验记录

- 官方 PDF：11 页，SHA-256 `2789edaacbf7f12ed0453c3a91cec05bf40047ef186152f602eea53704feeb23`；所有页可解析。
- [x] Table 1/2 与 Figures 3–6 已核对
- [x] 物理次数、墙钟与 API 费用已核对
- [x] 单次配对与非 NAS/HPO 边界已标记
- [ ] 人工决定 `retained` / `discarded`
