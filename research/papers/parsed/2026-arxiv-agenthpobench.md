---
title: "AgentHPOBench: A Benchmark For Evaluating LLM Agents as Sequential Hyperparameter Optimizers"
authors: "Tianyu Huai, Tingshuo Fan, Xinchi Chen, Yining Zheng, Yuxin Wang, Shuang Chen, Jie Zhou, Xuanjing Huang"
year: "2026"
venue: "arXiv"
status: codex_draft
paper_url: "https://arxiv.org/abs/2607.29626"
code_url: "https://github.com/OpenMOSS/AgentHPOBench"
tags: [hpo, benchmark, sequential-agent, mixed-search-space, test-feedback]
read_on: "2026-09-20"
---

# AgentHPOBench: A Benchmark For Evaluating LLM Agents as Sequential Hyperparameter Optimizers

## 一句话结论

AgentHPOBench 用 30 个可执行研究仓库、一个已验证基线和五次顺序干预测试 Agent 是否会把历史配置、指标与日志转化为下一次实验决策；它证明反馈有用且强 API Agent 的最终步聚合分数高于三种经典基线，但公开搜索空间混入结构与模型族变量、部分任务向 Agent 暴露 test 指标，主表又用“最后一步”而不是经典 HPO 常用的 incumbent，因此不能把结果直接解释为固定架构、无泄漏、同信息预算下的 HPO 优势。

## 书目信息与证据边界

