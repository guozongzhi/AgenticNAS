# EDGE-VIT-ARCH-001 · 边缘视觉轻量化混合 ViT/CNN 结构增益与延迟优化经验

| 字段 | 值 |
| --- | --- |
| 经验条目编号 | `EDGE-VIT-ARCH-001` |
| 修订版本 | `v1`（父版本：`-`） |
| 研究轨道 | `architecture` |
| 发布状态 | `published` |
| 适用模型族 | `edge_vit` |
| 审核人 | `seed-library` |
| 内容指纹 | `5db2ce87325264cd...` |

## 摘要

面向工业检测与端侧分类的轻量化混合视觉骨干。固定训练配方，平衡窗口感受野、倒残差/深度可分离模块与分类/检测头宽度，严控端侧推理时延与峰值显存。

## 适用边界与算量红线

- **目标算量上限**：`-` / 倍率 `<= 1.05x`
- **禁用算子**：-

### 参数合法域（`param_bounds`）

| 字段 | 类型 | 范围 / 枚举 |
| --- | --- | --- |
| `backbone.depth` | `int` | min=`4`, max=`10` |
| `backbone.embed_dim` | `int` | enum: `[128, 160, 192, 224, 256]` |
| `backbone.mlp_ratio` | `float` | min=`1.5`, max=`4.0` |
| `backbone.window_size` | `int` | enum: `[7, 14]` |
| `backbone.block_type` | `str` | enum: `['conv_attn_hybrid', 'depthwise_separable', 'inverted_bottleneck']` |
| `head.hidden_dim` | `int` | enum: `[64, 128, 192]` |

## 推荐有效模式（Patterns）

| ID | 说明 | 声明式变更 | 方向 | 均值增益(%) | 均值算量比 | 观测/胜出 | 置信度 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `P-VIT-IBN-MLP25` | 采用倒残差块 inverted_bottleneck 并将 mlp_ratio 收敛至 2.5 | `backbone.block_type="inverted_bottleneck";backbone.mlp_ratio=2.5` | `gain_up_compute_down` | +1.90% | 0.880x | 2/2 | `medium` |
| `P-VIT-SLIM-HEAD64` | 将任务头 hidden_dim 从 128 压缩至 64 | `head.hidden_dim=64` | `compute_down_tie` | +0.00% | 0.930x | 1/1 | `medium` |

## 已知反例与失效边界（Anti-Patterns）

| ID | 反例说明 | 避坑变更 | 失败类型 | 实测算量比 | 次数 |
| --- | --- | --- | --- | --- | --- |
| `AP-VIT-W14-DIM256` | 同时开启大窗口 window_size=14 与宽通道 embed_dim=256 | `backbone.embed_dim=256;backbone.window_size=14` | `compute_budget_exceeded` | 1.920x | 1 |

---

<!-- 机器精确解析块：请通过 autoresearch.py configure / knowledge-base distill / knowledge-base publish / knowledge-base prune 维护，勿手改导致 SHA-256 校验失败 -->
<!-- knowledge_base:record:start -->
```json
{
  "schema_version": 2,
  "entry_id": "EDGE-VIT-ARCH-001",
  "revision": "v1",
  "parent_revision": null,
  "track": "architecture",
  "status": "published",
  "tags": [
    "edge_vit",
    "architecture",
    "seed-library"
  ],
  "title": "边缘视觉轻量化混合 ViT/CNN 结构增益与延迟优化经验",
  "summary": "面向工业检测与端侧分类的轻量化混合视觉骨干。固定训练配方，平衡窗口感受野、倒残差/深度可分离模块与分类/检测头宽度，严控端侧推理时延与峰值显存。",
  "scope": {
    "model_family": "edge_vit",
    "forbidden_ops": [],
    "max_compute_value": null,
    "max_compute_ratio": 1.05,
    "param_bounds": {
      "backbone.depth": {
        "type": "int",
        "min": 4,
        "max": 10
      },
      "backbone.embed_dim": {
        "type": "int",
        "enum": [
          128,
          160,
          192,
          224,
          256
        ]
      },
      "backbone.mlp_ratio": {
        "type": "float",
        "min": 1.5,
        "max": 4.0
      },
      "backbone.window_size": {
        "type": "int",
        "enum": [
          7,
          14
        ]
      },
      "backbone.block_type": {
        "type": "str",
        "enum": [
          "conv_attn_hybrid",
          "depthwise_separable",
          "inverted_bottleneck"
        ]
      },
      "head.hidden_dim": {
        "type": "int",
        "enum": [
          64,
          128,
          192
        ]
      }
    }
  },
  "patterns": [
    {
      "pattern_id": "P-VIT-IBN-MLP25",
      "title": "采用倒残差块 inverted_bottleneck 并将 mlp_ratio 收敛至 2.5",
      "suggested_changes": {
        "backbone.block_type": "inverted_bottleneck",
        "backbone.mlp_ratio": 2.5
      },
      "effect": {
        "direction": "gain_up_compute_down",
        "notes": "对移动端/边缘 NPU 算子友好，推理延迟降低约 12% 且保持局部边缘特征"
      },
      "stats": {
        "observations": 2,
        "wins": 2,
        "mean_gain_pct": 1.9,
        "mean_compute_ratio": 0.88,
        "mean_cost": 240.0
      },
      "confidence": "medium",
      "evidence_refs": [
        "seed:edge-vision-prior"
      ],
      "change_signature": "backbone.block_type=\"inverted_bottleneck\";backbone.mlp_ratio=2.5",
      "target_fields": [
        "backbone.block_type",
        "backbone.mlp_ratio"
      ]
    },
    {
      "pattern_id": "P-VIT-SLIM-HEAD64",
      "title": "将任务头 hidden_dim 从 128 压缩至 64",
      "suggested_changes": {
        "head.hidden_dim": 64
      },
      "effect": {
        "direction": "compute_down_tie",
        "notes": "单任务工业场景类别数较少，收缩检测/分类头可在精度持平下削减尾部参数"
      },
      "stats": {
        "observations": 1,
        "wins": 1,
        "mean_gain_pct": 0.0,
        "mean_compute_ratio": 0.93,
        "mean_cost": 190.0
      },
      "confidence": "medium",
      "evidence_refs": [
        "seed:edge-vision-prior"
      ],
      "change_signature": "head.hidden_dim=64",
      "target_fields": [
        "head.hidden_dim"
      ]
    }
  ],
  "anti_patterns": [
    {
      "pattern_id": "AP-VIT-W14-DIM256",
      "title": "同时开启大窗口 window_size=14 与宽通道 embed_dim=256",
      "avoid_changes": {
        "backbone.window_size": 14,
        "backbone.embed_dim": 256
      },
      "failure_type": "compute_budget_exceeded",
      "observed_compute_ratio": 1.92,
      "observed_gain_pct": 2.3,
      "observed_failure": "窗口注意力计算量与端侧峰值显存激增至 1.92x，超出实时部署上限",
      "occurrences": 1,
      "evidence_refs": [
        "seed:edge-vision-prior"
      ],
      "change_signature": "backbone.embed_dim=256;backbone.window_size=14",
      "target_fields": [
        "backbone.embed_dim",
        "backbone.window_size"
      ]
    }
  ],
  "reviewed_by": "seed-library",
  "published_at": 0,
  "content_sha256": "5db2ce87325264cde2a43137ad64e81c70dad0f29ef93fceae3dc65c4f89a725"
}
```
<!-- knowledge_base:record:end -->
