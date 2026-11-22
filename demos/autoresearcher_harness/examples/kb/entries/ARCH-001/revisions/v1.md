# ARCH-001 · 4–10 层 Conv1d Transformer 增益与算量权衡结构经验

| 字段 | 值 |
| --- | --- |
| 经验编号 | `ARCH-001` |
| 修订版本 | `v1`（父版本：`-`） |
| 轨道 | `architecture` |
| 状态 | `published` |
| 允许用途 | `training`, `evaluation` |
| 标签 | `conv1d`, `transformer`, `gain-compute-tradeoff`, `ai-ran` |
| 审核人 | `seed` |
| 内容指纹 | `9cff3ac08f448165...` |

## 摘要

在固定训练配方与样本预算下，优化 4–10 层 Conv1d Transformer 结构（禁止在 Conv1d 路径引入 nn.Linear）。核心目标是在推理算量红线（<= 1.10x 基线，<= 132 MFLOPs）内最大化归因增益，并在同增益下优先压低推理 FLOPs。

## 适用范围与算量约束

- **模型族**：`conv1d_transformer_4_10L`
- **基线推理算量**：`120.0` MFLOPs
- **目标算量红线**：`<= 132.0` MFLOPs / `<= 1.1x`
- **禁用算子**：`nn.Linear`

### 参数合法域（`param_bounds`）

| 字段 | 类型 | 范围 / 枚举 |
| --- | --- | --- |
| `num_layers` | `int` | min=`4`, max=`10` |
| `d_model` | `int` | enum: `[128, 192, 256, 320]` |
| `kernel_size` | `int` | enum: `[3, 5, 7, 9]` |
| `dilation` | `int` | enum: `[1, 2, 4]` |
| `ffn_ratio` | `float` | min=`1.25`, max=`4.0` |
| `conv_type` | `str` | enum: `['standard', 'depthwise_separable']` |

## 推荐结构模式（Patterns）

| ID | 模式说明 | 声明式变更 | 方向 | 均值增益(pp) | 均值算量比 | 观测/胜出 | 置信度 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `P-DWCONV` | 深度可分离卷积替换标准 Conv1d + 适度扩大卷积核 | `conv_type="depthwise_separable";kernel_size=7` | `gain_up_compute_down` | +14.00 | 0.84x | 1/1 | `medium` |
| `P-DILATION` | 引入 dilation=2 扩大时序感受野而不增加参数与 FLOPs | `dilation=2` | `gain_up_compute_neutral` | +6.00 | 1.00x | 1/1 | `medium` |
| `P-PRUNE-FFN` | 同增益下收缩冗余 FFN 倍率以压低推理算量 | `ffn_ratio=1.75` | `compute_down_tie` | +0.00 | 0.91x | 1/1 | `medium` |

## 已知反例与失效边界（Anti-Patterns）

| ID | 反例说明 | 避坑变更 | 失败类型 | 实测算量比 | 实测增益(pp) | 次数 |
| --- | --- | --- | --- | --- | --- | --- |
| `AP-OVERDEEP-WIDE` | 同时堆叠至 9–10 层并放大 d_model / ffn_ratio | `d_model=256;ffn_ratio=3.5;num_layers=10` | `compute_budget_exceeded` | 1.68x | -4.20 | 1 |
| `AP-NARROW-KERNEL` | 过小卷积核（kernel_size <= 3）且无空洞 | `dilation=1;kernel_size=3` | `accuracy_regression` | 0.92x | -4.17 | 1 |

---

