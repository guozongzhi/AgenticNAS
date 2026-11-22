from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any

from .campaign import CAMPAIGN_TERMINAL, CampaignRunner
from .contracts import Proposal, TERMINAL
from .engine import Harness
from .knowledge_base import KnowledgeBase
from .scaffold import init_workspace
from .store import WorkerBusy


DEFAULT_ROOT = Path(__file__).resolve().parent / 'outputs'
DEFAULT_KB_ROOT = Path(__file__).resolve().parent / 'examples' / 'kb'
EXAMPLE = Path(__file__).resolve().parent / 'examples' / 'throughput.json'
CAMPAIGN_EXAMPLE = Path(__file__).resolve().parent / 'examples' / 'campaign_arch.json'


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _load_json_arg(raw_text: str | None, file_path: Path | None, default: Any = None) -> Any:
    if file_path is not None:
        return json.loads(file_path.read_text(encoding='utf-8'))
    if raw_text is not None:
        return json.loads(raw_text)
    return default


def drive(harness: Harness, run_id: str, once: bool, poll_seconds: float) -> int:
    previous = None
    while True:
        run = harness.step(run_id)
        summary = (run['status'], [(task['stage'], task['status']) for task in run['tasks']])
        if summary != previous:
            print(json.dumps({'run_id': run['run_id'], 'status': run['status'], 'tasks': summary[1]},
                             ensure_ascii=False), file=sys.stderr)
            previous = summary
        if run['status'] != 'running' or once:
            directory = harness.export(run_id)
            print_json({'run_id': run['run_id'], 'status': run['status'],
                        'error': run['error'], 'artifacts': str(directory), 'report': run['report']})
            return {'running': 0, 'succeeded': 0, 'cancelled': 0}.get(run['status'], 1)
        time.sleep(poll_seconds)


