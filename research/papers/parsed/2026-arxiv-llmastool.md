---
title: "LLM as a Tool, Not an Agent: Code-Mined Tree Transformations for Neural Architecture Search"
authors: "Masakazu Yoshimura, Zitang Sun, Yuiko Sakuma, Junji Otsuka, Atsushi Irie, Takeshi Ohashi"
year: "2026"
venue: "arXiv:2604.16555v1"
doi: "10.48550/arXiv.2604.16555"
paper_url: "https://arxiv.org/abs/2604.16555"
source_pdf: "https://arxiv.org/pdf/2604.16555"
source: "arXiv v1 metadata/PDF and GitHub repository/code search, accessed 2026-08-02"
parser: "Codex"
parsed_on: "2026-08-02"
status: codex_draft
tags: [llm-nas, tree-search, module-mining, bayesian, open-ended, cnn]
---

# LLM as a Tool, Not an Agent: Code-Mined Tree Transformations for Neural Architecture Search

> 本笔记基于 arXiv v1 的 72 页 PDF。正文未给作者实现链接，2026-08-02 的 GitHub 精确检索也未找到公开代码，因此可复现性判断保守。

## 一句话结论

LLMasTool 用 AST 从现有 PyTorch 代码挖出可复用模块，把整网表示成层次树，再由 Bayesian coarse-to-fine planner 选择 transformation，LLM 只补齐位置、模块和参数等剩余自由度；它与本仓库 block/cell/op typed action 很接近，但实验主要是 100/500 次、单目标 accuracy + FLOPs/parameter constraints，缺少代码、GPU/LLM 成本和设备 latency/memory 证据。（pp. 5–15, 19–26）

## 书目信息与来源核验

- arXiv ID：2604.16555v1；提交日期：2026-04-17；arXiv DOI：10.48550/arXiv.2604.16555。
- 作者：Masakazu Yoshimura、Zitang Sun、Yuiko Sakuma、Junji Otsuka、Atsushi Irie、Takeshi Ohashi；当前可核验 venue 为 arXiv。
- 论文：https://arxiv.org/abs/2604.16555
- 代码：论文参考文献只链接 PyTorch/MMCV/MMPretrain/timm 等依赖；截至 2026-08-02 未找到论文作者实现仓库。
- 置信度：书目信息 high；方法 high；表格转录 medium-high；公平性 medium；端到端可复现性 low。

## 研究问题与贡献

- 问题：自由代码生成容易无效且受 LLM 先验模式限制，传统 graph NAS 又依赖手工 search space；如何保留可执行模块资产，同时获得更开放的结构探索。（pp. 1–5）
- 模块挖掘：规则算法解析任意 PyTorch source 的 AST，提取 `nn.Module` 类、constructor arguments、forward 输入输出元信息、默认值和模块源码。（p. 5）
- 表示：整网是 model→backbone/neck→module→constructor argument 的层次树，支持 list/重复层，搜索通过 tree transformation 而不是完整代码生成。（pp. 5–8）
- 决策：operation/category 由分层 epsilon-greedy Thompson sampling 选择；LLM 只处理最后的具体 transformation。（pp. 7–9）

## 方法拆解

### 搜索或优化对象

- 搜索对象是真实 DNN 架构；候选从一个 base architecture 出发，修改层次树并实例化为可训练网络，不是搜索 Agent workflow。
- 模块库来自 PyTorch 2.9.0、MMCV 2.1.0、MMPretrain 1.2.0、timm 1.0.19，分别抽取 167、107、467、681 个 modules。（p. 11）
- 结构变量包括 channel width、kernel size、module type、内部 module、重复层、插入/删除位置和 composite module，属于 NAS；optimizer、data split 与每个实验的 training recipe 固定。（pp. 5, 8, 10–12, 20–21）
- 五个基本动作是 change hyperparameter、swap module、insert/delete module、create module；另有成功后复用方向的 repeat previous meta-operation。（pp. 7–8）
- 表示可映射到 block/cell/op 层级，但没有本仓库的 Conv1d Transformer、4–10 层和 `nn.Linear` 禁止约束。

### Agent 与优化闭环

