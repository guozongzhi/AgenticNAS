---
title: "Structured Progressive Knowledge Activation for LLM-Driven Neural Architecture Search"
authors: "Zhen Liu, Yuhan Liu, Jinjun Wang, Wei Song, Jianyi Liu, Jingwen Fu"
year: "2026"
venue: "ICML 2026 / arXiv:2605.04057v3 (acceptance stated by paper and code repository; official PMLR page not yet verified)"
doi: "10.48550/arXiv.2605.04057"
paper_url: "https://arxiv.org/abs/2605.04057"
source_pdf: "https://arxiv.org/pdf/2605.04057"
code_url: "https://github.com/AIM-ResearchLab/SPARK"
source: "arXiv v3 metadata/PDF and public project repository, accessed 2026-08-01"
parser: "Codex"
parsed_on: "2026-08-01"
status: codex_draft
tags: [llm-nas, structured-editing, action-validity, clrs, open-evolve, code-generation]
---

# Structured Progressive Knowledge Activation for LLM-Driven Neural Architecture Search

> 本笔记基于 arXiv v3 的 25 页 PDF 和公开项目仓库。PDF/仓库均声明 ICML 2026，PDF 写有 PMLR 306，但截至 2026-08-01 未核验到官方 PMLR 页面；所有结果仍为作者报告。

## 一句话结论

SPARK 把一次开放代码编辑拆成“先选 OPERATOR/ACTION 功能域，再在该域内生成 patch”，并拒绝跨域、接口和 shape 不合法的候选；在相同 100 proposal attempts 与同一 editor 的 OpenEvolve 对照中，它显著提高可执行率与 DFS best-so-far，但论文的 28.1× 来自 57 个已评估候选与 EvoPrompting 的 1,600-evaluation 设置相除，不是候选、LLM calls、GPU-hours 和训练都一致的端到端加速。（pp. 2–9）

## 书目信息与来源核验

- arXiv ID：2605.04057v3；v1 提交于 2026-04-10，v3 更新于 2026-06-30；arXiv DOI：10.48550/arXiv.2605.04057。
- 作者：Zhen Liu、Yuhan Liu、Jinjun Wang、Wei Song、Jianyi Liu、Jingwen Fu。
- venue：PDF 首页声明 Proceedings of ICML 2026, PMLR 306；公开仓库 release note 也声明 accepted to ICML 2026。当前未找到可核验的官方 PMLR 论文页，因此索引保留 `paper claim` 标记。
- 论文：https://arxiv.org/abs/2605.04057
- 代码：https://github.com/AIM-ResearchLab/SPARK ；公开仓库无 release，README 的 clone 地址与当前仓库 owner 不一致，并提示实际字段可能随分支变化。
- 置信度：arXiv 书目信息 high；ICML acceptance medium-high；方法 high；结果 medium；独立可复现性 medium-low。

## 研究问题与贡献

- 问题：开放代码级 LLM-NAS 的一次 free-form edit 往往同时改变 operator 定义、调用/wiring 和接口约束，导致 functional entanglement、credit assignment 模糊和不可执行候选。（pp. 1–3）
- 方法：Architecture Scope Router（ASR）选择 `OPERATOR` 或 `ACTION`；Refinement Compass（RC）根据停滞和失败信息生成域内 directive；Scoped Architecture Refiner（SAR）只在被选区域内生成修改。（pp. 3–5）
- validator：检查 diff 是否只触碰被选区域，再做语法、import、接口和 dummy-forward/shape 检查；失败 proposal 不进入完整训练。（p. 4）
- 搜索 backbone：OpenEvolve 的 island/archive evolution，fitness 为 CLRS OOD accuracy，descriptor 包含 OOD accuracy、MACs 和 parameter count。（pp. 4–6）

## 方法拆解

### 搜索或优化对象

- 搜索对象是真实、可执行的神经算法架构代码，不是 Agent 工作流；从 CLRS 官方参考 processor 的单个 seed program 开始迭代编辑。（pp. 3, 5–7）
- `OPERATOR` 覆盖 module parameterization/structure definitions，例如 projection 和 gating；`ACTION` 覆盖 forward 中的组合、routing、masking 和 control flow。（pp. 2, 4, 7）
- 训练和 evaluator 在候选间固定；architecture code 变化而 optimizer/data pipeline 不变，因此属于 NAS。
- 它提供两层功能域而非本仓库的 4–10 层 Conv1d Transformer block/cell/op schema；manual region tags 需要迁移验证。

### Agent 与优化闭环

