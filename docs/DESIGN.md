# 设计说明

## 1. 目标和非目标

Demo 的目标是提供一个最小、可运行、可迁移的 Agentic NAS 参考闭环。它验证数据结构和控制边界，不试图复刻公司内部 Archai 框架。

目标：

- 结构描述与 PyTorch 模型一一对应；
- 模型深度严格限制为 4–10 层；
- Transformer 内不出现 `nn.Linear`；
- Agent 只能提出声明式动作，不能直接修改模型代码；
- 所有 Agent 输入输出都可保存和回放；
- 搜索结果由确定性的 Pareto 规则决定，LLM 不能自行宣称某模型更优。

非目标：

- 不提供真实训练数据；
- 不把演示代理指标当作性能结论；
- 不绑定 GLM、MiniMax 或 Claude 的某个 SDK；
- 不复制 Archai 内部实现。

## 2. Conv1d Transformer

输入 token 的形状为 `[batch, time]`：

```text
token ids
  → token embedding + position embedding     [B, T, D]
  → transpose                                [B, D, T]
  → 4–10 × ConvTransformerBlock              [B, D, T]
  → channel LayerNorm                        [B, D, T]
  → Conv1d LM head                           [B, V, T]
  → transpose logits                         [B, T, V]
```

每个 block 使用 pre-norm 残差结构：

```text
x = x + ConvSelfAttention(LayerNorm(x))
x = x + ConvFeedForward(LayerNorm(x))
```

### 2.1 Attention cell

`ConvSelfAttention` 包含：

- `Conv1d(D, 3D, kernel_size=1)`：一次生成 Q/K/V；
- PyTorch `scaled_dot_product_attention`：执行因果注意力；
- `Conv1d(D, D, kernel_size=1)`：输出投影。

逐位置 `Conv1d(kernel_size=1)` 与 Linear 在数学上等价，但张量布局是 `[B, D, T]`，更接近卷积实现和某些内部算子接口。

### 2.2 FFN cell

`ConvFeedForward` 包含：

- 输入卷积 `Conv1d(D, ratio × D, kernel_size=1/3/5)`；
- GELU 或 SiLU；
- 输出卷积 `Conv1d(ratio × D, D, kernel_size=1)`。

当输入卷积核大于 1 时，只在序列左侧 padding，避免语言模型看到未来 token。

### 2.3 输出 head

输出采用 `Conv1d(D, vocab_size, kernel_size=1)`，因此模型中没有 `nn.Linear`。当前没有绑定 token embedding 和输出 head 权重；如果内部模型需要 weight tying，需要确认内部 Conv1d 权重布局后再实现。

## 3. 架构表示

`ArchitectureSpec` 保存全局配置：

- `embed_dim`：64、96、128；
- `depth`：由 block 数量推导，范围 4–10；
- `vocab_size`；
- `max_seq_len`；
- `blocks`：每一层的 `BlockSpec`。

每个 `BlockSpec` 包含：

- `num_heads`：2、4、8，且必须整除 `embed_dim`；
- `ffn_ratio`：2、3、4；
- `ffn_kernel_size`：1、3、5；
- `activation`：GELU 或 SiLU。

规范化 JSON 的 SHA-256 前 12 位作为 `arch_id`，用于去重和匿名引用。它不是安全匿名化方案；内部若需要跨边界导出，应使用公司批准的重新编号方式。

## 4. 层次化搜索动作

Agent 不返回完整架构，只返回一次局部变更：

```json
{
  "parent_id": "38b29330d061",
  "level": "cell",
  "target_index": 2,
  "field": "ffn_ratio",
  "value": 3
}
```

动作与层次的对应关系：

| level | field | 语义 |
|---|---|---|
| block | depth | 截断尾部 block，或复制最后一个 block 扩展深度 |
| cell | num_heads | 修改指定层 Attention head 数量 |
| cell | ffn_ratio | 修改指定层 FFN expansion ratio |
| op | ffn_kernel_size | 修改指定层 FFN 输入卷积核 |
| op | activation | 修改指定层激活函数 |

扩展深度时复制最后一个 block 是为了保持 Demo 简单。正式实现可让 Agent 同时指定新 block 的模板来源，但应保持为一个原子动作，避免无法归因的多处修改。

## 5. 搜索闭环

每轮执行：

1. 从已评估候选计算 Pareto 前沿；
2. 将前沿、剩余预算和动作约束组成 `AgentObservation`；
3. Agent 返回固定数量的 `MutationAction`；
4. 控制器检查 parent、层次、字段、取值、深度和重复架构；
5. 对合法候选进行评估；
6. 更新 archive 和 Pareto 前沿；
7. 保存 observation、action 和最终结果。

当前三个目标为：

- `quality_proxy`：最大化；
- `params_m`：最小化；
- `latency_proxy_ms`：最小化。

候选 A 支配 B，当且仅当 A 在所有目标上不差于 B，且至少一个目标严格优于 B。

## 6. Agent 边界

`HeuristicAgent` 是不依赖模型服务的基线。它从 Pareto 前沿选择父代并随机选择合法层次动作，用来证明搜索链路本身可运行。

`CallableJsonAgent` 接受一个内部 completion function：

```python
from agentic_nas_demo.agent import CallableJsonAgent

def company_completion(request: dict) -> str:
    # 在这里调用公司批准的 GLM、MiniMax 或 Claude 服务。
    # 必须返回 {"actions": [...]} 的 JSON 字符串。
    ...

policy = CallableJsonAgent(company_completion)
```

completion function 是唯一的模型相关边界。搜索空间、验证器、评估器和 Pareto 逻辑不依赖模型提供方。

## 7. 从 Demo 到研究系统

建议按以下顺序替换组件：

1. 先用内部真实 evaluator 替换演示代理；
2. 再将 `ArchitectureSpec` 映射到内部 Archai model metadata；
3. 用内部原生 mutation 作为对照，保留相同 parent 和评估预算；
4. 接入一个 LLM proposal policy；
5. 最后增加历史经验、评估等级和预算决策。

不要同时替换搜索空间、评估器、mutation 和 Agent，否则无法判断收益来源。

## 8. 必须补充的研究级验证

- 固定 evaluated architectures、完整训练次数、GPU-hours 和 LLM 调用次数；
- 多随机种子报告 hypervolume 随预算变化；
- 比较内部原生 mutation、随机 mutation、无状态 LLM 和带记忆 Agent；
- 记录无效动作率、重复率和每个层次动作的实际收益；
- 将 op 名称匿名化，检查 Agent 是否依赖预训练知识；
- 固定模型 endpoint、版本、temperature、最大 token 和提示词 hash；
- 使用真实设备的重复测量替换 latency proxy。
