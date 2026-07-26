# Agentic NAS Conv1d Transformer Demo

这是一个不依赖公司源码、也不依赖 Archai 安装的 clean-room Demo。它用于验证以下最小闭环：

1. 用结构化配置描述 4–10 层 Transformer；
2. 用 `Conv1d` 替换注意力、FFN 和输出头中的全连接投影；
3. 按 block / cell / op 三个层次修改架构；
4. 计算多目标指标并更新 Pareto 前沿；
5. 通过 JSON 契约让 Claude Code、GLM、MiniMax 或其他内部 Agent 提议搜索动作。

Demo 不包含公司内部 Archai 实现、真实数据集或训练代码，可以作为公开参考实现，也可以交给内部 Agent 按接口迁移。

## 关于“emd”的实现假设

当前将“emd”理解为 embedding dimension / embedding 结构：

- 输入由 token embedding 与 position embedding 组成；
- `embed_dim` 是全局通道宽度；
- 每个 Transformer block 包含 attention cell 和 FFN cell；
- Attention 的 QKV、Attention 输出、FFN 输入/输出以及 LM head 均使用 `nn.Conv1d`；
- `kernel_size=1` 与逐 token 的 Linear 等价；FFN 输入卷积允许搜索 `1/3/5`，其中 `3/5` 使用左侧 padding 保持因果性。

如果你所说的 EMD 是公司内部的特定算子，只需替换 `ConvFeedForward`，搜索和 Agent 协议无需改变。

## 快速运行

环境要求：Python 3.10+、PyTorch 2.0+。

```bash
PYTHONPATH=demos python3 -m unittest discover -s demos/agentic_nas_demo/tests -v
PYTHONPATH=demos python3 -m agentic_nas_demo \
  --seed 7 \
  --initial-population 6 \
  --iterations 3 \
  --proposals 4
```

运行后会生成：

```text
demos/agentic_nas_demo/outputs/demo/
├── iteration_01_observation.json
├── iteration_01_actions.json
├── iteration_02_observation.json
├── iteration_02_actions.json
└── search_result.json
```

`observation.json` 是可以发送给内部 Agent 的状态，`actions.json` 是 Agent 应返回的结构化动作，`search_result.json` 保存最终 Pareto 前沿。

## 代码结构

```text
demos/
├── README.md
├── agentic_nas_demo/
│   ├── model.py          # Conv1d Transformer
│   ├── search_space.py   # 架构配置和 block/cell/op 变异
│   ├── pareto.py         # 演示指标、支配关系和 Pareto 前沿
│   ├── agent.py          # Agent observation/action 契约
│   ├── search.py         # Agent proposal → 校验 → 评估 → Pareto 闭环
│   ├── __main__.py       # 命令行入口
│   ├── examples/         # Demo 专属输入输出示例
│   ├── tests/            # Demo 单元测试
│   └── outputs/          # 已忽略的本地运行产物
└── llm_paper_analysis/   # 本地 PDF 检索与 Codex 结构化解析

experiments/
└── README.md             # 正式实验的 src/tests/outputs 约定

docs/
├── README.md
├── design/
│   └── DESIGN.md
└── guides/
    ├── INTERNAL_AGENT_GUIDE.md
    ├── CLAUDE_CODE_TASK.md
    └── LLM_TRAINING_TUNING.md

research/
├── README.md
└── papers/                  # NAS paper index and retained reading notes
```

## 搜索层次

| 层次 | Demo 中的含义 | 可搜索动作 |
|---|---|---|
| block | 完整 Transformer 层 | 深度在 4–10 之间增减 |
| cell | Attention 或 FFN 子结构 | `num_heads`、`ffn_ratio` |
| op | cell 内的具体算子属性 | FFN 卷积核、激活函数 |

`embed_dim` 当前在初始采样时从 `64/96/128` 选择，变异阶段保持不变，以避免一次修改同时改变所有 block。后续若需要搜索全局宽度，应增加独立的 `model` 层次动作，而不是塞进 block mutation。

## 重要限制

当前 `quality_proxy` 和 `latency_proxy_ms` 是确定性的演示公式，只用于验证控制流，不能作为论文结果。`params_m` 来自真实 PyTorch 模型参数量。迁移到内部环境时应替换为：

- 代理精度或短周期训练结果；
- 真实设备 latency / throughput；
- 峰值显存；
- 编译成功率；
- 完整训练精度或 perplexity。

详细模型与搜索设计见 [DESIGN.md](docs/design/DESIGN.md)，内部 Agent 接入见 [INTERNAL_AGENT_GUIDE.md](docs/guides/INTERNAL_AGENT_GUIDE.md)。

## 研究工作流

- [LLM 训练参数调优方案](docs/guides/LLM_TRAINING_TUNING.md)：将 LLM 作为受约束的训练参数提议器，并与 NAS 结构收益公平分离。
- [研究资料入口](research/README.md)：维护 NAS 论文的阅读队列、单篇笔记和可复现行动项。
- [Codex 论文解析工具](demos/llm_paper_analysis/README.md)：从本地 PDF 检索带页码证据，并由 Codex 生成待人工核验的结构化笔记。
- [实验目录约定](experiments/README.md)：将后续实验的协议、专属代码和可公开结果按实验归档。

## 与 Archai 的关系

这个 Demo 有意保持框架无关。Archai 的公开接口通过 `EvolutionarySearchSpace.mutate/crossover` 定义进化搜索空间，并由 `EvolutionParetoSearch` 在当前 Pareto 前沿上生成和评估新候选；内部迁移时，Agent proposal 最适合插入 mutation proposal 位置，而不是重写 evaluator 或 Pareto 计算。可参考 [Archai 官方搜索空间文档](https://microsoft.github.io/archai/getting_started/notebooks/discrete_search/search_space.html)和[官方 Evolution Pareto API](https://microsoft.github.io/archai/reference/api/archai.discrete_search.algos.html)。
