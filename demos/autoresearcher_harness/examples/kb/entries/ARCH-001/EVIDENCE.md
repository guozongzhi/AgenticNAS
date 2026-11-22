# ARCH-001 · 实证账本（Evidence Log）

| 证据 ID | 修订 | Campaign | Holdout 验收 | 增益(pp) | 推理算量比 | 搜索 GPU(s) | 单位算量增益 | 胜出变更 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `seed-baseline` | `v1` | `-` | `True` | +0.00 | 1.00x | 0.0 | - | `-` |

<!-- kb:evidence:start -->
```json
[
  {
    "evidence_id": "seed-baseline",
    "revision": "v1",
    "campaign_id": null,
    "track": "architecture",
    "holdout_accepted": true,
    "holdout_gain_correct": 0,
    "holdout_gain_pp": 0.0,
    "candidate_inference_flops_m": 120.0,
    "flops_ratio": 1.0,
    "total_gpu_seconds": 0.0,
    "gain_per_gpu_hour": null,
    "incumbent_changes": {},
    "summary": "6层 d_model=192 k=5 standard Conv1d 基线：基准 16/24，推理算量 120.0 MFLOPs。"
  }
]
```
<!-- kb:evidence:end -->
