# FIXED-BACKBONE-HPO-001 · 架构锁定后的固定骨干训练超参数调优经验

| 字段 | 值 |
| --- | --- |
| 经验条目编号 | `FIXED-BACKBONE-HPO-001` |
| 修订版本 | `v1`（父版本：`-`） |
| 研究轨道 | `hpo` |
| 发布状态 | `published` |
| 适用模型族 | `fixed_backbone_hpo` |
| 审核人 | `seed-library` |
| 内容指纹 | `3fcc7b30009f30f3...` |

## 摘要

仅在模型架构完成独立留出集（Holdout）验收并冻结后启用。严格锁定模型深度、宽度、算子与连接方式，仅在等预算下优化学习率、预热比例、权重衰减与 Dropout。

## 适用边界与算量红线

- **目标算量上限**：`-` / 倍率 `<= 1.01x`
- **禁用算子**：-

### 参数合法域（`param_bounds`）

| 字段 | 类型 | 范围 / 枚举 |
| --- | --- | --- |
| `lr` | `float` | min=`1e-05`, max=`0.01` |
| `weight_decay` | `float` | min=`0.0`, max=`0.2` |
| `warmup_ratio` | `float` | min=`0.0`, max=`0.2` |
| `dropout` | `float` | min=`0.0`, max=`0.3` |
| `epochs` | `int` | min=`5`, max=`100` |

## 推荐有效模式（Patterns）

| ID | 说明 | 声明式变更 | 方向 | 均值增益(%) | 均值算量比 | 观测/胜出 | 置信度 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `P-HPO-WARMUP01-LR5E4` | 延长预热比例 warmup_ratio 至 0.10 并配合稳健学习率 5e-4 | `lr=0.0005;warmup_ratio=0.1` | `gain_up_compute_neutral` | +1.60% | 1.000x | 2/2 | `medium` |
| `P-HPO-WD005-DROP01` | 适度提高 weight_decay 至 0.05 并引入 dropout=0.1 缓解过拟合 | `dropout=0.1;weight_decay=0.05` | `gain_up_compute_neutral` | +1.10% | 1.000x | 1/1 | `medium` |

## 已知反例与失效边界（Anti-Patterns）

| ID | 反例说明 | 避坑变更 | 失败类型 | 实测算量比 | 次数 |
| --- | --- | --- | --- | --- | --- |
| `AP-HPO-LR1E2-NOWARMUP` | 高学习率 lr=0.01 叠加零预热 warmup_ratio=0.0 | `lr=0.01;warmup_ratio=0.0` | `training_crash` | 1.000x | 2 |
| `AP-HPO-DROP03-SHORT` | 短训预算下施加过高正则 dropout=0.3 | `dropout=0.3` | `accuracy_regression` | 1.000x | 1 |

---