def drive_campaign(runner: CampaignRunner, campaign_id: str, once: bool, poll_seconds: float) -> int:
    previous = None
    while True:
        campaign = runner.step(campaign_id)
        summary = (
            campaign['status'],
            campaign['incumbent_trial_id'],
            [(item['trial_id'], item['decision'] or item['run_status']) for item in campaign['trials']],
        )
        if summary != previous:
            print(json.dumps({
                'campaign_id': campaign['campaign_id'],
                'status': campaign['status'],
                'incumbent': campaign['incumbent_trial_id'],
                'total_cost': campaign.get('total_cost', 0.0),
                'trials': summary[2],
            }, ensure_ascii=False), file=sys.stderr)
            previous = summary
        if campaign['status'] not in {'running', 'evaluating_holdout'} or once:
            directory = runner.export(campaign_id)
            print_json({
                'campaign_id': campaign['campaign_id'],
                'status': campaign['status'],
                'incumbent_trial_id': campaign['incumbent_trial_id'],
                'total_cost': campaign.get('total_cost', 0.0),
                'total_gpu_seconds': campaign.get('total_gpu_seconds', 0.0),
                'total_train_tflops': campaign.get('total_train_tflops', 0.0),
                'error': campaign['error'],
                'artifacts': str(directory),
                'results_tsv': str(directory / 'results.tsv'),
                'holdout_report': campaign['holdout_report'],
            })
            return {'running': 0, 'evaluating_holdout': 0, 'succeeded': 0, 'cancelled': 0}.get(campaign['status'], 1)
        time.sleep(poll_seconds)


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description='AutoResearcher Harness · 通用模型优化控制面（BYO-MCP + 纯 Markdown 结构经验库）')
    command.add_argument('--output', type=Path, default=DEFAULT_ROOT, help='SQLite 状态和运行产物目录')
    command.add_argument('--kb-dir', type=Path, default=DEFAULT_KB_ROOT, help='纯 Markdown 结构经验库目录')
    subcommands = command.add_subparsers(dest='command', required=True)

    init_cmd = subcommands.add_parser('init', help='为任意模型工程师 1 秒初始化专属 BYO-MCP AutoResearch 工作区')
    init_cmd.add_argument('--workspace', type=Path, required=True, help='输出工作区目录')
    init_cmd.add_argument('--model-family', required=True, help='模型族标识，如 cnn_csi_encoder / vit_edge')
    init_cmd.add_argument('--kb-id', required=True, help='结构经验库编号，如 CSI-ARCH-001')
    init_cmd.add_argument('--metric', required=True, help='主增益指标名，如 nmse_db / map50 / accuracy / val_bpb')
    init_cmd.add_argument('--direction', choices=('maximize', 'minimize'), default='maximize')
    init_cmd.add_argument('--min-gain', type=float, default=0.5, help='单轮有效增益门槛（方向归一化后，正数表示变好）')
    init_cmd.add_argument('--holdout-target', type=float, default=None, help='独立留出集验收目标值')
    init_cmd.add_argument('--compute', default='flops_m', help='推理/模型算量指标名，如 flops_m / macs_m / latency_ms')
    init_cmd.add_argument('--compute-unit', default='MFLOPs')
    init_cmd.add_argument('--max-compute', type=float, default=None, help='推理算量绝对上限')
    init_cmd.add_argument('--max-compute-ratio', type=float, default=1.10, help='相对基线的算量倍率上限')
    init_cmd.add_argument('--cost', default='gpu_seconds', help='训练/搜索成本指标名，如 gpu_seconds / gpu_hours')
    init_cmd.add_argument('--cost-unit', default='s')
    init_cmd.add_argument('--max-cost', type=float, default=3600.0, help='总搜索成本预算上限')
    init_cmd.add_argument('--max-trials', type=int, default=10)
    init_cmd.add_argument('--track', choices=('architecture', 'hpo', 'data_recipe'), default='architecture')
    init_cmd.add_argument('--stages', default='training,evaluation', help='逗号分隔的阶段列表，如 simulation,training,evaluation')

    create = subcommands.add_parser('create', help='从 JSON 运行单创建单次研究运行')
    create.add_argument('--plan', type=Path, default=EXAMPLE)
    demo = subcommands.add_parser('demo', help='创建并推进单次示例')
    demo.add_argument('--plan', type=Path, default=EXAMPLE)
    resume = subcommands.add_parser('resume', help='继续指定运行或 latest')
    resume.add_argument('run_id', nargs='?', default='latest')
    for worker in (demo, resume):
        worker.add_argument('--once', action='store_true', help='只推进一次，演示进程退出后的恢复')
        worker.add_argument('--poll-seconds', type=float, default=0.2)
    for name in ('status', 'stop', 'events', 'export'):
        action = subcommands.add_parser(name)
        action.add_argument('run_id', nargs='?', default='latest')

    kb = subcommands.add_parser('kb', help='纯 Markdown 结构经验库：不可变修订、多维检索、草案隔离与去重聚合')
    kb_sub = kb.add_subparsers(dest='kb_command', required=True)
    kb_list = kb_sub.add_parser('list', help='列出经验条目')
    kb_list.add_argument('--track', choices=('architecture', 'hpo', 'data_recipe'))
    kb_list.add_argument('--status', choices=('draft', 'published', 'deprecated'))
    kb_search = kb_sub.add_parser('search', help='按维度检索 Markdown 经验条目、结构模式与反例')
    kb_search.add_argument('--query', default='')
    kb_search.add_argument('--track', choices=('architecture', 'hpo', 'data_recipe'))
    kb_search.add_argument('--model-family', default=None, help='按模型族过滤，如 conv1d / cnn_csi')
    kb_search.add_argument('--status', choices=('draft', 'published', 'deprecated'))
    kb_search.add_argument('--field', default=None, help='按目标可变字段过滤，如 kernel_size / encoder.depth')
    kb_search.add_argument('--max-flops', type=float, default=None, help='按适用算量预算上限过滤')
    kb_search.add_argument('--max-flops-ratio', type=float, default=None, help='按实测模式平均算量倍率上限过滤')
    kb_search.add_argument('--min-gain-pp', type=float, default=None, help='按实测模式平均增益下限过滤')
    kb_search.add_argument('--direction', default=None,
                           choices=('gain_up_compute_down', 'gain_up_compute_neutral', 'gain_up_compute_up', 'compute_down_tie', 'other'))
    kb_search.add_argument('--failure-type', default=None,
                           choices=('compute_budget_exceeded', 'guardrail_violated', 'accuracy_regression', 'training_crash', 'other'))
    kb_show = kb_sub.add_parser('show', help='查看单条经验详情（支持按历史修订回查）')
    kb_show.add_argument('kb_id')
    kb_show.add_argument('--revision', default=None, help='指定历史修订，如 v1')
    kb_drafts = kb_sub.add_parser('drafts', help='列出待人工审核的蒸馏草案')
    kb_drafts.add_argument('kb_id', nargs='?', default=None)
    kb_distill = kb_sub.add_parser('distill', help='从已完成 Campaign 蒸馏生成隔离草案 .md（不改写已发布文档）')
    kb_distill.add_argument('campaign_id', nargs='?', default='latest')
    kb_distill.add_argument('--kb-id', default=None)
    kb_publish = kb_sub.add_parser('publish', help='人工复核后去重聚合发布为新不可变修订 .md 并追加 EVIDENCE.md')
    kb_publish.add_argument('kb_id')
    kb_publish.add_argument('--revision', default=None)
    kb_publish.add_argument('--reviewer', default='human')
    kb_sub.add_parser('reindex', help='从 entries/ 下的 Markdown 文档全量重建 INDEX.md')

    campaign = subcommands.add_parser('campaign', help='多轮棘轮研究循环（支持自带 MCP 与托管模拟两种模式）')
    cmp_sub = campaign.add_subparsers(dest='campaign_command', required=True)
    cmp_create = cmp_sub.add_parser('create', help='从计划 JSON 与结构经验库创建 Campaign')
    cmp_create.add_argument('--plan', type=Path, default=CAMPAIGN_EXAMPLE)
    cmp_create.add_argument('--kb', default=None, help='覆盖 plan.kb_ref，从经验库冻结指定已发布条目')
    cmp_create.add_argument('--kb-revision', default=None, help='锁定历史修订号，如 v1')
    cmp_demo = cmp_sub.add_parser('demo', help='创建并自动运行内置架构优化示例')
    cmp_demo.add_argument('--plan', type=Path, default=CAMPAIGN_EXAMPLE)
    cmp_demo.add_argument('--kb', default=None)
    cmp_demo.add_argument('--kb-revision', default=None)
    cmp_resume = cmp_sub.add_parser('resume', help='继续指定 Campaign 或 latest（managed 模式）')
    cmp_resume.add_argument('campaign_id', nargs='?', default='latest')
    for worker in (cmp_demo, cmp_resume):
        worker.add_argument('--once', action='store_true', help='只推进一次，演示跨进程断点恢复')
        worker.add_argument('--poll-seconds', type=float, default=0.05)

    cmp_baseline = cmp_sub.add_parser('baseline', help='（Agent 入口）启动 trial-000 基线；external_mcp 模式返回基线配置工单')
    cmp_baseline.add_argument('campaign_id', nargs='?', default='latest')
    cmp_baseline.add_argument('--poll-seconds', type=float, default=0.05)

    cmp_context = cmp_sub.add_parser('context', help='（Agent 入口）输出经验先验、参数合法域、算量红线、剩余预算与 results.tsv')
    cmp_context.add_argument('campaign_id', nargs='?', default='latest')

    cmp_propose = cmp_sub.add_parser('propose', help='（Agent 入口）提交声明式假设提案（白名单 + param_bounds 校验），返回完整 candidate_config')
    cmp_propose.add_argument('campaign_id', nargs='?', default='latest')
    cmp_propose.add_argument('--hypothesis', default=None)
    cmp_propose.add_argument('--changes', default=None, help='JSON 对象，支持顶层字段或嵌套 dot-path')
    cmp_propose.add_argument('--proposal-file', type=Path, default=None)
    cmp_propose.add_argument('--reuse-simulation', action='store_true')
    cmp_propose.add_argument('--run', action='store_true', help='（managed 模式）提交后立即推进至本轮裁决完成')
    cmp_propose.add_argument('--poll-seconds', type=float, default=0.05)

    cmp_record = cmp_sub.add_parser('record', help='（BYO-MCP 入口）回填已有 MCP 跑完后的指标、算量、成本与产物，自动棘轮裁决')
    cmp_record.add_argument('campaign_id', nargs='?', default='latest')
    cmp_record.add_argument('--trial', default=None, help='Trial ID，默认当前活跃 trial')
    cmp_record.add_argument('--status', choices=('succeeded', 'failed', 'timeout', 'crash', 'cancelled'), default='succeeded')
    cmp_record.add_argument('--metrics', default=None, help='实测指标 JSON（含主指标、算量及护栏指标）')
    cmp_record.add_argument('--metrics-file', type=Path, default=None)
    cmp_record.add_argument('--cost', default=None, help='本轮消耗成本 JSON，如 {"gpu_seconds": 120}')
    cmp_record.add_argument('--artifacts', default=None, help='产物 URI JSON，如 {"model_ref": "uri://..."}')
    cmp_record.add_argument('--external-jobs', default=None, help='远端 MCP 任务记录 JSON 列表')
    cmp_record.add_argument('--note', default=None)

    cmp_finalize = cmp_sub.add_parser('finalize', help='（Agent 入口）锁定 incumbent 完成独立 Holdout 盲评（BYO-MCP 传入 --metrics）')
    cmp_finalize.add_argument('campaign_id', nargs='?', default='latest')
    cmp_finalize.add_argument('--status', choices=('succeeded', 'failed'), default='succeeded')
    cmp_finalize.add_argument('--metrics', default=None, help='（BYO-MCP）独立 Holdout 实测指标 JSON')
    cmp_finalize.add_argument('--metrics-file', type=Path, default=None)
    cmp_finalize.add_argument('--cost', default=None, help='（BYO-MCP）Holdout 评测消耗成本 JSON')
    cmp_finalize.add_argument('--artifacts', default=None, help='（BYO-MCP）Holdout 产物与模型校验 URI JSON')
    cmp_finalize.add_argument('--external-jobs', default=None)
    cmp_finalize.add_argument('--note', default=None)
    cmp_finalize.add_argument('--poll-seconds', type=float, default=0.05)

    for name in ('status', 'stop', 'events', 'export'):
        action = cmp_sub.add_parser(name)
        action.add_argument('campaign_id', nargs='?', default='latest')
    return command