<!-- 以下为机器精确解析用结构化块，请通过 kb CLI 或保持合法 JSON 维护 -->
<!-- kb:record:start -->
```json
{
  "schema_version": 2,
  "kb_id": "ARCH-001",
  "revision": "v1",
  "parent_revision": null,
  "track": "architecture",
  "status": "published",
  "approved_uses": [
    "training",
    "evaluation"
  ],
  "tags": [
    "conv1d",
    "transformer",
    "gain-compute-tradeoff",
    "ai-ran"
  ],
  "title": "4–10 层 Conv1d Transformer 增益与算量权衡结构经验",
  "summary": "在固定训练配方与样本预算下，优化 4–10 层 Conv1d Transformer 结构（禁止在 Conv1d 路径引入 nn.Linear）。核心目标是在推理算量红线（<= 1.10x 基线，<= 132 MFLOPs）内最大化归因增益，并在同增益下优先压低推理 FLOPs。",
  "scope": {
    "model_family": "conv1d_transformer_4_10L",
    "forbidden_ops": [
      "nn.Linear"
    ],
    "baseline_flops_m": 120.0,
    "target_flops_budget_m": 132.0,
    "max_flops_ratio": 1.1,
    "param_bounds": {
      "num_layers": {
        "type": "int",
        "min": 4,
        "max": 10
      },
      "d_model": {
        "type": "int",
        "enum": [
          128,
          192,
          256,
          320
        ]
      },
      "kernel_size": {
        "type": "int",
        "enum": [
          3,
          5,
          7,
          9
        ]
      },
      "dilation": {
        "type": "int",
        "enum": [
          1,
          2,
          4
        ]
      },
      "ffn_ratio": {
        "type": "float",
        "min": 1.25,
        "max": 4.0
      },
      "conv_type": {
        "type": "str",
        "enum": [
          "standard",
          "depthwise_separable"
        ]
      }
    }
  },
  "patterns": [
    {
      "pattern_id": "P-DWCONV",
      "title": "深度可分离卷积替换标准 Conv1d + 适度扩大卷积核",
      "suggested_changes": {
        "conv_type": "depthwise_separable",
        "kernel_size": 7
      },
      "effect": {
        "expected_gain_pp_range": [
          8.0,
          18.0
        ],
        "expected_flops_ratio_range": [
          0.78,
          0.9
        ],
        "direction": "gain_up_compute_down",
        "notes": "跨窗口联合特征捕获增强，同时显著压低卷积分支 FLOPs。"
      },
      "stats": {
        "observations": 1,
        "wins": 1,
        "mean_gain_pp": 14.0,
        "mean_flops_ratio": 0.84,
        "mean_gpu_seconds": 56.0
      },
      "confidence": "medium",
      "evidence_refs": [
        "seed-baseline"
      ],
      "change_signature": "conv_type=\"depthwise_separable\";kernel_size=7",
      "target_fields": [
        "conv_type",
        "kernel_size"
      ]
    },
    {
      "pattern_id": "P-DILATION",
      "title": "引入 dilation=2 扩大时序感受野而不增加参数与 FLOPs",
      "suggested_changes": {
        "dilation": 2
      },
      "effect": {
        "expected_gain_pp_range": [
          4.0,
          10.0
        ],
        "expected_flops_ratio_range": [
          0.98,
          1.02
        ],
        "direction": "gain_up_compute_neutral",
        "notes": "改善长窗口 SINR/BLER 与调度滞后的关联归因，推理 FLOPs 基本不变。"
      },
      "stats": {
        "observations": 1,
        "wins": 1,
        "mean_gain_pp": 6.0,
        "mean_flops_ratio": 1.0,
        "mean_gpu_seconds": 60.0
      },
      "confidence": "medium",
      "evidence_refs": [
        "seed-baseline"
      ],
      "change_signature": "dilation=2",
      "target_fields": [
        "dilation"
      ]
    },
    {
      "pattern_id": "P-PRUNE-FFN",
      "title": "同增益下收缩冗余 FFN 倍率以压低推理算量",
      "suggested_changes": {
        "ffn_ratio": 1.75
      },
      "effect": {
        "expected_gain_pp_range": [
          0.0,
          2.0
        ],
        "expected_flops_ratio_range": [
          0.85,
          0.94
        ],
        "direction": "compute_down_tie",
        "notes": "维持同等归因正确率并降低推理 FLOPs，触发同增益算量优先 keep。"
      },
      "stats": {
        "observations": 1,
        "wins": 1,
        "mean_gain_pp": 0.0,
        "mean_flops_ratio": 0.91,
        "mean_gpu_seconds": 55.0
      },
      "confidence": "medium",
      "evidence_refs": [
        "seed-baseline"
      ],
      "change_signature": "ffn_ratio=1.75",
      "target_fields": [
        "ffn_ratio"
      ]
    }
  ],
  "anti_patterns": [
    {
      "pattern_id": "AP-OVERDEEP-WIDE",
      "title": "同时堆叠至 9–10 层并放大 d_model / ffn_ratio",
      "avoid_changes": {
        "num_layers": 10,
        "d_model": 256,
        "ffn_ratio": 3.5
      },
      "failure_type": "compute_budget_exceeded",
      "observed_flops_ratio": 1.68,
      "observed_gain_pp": -4.2,
      "observed_failure": "推理算量激增超过 1.6x 基线触发算量红线，且小样本下容易过拟合退化。",
      "occurrences": 1,
      "evidence_refs": [
        "seed-baseline"
      ],
      "change_signature": "d_model=256;ffn_ratio=3.5;num_layers=10",
      "target_fields": [
        "d_model",
        "ffn_ratio",
        "num_layers"
      ]
    },
    {
      "pattern_id": "AP-NARROW-KERNEL",
      "title": "过小卷积核（kernel_size <= 3）且无空洞",
      "avoid_changes": {
        "kernel_size": 3,
        "dilation": 1
      },
      "failure_type": "accuracy_regression",
      "observed_flops_ratio": 0.92,
      "observed_gain_pp": -4.17,
      "observed_failure": "感受野不足以覆盖重传与调度窗口错位，归因正确率明显下降。",
      "occurrences": 1,
      "evidence_refs": [
        "seed-baseline"
      ],
      "change_signature": "dilation=1;kernel_size=3",
      "target_fields": [
        "dilation",
        "kernel_size"
      ]
    }
  ],
  "text": "4–10 层 Conv1d Transformer 增益与算量权衡结构经验。在固定训练配方与样本预算下，优化 4–10 层 Conv1d Transformer 结构（禁止在 Conv1d 路径引入 nn.Linear）。核心目标是在推理算量红线（<= 1.10x 基线，<= 132 MFLOPs）内最大化归因增益，并在同增益下优先压低推理 FLOPs。 推荐结构模式：深度可分离卷积替换标准 Conv1d + 适度扩大卷积核; 引入 dilation=2 扩大时序感受野而不增加参数与 FLOPs; 同增益下收缩冗余 FFN 倍率以压低推理算量。 已知反例：同时堆叠至 9–10 层并放大 d_model / ffn_ratio; 过小卷积核（kernel_size <= 3）且无空洞。",
  "reviewed_by": "seed",
  "published_at": 0,
  "content_sha256": "9cff3ac08f4481658e5cc24cb1aa7845901c5a2e1bf8643acc4eb40df3952474"
}
```
<!-- kb:record:end -->
