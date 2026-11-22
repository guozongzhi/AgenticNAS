from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time
from typing import Any
import uuid

from .contracts import Plan, RunState, STAGES, TaskState, TERMINAL, ToolClient
from .mock_mcp import MockMCP
from .store import Store, write_json, write_text


def _normalize_usage(raw: Any) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {'gpu_seconds': 0.0, 'train_tflops': 0.0}
    gpu_s = raw.get('gpu_seconds', 0.0)
    tflops = raw.get('train_tflops', 0.0)
    return {
        'gpu_seconds': float(gpu_s) if isinstance(gpu_s, (int, float)) and not isinstance(gpu_s, bool) and gpu_s >= 0 else 0.0,
        'train_tflops': float(tflops) if isinstance(tflops, (int, float)) and not isinstance(tflops, bool) and tflops >= 0 else 0.0,
    }


def _recompute_run_usage(run: dict[str, Any]) -> dict[str, float]:
    gpu_seconds = 0.0
    train_tflops = 0.0
    for task in run['tasks']:
        usage = task.get('usage') or {}
        gpu_seconds += float(usage.get('gpu_seconds', 0.0))
        train_tflops += float(usage.get('train_tflops', 0.0))
    totals = {'gpu_seconds': round(gpu_seconds, 3), 'train_tflops': round(train_tflops, 3)}
    run['compute_usage'] = totals
    return totals


