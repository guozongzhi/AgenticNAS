# 纯 Markdown 经验知识库（Knowledge Base）格式与完整性规范

经验知识库（`knowledge_base/`）完全采用纯 Markdown 文件存储（零数据库依赖），兼顾人工 / Obsidian 阅读、Git Diff 审查与 `autoresearch.py` 强类型解析。

- 技能内置开箱即用的预置知识库目录：[`assets/knowledge_base/INDEX.md`](../assets/knowledge_base/INDEX.md)（含 `CONV1D-ARCH-001`、`EDGE-VIT-ARCH-001`、`CNN-CSI-ARCH-001`、`FIXED-BACKBONE-HPO-001` 四条完整 Markdown 条目）。

---

## 1. 目录结构与 SHA-256 完整性防篡改

```text
knowledge_base/
  INDEX.md                         # 自动维护的总索引表（knowledge-base reindex 可随时重建）
  entries/
    <ENTRY_ID>/
      CURRENT.md                   # 当前生效发布版本（带 content_sha256 校验）
      revisions/
        v1.md                      # 永久不可变历史快照（knowledge-base show <id> --revision v1）
        v2.md
      drafts/
        v2-draft-<id>.md           # knowledge-base distill 生成的隔离待审草案（绝不污染 CURRENT.md）
      EVIDENCE.md                  # 追加式实证账本（记录每次 Campaign 的验收结果与审核人）
```

> **切勿手工直接编辑 `CURRENT.md`**：
> 文档底部 `<!-- knowledge_base:record:start -->` JSON 块包含 `content_sha256` 签名；手改文本会导致 `Revision integrity check failed` 报错并使 `revisions/v1.md` 与 `campaign.json` 冻结快照失步。
> - **初始化阶段修改 `v1` 种子配置**：统一使用 `autoresearch.py configure --workspace <ws> ...`。
> - **实验结束后沉淀新修订 `v2+`**：统一执行 `knowledge-base distill` → 用户审核 → `knowledge-base publish`。

---

## 2. `scope.param_bounds` 与 `forbidden_ops`

`campaign propose` 会在提交 MCP 前硬校验字段类型、范围/枚举及禁用算子：

```json
"scope": {
  "model_family": "cnn_csi_feedback",
  "forbidden_ops": ["nn.Linear"],
  "max_compute_value": 55.0,
  "max_compute_ratio": 1.1,
  "param_bounds": {
    "encoder.num_blocks": {"type": "int", "min": 2, "max": 8},
    "encoder.channels": {"type": "int", "enum": [32, 48, 64, 96, 128]},
    "encoder.use_se": {"type": "bool"},
    "encoder.mlp_ratio": {"type": "float", "min": 1.5, "max": 4.0},
    "encoder.block_type": {"type": "str", "enum": ["standard", "depthwise_separable"]}
  }
}
```

支持的 `type`：`int`（严格整数，拒绝 `bool`）、`float`（有限数值）、`str`（非空字符串）、`bool`（布尔值）。

---

## 3. 模式（`patterns`）与反例（`anti_patterns`）去重聚合

- 主键为规范化变更签名 `change_signature`（按键名排序的 `field=json_val` 分号拼接串，如 `encoder.kernel_size=5;encoder.use_se=true`）。
- **有效模式方向枚举（`effect.direction`）**：
  - `gain_up_compute_down`（增益提升且算量下降 <0.99x，最高优先级）
  - `gain_up_compute_neutral`（增益提升且算量基本持平 <=1.02x）
  - `gain_up_compute_up`（增益提升且算量在红线内温和上升）
  - `compute_down_tie`（主指标持平且算量显著下降）
  - `other`
- **失效反例类型枚举（`failure_type`）**：
  - `compute_budget_exceeded` | `guardrail_violated` | `accuracy_regression` | `training_crash` | `other`
  - 当提案命中已发布 `anti_patterns` 的 `change_signature` 时，`campaign propose` 默认直接拦截并返回历史失效原因（除非显式传入 `--force-anti-pattern`）。
- **跨 Campaign 发布聚合**：`knowledge-base publish` 合并草案时，相同 `change_signature` 的模式自动按观测次数加权更新 `observations / wins / mean_gain_pct / mean_compute_ratio / mean_cost` 并提升 `confidence`（`low` < `medium`/`dev_only` < `verified_holdout`）；相同签名的反例累加 `occurrences`。