def main() -> int:
    command = parser()
    args = command.parse_args()
    if hasattr(args, 'poll_seconds') and not 0.01 <= args.poll_seconds <= 60:
        command.error('--poll-seconds must be between 0.01 and 60')
    try:
        if args.command == 'init':
            stages = [s.strip() for s in args.stages.split(',') if s.strip()]
            result = init_workspace(
                workspace=args.workspace,
                model_family=args.model_family,
                kb_id=args.kb_id,
                primary_metric=args.metric,
                direction=args.direction,
                min_gain=args.min_gain,
                holdout_target=args.holdout_target,
                compute_metric=args.compute,
                compute_unit=args.compute_unit,
                max_compute_value=args.max_compute,
                max_compute_ratio=args.max_compute_ratio,
                cost_metric=args.cost,
                cost_unit=args.cost_unit,
                max_cost=args.max_cost,
                max_trials=args.max_trials,
                track=args.track,
                stages=stages,
            )
            print_json(result)
            return 0
        if args.command == 'kb':
            return _main_kb(args)
        if args.command == 'campaign':
            return _main_campaign(args)
        harness = Harness(args.output)
        if args.command in {'demo', 'create'}:
            run_id = harness.create(json.loads(args.plan.read_text(encoding='utf-8')))
            if args.command == 'create':
                print_json({'run_id': run_id, 'status': 'running'})
                return 0
            return drive(harness, run_id, args.once, args.poll_seconds)
        run_id = harness.status(args.run_id)['run_id']
        if args.command == 'resume':
            return drive(harness, run_id, args.once, args.poll_seconds)
        if args.command == 'stop':
            terminal = harness.status(run_id)['status'] in TERMINAL
            harness.request_stop(run_id)
            try:
                harness.step(run_id)
            except WorkerBusy:
                pass
            message = '运行已经结束。' if terminal else '停止意图已保存；如仍有任务，用 resume 继续对账和回收日志。'
            print_json({'run_id': run_id, 'stop_requested': not terminal,
                        'status': harness.status(run_id)['status'], 'message': message})
        elif args.command == 'status':
            print_json(harness.status(run_id))
        elif args.command == 'events':
            print_json(harness.events(run_id))
        elif args.command == 'export':
            print_json({'artifacts': str(harness.export(run_id))})
        return 0
    except (ValueError, OSError, WorkerBusy) as error:
        print_json({'error': str(error)})
        return 2
    except KeyboardInterrupt:
        print('运行状态已保留，使用 resume 继续；使用 stop 请求停止模拟任务。', file=sys.stderr)
        return 130


