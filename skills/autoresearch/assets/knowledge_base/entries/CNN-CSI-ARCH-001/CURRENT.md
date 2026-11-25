# CNN-CSI-ARCH-001 · 无线信道 CSI 压缩反馈轻量化 CNN 编解码结构经验

| 字段 | 值 |
| --- | --- |
| 经验条目编号 | `CNN-CSI-ARCH-001` |
| 修订版本 | `v1`（父版本：`-`） |
| 研究轨道 | `architecture` |
| 发布状态 | `published` |
| 适用模型族 | `cnn_csi_feedback` |
| 审核人 | `seed-library` |
| 内容指纹 | `1e40d4cb4ddebd05...` |

## 摘要

面向终端侧无线 CSI 压缩与基站侧重构的非对称编解码结构优化。固定训练配方，在严格受限的上行编码 MACs 与时延护栏下最小化重构误差 NMSE(dB)。

## 适用边界与算量红线

- **目标算量上限**：`-` / 倍率 `<= 1.1x`
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

## 推荐有效模式（Patterns）

| ID | 说明 | 声明式变更 | 方向 | 均值增益(%) | 均值算量比 | 观测/胜出 | 置信度 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `P-CSI-SE-K5` | 编码器开启轻量化 SE 通道注意力并将卷积核扩至 5 | `encoder.kernel_size=5;encoder.use_se=true` | `gain_up_compute_neutral` | +5.20% | 1.024x | 1/1 | `medium` |
| `P-CSI-DEC-REF3-CH48` | 解码器精炼块增至 3 层并将解码通道收窄至 48 | `decoder.channels=48;decoder.refine_blocks=3` | `gain_up_compute_down` | +3.10% | 0.930x | 1/1 | `medium` |

## 已知反例与失效边界（Anti-Patterns）

| ID | 反例说明 | 避坑变更 | 失败类型 | 实测算量比 | 次数 |
| --- | --- | --- | --- | --- | --- |
| `AP-CSI-WIDE-128` | 编码器通道直接翻倍至 128 | `encoder.channels=128` | `compute_budget_exceeded` | 1.840x | 1 |

---

<!-- 机器精确解析块：请通过 autoresearch.py configure / knowledge-base distill / knowledge-base publish 维护，勿手改导致 SHA-256 校验失败 -->
<!-- knowledge_base:record:start -->
```json
{
  "schema_version": 2,
  "entry_id": "CNN-CSI-ARCH-001",
  "revision": "v1",
  "parent_revision": null,
  "track": "architecture",
  "status": "published",
  "tags": [
    "cnn_csi_feedback",
    "architecture",
    "seed-library"
  ],
  "title": "无线信道 CSI 压缩反馈轻量化 CNN 编解码结构经验",
  "summary": "面向终端侧无线 CSI 压缩与基站侧重构的非对称编解码结构优化。固定训练配方，在严格受限的上行编码 MACs 与时延护栏下最小化重构误差 NMSE(dB)。",
  "scope": {
    "model_family": "cnn_csi_feedback",
    "forbidden_ops": [],
    "max_compute_value": null,
    "max_compute_ratio": 1.1,
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
      "title": "编码器开启轻量化 SE 通道注意力并将卷积核扩至 5",
      "suggested_changes": {
        "encoder.use_se": true,
        "encoder.kernel_size": 5
      },
      "effect": {
        "direction": "gain_up_compute_neutral",
        "notes": "增强多径空频相关性捕获，MACs 增幅约 2.4%"
      },
      "stats": {
        "observations": 1,
        "wins": 1,
        "mean_gain_pct": 5.2,
        "mean_compute_ratio": 1.024,
        "mean_cost": 0.45
      },
      "confidence": "medium",
      "evidence_refs": [
        "seed:csi-prior"
      ],
      "change_signature": "encoder.kernel_size=5;encoder.use_se=true",
      "target_fields": [
        "encoder.kernel_size",
        "encoder.use_se"
      ]
    },
    {
      "pattern_id": "P-CSI-DEC-REF3-CH48",
      "title": "解码器精炼块增至 3 层并将解码通道收窄至 48",
      "suggested_changes": {
        "decoder.refine_blocks": 3,
        "decoder.channels": 48
      },
      "effect": {
        "direction": "gain_up_compute_down",
        "notes": "以更窄的多步残差细化替代宽通道卷积，降低总 MACs 约 7% 同时改善 NMSE"
      },
      "stats": {
        "observations": 1,
        "wins": 1,
        "mean_gain_pct": 3.1,
        "mean_compute_ratio": 0.93,
        "mean_cost": 0.41
      },
      "confidence": "medium",
      "evidence_refs": [
        "seed:csi-prior"
      ],
      "change_signature": "decoder.channels=48;decoder.refine_blocks=3",
      "target_fields": [
        "decoder.channels",
        "decoder.refine_blocks"
      ]
    }
  ],
  "anti_patterns": [
    {
      "pattern_id": "AP-CSI-WIDE-128",
      "title": "编码器通道直接翻倍至 128",
      "avoid_changes": {
        "encoder.channels": 128
      },
      "failure_type": "compute_budget_exceeded",
      "observed_compute_ratio": 1.84,
      "observed_gain_pct": 8.0,
      "observed_failure": "终端上行编码 MACs 激增至 1.84x，突破实时预算红线",
      "occurrences": 1,
      "evidence_refs": [
        "seed:csi-prior"
      ],
      "change_signature": "encoder.channels=128",
      "target_fields": [
        "encoder.channels"
      ]
    }
  ],
  "reviewed_by": "seed-library",
  "published_at": 0,
  "content_sha256": "1e40d4cb4ddebd05543c541f196ee08b74737231e50597548d44a0d1a6e10110"
}
```
<!-- knowledge_base:record:end -->
