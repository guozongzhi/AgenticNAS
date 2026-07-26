# 实验目录约定

`experiments/` 用于后续正式实验的代码、协议和可公开结果。每个实验使用 `YYYYMMDD-short-topic/` 目录，例如 `20260726-agent-vs-random/`，并至少保留：

- `PROTOCOL.md`：假设、搜索空间、数据、硬件、预算、基线、指标和随机种子；
- `src/`：该实验专属的运行或评估代码；可复用能力成熟后再提取，避免提前抽象；
- `tests/`：该实验专属测试；
- `outputs/`：已忽略的本地运行 trace、日志和中间结果；
- `RESULTS.md`：聚合结果、失败运行、成本和结论；
- `artifacts/`：仅存放获批可提交的小型图表或机器可读汇总。

NAS 和训练参数调优必须分别标明预算。若实验包含 LLM，额外记录模型/端点版本、temperature、最大 token、提示词 hash、调用次数和无效动作率。完整 trace 放在该实验自己的 `outputs/`，并从 `RESULTS.md` 引用其内部位置或可公开摘要。

不要提交数据集、checkpoint、API key、公司内部源码或未经审批的原始日志。