<!-- 机器精确解析块：请通过 autoresearch.py configure / knowledge-base distill / knowledge-base publish / knowledge-base prune 维护，勿手改导致 SHA-256 校验失败 -->
<!-- knowledge_base:record:start -->
```json
{
  "schema_version": 2,
  "entry_id": "FIXED-BACKBONE-HPO-001",
  "revision": "v1",
  "parent_revision": null,
  "track": "hpo",
  "status": "published",
  "tags": [
    "fixed_backbone_hpo",
    "hpo",
    "seed-library"
  ],
  "title": "架构锁定后的固定骨干训练超参数调优经验",
  "summary": "仅在模型架构完成独立留出集（Holdout）验收并冻结后启用。严格锁定模型深度、宽度、算子与连接方式，仅在等预算下优化学习率、预热比例、权重衰减与 Dropout。",
  "scope": {
    "model_family": "fixed_backbone_hpo",
    "forbidden_ops": [],
    "max_compute_value": null,
    "max_compute_ratio": 1.01,
    "param_bounds": {
      "lr": {
        "type": "float",
        "min": 1e-05,
        "max": 0.01
      },
      "weight_decay": {
        "type": "float",
        "min": 0.0,
        "max": 0.2
      },
      "warmup_ratio": {
        "type": "float",
        "min": 0.0,
        "max": 0.2
      },
      "dropout": {
        "type": "float",
        "min": 0.0,
        "max": 0.3
      },
      "epochs": {
        "type": "int",
        "min": 5,
        "max": 100
      }
    }
  },
  "patterns": [
    {
      "pattern_id": "P-HPO-WARMUP01-LR5E4",
      "title": "延长预热比例 warmup_ratio 至 0.10 并配合稳健学习率 5e-4",
      "suggested_changes": {
        "lr": 0.0005,
        "warmup_ratio": 0.1
      },
      "effect": {
        "direction": "gain_up_compute_neutral",
        "notes": "抑制深层注意力/卷积块早期梯度尖峰，推理算量完全不变（1.00x）"
      },
      "stats": {
        "observations": 2,
        "wins": 2,
        "mean_gain_pct": 1.6,
        "mean_compute_ratio": 1.0,
        "mean_cost": 150.0
      },
      "confidence": "medium",
      "evidence_refs": [
        "seed:hpo-prior"
      ],
      "change_signature": "lr=0.0005;warmup_ratio=0.1",
      "target_fields": [
        "lr",
        "warmup_ratio"
      ]
    },
    {
      "pattern_id": "P-HPO-WD005-DROP01",
      "title": "适度提高 weight_decay 至 0.05 并引入 dropout=0.1 缓解过拟合",
      "suggested_changes": {
        "weight_decay": 0.05,
        "dropout": 0.1
      },
      "effect": {
        "direction": "gain_up_compute_neutral",
        "notes": "缩小训练/验证集泛化间隙，零推理开销增量"
      },
      "stats": {
        "observations": 1,
        "wins": 1,
        "mean_gain_pct": 1.1,
        "mean_compute_ratio": 1.0,
        "mean_cost": 150.0
      },
      "confidence": "medium",
      "evidence_refs": [
        "seed:hpo-prior"
      ],
      "change_signature": "dropout=0.1;weight_decay=0.05",
      "target_fields": [
        "dropout",
        "weight_decay"
      ]
    }
  ],
  "anti_patterns": [
    {
      "pattern_id": "AP-HPO-LR1E2-NOWARMUP",
      "title": "高学习率 lr=0.01 叠加零预热 warmup_ratio=0.0",
      "avoid_changes": {
        "lr": 0.01,
        "warmup_ratio": 0.0
      },
      "failure_type": "training_crash",
      "observed_compute_ratio": 1.0,
      "observed_gain_pct": null,
      "observed_failure": "前 2 个 epoch 内触发梯度爆炸与 Loss NaN 发散崩溃",
      "occurrences": 2,
      "evidence_refs": [
        "seed:hpo-prior"
      ],
      "change_signature": "lr=0.01;warmup_ratio=0.0",
      "target_fields": [
        "lr",
        "warmup_ratio"
      ]
    },
    {
      "pattern_id": "AP-HPO-DROP03-SHORT",
      "title": "短训预算下施加过高正则 dropout=0.3",
      "avoid_changes": {
        "dropout": 0.3
      },
      "failure_type": "accuracy_regression",
      "observed_compute_ratio": 1.0,
      "observed_gain_pct": -3.2,
      "observed_failure": "小模型表征容量受限下强丢弃导致严重欠拟合",
      "occurrences": 1,
      "evidence_refs": [
        "seed:hpo-prior"
      ],
      "change_signature": "dropout=0.3",
      "target_fields": [
        "dropout"
      ]
    }
  ],
  "reviewed_by": "seed-library",
  "published_at": 0,
  "content_sha256": "3fcc7b30009f30f3b9bf8f5f7902981ea165fdcf50106943e40b0f2a98166b52"
}
```
<!-- knowledge_base:record:end -->