- 状态包括 module database、architecture database 与 history database；history 记录 transformation、base architecture 和 metric improvement。（pp. 6–7）
- planner 先选 operation，再选三类 prompt category（依赖 LLM、反向探索、最小 LLM/强调多样性），再由规则枚举 location/module candidates，最后让 Qwen3-8B 生成唯一具体 transformation。（pp. 7–11）
- feasibility 检查 `executable × constraint-satisfied × intended-transformation`；通过后才实例化、训练并把 accuracy improvement 回写 history。（pp. 6–7）
- operation/category 的 Bayesian history 只保留 improvement sign，使用 Beta-Bernoulli Thompson sampling；epsilon 0.5 时混入 uniform exploration，避免架构变化导致 posterior 过早锁定。（p. 9, pp. 20, 23–24）
- 规则工具负责 subtree 查询、替换、插入、删除、module compatibility 与 candidate sampling；LLM 接收有限候选与源码，负责最终 location/module/hyperparameter 决定。（pp. 27–35）
- 论文没有报告 invalid/OOM/timeout/divergence 的逐类计数；feasibility 失败是否计入 100/500 trials 的精确口径需从代码核验。

### 评估与预算

- NAS-Bench-201：CIFAR-10、CIFAR-100、ImageNet16-120，从 ResNet-32 开始，报告 100 与 500 个 new architectures；参数上限 1.5M，FLOPs 上限分别 0.2/0.2/0.05 GFLOPs。（pp. 10–11）
- NAS-Bench-201 候选沿用 benchmark 的 data split、optimizer 与 200 epochs recipe；100-trial 结果的 `±` 为三次 runs 的标准差。（pp. 10–11, 20–21）
- ImageNet-100：主要从 MobileNetV3-Small0.5 开始，2M parameters、0.3 GFLOPs 约束；主消融搜索 100 architectures，每个只训练 1 epoch。（pp. 11–13, 21–26）
- Appendix 另用 100 candidates × 100 epochs 验证 coarse-to-fine/H-Thompson，但仍是 ImageNet-100 单项消融。（p. 26）
- 所有搜索使用 100 或 500 architecture trials，并行运行四个 evolution processes；100-trial 从 top-5 取 base，500-trial从 top-25 取 base。（p. 20）
- 作者称一次 LLM generation 约 1 分钟，而 NAS-Bench-201 每候选 200 epochs 训练约 60–150 分钟；未报告 GPU 型号、GPU-hours、总 wall time、LLM calls/tokens/费用。（pp. 19–20）
- FLOPs/parameter 是约束，不是目标设备 latency、peak memory、energy 或多目标 Pareto measurement。

## 实验证据

| Claim | Metric/result | Baseline | Evidence locator | Confidence |
|---|---|---|---|---|
| NAS-Bench-201 500-trial test | 95.31 / 77.83 / 53.20 | NADER 94.62 / 76.00 / 50.52；均列 500 architectures | p. 10, Table 1 | medium |
| 100-trial 三 run test | 95.08±0.22 / 76.52±0.28 / 50.43±0.55 | 同表 conventional 与 LLM NAS | p. 10, Table 1 | medium-high |
| ImageNet-100 组件累加 | base 24.21；code-gen 28.62；tree-trans 33.44；完整 H-Thompson 40.78 | 100 candidates、1 epoch | pp. 12–14, Table 2 | medium |
| module mining | primitive modules 33.21 vs mined modules 40.78 | 100 candidates、1 epoch | pp. 12–13, Table 3 | medium |
| 少依赖 LLM 的 swap 消融 | 完全 random location/module 35.58，高于两者由 LLM决定 29.98 | swap-only、100 evolutions | pp. 22–23, Table 6 | medium |
| longer-training 消融 | base 73.00；code-gen 74.96；tree-trans 81.00；H-Thompson 81.72 | 100 candidates × 100 epochs | p. 26, Table 11 | medium |

## 公平性与可信度检查

- NAS-Bench-201 明确使用相同 data partitions/training recipe，且 LLMasTool 100-trial 结果有三 runs；这是最可靠的内部可比部分。
- Table 1 多数 baseline 来自文献而非同环境重跑；parameter sharing、search space、candidate evaluator、GPU/LLM budget 不同，不能从 accuracy 表推导成本优势。
- LLMasTool 与 NADER 都列 500 architectures，但二者模块资产、LLM信息来源、每候选训练和调用成本未统一；“同候选数”不等于端到端 matched budget。
- ImageNet-100 Table 2 是逐步叠加多组件的 pipeline comparison，不是所有因素单独、等价地开关；40.78 不能归因于任一单组件。
- 一 epoch proxy 对 attention/MobileViT 收敛较慢有偏差，论文在 Appendix C.6 也观察到这一点；100-epoch消融只覆盖一个设置。（pp. 25–26）
- 论文没有完整报告 action validity、duplicate、search-seed variance（500-trial row）、失败 trials、GPU/LLM成本和真实设备指标。