- arXiv ID：`2607.29626v1`；2026-07-31 提交；当前仅核验为 arXiv 预印本，未发现 DOI 或正式 venue。
- 作者：Tianyu Huai、Tingshuo Fan、Xinchi Chen、Yining Zheng、Yuxin Wang、Shuang Chen、Jie Zhou、Xuanjing Huang。
- 一手来源：[arXiv metadata](https://arxiv.org/abs/2607.29626)、[PDF](https://arxiv.org/pdf/2607.29626)、[作者代码](https://github.com/OpenMOSS/AgentHPOBench)。
- 本轮核验的公开代码 commit：[`6d8d90071cdb16b06f0db866480ecaae48880fba`](https://github.com/OpenMOSS/AgentHPOBench/commit/6d8d90071cdb16b06f0db866480ecaae48880fba)（提交时间 2026-08-06，`Initial public release`）；未发现 release tag。
- PDF SHA-256：`d9c395c0c4f5c25bc5a83b5fde380b60c0d19e47d9b8621b3eef8c7cd0692ec8`；69 页。
- 置信度：书目信息与论文表格为高；公开代码结构为高；未运行 30 个上游仓库及 H200 实验，因此复现实验结论为中。

## 研究问题、真实搜索对象与搜索空间

- 研究问题：给定真实 ML 仓库的基线运行，Agent 能否读取累计配置、目标/辅助指标与日志，在有限实验预算内提出下一组有效配置并持续改进？（§1、§3）
- 任务：30 个仓库级任务，覆盖 NLP 3、CV 5、时间序列 7、图学习 2、RL 3、LLM 4、structured learning 6；数据、split、目标指标、评估代码和任务 metadata 固定。（Table 6、§3.1）
- 论文把允许字段统称为“hyperparameters”，但本轮对公开 `tasks/main/*/run_formal*_agent.py` 的 `SEARCH_SPACE` 静态核验发现 12 个任务含明显结构/模型选择字段；其中 11 个直接改变模型结构或模型族，例如：
  - iTransformer：`d_model`、`d_ff`、`n_heads`、`e_layers`；
  - TimeMixer/TimeXer：`d_model`、`d_ff`、`e_layers`、down-sampling/patch；
  - VBLL：`num_layers`；SparseTSF：`d_model`、`model_type`、`period_len`；
  - TabM/HyperbolicCV/TabMini/binary diffusion：`arch_type`、`model_type` 或 `model_family`；
  - 另一个 ART 任务改变策略 lookahead depth。
- 因此本笔记分类为 `mixed-search-space`，不是严格 `LLM × HPO`，也不是单一 NAS benchmark。论文中“固定 model family”的示例 prompt 只适用于该示例任务，不能外推到全部 30 个 task。

## Agent / LLM 决策循环

1. 每个任务先执行共享参考配置 `x_t,0`；其性能、配置和日志成为 trace 0。
2. Agent 在第 `k` 次干预前看到累计历史 `H_t,k-1`，包括配置、目标/辅助指标与日志，并从离散干预空间提出完整或部分配置。
3. harness 解析、验证并 clamp 到允许空间，执行实验，记录 raw response、配置、指标、日志、运行元数据和错误，再把反馈返回下一轮。
4. 共五次顺序干预；主结果用第五次的最终配置，而不是前五次的 best-so-far。（§3、§9–10）
5. no-feedback 消融保留同一基线，但在五次决策中隐藏干预 1–4 的指标与日志，用来隔离中间实验反馈。（§9、Table 5）

## 目标、候选、训练、GPU 与 LLM 预算

- 目标：每个任务一个标量指标，方向由任务定义；聚合指标为 bounded normalized score（BNS/MBNS）、baseline win rate（BWR）和 mean anchor attainment（MAA）。BNS 相对共享基线和论文/仓库 anchor 归一化并截断到 `[-1,1]`。（§3.4、§10）
- 候选预算：每个方法每任务一个基线 + 五次干预；经典基线也获得五次配置评估。（§4、§9）
- limited budget：每个基线/干预约使用原实验训练或评估预算的 10%；full budget 只对三种 Agent 补做，保持任务定义与五次干预不变。（§4）
- 本地模型和经典 HPO：30 tasks × 5 decisions × 3 seeds = 每模型 450 个已接受决策；seeds 为 `0,1,42`。（§9、Table 8）
- 开源模型输出 token：Gemma2-2B 40,857；Llama-3.1-8B 53,700；Qwen3-8B 60,636；Qwen3-32B 54,771；Phi-4-14B 91,327；DeepSeek-R1-Qwen-14B 153,673。这里仅统计生成文本，不含输入 token，不能与 API 总 token 直接比较。（Table 8）
- API Agent 每个应有 150 个已接受逻辑决策，但 campaign 记录 1,231–1,695 requests、约 1.866M–2.498M provider-recorded total tokens，包含 retry、解析/验证恢复及 harness 调用；未给货币成本。（Table 9）
- 硬件：受控实验运行在 Linux + NVIDIA H200，单机可见显存 143,771 MiB；未给总 GPU-hours、每任务 wall time 或能耗。（§9）

## 基线、公平性与关键结果

- 基线：random search、TPE、fixed-budget BOHB-style proposer；它们和 Agent 共享 task、baseline、离散 intervention space、五次配置评估与 scoring。（§4、§11.1）
- 信息不对称：经典方法只处理配置与标量目标，Agent 还看到任务描述、辅助指标和文本日志；因此比较的是完整系统，不是纯 proposer 的等信息消融。（§11.1）
- limited-budget 最终步主表：Claude Sonnet 4.6 的 MBNS/BWR/MAA 为 `0.407/76.7%/79.5%`；最佳开源模型 Qwen3-32B 为 `0.148/60.0%/69.1%`。random/TPE/BOHB-style 的 MBNS 为 `-0.034/-0.113/0.018`。（Table 2）
- 中间反馈消融：Qwen3-32B 的 standard/no-feedback MBNS 为 `0.148/0.052`，BWR 为 `60.0%/50.0%`，说明反馈有价值，但没有把日志、辅助指标和目标值进一步拆分。（Table 5）
- full-budget：Qwen3-32B、DeepSeek-R1-Qwen-14B、Claude Sonnet 4.6 的 MBNS 分别由 `0.148/0.018/0.407` 变为 `0.191/0.151/0.472`，但 BWR 不一致改善。（Table 3）
- 关键口径风险：主表取第五次结果；best-so-far 诊断中 random/TPE/BOHB-style MBNS 升到 `0.325/0.298/0.291`，超过所有开源 Agent，而 Claude Sonnet 4.6/GPT-5.5 仍为 `0.469/0.347`。这说明“是否保留 incumbent”本身显著改变排序，经典 HPO 不应被强制用最后一次候选代表最终输出。（Tables 12–14）
- API Agent 只有一次 hosted run，论文明确承认它不是受控 seed replicate；不同 provider/serving state 可能漂移。（§9）

## 数据集、模型与硬件范围

- 数据/任务包括 FineWeb/HellaSwag、CIFAR-10/100、MNLI、ETT/PJM/Weather、Cora、GSM8K/MATH-500、ImageNet 256、MathVista、表格与游戏任务等；任务异质性很高。（Table 6）
- Agent：Gemma2-2B、DeepSeek-R1-Distill-Qwen-14B、Qwen3-8B/32B、Llama-3.1-8B、Phi-4-14B，以及 GLM-5.1、Kimi-2.6、GLM-4.7、DeepSeek-V4-Pro、GPT-5.5、Claude Sonnet 4.6。（§4）
- prompt/decoding：本地模型 temperature 0、禁 sampling；API 在 endpoint 支持时设 temperature 0。（§9）
- 部分任务把 test metric 或 validation 选 checkpoint 后的 test metric 暴露给顺序决策；论文明确说没有独立 hidden test，结果不能解释为自适应模型选择后的泛化估计。（§9）

## 可复现性、代码与数据

- 优点：作者仓库公开 Apache-2.0 代码、30 个任务 adapter、上游仓库 pinned revision、环境/资产说明、prompt、验证器、聚合脚本和 strict result-integrity checks。
- 公开 commit 当前只有 initial release，未发现 release tag；README 明确 raw runs 和 generated summaries 不提交，第三方仓库、数据、权重和 checkpoints 也不分发。因而主表不能仅从当前仓库离线重算。
- 30 个任务依赖异构 Conda 环境、许可证和大模型/数据资产；完整复现的工程与计算成本显著，但论文没有总 GPU-hours 或 wall time。
- 本轮只做静态代码/规范审计，没有启动上游训练，不把“代码可见”写成“主结果已复现”。

## 局限与威胁

- 搜索空间定义与论文叙述不一致：多个 task 改模型结构或模型族，不能作为固定架构 HPO 的整体验证。
- 自适应循环可见 test 类指标，没有 hidden test；这会把搜索分数与泛化估计混在一起。
- Agent 与经典基线的信息输入不同，且 BOHB 只保留 proposer、没有 multi-fidelity resource allocation；结论应限于这些完整系统的比较。
- 主表用 final-step，经典方法通常返回 incumbent；best-so-far 后排序明显变化。
- API 方法没有多 seed，requests/token 口径与本地模型不同，且没有货币、总 GPU、wall-clock 或失败重试成本的统一核算。
- 上游任务 anchor 来自论文、仓库或 reproduction，可靠性和可比性并不完全同质。

## 与当前 AgenticNAS 的直接关联

- 可复用：基线 + typed intervention schema + 每步验证 + 原始响应/失败 provenance + no-feedback 消融；这套轨迹结构适合评估 Agent 是否真正利用实验反馈。
- 必须改造：把 30 个任务按 `architecture-only`、`training-HPO-only`、`mixed` 显式拆分；当前仓库的总体平均数不能越过课题边界。
- 评估协议应同时报告 `final-step` 与 `incumbent/best-so-far`，并给 seeds × iterations 二维预算；不能因 Agent 忘记较优候选就给经典 HPO 施加同样的非标准输出规则。
- 所有搜索反馈必须 validation-only，test 仅用于最终一次确认；真实 latency、peak memory、energy 和部署正确性 gate 仍未被该 benchmark 覆盖。
- `quality_proxy` 与 `latency_proxy_ms` 在本仓库中仍只能作为流程占位符，不能借本论文包装成研究指标。

## 最小复现建议

- 选择 iTransformer 或 TimeXer 一个含结构字段的任务，复制原五步协议，但拆成三条 lane：固定结构 HPO、结构-only、mixed；每条至少 5 个 search seeds。
- 对每条 lane 同时运行 default-seeded random/TPE、LLM metric-only、LLM metric+logs；保持 attempted/accepted/evaluated、训练预算和可见信息一致。
- 只向循环暴露 validation metric，最终对每个 seed 的 incumbent 做一次 test；同时报告 final-step 与 best-so-far。
- 记录每次 LLM request/retry/tokens、GPU-hours、wall time、失败类型和设备指标；预期成本取决于所选 task，论文不足以给出可靠估算。

## Citation-ready note

AgentHPOBench 把 30 个真实研究仓库包装为“参考基线 + 五次顺序干预”的 Agent 优化任务，并显示中间实验反馈能改善 Qwen3-32B 的总体 MBNS。其公开任务中存在大量结构与模型族字段，部分循环还直接观察 test 类指标；同时，final-step 与 best-so-far 口径会显著改变经典 HPO 和 Agent 的相对排序。因此它更适合作为 mixed-search-space Agent benchmark 和轨迹审计框架，而不是固定架构、validation-only HPO 优势的证据。
