# 纯 Markdown 结构经验库格式规范

结构经验库完全使用纯 Markdown 文档存储（零数据库依赖），兼顾人工/Obsidian 阅读、Git 评审与程序精确解析。

## 目录结构

```text
kb/
  INDEX.md                         # 自动维护的总目录表（kb reindex 可一键重建）
  entries/
    <KB_ID>/
      CURRENT.md                   # 当前生效发布版本
      revisions/
        v1.md                      # 永久不可变历史修订（支持 kb show <id> --revision v1）
        v2.md
      drafts/
        v2-draft-<cmp>.md          # kb distill 生成的隔离草案（绝不污染 CURRENT.md）
      EVIDENCE.md                  # 追加式实证账本
```

## `scope.param_bounds` 写法

在 `CURRENT.md` 底部的 `<!-- kb:record:start -->` JSON 块中配置 `scope.param_bounds`，支持顶层字段或嵌套 dot-path，Harness 会在 `campaign propose` 阶段强制拦截越界提案：

```json
"param_bounds": {
  "encoder.num_blocks": {"type": "int", "min": 2, "max": 8},
  "encoder.channels": {"type": "int", "enum": [32, 48, 64, 96, 128]},
  "encoder.use_se": {"type": "bool"},
  "encoder.ffn_ratio": {"type": "float", "min": 1.25, "max": 4.0},
  "encoder.block_type": {"type": "str", "enum": ["standard", "depthwise_separable"]}
}
```

## 模式去重与聚合规则

- `patterns` 与 `anti_patterns` 以规范化 `change_signature`（按键排序的变更签名）作为主键。
- `kb publish` 合并草案时：
  - 已有相同 `change_signature` 的模式不会重复追加，而是加权更新 `stats.observations / wins / mean_gain_pp / mean_flops_ratio / mean_gpu_seconds` 并升级 `confidence`；
  - 已有相同 `change_signature` 的反例累加 `occurrences` 并更新 `failure_type`（`compute_budget_exceeded | guardrail_violated | accuracy_regression | training_crash | other`）。