- 单个 base LLM 通过不同 role prompts 扮演 router、directive generator 和 editor；默认 editor 为通过 OpenAI-compatible API 调用的 DeepSeek-R1-0528，temperature 0.7。（pp. 3, 5）
- ASR 最多重试若干次解析功能域，失败 fallback 到 `ACTION`；RC 使用最近 3 个已评估候选的停滞信号与最近 10 个 proposals 的失败类型；SAR 生成 factor-conditioned edit。（pp. 4–5, Algorithms 1–2）
- 候选 diff 只有全部修改行落在所选区域内才接受；syntax/interface/shape feasibility 失败直接拒绝，不消耗论文定义的 evaluation budget，但仍消耗 proposal 与 LLM budget。（p. 4）
- 合法候选完整训练、评分后进入 islanded MAP-Elites/OpenEvolve archive；更高 fitness 替换 cell elite，MACs 用于 tie-break。（p. 4）
- 搜索使用 5 islands、population 100、archive 100；prompt 含 top-performing 与 diverse archive programs，并有 timeout/retry。（p. 5）

### 评估与预算

- 主搜索仅在 CLRS DFS 上运行 100 proposal attempts，再把 best architecture 从头训练并迁移到另外 9 个代表任务与完整 30-task suite。（pp. 5–7）
- 可靠性曲线按固定 100 attempts 统计；“evaluated candidate”只计通过 feasibility 并进入完整训练的候选。主预算同时报告 attempts 与 evaluated candidates 是必要的，但论文的 28.1× 只使用后者。（pp. 5–6）
- 作者对受控 OpenEvolve baseline 使用相同 backbone、editor、100 attempts 和 evaluator；FunSearch 也由作者在同一 CLRS pipeline 重跑。EvoPrompting 的 1,600 evaluations 来自另一设置。（p. 6）
- 附录的 SPARK 100-candidate trajectory 聚合 5 个 random seeds；正文没有在所核对位置清楚给出所有 baselines 的同样五 seed 搜索方差。（pp. 12–13）
- 模型计算报告 MACs；搜索成本应另看 LLM calls、GPU-hours、wall time。SPARK 每 proposal 会有多次 role calls，但正文主 CLRS 表未给出可直接核验的完整 calls/tokens/费用/GPU-hours 对账。（pp. 9, 12–13）
- 没有实测目标硬件 latency、peak memory 或 energy，也不是 quality/latency/memory 的 Pareto 搜索。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| 同 100 attempts 的 DFS 结果 | SPARK 83.74 OOD accuracy；OpenEvolve 32.54 | 相同 search backbone/editor/evaluator | pp. 6–8, Table 1/Fig. 2 | medium-high |
| 合法性 | 100 attempts 后 SPARK cumulative valid rate 约 0.5–0.6，OpenEvolve 约 0.25–0.3 | OpenEvolve free-form edit | pp. 8–9, Fig. 2 | medium |
| 结构编辑消融 | DeepSeek-R1：RC+SAR 56.79、ASR 65.28、Full 83.74；Qwen-Plus 56.00/64.50/80.50 | CLRS reference 46.78 | pp. 7–8, Table 3 | high |
| 10-task transfer | mean OOD 83.92，avg MACs 453K | EvoPrompting 74.42/448K，CLRS 71.22/450K | p. 6, Table 1 | medium |
| 30-task transfer | SPARK 83.91，EvoPrompting 80.89，CLRS 75.98；分别胜过后两者 19/30、21/30 tasks | 同表列方法 | pp. 9, 12–13, Table A.1 | medium |
| 论文所称 evaluation efficiency | DFS best 83.74 在 57 evaluated candidates；`1600/57≈28.1×` | EvoPrompting 1,600-evaluation setting | p. 6 | low-medium |

## 公平性与可信度检查

- 最可信的是 SPARK 与 OpenEvolve 的同 backbone/editor/evaluator/100-attempt comparison；它支持 factor-scoped edits 提高 proposal validity 和 best-so-far，不自动支持对所有 NAS 方法的端到端优势。
- 28.1× 分子/分母来自不同 search procedure 和 budget accounting：EvoPrompting 1,600 evaluations vs SPARK 57 evaluated candidates。SPARK 每 attempt 又可能产生 ASR/RC/SAR 多次 LLM calls，因此不能解释为 GPU、wall time、LLM cost 或总候选预算的 28.1×。
- invalid proposal 不计 evaluation budget 会掩盖失败 LLM calls；论文同时给 100-attempt curves 是正确补充，本仓库应以 attempted candidates 为主预算。
- 五 seed 曲线只明确展示 SPARK trajectory；所有 baseline 是否相同 seeds、prompt sampling 和 full training budget，需从代码/原始 logs 进一步核对。
- DFS search 后向其余任务 transfer，能检验跨任务泛化，但不能等价于每任务独立 NAS；BFS、Floyd–Warshall、KMP 等任务仍失败。（p. 9）
- MACs 只是 final model compute，不是 search cost，也不是设备 latency/memory；额外 router/directive calls 明确提高搜索开销。

