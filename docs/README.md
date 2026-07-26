# 文档导航

文档按“系统设计”和“使用指南”分开维护：

- [系统设计](design/DESIGN.md)：Conv1d Transformer、层次搜索空间、Agent 边界和 Pareto 搜索闭环；
- [内部 Agent 接入](guides/INTERNAL_AGENT_GUIDE.md)：将 GLM、MiniMax 或 Claude 接入现有 NAS 控制器；
- [Claude Code 迁移任务](guides/CLAUDE_CODE_TASK.md)：可交给内部 Claude Code 的受约束实施说明；
- [LLM 训练参数调优](guides/LLM_TRAINING_TUNING.md)：训练超参提议、分级评估及与 NAS 的公平性边界。

架构、搜索协议或指标定义变化时更新 `design/`；接入步骤、提示词或工作流变化时更新 `guides/`。
