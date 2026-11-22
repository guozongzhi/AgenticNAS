# HPO-001 · 锁定胜出结构后的收尾 HPO 训练配方经验

| 字段 | 值 |
| --- | --- |
| 经验编号 | `HPO-001` |
| 修订版本 | `v1`（父版本：`-`） |
| 轨道 | `hpo` |
| 状态 | `published` |
| 允许用途 | `training`, `evaluation` |
| 标签 | `hpo`, `post-architecture`, `recipe` |
| 审核人 | `seed` |
| 内容指纹 | `c1f49238278ab5da...` |

## 摘要

仅在架构搜索轨道锁定最终结构并验收后启用。固定模型结构不变，仅微调学习率、权重衰减、warmup 与 epochs，榨取最后一段稳定增益并控制训练 GPU 算量。

## 适用范围与算量约束

- **模型族**：`locked_conv1d_winner`
- **基线推理算量**：`None` MFLOPs
- **目标算量红线**：`<= None` MFLOPs / `<= 1.0x`
- **禁用算子**：-

### 参数合法域（`param_bounds`）

| 字段 | 类型 | 范围 / 枚举 |
| --- | --- | --- |
| `lr` | `float` | min=`1e-05`, max=`0.01` |
| `weight_decay` | `float` | min=`0.0`, max=`0.1` |
| `epochs` | `int` | min=`1`, max=`6` |

## 推荐结构模式（Patterns）

| ID | 模式说明 | 声明式变更 | 方向 | 均值增益(pp) | 均值算量比 | 观测/胜出 | 置信度 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `P-COSINE-LR` | 降低初始学习率配合轻度 weight_decay 稳定收敛 | `lr=0.0005;weight_decay=0.02` | `gain_up_compute_neutral` | +4.17 | 1.00x | 1/1 | `low` |

## 已知反例与失效边界（Anti-Patterns）

| ID | 反例说明 | 避坑变更 | 失败类型 | 实测算量比 | 实测增益(pp) | 次数 |
| --- | --- | --- | --- | --- | --- | --- |
| `AP-LONG-EPOCHS` | 小样本下将 epochs 翻倍至 8 以上 | `epochs=8` | `accuracy_regression` | 1.00x | -4.17 | 1 |

---

<!-- 以下为机器精确解析用结构化块，请通过 kb CLI 或保持合法 JSON 维护 -->
<!-- kb:record:start -->
```json
{
  "schema_version": 2,
  "kb_id": "HPO-001",
  "revision": "v1",
  "parent_revision": null,
  "track": "hpo",
  "status": "published",
  "approved_uses": [
    "training",
    "evaluation"
  ],
  "tags": [
    "hpo",
    "post-architecture",
    "recipe"
  ],
  "title": "锁定胜出结构后的收尾 HPO 训练配方经验",
  "summary": "仅在架构搜索轨道锁定最终结构并验收后启用。固定模型结构不变，仅微调学习率、权重衰减、warmup 与 epochs，榨取最后一段稳定增益并控制训练 GPU 算量。",
  "scope": {
    "model_family": "locked_conv1d_winner",
    "forbidden_ops": [],
    "baseline_flops_m": null,
    "target_flops_budget_m": null,
    "max_flops_ratio": 1.0,
    "param_bounds": {
      "lr": {
        "type": "float",
        "min": 1e-05,
        "max": 0.01
      },
      "weight_decay": {
        "type": "float",
        "min": 0.0,
        "max": 0.1
      },
      "epochs": {
        "type": "int",
        "min": 1,
        "max": 6
      }
    }
  },
  "patterns": [
    {
      "pattern_id": "P-COSINE-LR",
      "title": "降低初始学习率配合轻度 weight_decay 稳定收敛",
      "suggested_changes": {
        "lr": 0.0005,
        "weight_decay": 0.02
      },
      "effect": {
        "expected_gain_pp_range": [
          2.0,
          5.0
        ],
        "expected_flops_ratio_range": [
          1.0,
          1.0
        ],
        "direction": "gain_up_compute_neutral",
        "notes": "减少末期震荡，推理与训练算量均不增加。"
      },
      "stats": {
        "observations": 1,
        "wins": 1,
        "mean_gain_pp": 4.17,
        "mean_flops_ratio": 1.0,
        "mean_gpu_seconds": 60.0
      },
      "confidence": "low",
      "evidence_refs": [],
      "change_signature": "lr=0.0005;weight_decay=0.02",
      "target_fields": [
        "lr",
        "weight_decay"
      ]
    }
  ],
  "anti_patterns": [
    {
      "pattern_id": "AP-LONG-EPOCHS",
      "title": "小样本下将 epochs 翻倍至 8 以上",
      "avoid_changes": {
        "epochs": 8
      },
      "failure_type": "accuracy_regression",
      "observed_flops_ratio": 1.0,
      "observed_gain_pp": -4.17,
      "observed_failure": "训练 GPU 算量翻倍以上且开发集过拟合。",
      "occurrences": 1,
      "evidence_refs": [],
      "change_signature": "epochs=8",
      "target_fields": [
        "epochs"
      ]
    }
  ],
  "text": "锁定胜出结构后的收尾 HPO 训练配方经验。仅在架构搜索轨道锁定最终结构并验收后启用。固定模型结构不变，仅微调学习率、权重衰减、warmup 与 epochs，榨取最后一段稳定增益并控制训练 GPU 算量。 推荐结构模式：降低初始学习率配合轻度 weight_decay 稳定收敛。 已知反例：小样本下将 epochs 翻倍至 8 以上。",
  "reviewed_by": "seed",
  "published_at": 0,
  "content_sha256": "c1f49238278ab5da416e0c3898b537ceab233eec6df8a56f3066588a97d878bb"
}
```
<!-- kb:record:end -->
