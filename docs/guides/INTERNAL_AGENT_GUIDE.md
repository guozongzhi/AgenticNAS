# 内部 Agent 接入指南

本文说明如何在不导出公司源码的前提下，把 Claude Code、GLM 或 MiniMax 接到现有 Archai NAS 搜索闭环。

## 1. 推荐接入位置

Archai 的公开 `EvolutionParetoSearch` 会从当前 Pareto 前沿选择父代，再通过 search space 的 mutation/crossover 产生新候选。内部最小改动方案是：

```text
原有 Pareto parent selection
        ↓
构造匿名 AgentObservation
        ↓
Agent 选择 parent / block-cell-op / mutation
        ↓
内部 search space 校验并构建 child
        ↓
原有 evaluator + Pareto update
```

保留原有 evaluator、训练器、缓存、搜索结果和 Pareto 实现。第一阶段只替换或旁路 mutation proposal。

## 2. 公司内部需要实现的四个适配函数

```python
def summarize_frontier(internal_search_result) -> dict:
    """将内部前沿转换成允许提供给 Agent 的匿名摘要。"""

def parse_agent_action(payload: dict) -> InternalMutation:
    """校验 Agent JSON，并映射到内部 block/cell/op mutation。"""

def apply_internal_mutation(parent, mutation):
    """调用现有 Archai search space 构造 child，不允许 Agent 直接改源码。"""

def record_agent_trace(observation, action, result) -> None:
    """将敏感原始轨迹保存在内部环境。"""
```

四个函数之外的代码尽量保持不变。

## 3. Agent 系统提示词模板

```text
你是一个受约束的多目标神经网络架构搜索策略器。

目标：在固定候选评估预算内，提高 accuracy/quality，降低 latency、memory 和 parameter count，并扩大 Pareto 前沿的 hypervolume。

规则：
1. 只能从输入 pareto_frontier 中选择 parent_id。
2. 只能使用 allowed_action_schema 声明的 block/cell/op 动作。
3. 每个动作只改变一个字段。
4. 不得生成 Python 代码、完整模型或新的算子名称。
5. 避免重复已有架构。
6. 严格返回 JSON，不要返回 Markdown 或解释。
7. actions 数量必须等于 requested_action_count。

选择策略：
- 一部分动作改善当前高质量模型；
- 一部分动作探索 Pareto 前沿稀疏区域；
- 根据历史局部修改的指标增量选择搜索层次；
- 不要把代理指标描述为真实精度或真实延迟。

输出格式：
{"actions": [{"parent_id": "...", "level": "...", "target_index": null, "field": "...", "value": 0}]}
```

将 `AgentObservation.to_dict()` 和 `requested_action_count` 作为用户消息发送。

## 4. 模型接入示意

不同内部平台的 SDK 不同，因此公开 Demo 不提供具体密钥、endpoint 或客户端。适配层只需要满足：输入 Python dict，输出 JSON 字符串。

```python
import json

from agentic_nas_demo.agent import CallableJsonAgent
from agentic_nas_demo.search import run_search


def internal_completion(request: dict) -> str:
    prompt = json.dumps(request, ensure_ascii=False)
    response_text = approved_internal_client.generate(prompt)
    return response_text


result = run_search(
    policy=CallableJsonAgent(internal_completion),
    initial_population=8,
    iterations=5,
    proposals_per_iteration=6,
    trace_dir="demos/agentic_nas_demo/outputs/internal_agent",
)
```

生产环境还应在 `internal_completion` 外增加：

- JSON schema 校验；
- 超时和有限次数重试；
- 模型版本及生成参数记录；
- 请求/响应 hash；
- 敏感字段过滤；
- 失败时回退原生 mutation，而不是中止整轮搜索。

这些属于内部基础设施，Demo 没有假设具体实现。

## 5. Claude Code 的两种用法

### 5.1 作为开发 Agent

推荐先让 Claude Code 阅读内部工程，并按 [CLAUDE_CODE_TASK.md](CLAUDE_CODE_TASK.md) 实现上述适配器。此时 Claude Code 不参与每一轮搜索，只负责代码集成和测试。

### 5.2 作为搜索 Agent

如果内部允许 Claude Code 在搜索运行期间读写文件，可以使用文件交换：

1. 搜索器写入 `iteration_N_observation.json`；
2. Claude Code 读取文件，只生成 `iteration_N_actions.json`；
3. 搜索器校验动作并执行；
4. 结果写入内部 trace；
5. 下一轮 observation 只暴露批准的信息。

文件模式适合早期实验，但不适合大量并行搜索。确认方法有效后，再改成内部模型 API 调用。

## 6. GLM 与 MiniMax 的实验定位

不要同时让两个模型互相讨论。先把模型能力与 Agent 机制分开：

- 主实验固定一个模型，比较是否有 Pareto 状态、历史记忆和层次决策；
- 迁移实验把同一提示词和状态格式换到另一个模型；
- 所有模型使用相同 candidate budget；
- 另外报告 token、调用次数、调用延迟、JSON 无效率和重复率。

模型切换后方法仍有效，才能说明贡献来自 Agentic NAS 机制，而不是某个模型的预训练偏好。

## 7. 内部信息边界

建议至少划分：

| 数据 | 内部原始日志 | 可公开 clean-room 日志 |
|---|---|---|
| 源码和算子实现 | 保留 | 不允许 |
| 真实 op 名称 | 保留 | 替换为匿名 ID |
| 完整架构图 | 保留 | 仅公开公共 benchmark 架构 |
| 公司任务/数据 | 保留 | 不允许或按审批范围 |
| Agent 动作类别 | 保留 | 可聚合统计 |
| hypervolume/预算曲线 | 保留 | 仅在获批后导出 |
| 提示词 | 保留 | 另写无机密公共版本 |

不要假设 SHA-256 架构 ID 自动满足匿名化要求；是否可以导出仍应由公司审批边界决定。

## 8. 最小验收

内部接入完成后，先运行小规模验收：

1. 原生 mutation 和 Agent mutation 各跑 3 个种子；
2. 每个种子使用相同初始种群和评估预算；
3. 检查 Agent action 合法率和重复率；
4. 对比 hypervolume 随候选数变化；
5. 随机抽取 20 条动作，人工确认 observation 足以解释动作；
6. 确认关闭 Agent 后原有 Archai 搜索行为不变。

通过这组验收后，再增加长期记忆、多精度评估或多 Agent。