def _main_kb(args: argparse.Namespace) -> int:
    kb = KnowledgeBase(args.kb_dir)
    if args.kb_command == 'list':
        entries = kb.list_entries(track=args.track, status=args.status)
        print_json([{
            'kb_id': e['kb_id'], 'revision': e['revision'], 'track': e['track'],
            'status': e['status'], 'model_family': (e.get('scope') or {}).get('model_family'),
            'title': e['title'],
            'patterns': len(e.get('patterns', [])), 'anti_patterns': len(e.get('anti_patterns', [])),
            'evidence': len(e.get('evidence', [])), 'drafts': len(e.get('draft_revisions', [])),
            'content_sha256': e.get('content_sha256'),
        } for e in entries])
        return 0
    if args.kb_command == 'search':
        entries = kb.search(
            query=args.query,
            track=args.track,
            model_family=args.model_family,
            status=args.status,
            field=args.field,
            max_flops_m=args.max_flops,
            max_flops_ratio=args.max_flops_ratio,
            min_gain_pp=args.min_gain_pp,
            direction=args.direction,
            failure_type=args.failure_type,
        )
        print_json([{
            'kb_id': e['kb_id'], 'revision': e['revision'], 'track': e['track'],
            'status': e['status'], 'title': e['title'], 'scope': e.get('scope', {}),
            'matched_patterns': e.get('matched_patterns', []),
            'matched_anti_patterns': e.get('matched_anti_patterns', []),
        } for e in entries])
        return 0
    if args.kb_command == 'show':
        print_json(kb.load(args.kb_id, revision=args.revision))
        return 0
    if args.kb_command == 'drafts':
        print_json(kb.list_drafts(args.kb_id))
        return 0
    if args.kb_command == 'distill':
        runner = CampaignRunner(args.output)
        campaign = runner.status(args.campaign_id)
        draft = kb.distill_from_campaign(campaign, kb_id=args.kb_id)
        print_json({'kb_id': draft['kb_id'], 'draft': draft})
        return 0
    if args.kb_command == 'publish':
        published = kb.publish(args.kb_id, draft_revision=args.revision, reviewer=args.reviewer)
        print_json({
            'kb_id': published['kb_id'], 'revision': published['revision'],
            'status': published['status'], 'reviewed_by': published.get('reviewed_by'),
            'patterns': len(published.get('patterns', [])),
            'anti_patterns': len(published.get('anti_patterns', [])),
            'evidence': len(published.get('evidence', [])),
            'content_sha256': published.get('content_sha256'),
        })
        return 0
    if args.kb_command == 'reindex':
        index_path = kb.reindex()
        print_json({'index_md': str(index_path), 'entries': len(kb.list_entries())})
        return 0
    return 2


