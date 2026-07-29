# AgenticNAS

一个面向研究复现与方法验证的 clean-room 参考仓库：使用 LLM Agent 在受约束的空间中搜索 **真实神经网络架构**，而不是搜索 Agent 工作流。当前可运行基线为 4–10 层 Conv1d Transformer，重点保留可验证的动作契约、评估协议与 Pareto 搜索闭环。

仓库不包含公司内部 Archai 实现、私有模型端点、训练数据、未审批的架构细节或运行日志。它的作用是为公开研究、方法原型和受控的内部迁移提供清晰边界。

## 当前内容

- **Agentic NAS Demo**：以结构化 `ArchitectureSpec` 表示 4–10 层 Conv1d Transformer；Agent 只能提交经过校验的 `MutationAction`。
- **多目标搜索基线**：保留随机/进化式 mutation、候选去重、Pareto 维护和可回放 observation/action/result trace。
- **本地论文证据工具**：从本地 PDF 抽取带页码的证据包，供 Codex 生成待人工核验的结构化论文笔记；不需要额外 LLM API。
- **研究工作区**：维护论文索引、解析草稿、每日检索报告、技术点研究档案（`research/topics/`，当前包括边缘视觉小模型与 LLM 超参优化/训练自动化两条线），以及后续可复现实验的协议与结果。

研究组织上，`LLM × NAS` 与 `LLM × HPO` 是两条独立主线：NAS 固定训练配方并搜索架构，HPO 固定模型架构并搜索训练超参；当前不做联合搜索。

## 先明确研究边界

本仓库的 `quality_proxy` 和 `latency_proxy_ms` 仅用于验证搜索控制流，**不是实验结果**。形成研究结论前，必须以同一候选数、训练预算、GPU/硬件预算和 LLM 预算比较下列策略：

1. native/random mutation；
2. stateless LLM policy；
3. memory-aware LLM policy。

每组实验至少报告 action validity、duplicate rate、Pareto hypervolume、成本与多随机种子方差。真实延迟、吞吐、显存和训练质量应由实际评估器替换，而不是由 Demo 代理指标推断。

## 快速开始

要求：Python 3.10+、PyTorch 2.0+。安装项目依赖：

```bash
python3 -m pip install -e .
```

从仓库根目录运行完整的 Demo 验证和一次小规模搜索：

```bash
PYTHONPATH=demos python3 -m unittest discover -s demos/agentic_nas_demo/tests -v
PYTHONPATH=demos python3 -m agentic_nas_demo \
  --seed 7 \
  --initial-population 6 \
  --iterations 3 \
  --proposals 4
```

搜索 trace 默认写入 `demos/agentic_nas_demo/outputs/demo/`，包括每轮 observation、Agent actions 和最终 Pareto 前沿。该目录已被 Git 忽略。

## 论文检索与解析

本地 PDF 解析工具按关键词选取证据片段，并把 PDF 页码一起写入 Codex 上下文包。安装 `pypdf`、PyMuPDF 或 Poppler 的 `pdftotext` 任一工具后即可使用：

```bash
PYTHONPATH=demos/llm_paper_analysis python3 \
  demos/llm_paper_analysis/paper_parser.py \
  --pdf research/papers/pdfs/2302.14838-evoprompting.pdf \
  --query "LLM NAS mutation crossover Pareto budget ablation" \
  --force

PYTHONPATH=demos/llm_paper_analysis python3 -m unittest discover \
  -s demos/llm_paper_analysis/tests -v
```

工具仅生成证据包；论文笔记必须写入 `research/papers/parsed/` 并标记为 `codex_draft`。在人工核对标题、主要数字、预算、硬件和证据位置前，不得将笔记视为 related-work 或实验结论。

每日检索结果写入 `research/daily/`，并更新论文索引与新增解析笔记。自动任务在隔离副本中工作、只提交本次生成的研究材料，并直接推送 `main`；若远端发生并发变化则停止报告，不强推覆盖。

## 目录导航

```text
demos/
├── agentic_nas_demo/       # Conv1d Transformer、搜索空间、Agent 契约与 Pareto 搜索
└── llm_paper_analysis/     # 本地 PDF 证据提取与测试

docs/
├── design/                 # 模型、层次搜索空间、Pareto 和 Agent 边界
└── guides/                 # 内部接入、任务迁移与训练调优

research/
├── daily/                  # 每日文献检索报告
├── topics/                 # 技术点研究档案（边缘视觉小模型、LLM 超参优化）
└── papers/
    ├── INDEX.md            # 阅读队列与状态
    ├── parsed/             # Codex 草稿和人工核验模板
    └── pdfs/               # 本地缓存的 PDF（已忽略）

experiments/
└── YYYYMMDD-short-topic/   # 协议、专属代码、测试、结果与已忽略输出
```

## 架构与搜索协议

| 层次 | 当前含义 | 可搜索动作 |
|---|---|---|
| `block` | 完整 Transformer 层 | 深度在 4–10 层之间增减 |
| `cell` | attention 或 FFN 子结构 | `num_heads`、`ffn_ratio` |
| `op` | cell 内具体属性 | FFN 卷积核、激活函数 |

`embed_dim` 在初始采样时从 `64/96/128` 选择，并在单次 mutation 期间保持不变。后续若搜索全局宽度，应增加独立的 model 层动作，而不是把它混入 block mutation。

Agent 提议必须是可序列化、可回放的声明式动作。validator 应拒绝未知父候选、非法层级/字段/取值/深度、重复架构和任意 Python 代码；训练、硬件评估和 Pareto 更新保持确定性。

## 实验与提交要求

每个正式实验先在 `experiments/YYYYMMDD-short-topic/` 建立 `PROTOCOL.md`，明确任务、搜索空间、候选/训练/GPU/LLM 预算、硬件、基线、指标和随机种子。LLM 实验还应记录模型或端点版本、temperature、最大 token、提示词 hash、调用次数和无效动作率。

可提交：协议、专属代码、测试、聚合结果、人工核验笔记和获批的图表/摘要。
不可提交：数据集、checkpoint、受版权保护的 PDF、API key、公司内部源码、原始内部日志或未经审批的架构细节。

## 延伸阅读

- [系统设计](docs/design/DESIGN.md)
- [内部 Agent 接入](docs/guides/INTERNAL_AGENT_GUIDE.md)
- [LLM 训练参数调优](docs/guides/LLM_TRAINING_TUNING.md)
- [可运行 Demo](demos/README.md)
- [研究资料入口](research/README.md)
- [研究课题边界：LLM × NAS / LLM × HPO](research/topics/README.md)
- [技术点：边缘视觉小模型](research/topics/edge-vision-small-models.md)
- [课题二：LLM 辅助的超参数优化](research/topics/llm-hpo-training-automation.md)
- [实验目录约定](experiments/README.md)