## 可复现性与代码/数据

- PDF 提供搜索算法、树工具伪代码、依赖版本、候选数、训练 recipe、FLOPs/parameter constraints 和大量附录消融。
- 论文没有给作者代码 URL；GitHub 以完整标题和 `LLMasTool` 检索未找到公开仓库。依赖仓库不是方法实现。
- 缺少具体 prompts、完整 module metadata schema、tree serialization、validator edge cases、LLM serving/sampling、random seeds、GPU 环境和原始 traces。
- 没有冻结的 search results/artifacts，无法核对 100/500 trials 是否含 feasibility failures、重复候选或并行 race 的精确预算。

## 与 AgenticNAS 的关系

- 层次树和五类 transformation 可映射为 `block/cell/op/connectivity` scope + typed `MutationAction`；高层由可审计 sampler 控制，LLM 只填少量合法枚举值。
- history 只保存 operation/category 与 improvement sign，提供了比完整 prompt/log 更窄的 clean-room memory 接口；本仓库还应保存 typed error 与 objective vector。
- module mining 提醒搜索空间可从资产自动构建，但公开实现不能扫描或携出内部源码；clean-room 版本只能读取批准的 operator manifest、license metadata 和结构化 signature。
- repeat-previous 可作为 exploitation action，但必须与 random/native mutation、stateless LLM、memory-aware LLM 在相同 attempted candidates 和 seeds 下比较。
- 单目标 accuracy + FLOPs constraints 应扩展为真实 quality/latency/peak-memory/cost Pareto；FLOPs 不是 device latency。
- `quality_proxy` 与 `latency_proxy_ms` 只能作控制流占位符，不能用本文 accuracy/FLOPs 充当仓库实验结果。

## 最小复现实验

- 用公开 Conv1d operator registry 构造 4–10 层 architecture tree，固定训练 recipe、data split 和真实设备 evaluator。
- 对照 native random transformation、uniform tree search、flat Thompson、hierarchical Thompson、LLM 全规划、algorithm scope + LLM details。
- 每组 200 attempted candidates、三组以上 search seeds；统一 LLM calls/tokens、training steps、GPU-hours、timeout 和 parallelism。
- 所有 invalid/duplicate/OOM/timeout 计预算；top-k 相同完整训练和真实设备复测。
- 指标：best-so-far、hypervolume、validity、duplicate、operation coverage、seed variance、LLM/GPU cost、latency 和 peak memory。

## 局限与风险

- 无公开实现，关键预算口径和并行细节无法独立核对。
- 依赖大规模第三方模块库，接口兼容检查只看 forward 变量数仍可能漏掉 shape/semantic constraints。
- ImageNet-100 主要使用一 epoch proxy；NAS-Bench-201 每候选完整训练又带来高搜索成本。
- baseline 不是完整 matched GPU/LLM budget，且部分 500-trial结果没有搜索方差。
- 没有真实 latency/memory/energy 或多目标 Pareto 证据；“deploy-friendly”是表示主张，不是部署测量。

## 可引用摘要

LLMasTool 从现有 PyTorch 代码挖取模块，将网络表示为层次树，并用规则枚举、层次 Thompson sampling 和小范围 LLM 决策执行 change/swap/insert/delete/create transformations。作者在 NAS-Bench-201 的 100/500 architecture trials 和 ImageNet-100 消融中报告 accuracy 提升。当前证据受无公开代码、GPU/LLM 成本缺失、baseline 预算不完全匹配和缺少真实设备多目标测量限制。

## 检索与人工核验记录

- arXiv：https://arxiv.org/abs/2604.16555
- PDF：https://arxiv.org/pdf/2604.16555
- 已核对：标题、作者、日期、arXiv ID/DOI、module mining、tree representation、transformations、Bayesian loop、候选/训练约束、主要表格与 limitations。
- 未核对：作者代码、独立运行、GPU/LLM成本、完整失败账、500-trial search seeds 和原始 traces。
- [ ] 已由人工决定 `retained` / `discarded`
