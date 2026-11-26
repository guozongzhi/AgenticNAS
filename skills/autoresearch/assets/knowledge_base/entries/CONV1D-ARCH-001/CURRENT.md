# CONV1D-ARCH-001 · 4–10 层因果 Conv1d Transformer 结构增益与算量优化经验

| 字段 | 值 |
| --- | --- |
| 经验条目编号 | `CONV1D-ARCH-001` |
| 修订版本 | `v1`（父版本：`-`） |
| 研究轨道 | `architecture` |
| 发布状态 | `published` |
| 适用模型族 | `conv1d_transformer` |
| 审核人 | `seed-library` |
| 内容指纹 | `8921bc939f2ac26f...` |

## 摘要

面向无 nn.Linear 的 4–10 层因果 Conv1d Transformer。固定训练配方，围绕深度、注意力头数、FFN 扩展比、因果卷积核尺寸与激活函数做增益-算量双目标寻优。

## 适用边界与算量红线

- **目标算量上限**：`-` / 倍率 `<= 1.1x`
- **禁用算子**：`nn.Linear`

### 参数合法域（`param_bounds`）

| 字段 | 类型 | 范围 / 枚举 |
| --- | --- | --- |
| `depth` | `int` | min=`4`, max=`10` |
| `attention.num_heads` | `int` | enum: `[2, 4, 8]` |
| `ffn.ratio` | `int` | enum: `[2, 3, 4]` |
| `ffn.kernel_size` | `int` | enum: `[1, 3, 5]` |
| `ffn.activation` | `str` | enum: `['gelu', 'silu']` |

## 推荐有效模式（Patterns）

| ID | 说明 | 声明式变更 | 方向 | 均值增益(%) | 均值算量比 | 观测/胜出 | 置信度 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `P-CONV1D-K3-SILU` | FFN 采用局部因果卷积核 3 配合 SiLU 激活 | `ffn.activation="silu";ffn.kernel_size=3` | `gain_up_compute_neutral` | +2.40% | 1.012x | 2/2 | `medium` |
| `P-CONV1D-SHALLOW6-R4` | 在串行延迟受限时保持 6 层中等深度并将 FFN 扩展比提至 4 | `depth=6;ffn.ratio=4` | `gain_up_compute_down` | +1.80% | 0.940x | 1/1 | `medium` |

## 已知反例与失效边界（Anti-Patterns）

| ID | 反例说明 | 避坑变更 | 失败类型 | 实测算量比 | 次数 |
| --- | --- | --- | --- | --- | --- |
| `AP-CONV1D-D10-K5-R4` | 同时推满 10 层深度、卷积核 5 与 FFN 扩展比 4 | `depth=10;ffn.kernel_size=5;ffn.ratio=4` | `compute_budget_exceeded` | 1.680x | 1 |
| `AP-CONV1D-D4-K1` | 深度压至 4 层下界且退化为 kernel_size=1 纯逐点卷积 | `depth=4;ffn.kernel_size=1` | `accuracy_regression` | 0.620x | 1 |

---

