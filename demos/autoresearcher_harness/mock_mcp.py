from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Iterator
import uuid

from .contracts import STAGES


def estimate_conv1d_arch_metrics(
    architecture: dict[str, Any],
    total_cases: int = 24,
    is_holdout: bool = False,
) -> dict[str, Any]:
    """Deterministic surrogate for Conv1d Transformer architecture gain & compute demos.

    Allows Claude Code / Codex / OpenCode to explore arbitrary valid architecture
    proposals interactively without pre-authoring per-proposal mock overrides.
    """
    num_layers = int(architecture.get('num_layers', 6))
    d_model = int(architecture.get('d_model', 192))
    kernel_size = int(architecture.get('kernel_size', 5))
    ffn_ratio = float(architecture.get('ffn_ratio', 2.0))
    conv_type = str(architecture.get('conv_type', 'standard'))
    dilation = int(architecture.get('dilation', 1))

    # Inference FLOPs estimate (MFLOPs) normalized so 6L/d192/k5/ffn2.0/standard == 120.0 MFLOPs.
    conv_factor = 0.42 if conv_type == 'depthwise_separable' else 1.0
    width_scale = (d_model / 192.0) ** 2
    per_layer_m = (8.0 * (kernel_size / 5.0) * conv_factor + 12.0 * (ffn_ratio / 2.0)) * width_scale
    cand_flops_m = round(max(12.0, num_layers * per_layer_m), 2)

    # Deterministic accuracy response surface rewarding balanced depth, dilated/larger receptive field,
    # and depthwise-separable efficiency while penalizing extreme over-parameterization on small data.
    score = 16.0
    if conv_type == 'depthwise_separable':
        score += 2.0
    if kernel_size in (7, 9):
        score += 1.8
    elif kernel_size >= 11:
        score += 0.6
    elif kernel_size <= 3:
        score -= 1.0
    if dilation == 2:
        score += 1.2
    elif dilation > 2:
        score -= 0.5
    if 6 <= num_layers <= 8:
        score += 0.6 * (num_layers - 6)
    elif num_layers > 8:
        score -= 1.0 * (num_layers - 8)
    elif num_layers < 5:
        score -= 1.5
    if d_model > 256:
        score -= 1.0
    elif d_model < 128:
        score -= 1.2
    if ffn_ratio >= 3.5:
        score -= 0.8
    elif ffn_ratio < 1.5:
        score -= 0.6

    # Holdout slightly more conservative than dev to mimic realistic generalization gap.
    if is_holdout and score > 16.0:
        score -= 0.6

    candidate_correct = max(0, min(total_cases, int(round(score))))
    mixed_err = round(max(0.05, min(0.45, 0.30 - (candidate_correct - 16) * 0.032)), 3)
    latency_ms = round(cand_flops_m / 28.0, 2)
    return {
        'baseline_correct': 16,
        'candidate_correct': candidate_correct,
        'total_cases': total_cases,
        'baseline_inference_flops_m': 120.0,
        'candidate_inference_flops_m': cand_flops_m,
        'metrics': {
            'mixed_error_rate': mixed_err,
            'latency_ms': latency_ms,
        },
    }