class Harness:
    def __init__(self, output: Path, client: ToolClient | None = None, stop_retry_seconds: float = 5.0) -> None:
        self.store = Store(output)
        self.root = self.store.root
        self.client = client
        self.stop_retry_seconds = stop_retry_seconds
        self._mock_clients: dict[str, MockMCP] = {}

    def _client_for(self, run: dict[str, Any]) -> ToolClient:
        if self.client is not None:
            return self.client
        mock_settings = run['plan'].get('mock')
        if mock_settings is None:
            raise ValueError('A real ToolClient is required when plan.mock is omitted')
        key = json.dumps(mock_settings, sort_keys=True, ensure_ascii=False)
        client = self._mock_clients.get(key)
        if client is None:
            client = MockMCP(self.root, mock_settings)
            self._mock_clients[key] = client
        return client

    def _mode(self, run: dict[str, Any]) -> str:
        if self.client is not None:
            return str(getattr(self.client, 'mode', 'live'))
        return 'mock' if run['plan'].get('mock') is not None else 'live'

    def create(self, value: dict[str, Any]) -> str:
        plan = Plan.from_dict(value).to_dict()
        run_id = 'run-' + uuid.uuid4().hex
        snapshot = json.dumps(plan['knowledge'], ensure_ascii=False, sort_keys=True).encode('utf-8')
        tasks = [asdict(TaskState(stage, f'{run_id}/{stage}')) for stage in STAGES]
        if plan.get('reuse_model_ref'):
            tasks[0]['status'] = 'succeeded'
            tasks[0]['remote_status'] = 'reused'
            tasks[0]['result'] = {'dataset_ref': plan.get('reuse_dataset_ref') or plan['dataset_ref'], 'reused': True}
            tasks[1]['status'] = 'succeeded'
            tasks[1]['remote_status'] = 'reused'
            tasks[1]['result'] = {'model_ref': plan['reuse_model_ref'], 'reused': True}
        elif plan.get('reuse_dataset_ref'):
            tasks[0]['status'] = 'succeeded'
            tasks[0]['remote_status'] = 'reused'
            tasks[0]['result'] = {'dataset_ref': plan['reuse_dataset_ref'], 'reused': True}
        state = RunState(run_id, plan, hashlib.sha256(snapshot).hexdigest(), time.time(), tasks).to_dict()
        self.store.create(state)
        self.store.event(run_id, 'created', {
            'knowledge_sha256': state['knowledge_sha256'],
            'mode': self._mode(state),
            'evaluation_scope': plan.get('evaluation_scope', 'holdout'),
        })
        return run_id

    def status(self, run_id: str) -> dict[str, Any]:
        return self.store.load(run_id)

    def events(self, run_id: str) -> list[dict[str, Any]]:
        return self.store.events(self.status(run_id)['run_id'])

    def request_stop(self, run_id: str) -> None:
        run = self.status(run_id)
        if run['status'] in TERMINAL:
            return
        self.store.request_stop(run['run_id'])
        self.store.event(run['run_id'], 'stop_requested', {})

    def call(self, run: dict[str, Any], name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.store.event(run['run_id'], 'tool_call', {'name': name, 'arguments': arguments})
        client = self._client_for(run)
        try:
            result = client.call_tool(name, arguments)
            if not isinstance(result, dict):
                raise ValueError('MCP adapter must return a normalized object')
        except Exception as error:
            self.store.event(run['run_id'], 'tool_error', {'name': name, 'error': str(error)})
            raise
        self.store.event(run['run_id'], 'tool_result', {'name': name, 'result': result})
        return result

    def step(self, run_id: str) -> dict[str, Any]:
        run_id = self.status(run_id)['run_id']
        with self.store.worker_lock(run_id):
            run = self.status(run_id)
            if run['status'] in TERMINAL:
                return run
            run['status'], run['error'] = 'running', None
            try:
                self.advance(run)
            except Exception as error:
                run['status'], run['error'] = 'paused', str(error)
                self.store.event(run_id, 'paused', {'error': str(error)})
            self.store.save(run)
            return run

    def advance(self, run: dict[str, Any]) -> None:
        plan = run['plan']
        if self.store.cancel_requested(run['run_id']):
            run['stop_reason'] = run['stop_reason'] or 'cancelled'
        if time.time() - run['created_at'] >= plan['budget']['wall_seconds']:
            run['stop_reason'] = run['stop_reason'] or 'budget_exhausted'
        max_gpu = plan['budget'].get('max_gpu_seconds')
        if max_gpu is not None and run.get('compute_usage', {}).get('gpu_seconds', 0.0) >= max_gpu:
            run['stop_reason'] = run['stop_reason'] or 'budget_exhausted'
        task = next((task for task in run['tasks'] if task['status'] != 'succeeded'), None)
        if task is None:
            self.finish(run)
            return
        if task['status'] == 'pending':
            if run['attempted_tasks'] >= plan['budget']['max_tasks']:
                run['stop_reason'] = run['stop_reason'] or 'budget_exhausted'
            if run['stop_reason']:
                run['status'] = run['stop_reason']
                return
            # Persist the intent before the side effect. A restart reconciles this request ID.
            task['status'] = 'reconciling'
            run['attempted_tasks'] += 1
            self.store.save(run)
            self.submit(run, task)
            return
        if task['status'] == 'reconciling':
            found = self.call(run, 'find_job', {'request_id': task['request_id']})
            if found.get('found'):
                task['job_id'] = self.valid_job_id(found)
                task['status'] = 'running'
            elif found.get('conclusive') is True:
                if run['stop_reason']:
                    run['status'] = run['stop_reason']
                    return
                self.submit(run, task)
            else:
                raise RuntimeError('Submission outcome unknown; reconcile before retrying')
            return
        if task['status'] == 'running':
            if run['stop_reason'] and not task.get('stop_unsupported'):
                now = time.time()
                last_sent = task.get('stop_sent_at')
                if last_sent is None or now - last_sent >= self.stop_retry_seconds:
                    try:
                        stop_reply = self.call(run, 'stop_job', {'job_id': task['job_id']})
                    except NotImplementedError:
                        task['stop_unsupported'] = True
                        self.store.event(run['run_id'], 'stop_unsupported', {'stage': task['stage'], 'job_id': task['job_id']})
                    else:
                        task['stop_sent_at'] = now
                        if stop_reply.get('supported') is False:
                            task['stop_unsupported'] = True
                            self.store.event(run['run_id'], 'stop_unsupported', {'stage': task['stage'], 'job_id': task['job_id']})
            result = self.call(run, 'get_job', {'job_id': task['job_id']})
            status = result['status']
            if status not in {'queued', 'running', 'succeeded', 'failed', 'cancelled'}:
                raise ValueError(f'Unknown remote status: {status}')
            task['remote_status'] = status
            if 'usage' in result:
                task['usage'] = _normalize_usage(result.get('usage'))
                _recompute_run_usage(run)
            if status in {'succeeded', 'failed', 'cancelled'}:
                task['result'] = result.get('result', {})
                task['status'] = 'collecting'
            return
        if task['status'] == 'collecting':
            remote = self.call(run, 'get_job', {'job_id': task['job_id']})
            if remote['status'] not in {'succeeded', 'failed', 'cancelled'}:
                raise ValueError('Collecting job must still have a remote terminal status')
            task['remote_status'] = remote['status']
            task['result'] = remote.get('result', {})
            if 'usage' in remote:
                task['usage'] = _normalize_usage(remote.get('usage'))
                _recompute_run_usage(run)
            logs = self.call(run, 'download_logs', {'job_id': task['job_id']})
            if not isinstance(logs.get('text'), str):
                raise ValueError('Log payload must contain text')
            path = Path(run['run_id']) / (task['stage'] + '.log')
            write_text(self.root / path, logs['text'])
            task['log_path'] = str(path)
            # Cancellation always wins downstream scheduling even when the remote job finished first.
            if self.store.cancel_requested(run['run_id']):
                run['stop_reason'] = run['stop_reason'] or 'cancelled'
            # Preserve a completed final evaluation report if wall-clock expired only during collection.
            preserve_final_eval = (
                run['stop_reason'] == 'budget_exhausted'
                and task['stage'] == 'evaluation'
                and task['remote_status'] == 'succeeded'
            )
            if run['stop_reason'] and not preserve_final_eval:
                task['status'] = task['remote_status']
                run['status'] = run['stop_reason']
            elif task['remote_status'] != 'succeeded':
                task['status'] = task['remote_status']
                run['status'] = task['remote_status']
            else:
                if not isinstance(task['result'], dict):
                    raise ValueError('Successful job result must be an object')
                if task['stage'] == 'evaluation':
                    self.finish(run, allow_budget_exhausted=preserve_final_eval)
                else:
                    required = 'dataset_ref' if task['stage'] == 'simulation' else 'model_ref'
                    if not isinstance(task['result'].get(required), str) or not task['result'][required]:
                        raise ValueError(f'Missing {required} in successful job result')
                task['status'] = 'succeeded'
            return
        raise ValueError('Unsupported local task status')

    @staticmethod
    def valid_job_id(result: dict[str, Any]) -> str:
        job_id = result.get('job_id')
        if not isinstance(job_id, str) or not job_id:
            raise ValueError('Submission response has no job_id; reconciliation required')
        return job_id

    def submit(self, run: dict[str, Any], task: dict[str, Any]) -> None:
        if self.store.cancel_requested(run['run_id']):
            run['stop_reason'], run['status'] = 'cancelled', 'cancelled'
            return
        plan = run['plan']
        arguments: dict[str, Any] = {'request_id': task['request_id'], 'knowledge_sha256': run['knowledge_sha256']}
        if task['stage'] == 'simulation':
            arguments.update(dataset_ref=plan['dataset_ref'], hypothesis=plan['hypothesis'])
        elif task['stage'] == 'training':
            arguments.update(
                dataset_ref=run['tasks'][0]['result']['dataset_ref'],
                baseline_model_ref=plan['baseline_model_ref'],
                recipe=plan['training_recipe'],
            )
            if plan.get('architecture') is not None:
                arguments['architecture'] = plan['architecture']
        else:
            arguments.update(
                model_ref=run['tasks'][1]['result']['model_ref'],
                baseline_model_ref=plan['baseline_model_ref'],
                evaluator_ref=plan['evaluator_ref'],
            )
        result = self.call(run, 'submit_' + task['stage'], arguments)
        task['job_id'] = self.valid_job_id(result)
        task['status'] = 'running'

    def finish(self, run: dict[str, Any], allow_budget_exhausted: bool = False) -> None:
        result = run['tasks'][2]['result']
        acceptance = run['plan']['acceptance']
        expected = {
            'model_ref': run['tasks'][1]['result']['model_ref'],
            'baseline_model_ref': run['plan']['baseline_model_ref'],
            'evaluator_ref': run['plan']['evaluator_ref'],
        }
        for name, value in expected.items():
            if result.get(name) != value:
                raise ValueError(f'Evaluation result has mismatched {name}')
        total = result['total_cases']
        if type(total) is not int or total != acceptance['total_cases']:
            raise ValueError('Evaluation case count differs from the frozen acceptance plan')
        for name in ('baseline_correct', 'candidate_correct'):
            if type(result[name]) is not int or not 0 <= result[name] <= total:
                raise ValueError(f'Invalid evaluation count: {name}')
        metrics = result.get('metrics')
        if metrics is not None and not isinstance(metrics, dict):
            raise ValueError('Evaluation metrics must be an object')

        base_flops = result.get('baseline_inference_flops_m')
        cand_flops = result.get('candidate_inference_flops_m')
        if base_flops is not None and (isinstance(base_flops, bool) or not isinstance(base_flops, (int, float)) or base_flops <= 0):
            raise ValueError('Invalid baseline_inference_flops_m')
        if cand_flops is not None and (isinstance(cand_flops, bool) or not isinstance(cand_flops, (int, float)) or cand_flops <= 0):
            raise ValueError('Invalid candidate_inference_flops_m')
        flops_ratio = round(cand_flops / base_flops, 4) if (base_flops is not None and cand_flops is not None) else None

        compute_within_budget = True
        max_flops = acceptance.get('max_inference_flops_m')
        if max_flops is not None:
            if cand_flops is None or cand_flops > max_flops:
                compute_within_budget = False
        max_ratio = acceptance.get('max_flops_ratio')
        if max_ratio is not None:
            if flops_ratio is None or flops_ratio > max_ratio:
                compute_within_budget = False

        gain_correct = result['candidate_correct'] - result['baseline_correct']
        gain_pp = round(gain_correct * 100.0 / total, 2)
        usage = _recompute_run_usage(run)
        gpu_seconds = usage['gpu_seconds']
        gain_per_gpu_hour = round(gain_pp / (gpu_seconds / 3600.0), 4) if gpu_seconds > 0 else None

        run['report'] = {
            'mode': self._mode(run),
            'evaluation_scope': run['plan'].get('evaluation_scope', 'holdout'),
            'run_id': run['run_id'],
            'knowledge_sha256': run['knowledge_sha256'],
            'baseline_correct': result['baseline_correct'],
            'candidate_correct': result['candidate_correct'],
            'total_cases': total,
            'min_correct': acceptance['min_correct'],
            'baseline_accuracy': round(result['baseline_correct'] / total, 4),
            'candidate_accuracy': round(result['candidate_correct'] / total, 4),
            'gain_correct': gain_correct,
            'gain_pp': gain_pp,
            'baseline_inference_flops_m': float(base_flops) if base_flops is not None else None,
            'candidate_inference_flops_m': float(cand_flops) if cand_flops is not None else None,
            'flops_ratio': flops_ratio,
            'compute_within_budget': compute_within_budget,
            'accepted': (result['candidate_correct'] >= acceptance['min_correct']) and compute_within_budget,
            'model_ref': result['model_ref'],
            'baseline_model_ref': result['baseline_model_ref'],
            'evaluator_ref': result['evaluator_ref'],
            'metrics': metrics or {},
            'compute_usage': usage,
            'gain_per_gpu_hour': gain_per_gpu_hour,
            'gpu_cost': gpu_seconds if gpu_seconds > 0 else None,
            'llm_cost': None,
        }
        if allow_budget_exhausted:
            run['status'] = 'succeeded'
        else:
            run['status'] = run['stop_reason'] or 'succeeded'

    def export(self, run_id: str) -> Path:
        run_id = self.status(run_id)['run_id']
        with self.store.worker_lock(run_id):
            run = self.status(run_id)
            directory = self.root / run_id
            write_json(directory / 'run.json', run)
            # Always overwrite to avoid showing a report from an earlier export.
            write_json(directory / 'report.json', run['report'])
            events = ''.join(json.dumps(event, ensure_ascii=False) + '\n' for event in self.events(run_id))
            write_text(directory / 'trace.jsonl', events)
            return directory

    def mcp_jobs(self) -> list[dict[str, Any]]:
        mock = MockMCP(self.root, {'duration_seconds': 0})
        with mock.connect() as connection:
            return [dict(row) for row in connection.execute('SELECT * FROM jobs').fetchall()]
