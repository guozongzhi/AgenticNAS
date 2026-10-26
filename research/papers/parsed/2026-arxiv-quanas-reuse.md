---
title: "QuaNAS: Uncertainty-Aware Reuse of Earlier Searches for Query-Efficient Neural Architecture Search"
authors: "Brama Seta Putra Satria, Dwi Sunaryono, Misbakhul Munir Irfan Subakti, Irzal Ahmad Sabilla, Laras Suciningtyas"
year: "2026"
venue: "arXiv:2610.31251v1"
paper_url: "https://arxiv.org/abs/2610.31251"
source_pdf: "https://arxiv.org/pdf/2610.31251"
parser: "Codex"
parsed_on: "2026-10-27"
status: codex_draft
tags: [nas, bayesian-optimization, transfer, archive, uncertainty, query-efficient]
---

# QuaNAS

> 本笔记基于 arXiv v1 官方 PDF。QuaNAS 不使用 LLM/Agent，归为传统 NAS 邻接基线；论文数字均为作者报告，不是本仓库实测。

## 一句话结论

- QuaNAS 把同一 search space 的历史搜索表压缩成可解释的 main-effect architecture prior，再与 zero-cost proxy 共同作为 GP-BO 的不确定先验；新任务首个 query 直接取 prior optimum，后续用真实短训结果重新估计 prior 权重。（PDF pp. 3–9, Fig. 2）
- 在 12 个 held-out image/time-series/text/tabular 数据集、相同 100 次 distinct-query 预算下，作者报告 mean anytime regret 0.058，对 QIEA-ZC/LS/RoBoT-style/REA/proxy ranking 为 0.155/0.177/0.182/0.184/0.226；但完整 100-query 搜索并不总是更省时，优势集中在较早找到好架构。（PDF pp. 13–15, Table 5, Fig. 4）

## 搜索对象、变量与固定项

- 搜索对象是真实神经架构。卷积空间包含 1-D/2-D convolution 的 depth、width、kernel 等结构决策；文本空间改变 encoder（bag-of-embeddings/TextCNN/residual 1-D convolution/BiGRU）、layers、kernel、width、pooling、skip、dropout、activation；tabular 空间也改变网络结构字段。（PDF pp. 9–10）
- 每个 task 的数据切分、短训/全训 fidelity、optimizer、learning rate、schedule、batch、最终 evaluator 固定；各方法搜索同一 candidate pool。因 recipe 不随 candidate 改变，归 `traditional NAS`，不是 HPO 或 mixed search。（PDF pp. 10–12）
- 历史 archive 只来自同一 search space 的早期任务；ridge main-effect models 产生 architecture prior，leave-one-task-out stacking 决定它与 zero-cost proxies 的初始权重。搜索过程中用观测噪声重新估计权重，低可靠性 prior 可被关闭。（PDF pp. 6–9）

## Proposal、feedback、memory 与停止机制

- Proposal：首个 candidate 为 prior optimum；之后 GP 以 expected improvement 在未查询 pool 中选点，不设随机 initial design。（PDF pp. 8–9, Algorithm 1）
- Feedback：每次 candidate 短训 accuracy 回写 GP，并重估 architecture/proxy prior 的可信度；历史 archive 是任务级表格，不是自然语言反思。（PDF pp. 8–9）
- 最多 100 个 distinct architecture queries，并限制最多 2,000 次 proxy evaluations；最终从前 50 queries 中 low-fidelity 最好的 3 个各全训一次，再以 validation 选择一个架构，用 10 个新 seeds 评 test。（PDF pp. 9, 11–12）
- 论文未报告 invalid action、OOM、duplicate proposal 或 retry 的单独账本；candidate pool 和算法本身保证 distinct queries。Amazon Polarity pool 中 1 次 diverged short training 被保留并报告。（PDF p. 13）

## 评估、预算与硬件