class MockMCP:
    """Local tools with durable remote-job semantics, compute usage accounting, and fixture results."""

    mode = 'mock'

    def __init__(self, root: Path, settings: dict[str, Any]) -> None:
        self.path = root / 'mock_mcp.sqlite3'
        self.settings = settings
        with self.connect() as connection:
            connection.execute('PRAGMA journal_mode=WAL')
            connection.execute('''CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY, request_id TEXT UNIQUE NOT NULL,
                stage TEXT NOT NULL, arguments TEXT NOT NULL, ready_at REAL NOT NULL,
                terminal_status TEXT NOT NULL, cancelled INTEGER NOT NULL DEFAULT 0
            )''')

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA busy_timeout=10000')
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name.startswith('submit_') and name.removeprefix('submit_') in STAGES:
            return self.submit(name.removeprefix('submit_'), arguments)
        if name == 'find_job':
            with self.connect() as connection:
                row = connection.execute('SELECT job_id FROM jobs WHERE request_id = ?',
                                         (arguments['request_id'],)).fetchone()
            return {'found': row is not None, 'job_id': row['job_id'] if row else None, 'conclusive': True}
        if name not in {'get_job', 'stop_job', 'download_logs'}:
            raise ValueError(f'Unknown mock MCP tool: {name}')
        with self.connect() as connection:
            row = connection.execute('SELECT * FROM jobs WHERE job_id = ?', (arguments['job_id'],)).fetchone()
            if row is None:
                raise ValueError('Unknown mock job')
            if name == 'stop_job':
                if self.settings.get('stop_unsupported'):
                    return {'supported': False, 'status': self.remote_status(row)}
                if self.remote_status(row) == 'running':
                    connection.execute('UPDATE jobs SET cancelled = 1 WHERE job_id = ?', (row['job_id'],))
                    return {'supported': True, 'status': 'cancelled'}
                return {'supported': True, 'status': self.remote_status(row)}
        status = self.remote_status(row)
        if name == 'download_logs':
            usage = self.usage(row, status)
            text = '\n'.join([
                'mode=mock', 'job_id=' + row['job_id'], 'stage=' + row['stage'],
                'status=' + status, 'arguments=' + row['arguments'],
                f"usage=gpu_seconds:{usage['gpu_seconds']},train_tflops:{usage['train_tflops']}",
                'note=simulated compute & metrics for offline development',
            ]) + '\n'
            return {'text': text}
        return {
            'job_id': row['job_id'],
            'status': status,
            'usage': self.usage(row, status),
            'result': self.result(row) if status == 'succeeded' else {},
        }

    def submit(self, stage: str, arguments: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps(arguments, sort_keys=True, ensure_ascii=False)
        with self.connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            existing = connection.execute('SELECT * FROM jobs WHERE request_id = ?',
                                          (arguments['request_id'],)).fetchone()
            if existing:
                if existing['stage'] != stage or existing['arguments'] != payload:
                    raise ValueError('Idempotency key reused for a different submission')
                return {'job_id': existing['job_id']}
            job_id = 'mock-' + uuid.uuid4().hex
            terminal = 'failed' if self.settings.get('fail_stage') == stage else 'succeeded'
            connection.execute('INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, 0)', (
                job_id, arguments['request_id'], stage, payload,
                time.time() + self.settings['duration_seconds'], terminal,
            ))
        if self.settings.get('lose_submit_reply_stage') == stage:
            raise TimeoutError('Fixture: submission accepted but its response was lost')
        return {'job_id': job_id}

    @staticmethod
    def remote_status(row: sqlite3.Row) -> str:
        if row['cancelled']:
            return 'cancelled'
        return row['terminal_status'] if time.time() >= row['ready_at'] else 'running'

    def _lookup_architecture_for_model(self, model_ref: str) -> dict[str, Any] | None:
        if not model_ref.startswith('mock://models/'):
            return None
        train_job_id = model_ref.removeprefix('mock://models/')
        with self.connect() as connection:
            row = connection.execute('SELECT arguments FROM jobs WHERE job_id = ?', (train_job_id,)).fetchone()
        if row is None:
            return None
        args = json.loads(row['arguments'])
        arch = args.get('architecture')
        return arch if isinstance(arch, dict) else None

    def usage(self, row: sqlite3.Row, status: str) -> dict[str, float]:
        stage_usage = (self.settings.get('stage_usage') or {}).get(row['stage'])
        if isinstance(stage_usage, dict):
            return {
                'gpu_seconds': float(stage_usage.get('gpu_seconds', 0.0)),
                'train_tflops': float(stage_usage.get('train_tflops', 0.0)),
            }
        arguments = json.loads(row['arguments'])
        scale = 0.5 if status in {'failed', 'cancelled'} else 1.0
        if row['stage'] == 'simulation':
            return {'gpu_seconds': round(12.0 * scale, 2), 'train_tflops': round(1.8 * scale, 2)}
        if row['stage'] == 'training':
            arch = arguments.get('architecture')
            if isinstance(arch, dict):
                surrogate = estimate_conv1d_arch_metrics(arch)
                flops_ratio = surrogate['candidate_inference_flops_m'] / 120.0
                return {
                    'gpu_seconds': round(60.0 * flops_ratio * scale, 2),
                    'train_tflops': round(18.0 * flops_ratio * scale, 2),
                }
            recipe = arguments.get('recipe') or {}
            epochs = float(recipe.get('epochs', 2))
            return {
                'gpu_seconds': round(30.0 * epochs * scale, 2),
                'train_tflops': round(9.0 * epochs * scale, 2),
            }
        return {'gpu_seconds': round(6.0 * scale, 2), 'train_tflops': round(0.9 * scale, 2)}

    def result(self, row: sqlite3.Row) -> dict[str, Any]:
        arguments = json.loads(row['arguments'])
        if row['stage'] == 'simulation':
            return {'mode': 'mock', 'dataset_ref': 'mock://datasets/' + row['job_id']}
        if row['stage'] == 'training':
            payload: dict[str, Any] = {
                'mode': 'mock',
                'model_ref': 'mock://models/' + row['job_id'],
                'dataset_ref': arguments['dataset_ref'],
            }
            if arguments.get('architecture'):
                payload['architecture'] = arguments['architecture']
            return payload

        fixture = self.settings.get('eval_fixture')
        if isinstance(fixture, dict):
            result: dict[str, Any] = {
                'mode': 'mock',
                'baseline_correct': fixture.get('baseline_correct', 16),
                'candidate_correct': fixture.get('candidate_correct', 20),
                'total_cases': fixture.get('total_cases', 24),
                'evaluator_ref': arguments['evaluator_ref'],
                'model_ref': arguments['model_ref'],
                'baseline_model_ref': arguments['baseline_model_ref'],
            }
            for key in ('baseline_inference_flops_m', 'candidate_inference_flops_m', 'metrics'):
                if key in fixture:
                    result[key] = fixture[key]
            return result

        arch = self._lookup_architecture_for_model(arguments['model_ref'])
        if arch is not None:
            is_holdout = 'holdout' in str(arguments['evaluator_ref']).lower()
            surrogate = estimate_conv1d_arch_metrics(arch, total_cases=24, is_holdout=is_holdout)
            return {
                'mode': 'mock',
                **surrogate,
                'evaluator_ref': arguments['evaluator_ref'],
                'model_ref': arguments['model_ref'],
                'baseline_model_ref': arguments['baseline_model_ref'],
            }

        return {
            'mode': 'mock',
            'baseline_correct': 16,
            'candidate_correct': 20,
            'total_cases': 24,
            'baseline_inference_flops_m': 120.0,
            'candidate_inference_flops_m': 120.0,
            'evaluator_ref': arguments['evaluator_ref'],
            'model_ref': arguments['model_ref'],
            'baseline_model_ref': arguments['baseline_model_ref'],
        }
