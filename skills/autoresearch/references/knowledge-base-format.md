# 纯 Markdown 经验知识库（Knowledge Base）格式、完整性与修剪规范

经验知识库（`knowledge_base/`）完全采用纯 Markdown 文件存储（零数据库依赖），兼顾人工 / Obsidian 阅读、Git Diff 审查与 `autoresearch.py` 强类型解析。

- 内置预置知识库目录：[`assets/knowledge_base/INDEX.md`](../assets/knowledge_base/INDEX.md)（含 `CONV1D-ARCH-001`、`EDGE-VIT-ARCH-001`、`CNN-CSI-ARCH-001`、`FIXED-BACKBONE-HPO-001`）。

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
> 底部 `<!-- knowledge_base:record:start -->` JSON 块包含 `content_sha256` 签名；手改文本会触发 `Revision integrity check failed`。
> - **初始化阶段修改 `v1` 种子配置**：统一使用 `autoresearch.py configure --workspace <ws> ...`。
> - **实验沉淀与规则淘汰**：统一使用 `knowledge-base distill` / `knowledge-base publish` / `knowledge-base prune`。

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

---

## 3. 模式加权聚合、自然衰减与陈旧经验修剪（Skill Pruning）

1. **加权聚合与负向衰减**：
   - `patterns` 与 `anti_patterns` 以规范化 `change_signature` 作为唯一去重主键；
   - `distill` 仅采集 `fidelity == "full"` 且非 `infra_flake` 的可靠试验结果；
   - 当某条历史已知 `pattern` 在新 Campaign 中被复测却遭遇 `discard / crash` 时，`distill` 会自动生成一条 `wins=0, observations=1` 的衰减记录——`publish` 合并后该模式的胜率（`wins / observations`）随之自然下降。
2. **主动淘汰陈旧失效经验（`knowledge-base prune`，参考 `MLEvolver` Skill Deletion）**：
   - 长期堆积未验证或低胜率规则会稀释检索信噪比；
   - 运行 `knowledge-base prune <entry_id> [--min-win-rate 0.34] [--min-observations 2]` 可预览待清理的低胜率非 Holdout 模式（默认保护 `verified_holdout` 模式与所有 `anti_patterns` 安全护栏）；
   - 经用户确认后加 `--apply --reviewer <name>` 生成精简后的新不可变修订 `revisions/vN.md`。
