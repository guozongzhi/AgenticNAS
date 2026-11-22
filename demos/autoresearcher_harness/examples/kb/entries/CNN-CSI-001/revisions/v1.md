# CNN-CSI-001 · 无线 CSI 反馈 CNN 编解码结构增益与 MACs 算量经验

| 字段 | 值 |
| --- | --- |
| 经验编号 | `CNN-CSI-001` |
| 修订版本 | `v1`（父版本：`-`） |
| 轨道 | `architecture` |
| 状态 | `published` |
| 允许用途 | `training`, `evaluation` |
| 标签 | `cnn`, `csi-feedback`, `regression`, `nmse`, `macs` |
| 审核人 | `seed` |
| 内容指纹 | `6f8c35dc28144547...` |

## 摘要

面向无线信道估计/CSI 压缩反馈的轻量化 CNN 编解码器。固定训练配方，优化嵌套编码器/解码器结构，在推理算量 <= 55 MMACs（<= 1.10x 基线）与延迟 <= 2.5ms 约束下最小化 NMSE(dB)。

## 适用范围与算量约束

- **模型族**：`cnn_csi_feedback`
- **基线推理算量**：`50.0` MFLOPs
- **目标算量红线**：`<= 55.0` MFLOPs / `<= 1.1x`
- **禁用算子**：-

### 参数合法域（`param_bounds`）

| 字段 | 类型 | 范围 / 枚举 |
| --- | --- | --- |
| `encoder.num_blocks` | `int` | min=`2`, max=`8` |
| `encoder.channels` | `int` | enum: `[32, 48, 64, 96, 128]` |
| `encoder.kernel_size` | `int` | enum: `[3, 5, 7]` |
| `encoder.use_se` | `bool` | min=`-`, max=`-` |
| `decoder.refine_blocks` | `int` | min=`1`, max=`4` |
| `decoder.channels` | `int` | enum: `[32, 48, 64, 96]` |

## 推荐结构模式（Patterns）

| ID | 模式说明 | 声明式变更 | 方向 | 均值增益(pp) | 均值算量比 | 观测/胜出 | 置信度 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `P-CSI-SE-K5` | 编码器引入轻量化 SE 通道注意力并增大卷积核至 5 | `encoder.kernel_size=5;encoder.use_se=true` | `gain_up_compute_neutral` | +10.30 | 1.02x | 1/1 | `medium` |

## 已知反例与失效边界（Anti-Patterns）

| ID | 反例说明 | 避坑变更 | 失败类型 | 实测算量比 | 实测增益(pp) | 次数 |
| --- | --- | --- | --- | --- | --- | --- |
| `AP-CSI-WIDE-CH` | 编码器通道翻倍至 128 | `encoder.channels=128` | `compute_budget_exceeded` | 1.84x | +15.00 | 1 |

---

<!-- 以下为机器精确解析用结构化块，请通过 kb CLI 或保持合法 JSON 维护 -->
<!-- kb:record:start -->
```json
{
  "schema_version": 2,
  "kb_id": "CNN-CSI-001",
  "revision": "v1",
  "parent_revision": null,
  "track": "architecture",
  "status": "published",
  "approved_uses": [
    "training",
    "evaluation"
  ],
  "tags": [
    "cnn",
    "csi-feedback",
    "regression",
    "nmse",
    "macs"
  ],
  "title": "无线 CSI 反馈 CNN 编解码结构增益与 MACs 算量经验",
  "summary": "面向无线信道估计/CSI 压缩反馈的轻量化 CNN 编解码器。固定训练配方，优化嵌套编码器/解码器结构，在推理算量 <= 55 MMACs（<= 1.10x 基线）与延迟 <= 2.5ms 约束下最小化 NMSE(dB)。",
  "scope": {
    "model_family": "cnn_csi_feedback",
    "forbidden_ops": [],
    "baseline_flops_m": 50.0,
    "target_flops_budget_m": 55.0,
    "max_flops_ratio": 1.1,
    "param_bounds": {
      "encoder.num_blocks": {
        "type": "int",
        "min": 2,
        "max": 8
      },
      "encoder.channels": {
        "type": "int",
        "enum": [
          32,
          48,
          64,
          96,
          128
        ]
      },
      "encoder.kernel_size": {
        "type": "int",
        "enum": [
          3,
          5,
          7
        ]
      },
      "encoder.use_se": {
        "type": "bool"
      },
      "decoder.refine_blocks": {
        "type": "int",
        "min": 1,
        "max": 4
      },
      "decoder.channels": {
        "type": "int",
        "enum": [
          32,
          48,
          64,
          96
        ]
      }
    }
  },
  "patterns": [
    {
      "pattern_id": "P-CSI-SE-K5",
      "title": "编码器引入轻量化 SE 通道注意力并增大卷积核至 5",
      "suggested_changes": {
        "encoder.use_se": true,
        "encoder.kernel_size": 5
      },
      "effect": {
        "expected_gain_pp_range": [
          6.0,
          14.0
        ],
        "expected_flops_ratio_range": [
          1.0,
          1.06
        ],
        "direction": "gain_up_compute_neutral",
        "notes": "增强多径空间相关性建模，MACs 增幅极小。"
      },
      "stats": {
        "observations": 1,
        "wins": 1,
        "mean_gain_pp": 10.3,
        "mean_flops_ratio": 1.024,
        "mean_gpu_seconds": 0.45
      },
      "confidence": "medium",
      "evidence_refs": [
        "seed-csi"
      ],
      "change_signature": "encoder.kernel_size=5;encoder.use_se=true",
      "target_fields": [
        "encoder.kernel_size",
        "encoder.use_se"
      ]
    }
  ],
  "anti_patterns": [
    {
      "pattern_id": "AP-CSI-WIDE-CH",
      "title": "编码器通道翻倍至 128",
      "avoid_changes": {
        "encoder.channels": 128
      },
      "failure_type": "compute_budget_exceeded",
      "observed_flops_ratio": 1.84,
      "observed_gain_pp": 15.0,
      "observed_failure": "MACs 激增至 1.84x，突破终端实时反馈算量红线。",
      "occurrences": 1,
      "evidence_refs": [
        "seed-csi"
      ],
      "change_signature": "encoder.channels=128",
      "target_fields": [
        "encoder.channels"
      ]
    }
  ],
  "text": "无线 CSI 反馈 CNN 编解码结构增益与 MACs 算量经验。面向无线信道估计/CSI 压缩反馈的轻量化 CNN 编解码器。固定训练配方，优化嵌套编码器/解码器结构，在推理算量 <= 55 MMACs（<= 1.10x 基线）与延迟 <= 2.5ms 约束下最小化 NMSE(dB)。 推荐结构模式：编码器引入轻量化 SE 通道注意力并增大卷积核至 5。 已知反例：编码器通道翻倍至 128。",
  "reviewed_by": "seed",
  "published_at": 0,
  "content_sha256": "6f8c35dc281445473282e78c4d94e9c4ae6cde2d283d190a6bf2ea4484566f8e"
}
```
<!-- kb:record:end -->