## 可复现性与代码/数据

- 公开仓库包含 LLM client、ASR/RC/SAR prompts、diff checking、archive/controller、CLRS evaluator、seed program 和多 seed 命令；README 给出 100 iterations、5 islands、population/archive 100、timeout/retry 等配置。
- 仓库没有 tag/release；README clone URL 指向不同 owner，且明确提醒 config 字段可能随分支变化，当前 HEAD 不能视为论文冻结 artifact。
- 论文/仓库未在所核对位置提供完整主 CLRS 原始 traces、每 role 的 calls/tokens/费用、全部 GPU-hours 和一键聚合脚本；README 甚至说明 aggregation script 依本地 evaluator 而定。
- 官方 PMLR 页面尚未核验，当前以 arXiv v3 和公开仓库作正文/代码证据。

## 与 AgenticNAS 的关系

- 最直接可复用的是“先选 scope，再发局部 action”：可映射为 `block/cell/op/connectivity` scope + typed `MutationAction`，由本地 builder/validator 生成代码，而不是让 Agent 输出完整 Python。
- 把 entanglement rate 改写为跨 scope 修改率、非法字段率和 unintended-diff rate；把 valid rate 与 duplicate/OOM/divergence 一起按 attempted candidates 统计。
- RC 可只读取公开、结构化的 recent outcomes/error codes；不得传递内部架构代码、端点或日志，保持 clean-room 窄接口。
- 主实验应在相同 attempts、LLM calls/tokens、GPU-hours 和至少三组 seeds 下比较 native mutation、free-form/stateless LLM、scope-only、scope+directive 与 memory-aware policy。
- MACs 可作模型复杂度 descriptor，但最终 Pareto 仍需真实 quality、latency、peak memory 和成本；`quality_proxy`、`latency_proxy_ms` 只能作控制流占位符。

## 最小复现实验

- 固定 4–10 层 Conv1d Transformer、训练 recipe、数据 split 和 200 attempted trials；每次只允许修改 `block/cell/op/connectivity` 一个 scope。
- 对照 native random mutation、free-form LLM、random-scope local action、scope router only、scope+directive、scope+directive+memory。
- 每组至少三 search seeds；统一 LLM calls/tokens、training steps、GPU-hours 和 timeout，所有 invalid/duplicate/OOM 都计入预算。
- 指标：best-so-far/hypervolume、action validity、entanglement、duplicate、失败类型、seed variance、真实 latency/memory 与总 LLM/GPU cost。

## 局限与风险

- 当前 factorization 只有人工定义的 OPERATOR/ACTION 两区；向更细 block/cell/op 或不同框架迁移可能失效。
- 多 role calls 提高搜索成本，论文没有完成严格的 calls/tokens/GPU-hours matched-budget 结论。
- 搜索集中在 CLRS DFS 后 transfer；部分 30-task 结果仍低，不能宣称普遍架构泛化。
- 代码仓库没有冻结 release，配置/owner 信息存在不一致；复现前需锁定 commit 并保存完整 traces。
- 论文不支持真实设备 latency/memory/energy 或多目标 Pareto 结论。

## 可引用摘要

SPARK 将 LLM 驱动的开放代码编辑拆分为功能域选择、域内 refinement directive 和局部 patch，并在完整训练前拒绝跨域或接口/shape 不合法的候选。作者在 CLRS DFS 的固定 100 proposal attempts 下报告比相同 editor/backbone 的 OpenEvolve 更高的可执行率和 best-so-far OOD accuracy，并通过 OPERATOR/ACTION 消融支持两阶段编辑的贡献。其 28.1× 只按与 EvoPrompting 不同设置下的 evaluated candidates 计算，且主实验未完整统一 LLM calls、GPU-hours 与多 seed baseline 成本，不能视为端到端 matched-budget 加速。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2605.04057
- PDF：https://arxiv.org/pdf/2605.04057
- 代码：https://github.com/AIM-ResearchLab/SPARK
- 已核对：标题、作者、arXiv 日期/ID/DOI、ICML/PMLR 自述、OPERATOR/ACTION、ASR/RC/SAR、validator、100 attempts、主要表格、五 seed 附录、限制与仓库 README。
- 未核对：官方 PMLR 页面、独立运行、论文冻结 commit、完整 LLM/GPU 成本、所有 baseline 的相同 search seeds 和原始 traces。
- [ ] 已由人工决定 `retained` / `discarded`