<!-- 机器精确解析块：请通过 autoresearch.py configure / knowledge-base distill / knowledge-base publish / knowledge-base prune 维护，勿手改导致 SHA-256 校验失败 -->
<!-- knowledge_base:record:start -->
```json
{
  "schema_version": 2,
  "entry_id": "CONV1D-ARCH-001",
  "revision": "v1",
  "parent_revision": null,
  "track": "architecture",
  "status": "published",
  "tags": [
    "conv1d_transformer",
    "architecture",
    "seed-library"
  ],
  "title": "4–10 层因果 Conv1d Transformer 结构增益与算量优化经验",
  "summary": "面向无 nn.Linear 的 4–10 层因果 Conv1d Transformer。固定训练配方，围绕深度、注意力头数、FFN 扩展比、因果卷积核尺寸与激活函数做增益-算量双目标寻优。",
  "scope": {
    "model_family": "conv1d_transformer",
    "forbidden_ops": [
      "nn.Linear"
    ],
    "max_compute_value": null,
    "max_compute_ratio": 1.1,
    "param_bounds": {
      "depth": {
        "type": "int",
        "min": 4,
        "max": 10
      },
      "attention.num_heads": {
        "type": "int",
        "enum": [
          2,
          4,
          8
        ]
      },
      "ffn.ratio": {
        "type": "int",
        "enum": [
          2,
          3,
          4
        ]
      },
      "ffn.kernel_size": {
        "type": "int",
        "enum": [
          1,
          3,
          5
        ]
      },
      "ffn.activation": {
        "type": "str",
        "enum": [
          "gelu",
          "silu"
        ]
      }
    }
  },
  "patterns": [
    {
      "pattern_id": "P-CONV1D-K3-SILU",
      "title": "FFN 采用局部因果卷积核 3 配合 SiLU 激活",
      "suggested_changes": {
        "ffn.kernel_size": 3,
        "ffn.activation": "silu"
      },
      "effect": {
        "direction": "gain_up_compute_neutral",
        "notes": "增强局部短程时序归纳偏置，参数量与 MACs 增幅约 1%"
      },
      "stats": {
        "observations": 2,
        "wins": 2,
        "mean_gain_pct": 2.4,
        "mean_compute_ratio": 1.012,
        "mean_cost": 120.0
      },
      "confidence": "medium",
      "evidence_refs": [
        "seed:conv1d-prior"
      ],
      "change_signature": "ffn.activation=\"silu\";ffn.kernel_size=3",
      "target_fields": [
        "ffn.activation",
        "ffn.kernel_size"
      ]
    },
    {
      "pattern_id": "P-CONV1D-SHALLOW6-R4",
      "title": "在串行延迟受限时保持 6 层中等深度并将 FFN 扩展比提至 4",
      "suggested_changes": {
        "depth": 6,
        "ffn.ratio": 4
      },
      "effect": {
        "direction": "gain_up_compute_down",
        "notes": "相比盲目堆叠 9~10 层减少自回归串行步数，保持非线性通道容量"
      },
      "stats": {
        "observations": 1,
        "wins": 1,
        "mean_gain_pct": 1.8,
        "mean_compute_ratio": 0.94,
        "mean_cost": 110.0
      },
      "confidence": "medium",
      "evidence_refs": [
        "seed:conv1d-prior"
      ],
      "change_signature": "depth=6;ffn.ratio=4",
      "target_fields": [
        "depth",
        "ffn.ratio"
      ]
    }
  ],
  "anti_patterns": [
    {
      "pattern_id": "AP-CONV1D-D10-K5-R4",
      "title": "同时推满 10 层深度、卷积核 5 与 FFN 扩展比 4",
      "avoid_changes": {
        "depth": 10,
        "ffn.kernel_size": 5,
        "ffn.ratio": 4
      },
      "failure_type": "compute_budget_exceeded",
      "observed_compute_ratio": 1.68,
      "observed_gain_pct": 3.1,
      "observed_failure": "参数与因果卷积算量膨胀至 1.68x，远超 1.10x 预算红线",
      "occurrences": 1,
      "evidence_refs": [
        "seed:conv1d-prior"
      ],
      "change_signature": "depth=10;ffn.kernel_size=5;ffn.ratio=4",
      "target_fields": [
        "depth",
        "ffn.kernel_size",
        "ffn.ratio"
      ]
    },
    {
      "pattern_id": "AP-CONV1D-D4-K1",
      "title": "深度压至 4 层下界且退化为 kernel_size=1 纯逐点卷积",
      "avoid_changes": {
        "depth": 4,
        "ffn.kernel_size": 1
      },
      "failure_type": "accuracy_regression",
      "observed_compute_ratio": 0.62,
      "observed_gain_pct": -4.5,
      "observed_failure": "丧失局部卷积感受野且层数过浅，序列建模质量明显退化",
      "occurrences": 1,
      "evidence_refs": [
        "seed:conv1d-prior"
      ],
      "change_signature": "depth=4;ffn.kernel_size=1",
      "target_fields": [
        "depth",
        "ffn.kernel_size"
      ]
    }
  ],
  "reviewed_by": "seed-library",
  "published_at": 0,
  "content_sha256": "8921bc939f2ac26f32563a3500557b7ad2a5a784fefab4999ed9c76d74b6b403"
}
```
<!-- knowledge_base:record:end -->
