---
title: "From Human Intent to In-Orbit Action: A Self-Learning Large Language Model Agent for 6G Satellite Networks"
authors: "Zhengqian Xu, Yasheng Zhang, Chenhua Sun, Shan Lu, Chengcheng Li"
year: "2026"
venue: "arXiv:2610.34387v1"
paper_url: "https://arxiv.org/abs/2610.34387"
source_pdf: "https://arxiv.org/pdf/2610.34387"
code_url: "not found"
parser: "Codex"
parsed_on: "2026-10-28"
status: codex_draft
tags: [llm-nas, graph-neuroevolution, memory, reflection, pareto, satellite]
---

# ALMOND

> 本笔记基于 arXiv v1 官方 PDF。作者结果来自 350 星数字孪生，不是真实卫星或本仓库实测。

## 搜索对象与闭环

- 搜索对象是 PPO policy DAG：节点可选 self-attention、GCN、MLP，边表示数据流；graph grammar 限制物理可行拓扑。LLM 输出结构 sketch、局部 mutation、homologous-subgraph crossover 和每 10 代一次的 top-5 population critique，不生成权重。（PDF pp.8–10, Algorithm 2）
- 每代 population=20，目标为 task reward、参数量 `<=50K`、推理 latency `<15 ms`；offspring 继承 parent weights，输出 5–10 个 Pareto policies。停止写为 plateau early stop，但论文未报告实际 generations、attempted/valid/unique/trained candidates 或 duplicate/retry 账本。（PDF pp.9–10, 13, Table 3）
- 另一个闭环把最差 5% RL trajectories 送入 reverse forensics，LLM 从失败中提出约束，只有 counterfactual replay 提升至少 5% 且不破坏 latency budget 才写入版本化 knowledge graph；失败会 re-prompt 或触发人工告警。（PDF pp.6–7）

## 预算、实验与结果

- 作者报告一次 topology adaptation 约 20 GPU-hours，约为 unseeded evolution 的 1/20；平台为 8×H100 workstation。forward translation 为 1 次约 3K-token LLM call，reverse forensics 为 2–5 calls；NAS critique/mutation 的总 calls、tokens、费用和 wall-time 未报告。（PDF pp.11–13, Tables 2–3）
- 数字孪生使用真实 TLE/SGP4 轨道数据模拟 350 颗卫星；所有配置 10 个独立 seeds。作者报告 ALMOND 约 3× 更快收敛、polar handover success 从 55% 提升到 90% 以上，且很多 Pareto policies 在 `<40K` 参数下超过 95% success。（PDF pp.12–15, Figs.6–8）
- latency 是未具名 “target-class processor” 的 wall-clock；没有真实星上 hardware-in-the-loop、peak memory 或 energy。作者明确把硬件在环留作未来工作。（PDF pp.12, 17）

## 公平性、边界与复现价值

- PPO-MLP、static-LLM 和 random-NAS 分别用于 reward loop、backward loop 与 structural prior 对照，但 random-NAS 的 generation/candidate/GPU/LLM 等预算表未展开，不能把“20×”当作完整 matched-cost 结论。
- 归类为 `LLM × NAS`，但系统还同时改变 reward 与 architecture；本仓库复现时必须固定 reward/training recipe，只比较 random/native evolution/stateless LLM/memory-aware LLM 的 typed architecture proposals。
- 可迁移机制：structure-only action contract、失败约束 counterfactual gate、版本化 memory、population-level critique 与 Pareto envelope。最小复现实验应报告 attempted/valid/unique/trained、invalid/duplicate、GPU-hours、LLM calls/tokens/费用和真实 device latency/memory/energy。

## 检索与人工核验记录

- 官方 PDF：18 页，SHA-256 `a380f1250c0f62492437e44a9b543288652c35a91b1007c1c583ac7451572be1`。
- 本轮网页与 GitHub 检索未发现作者官方代码；论文写明数据可向作者申请。
- [x] 标题、作者、版本和关键表图已核对
- [x] 作者结果与仓库实测已区分
- [ ] 人工决定 `retained` / `discarded`
