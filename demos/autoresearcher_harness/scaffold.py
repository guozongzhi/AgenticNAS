from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .knowledge_base import KnowledgeBase
from .store import write_json, write_text


def init_workspace(
    workspace: Path,
    model_family: str,
    kb_id: str,
    primary_metric: str,
    direction: str = 'maximize',
    min_gain: float = 0.5,
    holdout_target: float | None = None,
    compute_metric: str = 'flops_m',
    compute_unit: str = 'MFLOPs',
    max_compute_value: float | None = None,
    max_compute_ratio: float = 1.10,
    cost_metric: str = 'gpu_seconds',
    cost_unit: str = 's',
    max_cost: float = 3600.0,
    max_trials: int = 10,
    track: str = 'architecture',
    stages: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a ready-to-run BYO-MCP AutoResearch workspace for any model engineer."""
    root = workspace.resolve()
    root.mkdir(parents=True, exist_ok=True)
    kb_root = root / 'kb'
    kb = KnowledgeBase(kb_root)

    default_base_config: dict[str, Any] = {
        'backbone': {
            'depth': 6,
            'width': 192,
            'kernel_size': 5,
            'block_type': 'standard',
        },
        'head': {
            'hidden_dim': 128,
        },
    }
    default_mutable = [
        'backbone.depth',
        'backbone.width',
        'backbone.kernel_size',
        'backbone.block_type',
        'head.hidden_dim',
    ]
    default_param_bounds: dict[str, Any] = {
        'backbone.depth': {'type': 'int', 'min': 2, 'max': 12},
        'backbone.width': {'type': 'int', 'enum': [96, 128, 192, 256, 320]},
        'backbone.kernel_size': {'type': 'int', 'enum': [3, 5, 7, 9]},
        'backbone.block_type': {'type': 'str', 'enum': ['standard', 'depthwise_separable', 'inverted_bottleneck']},
        'head.hidden_dim': {'type': 'int', 'enum': [64, 128, 192, 256]},
    }
    default_recipe: dict[str, Any] = {
        'epochs': 10,
        'lr': 0.001,
        'weight_decay': 0.01,
        'seed': 42,
    }
    if track != 'architecture':
        default_mutable = ['lr', 'weight_decay', 'epochs']
        default_param_bounds = {
            'lr': {'type': 'float', 'min': 1e-5, 'max': 1e-2},
            'weight_decay': {'type': 'float', 'min': 0.0, 'max': 0.1},
            'epochs': {'type': 'int', 'min': 1, 'max': 30},
        }

    kb.save({
        'schema_version': 2,
        'kb_id': kb_id,
        'revision': 'v1',
        'parent_revision': None,
        'track': track,
        'status': 'published',
        'approved_uses': ['training', 'evaluation'],
        'tags': [model_family, track, 'gain-compute'],
        'title': f'{model_family} 结构优化增益与算量经验',
        'summary': (
            f'面向 {model_family} 的自主结构优化经验库。'
            f'核心指标：{primary_metric}（{direction}）；推理算量：{compute_metric}（<= {max_compute_ratio}x 基线）；'
            f'训练/搜索成本：{cost_metric}（上限 {max_cost}{cost_unit}）。'
        ),
        'reviewed_by': 'engineer-init',
        'published_at': 0,
        'scope': {
            'model_family': model_family,
            'forbidden_ops': [],
            'baseline_flops_m': None,
            'target_flops_budget_m': max_compute_value,
            'max_flops_ratio': max_compute_ratio,
            'param_bounds': default_param_bounds,
        },
        'patterns': [],
        'anti_patterns': [],
        'evidence': [],
    }, allow_overwrite_revision=True)

    stage_list = stages or ['training', 'evaluation']
    campaign_plan: dict[str, Any] = {
        'schema_version': 1,
        'execution_mode': 'external_mcp',
        'track': track,
        'model_family': model_family,
        'kb_ref': kb_id,
        'program_ref': 'program.md',
        'mcp_tools_ref': 'mcp_tools.md',
        'stages': stage_list,
        'knowledge': kb.freeze_snapshot(kb_id),
        'base_hypothesis': f'{model_family} 基线配置：建立 {primary_metric} 与 {compute_metric} 参照基准。',
        'baseline_model_ref': f'uri://models/{model_family}-baseline',
        'dataset_ref': f'uri://datasets/{model_family}-train',
        'dev_evaluator_ref': f'uri://evaluators/{model_family}-dev',
        'holdout_evaluator_ref': f'uri://evaluators/{model_family}-holdout',
        'base_config': default_base_config if track == 'architecture' else default_recipe,
        'base_architecture': default_base_config,
        'base_training_recipe': default_recipe,
        'mutable_fields': default_mutable,
        'budget': {
            'max_trials': max_trials,
            'per_trial_wall_seconds': 1800,
            'total_wall_seconds': 28800,
            'cost_metric': {
                'name': cost_metric,
                'unit': cost_unit,
                'max_total': max_cost,
            },
        },
        'acceptance': {
            'primary_metric': {
                'name': primary_metric,
                'direction': direction,
                'min_gain': min_gain,
                'tie_tolerance': 0.0,
                'holdout_target': holdout_target,
            },
            'compute_metric': {
                'name': compute_metric,
                'unit': compute_unit,
                'direction': 'minimize',
                'max_value': max_compute_value,
                'max_ratio': max_compute_ratio,
            },
            'guardrails': {
                'max_metrics': {},
                'min_metrics': {},
            },
        },
    }
    campaign_path = root / 'campaign.json'
    write_json(campaign_path, campaign_plan)

    mcp_doc = '\n'.join([
        f'# {model_family} · 已有 MCP 工具映射说明（给 Agent 阅读）',
        '',
        '本工作区采用 **BYO-MCP（自带 MCP）** 模式：Claude Code / Codex / OpenCode 直接调用你已经配置好的 MCP 工具，',
        '并将真实测得的指标、算量、成本与产物 URI 回填给 Harness 做棘轮裁决与经验沉淀。',
        '',
        '请将下方尖括号替换为你环境里实际的 MCP 工具名与参数说明：',
        '',
        '| 阶段 | 你的 MCP 工具名 | 输入映射 | 需提取的回填字段 |',
        '| --- | --- | --- | --- |',
        *[
            f'| `{stage}` | `<your_{stage}_mcp_tool>` | 传入 `candidate_config`（及冻结配方/数据） | '
            + (f'`{primary_metric}`, `{compute_metric}`, 护栏指标, `cost.{cost_metric}`' if stage == 'evaluation' else f'产物 URI（如 `model_ref`）, `cost.{cost_metric}`, 远端 `job_id`')
            + ' |'
            for stage in stage_list
        ],
        '',
        '## 失败与超时约定',
        '',
        '- 若远端训练 OOM、发散或超时，务必先通过 MCP 取消远端任务并回收日志，然后执行：',
        f'  `campaign record latest --status crash --cost \'{{"{cost_metric}": <已消耗>}}\' --note "<失败原因>"`',
        '- 严禁跳过 `campaign propose` 私自跑训练，也严禁在开发迭代期调用 `holdout_evaluator_ref`。',
        '',
    ])
    mcp_path = root / 'mcp_tools.md'
    write_text(mcp_path, mcp_doc)

    out_dir = root / 'outputs'
    cli_prefix = f'PYTHONPATH=demos python3 -m autoresearcher_harness --output "{out_dir}" --kb-dir "{kb_root}"'
    program_doc = '\n'.join([
        f'# Research Program · {model_family}（{track} 轨道）',
        '',
        '直接将本文件交给 **Claude Code / Codex / OpenCode**，即可自动按以下协议使用你已搭好的 MCP 工具跑完多轮研究闭环。',
        '',
        '## 1. 目标与红线',
        '',
        f'- **主指标（增益）**：`{primary_metric}`（方向：`{direction}`，单轮有效增益门槛 `>= {min_gain}`，Holdout 目标：`{holdout_target}`）。',
        f'- **模型算量红线**：`{compute_metric}`（单位 `{compute_unit}`，上限：`{max_compute_value}` / 倍率 `<= {max_compute_ratio}x` 基线）；同增益下算量更低优先 `keep`。',
        f'- **搜索/训练成本上限**：`{cost_metric} <= {max_cost} {cost_unit}`，最大尝试轮数 `{max_trials}`。',
        f'- **MCP 工具清单**：先阅读 [mcp_tools.md](mcp_tools.md) 了解当前环境可用的训练/仿真/评测 MCP 工具。',
        '',
        '## 2. 执行循环',
        '',
        '### Step 1：检索结构经验库（先验与反例）',
        '```bash',
        f'{cli_prefix} kb show {kb_id}',
        f'{cli_prefix} kb search --model-family {model_family} --track {track}',
        '```',
        '',
        '### Step 2：创建 Campaign 并建立基线（Baseline-first）',
        '```bash',
        f'{cli_prefix} campaign create --plan "{campaign_path}" --kb {kb_id}',
        f'{cli_prefix} campaign baseline latest',
        '# 用你已搭好的 MCP 对 trial-000 的 base_config 执行基线训练与 Dev 评测，然后回填：',
        f'{cli_prefix} campaign record latest --status succeeded \\',
        f'  --metrics \'{{"{primary_metric}": <base_val>, "{compute_metric}": <base_compute>}}\' \\',
        f'  --cost \'{{"{cost_metric}": <cost_val>}}\' \\',
        '  --artifacts \'{"model_ref": "<base_model_uri>"}\'',
        '```',
        '',
        '### Step 3：多轮棘轮循环（Context → Propose → 调你的 MCP → Record）',
        '```bash',
        f'{cli_prefix} campaign context latest',
        f'{cli_prefix} campaign propose latest --hypothesis "<单一清晰假设>" --changes \'{{"<mutable_field>": <value>}}\'',
        '# 读取返回的 candidate_config，调用你已搭好的 MCP 工具跑完本轮试验并回填实测指标与算量：',
        f'{cli_prefix} campaign record latest --status succeeded \\',
        f'  --metrics \'{{"{primary_metric}": <val>, "{compute_metric}": <compute>}}\' \\',
        f'  --cost \'{{"{cost_metric}": <cost>}}\' \\',
        '  --artifacts \'{"model_ref": "<cand_model_uri>"}\'',
        '```',
        '',
        '### Step 4：锁定最终 Incumbent 跑唯一一次独立 Holdout 盲评',
        '```bash',
        '# 对 context.incumbent.model_ref 调用你的 Holdout 评测 MCP（严禁重新训练），再回填验收：',
        f'{cli_prefix} campaign finalize latest \\',
        f'  --metrics \'{{"{primary_metric}": <holdout_val>, "{compute_metric}": <compute>}}\' \\',
        f'  --cost \'{{"{cost_metric}": <eval_cost>}}\' \\',
        '  --artifacts \'{"model_ref": "<incumbent_model_uri>"}\'',
        '```',
        '',
        '### Step 5：沉淀结构经验草案并审核发布',
        '```bash',
        f'{cli_prefix} kb distill latest',
        f'{cli_prefix} kb drafts {kb_id}',
        f'# 人工审核通过后执行：\n# {cli_prefix} kb publish {kb_id} --reviewer <your_name>',
        '```',
        '',
    ])
    program_path = root / 'program.md'
    write_text(program_path, program_doc)

    return {
        'workspace': str(root),
        'campaign_plan': str(campaign_path),
        'program_md': str(program_path),
        'mcp_tools_md': str(mcp_path),
        'kb_dir': str(kb_root),
        'kb_index': str(kb.index_md_path),
        'kb_id': kb_id,
    }
