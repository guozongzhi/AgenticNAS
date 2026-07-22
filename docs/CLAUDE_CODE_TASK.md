# 可交给内部 Claude Code 的迁移任务

下面内容可以复制给公司内部 Claude Code。提交前请把方括号内路径和命令替换成真实值。

---

你需要在现有 Archai NAS 工程中加入一个最小、可关闭的 Agent mutation proposal 适配层。

约束：

1. 不重写现有训练器、evaluator、Pareto 计算、模型构建或缓存逻辑。
2. 不改变关闭 Agent 时的原有搜索行为。
3. 第一版仅替换候选 mutation proposal，不实现多 Agent、长期记忆或自动调参。
4. Agent 不能直接生成或修改模型源码，只能返回结构化 block/cell/op 动作。
5. 所有 Agent 动作必须由现有 search space 再次校验。
6. 不把源码、真实 op 定义、完整架构或公司数据发送到未批准的服务。
7. 遵循工程现有代码风格和测试方式，不重构无关代码。

开始前只读检查：

- 找到 `EvolutionParetoSearch` 或等价搜索控制器的调用位置；
- 找到当前 parent selection、mutation、crossover、evaluator 和 Pareto update；
- 找到 block/cell/op 配置的内部表示；
- 找到搜索 trace、随机种子和 objective 保存位置；
- 汇报最小插入点和预计修改文件，不要立即大范围修改。

需要实现：

```python
class AgentProposalPolicy(Protocol):
    def propose(self, observation: dict, count: int) -> list[dict]:
        ...
```

以及四个边界函数：

```python
summarize_frontier(search_state) -> dict
validate_and_parse_action(payload) -> InternalMutation
apply_agent_mutation(parent, mutation) -> ChildModel
record_agent_trace(observation, action, result) -> None
```

Agent observation 至少包含：

- iteration；
- evaluated_count；
- remaining_budget；
- 匿名 Pareto frontier；
- 每个父代允许执行的 block/cell/op 动作；
- objective 的优化方向；
- requested_action_count。

Agent action 格式：

```json
{
  "parent_id": "anonymous id",
  "level": "block | cell | op",
  "target_index": 0,
  "field": "allowed field",
  "value": "allowed value"
}
```

必须拒绝：

- 不存在的 parent；
- 超出 4–10 层的架构；
- embed dim 不能被 head 数整除；
- 不存在的 block/cell/op；
- 未声明字段或取值；
- 一次修改多个字段；
- 重复架构；
- Agent 返回的代码或自由文本。

配置开关：

```text
agent.enabled = false               # 默认关闭
agent.provider = glm|minimax|claude
agent.proposals_per_iteration = N
agent.fallback_to_native_mutation = true
agent.trace_dir = [内部路径]
```

测试要求：

1. Agent 关闭时，固定种子结果与修改前一致；
2. block/cell/op 各有合法和非法动作测试；
3. 4 层和 10 层边界测试；
4. 无效 JSON、超时和重复动作回退原生 mutation；
5. Agent observation 不包含被禁止字段；
6. 搜索 trace 可从 observation/action/result 回放；
7. 运行项目原有 NAS 测试。

交付时输出：

- 修改文件清单；
- Agent 插入位置；
- JSON schema；
- 开关和回退行为；
- 测试命令及结果；
- 尚未解决的风险。

不要把内部源码或日志复制到外部位置。

---