def _main_campaign(args: argparse.Namespace) -> int:
    runner = CampaignRunner(args.output)
    if args.campaign_command in {'demo', 'create'}:
        plan_path: Path = args.plan.resolve()
        campaign_id = runner.create(
            json.loads(plan_path.read_text(encoding='utf-8')),
            plan_dir=plan_path.parent,
            kb_root=args.kb_dir,
            kb_id=args.kb,
            kb_revision=args.kb_revision,
        )
        if args.campaign_command == 'create':
            state = runner.status(campaign_id)
            print_json({
                'campaign_id': campaign_id,
                'execution_mode': state['plan']['execution_mode'],
                'track': state['plan']['track'],
                'status': 'running',
            })
            return 0
        return drive_campaign(runner, campaign_id, args.once, args.poll_seconds)

    campaign_id = runner.status(args.campaign_id)['campaign_id']
    if args.campaign_command == 'resume':
        return drive_campaign(runner, campaign_id, args.once, args.poll_seconds)
    if args.campaign_command == 'baseline':
        trial = runner.run_baseline(campaign_id, poll_seconds=args.poll_seconds)
        runner.export(campaign_id)
        ctx = runner.get_context(campaign_id)
        print_json({
            'campaign_id': campaign_id,
            'execution_mode': ctx['execution_mode'],
            'trial': trial,
            'remaining_budget': ctx['remaining_budget'],
        })
        return 0 if trial['decision'] in {'baseline', None} else 1
    if args.campaign_command == 'context':
        print_json(runner.get_context(campaign_id))
        return 0
    if args.campaign_command == 'propose':
        if args.proposal_file is not None:
            proposal = Proposal.from_dict(json.loads(args.proposal_file.read_text(encoding='utf-8')))
        else:
            if not args.hypothesis or not args.changes:
                raise ValueError('Provide --proposal-file or both --hypothesis and --changes')
            proposal = Proposal.from_dict({
                'hypothesis': args.hypothesis,
                'changes': json.loads(args.changes),
                'reuse_simulation': args.reuse_simulation,
            })
        state = runner.status(campaign_id)
        if args.run and state['plan'].get('execution_mode') == 'managed' and not state['trials']:
            runner.run_baseline(campaign_id, poll_seconds=args.poll_seconds)
        trial = runner.submit_proposal(campaign_id, proposal)
        if args.run and state['plan'].get('execution_mode') == 'managed':
            trial = runner.run_active_trial(campaign_id, poll_seconds=args.poll_seconds)
            directory = runner.export(campaign_id)
            ctx = runner.get_context(campaign_id)
            print_json({
                'campaign_id': campaign_id,
                'trial_id': trial['trial_id'],
                'decision': trial['decision'],
                'reason': trial['decision_reason'],
                'gain': {
                    'primary_value': trial['primary_value'],
                    'gain': trial['gain'],
                    'gain_pct': trial['gain_pct'],
                },
                'compute': {
                    'compute_value': trial['compute_value'],
                    'compute_ratio': trial['compute_ratio'],
                    'cost_value': trial['cost_value'],
                    'cumulative_cost': trial['cumulative_cost'],
                },
                'incumbent_trial_id': ctx['incumbent']['trial_id'] if ctx['incumbent'] else None,
                'remaining_budget': ctx['remaining_budget'],
                'results_tsv': str(directory / 'results.tsv'),
            })
            return 0 if runner.status(campaign_id)['status'] not in {'paused', 'failed'} else 1
        print_json({
            'campaign_id': campaign_id,
            'trial_id': trial['trial_id'],
            'status': trial['run_status'],
            'candidate_config': trial['candidate_config'],
            'frozen_training_recipe': trial['training_recipe'],
            'dev_evaluator_ref': runner.status(campaign_id)['plan']['dev_evaluator_ref'],
        })
        return 0
    if args.campaign_command == 'record':
        metrics = _load_json_arg(args.metrics, args.metrics_file, default={})
        cost = _load_json_arg(args.cost, None, default={})
        artifacts = _load_json_arg(args.artifacts, None, default={})
        external_jobs = _load_json_arg(args.external_jobs, None, default=[])
        trial = runner.record_trial(
            campaign_id=campaign_id,
            trial_id=args.trial,
            status=args.status,
            metrics=metrics,
            cost=cost,
            artifacts=artifacts,
            external_jobs=external_jobs,
            note=args.note,
        )
        directory = runner.export(campaign_id)
        ctx = runner.get_context(campaign_id)
        print_json({
            'campaign_id': campaign_id,
            'campaign_status': ctx['status'],
            'trial_id': trial['trial_id'],
            'decision': trial['decision'],
            'reason': trial['decision_reason'],
            'gain': {
                'primary_metric': ctx['primary_metric']['name'],
                'primary_value': trial['primary_value'],
                'gain': trial['gain'],
                'gain_pct': trial['gain_pct'],
            },
            'compute': {
                'compute_metric': ctx['compute_metric']['name'],
                'compute_value': trial['compute_value'],
                'compute_ratio': trial['compute_ratio'],
                'cost_metric': ctx['cost_metric']['name'],
                'cost_value': trial['cost_value'],
                'cumulative_cost': trial['cumulative_cost'],
            },
            'incumbent_trial_id': ctx['incumbent']['trial_id'] if ctx['incumbent'] else None,
            'remaining_budget': ctx['remaining_budget'],
            'results_tsv': str(directory / 'results.tsv'),
        })
        return 0 if ctx['status'] not in {'failed', 'paused'} else 1
    if args.campaign_command == 'finalize':
        state = runner.status(campaign_id)
        if state['plan'].get('execution_mode') == 'external_mcp' or args.metrics is not None or args.metrics_file is not None:
            metrics = _load_json_arg(args.metrics, args.metrics_file, default={})
            cost = _load_json_arg(args.cost, None, default={})
            artifacts = _load_json_arg(args.artifacts, None, default={})
            external_jobs = _load_json_arg(args.external_jobs, None, default=[])
            campaign = runner.finalize_external_holdout(
                campaign_id=campaign_id,
                metrics=metrics,
                cost=cost,
                artifacts=artifacts,
                external_jobs=external_jobs,
                status=args.status,
                note=args.note,
            )
        else:
            campaign = runner.finalize_holdout(campaign_id, poll_seconds=args.poll_seconds)
        directory = runner.export(campaign_id)
        print_json({
            'campaign_id': campaign_id,
            'status': campaign['status'],
            'incumbent_trial_id': campaign['incumbent_trial_id'],
            'holdout_report': campaign['holdout_report'],
            'results_tsv': str(directory / 'results.tsv'),
        })
        return 0 if campaign['status'] == 'succeeded' else 1
    if args.campaign_command == 'stop':
        terminal = runner.status(campaign_id)['status'] in CAMPAIGN_TERMINAL
        runner.request_stop(campaign_id)
        if runner.status(campaign_id)['plan'].get('execution_mode') == 'managed':
            try:
                runner.step(campaign_id)
            except WorkerBusy:
                pass
        message = 'Campaign 已经结束。' if terminal else '停止意图已保存；如仍有远端任务，请回收终态与日志。'
        print_json({
            'campaign_id': campaign_id,
            'stop_requested': not terminal,
            'status': runner.status(campaign_id)['status'],
            'message': message,
        })
    elif args.campaign_command == 'status':
        print_json(runner.status(campaign_id))
    elif args.campaign_command == 'events':
        print_json(runner.events(campaign_id))
    elif args.campaign_command == 'export':
        directory = runner.export(campaign_id)
        print_json({'artifacts': str(directory), 'results_tsv': str(directory / 'results.tsv')})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