- 35 个 development pools 用于冻结方法；确认阶段为 12 个从未载入的 datasets，17 search methods × 30 seeds，加上 ablation/sensitivity/acquisition/capped-pool runs，共 16,920 searches。（PDF p. 11, Fig. 3）
- 主比较为同 pool、同 100 distinct queries、同 proxy 上限。QuaNAS 到 normalized regret 0.05 的作者报告平均累计成本为 197 s，对 QIEA-ZC/REA/LS/RoBoT-style/PTK-MR 为 589/677/817/1042/1068 s；完整 100-query 成本为 914 s，高于 random/LS/REA 的 602/660/695 s。（PDF pp. 13–15, Table 5）
- 所有训练在 RTX 4080 16 GB；search 是 Ryzen 9 9950X CPU table lookup。额外 final/reference/comparator full training 为 454 runs、19.3 GPU-hours，低于预设 40 GPU-hour cap。（PDF pp. 11–12）
- 未报告完整 short-training GPU-hours、peak memory、energy、USD 或 LLM cost（方法不使用 LLM）。

## 核心证据

| Claim | 作者报告结果 | 对照 | 证据位置 | 置信度 |
|---|---|---|---|---|
| 较低 anytime regret | 0.058；比五个 primary comparators 低 2.7–3.9× | QIEA-ZC、LS、RoBoT-style、REA、PTK-MR | PDF pp. 13–14, Table 5 | high |
| 较早达到近优架构 | mean TTT0.05 197 s；88.6% runs 达标 | comparators 589–1068 s、52.8–69.4% | PDF pp. 13–14, Table 5/Fig. 4 | high |
| archive 而非 proxy 是主要来源 | 去除 architecture prior 的 GP-BO mean AUC 0.130；QuaNAS 0.058 | same-library GP comparators | PDF p. 15, Table 6 | medium-high |
| final model 并非只追 low fidelity | 12 tasks 中 7 个高于 reference、9 个在 0.5 pp non-inferiority margin 内 | matched-recipe references | PDF pp. 17–18, Table 9 | high |

## 公平性、代码与局限

- 主 search comparators 的 candidate/query/proxy 预算匹配；四个 transfer comparators 是确认阶段后的 post-hoc 分析，不能与 pre-specified primary comparison 混写。（PDF pp. 11, 15）
- 论文把 task 而不是近乎 deterministic 的 seed 当统计单位，并在 12 个 task means 上做 Holm-adjusted Wilcoxon；这比把 30 seeds 当独立样本稳健。（PDF p. 12）
- transfer 只发生在共享 search space 内；跨 search-space、library 与目标分布不匹配、low-fidelity 排名偏差仍是主要外推风险。（PDF pp. 28–29）
- 作者在 Zenodo DOI `10.5281/zenodo.23562488` 发布 v1.0.0：23,349,422-byte ZIP，声明包含 code、47 candidate pools、frozen protocol、per-run results 与表图脚本；本轮只核对记录/文件清单，未运行代码。

## 对本仓库的价值

- 可复用：把 prior/archive 明确限制到同一 typed Conv1d search space；用 leave-one-task-out 学 prior 权重；首个 proposal 前就记录 prior provenance，并允许 feedback 把不可靠 prior 关掉。
- 必须补的对照：random/native evolution/stateless LLM/memory-aware LLM 仍要在相同 attempted、valid、trained、GPU、LLM 和 wall-time 预算下比较；QuaNAS 不能支持 LLM policy 的效果结论。
- 最小实验：在固定 4–10 层 Conv1d typed space 上积累多个数据集的完整 archive，比较 no-transfer GP、nearest-task、QuaNAS-style main-effect prior 与 memory-aware Agent；报告 regret/AUC、time-to-target、duplicate/invalid、GPU-hours 和 archive mismatch failure。

## 检索与人工核验记录

- 官方 PDF：30 页，SHA-256 `e1cb7f7af8a17c1b29dbec82dbf61a436894d15e25fa3b04a5da556c759cf3b2`。
- 重点核对：PDF pp. 6–15、17–18、28–29，Algorithm 1、Figures 2–4、Tables 3、5、6、9。
- [x] 标题、作者、版本已核对
- [x] 主要数字已对照原表
- [x] query/GPU/硬件预算已核对
- [x] 作者结果与仓库实测已区分
- [ ] 人工决定 `retained` / `discarded`
