"""Reference MCP adapter showing how to bridge an external MCP server to ToolClient.

No external MCP SDK or network service is required to run this module.
Replace `StubRawMCPTransport` with your real MCP client session call
(for example `session.call_tool(remote_name, payload)`) while keeping the
normalized contract and compute/gain fields intact.
"""
from __future__ import annotations

from typing import Any, Protocol
import uuid

from .contracts import ToolClient
from .spec_utils import extract_by_path


DEFAULT_MCP_MAPPING: dict[str, Any] = {
    'tools': {
        'submit_simulation': 'sim.run_workload',
        'submit_training': 'train.launch_job',
        'submit_evaluation': 'eval.run_benchmark',
        'find_job': 'platform.lookup_by_token',
        'get_job': 'platform.query_task',
        'stop_job': 'platform.cancel_task',
        'download_logs': 'platform.fetch_logs',
    },
    'status_map': {
        'PENDING': 'queued',
        'QUEUED': 'queued',
        'SUBMITTED': 'queued',
        'RUNNING': 'running',
        'IN_PROGRESS': 'running',
        'SUCCEEDED': 'succeeded',
        'COMPLETED': 'succeeded',
        'FAILED': 'failed',
        'ERROR': 'failed',
        'ABORTED': 'cancelled',
        'CANCELED': 'cancelled',
        'CANCELLED': 'cancelled',
    },
    'response_paths': {
        'job_id': 'remote_task_id',
        'status': 'exec_status',
        'usage_gpu_seconds': 'exec_gpu_sec',
        'usage_train_tflops': 'exec_tflops',
        'dataset_ref': 'outputs.dataset_uri',
        'model_ref': 'outputs.model_uri',
        'log_text': 'log_content',
        'eval_baseline_correct': 'eval_summary.baseline_hits',
        'eval_candidate_correct': 'eval_summary.candidate_hits',
        'eval_total_cases': 'eval_summary.num_cases',
        'eval_baseline_flops_m': 'eval_summary.baseline_flops_m',
        'eval_candidate_flops_m': 'eval_summary.candidate_flops_m',
        'eval_model_ref': 'eval_summary.model_uri',
        'eval_baseline_model_ref': 'eval_summary.baseline_model_uri',
        'eval_evaluator_ref': 'eval_summary.evaluator_uri',
        'eval_metrics': 'eval_summary.slice_metrics',
    },
}


REMOTE_STATUS_MAP = {
    'PENDING': 'queued',
    'QUEUED': 'queued',
    'SUBMITTED': 'queued',
    'RUNNING': 'running',
    'IN_PROGRESS': 'running',
    'SUCCEEDED': 'succeeded',
    'COMPLETED': 'succeeded',
    'FAILED': 'failed',
    'ERROR': 'failed',
    'ABORTED': 'cancelled',
    'CANCELED': 'cancelled',
    'CANCELLED': 'cancelled',
}


class RawMCPTransport(Protocol):
    """Minimal transport interface representing an internal MCP server RPC."""

    def invoke(self, tool_name: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class StubRawMCPTransport:
    """In-memory heterogeneous MCP server stub used to demonstrate schema translation."""

    def __init__(self, support_cancel: bool = True, support_idempotent_lookup: bool = True) -> None:
        self.support_cancel = support_cancel
        self.support_idempotent_lookup = support_idempotent_lookup
        self._jobs: dict[str, dict[str, Any]] = {}
        self._by_token: dict[str, str] = {}

    def invoke(self, tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        if tool_name in {'sim.run_workload', 'train.launch_job', 'eval.run_benchmark'}:
            token = payload['client_token']
            if token in self._by_token:
                return {'remote_task_id': self._by_token[token]}
            task_id = f'ext-{uuid.uuid4().hex[:10]}'
            self._by_token[token] = task_id
            self._jobs[task_id] = {
                'remote_task_id': task_id,
                'tool': tool_name,
                'payload': payload,
                'exec_status': 'SUCCEEDED',
            }
            return {'remote_task_id': task_id}

        if tool_name == 'platform.lookup_by_token':
            if not self.support_idempotent_lookup:
                return {'lookup_supported': False, 'remote_task_id': None}
            task_id = self._by_token.get(payload['client_token'])
            return {'lookup_supported': True, 'remote_task_id': task_id}

        if tool_name == 'platform.query_task':
            record = self._jobs[payload['remote_task_id']]
            return self._build_query_response(record)

        if tool_name == 'platform.cancel_task':
            if not self.support_cancel:
                return {'cancel_supported': False, 'exec_status': 'RUNNING'}
            record = self._jobs[payload['remote_task_id']]
            record['exec_status'] = 'ABORTED'
            return {'cancel_supported': True, 'exec_status': 'ABORTED'}

        if tool_name == 'platform.fetch_logs':
            record = self._jobs[payload['remote_task_id']]
            return {'log_content': f"external_tool={record['tool']}\ntask_id={record['remote_task_id']}\n"}

        raise ValueError(f'Unknown external MCP tool: {tool_name}')

    @staticmethod
    def _build_query_response(record: dict[str, Any]) -> dict[str, Any]:
        task_id = record['remote_task_id']
        payload = record['payload']
        if record['tool'] == 'sim.run_workload':
            return {
                'remote_task_id': task_id,
                'exec_status': record['exec_status'],
                'exec_gpu_sec': 10.0,
                'exec_tflops': 1.5,
                'outputs': {'dataset_uri': f'mcp://datasets/{task_id}'},
            }
        if record['tool'] == 'train.launch_job':
            arch = payload.get('architecture_spec') or {}
            layers = int(arch.get('num_layers', 6))
            return {
                'remote_task_id': task_id,
                'exec_status': record['exec_status'],
                'exec_gpu_sec': round(40.0 + layers * 8.0, 2),
                'exec_tflops': round(12.0 + layers * 2.5, 2),
                'outputs': {'model_uri': f'mcp://models/{task_id}', 'dataset_uri': payload['dataset_uri']},
            }
        arch = payload.get('architecture_spec') or {}
        conv_type = arch.get('conv_type', 'standard')
        cand_flops = 98.0 if conv_type == 'depthwise_separable' else 120.0
        cand_correct = 21 if conv_type == 'depthwise_separable' else 20
        return {
            'remote_task_id': task_id,
            'exec_status': record['exec_status'],
            'exec_gpu_sec': 5.0,
            'exec_tflops': 0.8,
            'eval_summary': {
                'baseline_hits': 16,
                'candidate_hits': cand_correct,
                'num_cases': 24,
                'baseline_flops_m': 120.0,
                'candidate_flops_m': cand_flops,
                'model_uri': payload['model_uri'],
                'baseline_model_uri': payload['baseline_model_uri'],
                'evaluator_uri': payload['evaluator_uri'],
                'slice_metrics': {'mixed_error_rate': 0.12, 'latency_ms': round(cand_flops / 28.0, 2)},
            },
        }


class ExampleMCPAdapter(ToolClient):
    """Reference adapter translating external MCP payloads into Harness ToolClient contracts."""

    mode = 'mcp_example'

    def __init__(self, transport: RawMCPTransport) -> None:
        self.transport = transport
        # Remember architecture specs by model_uri only for the in-memory stub evaluation demo.
        self._model_arch_cache: dict[str, dict[str, Any]] = {}

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == 'submit_simulation':
            raw = self.transport.invoke('sim.run_workload', {
                'client_token': arguments['request_id'],
                'knowledge_fingerprint': arguments['knowledge_sha256'],
                'source_dataset_uri': arguments['dataset_ref'],
                'hypothesis': arguments['hypothesis'],
            })
            return {'job_id': raw['remote_task_id']}

        if name == 'submit_training':
            raw = self.transport.invoke('train.launch_job', {
                'client_token': arguments['request_id'],
                'knowledge_fingerprint': arguments['knowledge_sha256'],
                'dataset_uri': arguments['dataset_ref'],
                'baseline_model_uri': arguments['baseline_model_ref'],
                'training_recipe': arguments['recipe'],
                'architecture_spec': arguments.get('architecture'),
            })
            job_id = raw['remote_task_id']
            if arguments.get('architecture'):
                self._model_arch_cache[f'mcp://models/{job_id}'] = arguments['architecture']
            return {'job_id': job_id}

        if name == 'submit_evaluation':
            raw = self.transport.invoke('eval.run_benchmark', {
                'client_token': arguments['request_id'],
                'knowledge_fingerprint': arguments['knowledge_sha256'],
                'model_uri': arguments['model_ref'],
                'baseline_model_uri': arguments['baseline_model_ref'],
                'evaluator_uri': arguments['evaluator_ref'],
                'architecture_spec': self._model_arch_cache.get(arguments['model_ref']),
            })
            return {'job_id': raw['remote_task_id']}

        if name == 'find_job':
            raw = self.transport.invoke('platform.lookup_by_token', {'client_token': arguments['request_id']})
            if not raw.get('lookup_supported'):
                # Crucial safety rule: if remote lacks lookup, report conclusive=False so Harness pauses instead of double-submitting.
                return {'found': False, 'job_id': None, 'conclusive': False}
            task_id = raw.get('remote_task_id')
            return {'found': task_id is not None, 'job_id': task_id, 'conclusive': True}

        if name == 'get_job':
            raw = self.transport.invoke('platform.query_task', {'remote_task_id': arguments['job_id']})
            status = REMOTE_STATUS_MAP.get(str(raw.get('exec_status', '')).upper())
            if status is None:
                raise ValueError(f"Unmapped external status: {raw.get('exec_status')}")
            normalized: dict[str, Any] = {
                'job_id': raw['remote_task_id'],
                'status': status,
                'usage': {
                    'gpu_seconds': float(raw.get('exec_gpu_sec', 0.0)),
                    'train_tflops': float(raw.get('exec_tflops', 0.0)),
                },
                'result': {},
            }
            if status == 'succeeded':
                if 'outputs' in raw:
                    outputs = raw['outputs']
                    if 'dataset_uri' in outputs:
                        normalized['result']['dataset_ref'] = outputs['dataset_uri']
                    if 'model_uri' in outputs:
                        normalized['result']['model_ref'] = outputs['model_uri']
                if 'eval_summary' in raw:
                    summary = raw['eval_summary']
                    normalized['result'].update({
                        'baseline_correct': int(summary['baseline_hits']),
                        'candidate_correct': int(summary['candidate_hits']),
                        'total_cases': int(summary['num_cases']),
                        'baseline_inference_flops_m': float(summary['baseline_flops_m']),
                        'candidate_inference_flops_m': float(summary['candidate_flops_m']),
                        'model_ref': summary['model_uri'],
                        'baseline_model_ref': summary['baseline_model_uri'],
                        'evaluator_ref': summary['evaluator_uri'],
                        'metrics': dict(summary.get('slice_metrics') or {}),
                    })
            return normalized

        if name == 'stop_job':
            raw = self.transport.invoke('platform.cancel_task', {'remote_task_id': arguments['job_id']})
            if raw.get('cancel_supported') is False:
                return {'supported': False, 'status': REMOTE_STATUS_MAP.get(raw.get('exec_status', ''), 'running')}
            return {'supported': True, 'status': REMOTE_STATUS_MAP.get(raw.get('exec_status', ''), 'cancelled')}

        if name == 'download_logs':
            raw = self.transport.invoke('platform.fetch_logs', {'remote_task_id': arguments['job_id']})
            return {'text': str(raw['log_content'])}

        raise ValueError(f'Unsupported normalized tool: {name}')


class ConfigurableMCPAdapter(ToolClient):
    """Data-driven MCP adapter: bind any remote MCP tool names & field paths via JSON mapping."""

    mode = 'configurable_mcp'

    def __init__(self, transport: RawMCPTransport, mapping: dict[str, Any] | None = None) -> None:
        self.transport = transport
        cfg = mapping or DEFAULT_MCP_MAPPING
        self.tools = {**DEFAULT_MCP_MAPPING['tools'], **(cfg.get('tools') or {})}
        self.status_map = {**DEFAULT_MCP_MAPPING['status_map'], **(cfg.get('status_map') or {})}
        self.paths = {**DEFAULT_MCP_MAPPING['response_paths'], **(cfg.get('response_paths') or {})}
        self._model_arch_cache: dict[str, dict[str, Any]] = {}

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in self.tools:
            raise ValueError(f'Unsupported normalized tool: {name}')
        remote_tool = self.tools[name]
        if name == 'submit_simulation':
            raw = self.transport.invoke(remote_tool, {
                'client_token': arguments['request_id'],
                'knowledge_fingerprint': arguments['knowledge_sha256'],
                'source_dataset_uri': arguments['dataset_ref'],
                'hypothesis': arguments['hypothesis'],
            })
            return {'job_id': extract_by_path(raw, self.paths['job_id'])}
        if name == 'submit_training':
            raw = self.transport.invoke(remote_tool, {
                'client_token': arguments['request_id'],
                'knowledge_fingerprint': arguments['knowledge_sha256'],
                'dataset_uri': arguments['dataset_ref'],
                'baseline_model_uri': arguments['baseline_model_ref'],
                'training_recipe': arguments['recipe'],
                'architecture_spec': arguments.get('architecture'),
            })
            job_id = extract_by_path(raw, self.paths['job_id'])
            if arguments.get('architecture') and job_id:
                self._model_arch_cache[f'mcp://models/{job_id}'] = arguments['architecture']
            return {'job_id': job_id}
        if name == 'submit_evaluation':
            raw = self.transport.invoke(remote_tool, {
                'client_token': arguments['request_id'],
                'knowledge_fingerprint': arguments['knowledge_sha256'],
                'model_uri': arguments['model_ref'],
                'baseline_model_uri': arguments['baseline_model_ref'],
                'evaluator_uri': arguments['evaluator_ref'],
                'architecture_spec': self._model_arch_cache.get(arguments['model_ref']),
            })
            return {'job_id': extract_by_path(raw, self.paths['job_id'])}
        if name == 'find_job':
            raw = self.transport.invoke(remote_tool, {'client_token': arguments['request_id']})
            if not raw.get('lookup_supported', True):
                return {'found': False, 'job_id': None, 'conclusive': False}
            task_id = extract_by_path(raw, self.paths['job_id'])
            return {'found': task_id is not None, 'job_id': task_id, 'conclusive': True}
        if name == 'get_job':
            raw = self.transport.invoke(remote_tool, {'remote_task_id': arguments['job_id']})
            raw_status = extract_by_path(raw, self.paths['status'])
            status = self.status_map.get(str(raw_status).upper())
            if status is None:
                raise ValueError(f'Unmapped external status: {raw_status}')
            normalized: dict[str, Any] = {
                'job_id': extract_by_path(raw, self.paths['job_id']),
                'status': status,
                'usage': {
                    'gpu_seconds': float(extract_by_path(raw, self.paths['usage_gpu_seconds'], 0.0) or 0.0),
                    'train_tflops': float(extract_by_path(raw, self.paths['usage_train_tflops'], 0.0) or 0.0),
                },
                'result': {},
            }
            if status == 'succeeded':
                ds_ref = extract_by_path(raw, self.paths['dataset_ref'])
                if ds_ref:
                    normalized['result']['dataset_ref'] = ds_ref
                m_ref = extract_by_path(raw, self.paths['model_ref'])
                if m_ref:
                    normalized['result']['model_ref'] = m_ref
                eval_cand = extract_by_path(raw, self.paths['eval_candidate_correct'])
                if eval_cand is not None:
                    normalized['result'].update({
                        'baseline_correct': int(extract_by_path(raw, self.paths['eval_baseline_correct'])),
                        'candidate_correct': int(eval_cand),
                        'total_cases': int(extract_by_path(raw, self.paths['eval_total_cases'])),
                        'baseline_inference_flops_m': float(extract_by_path(raw, self.paths['eval_baseline_flops_m'])),
                        'candidate_inference_flops_m': float(extract_by_path(raw, self.paths['eval_candidate_flops_m'])),
                        'model_ref': extract_by_path(raw, self.paths['eval_model_ref']),
                        'baseline_model_ref': extract_by_path(raw, self.paths['eval_baseline_model_ref']),
                        'evaluator_ref': extract_by_path(raw, self.paths['eval_evaluator_ref']),
                        'metrics': dict(extract_by_path(raw, self.paths['eval_metrics']) or {}),
                    })
            return normalized
        if name == 'stop_job':
            raw = self.transport.invoke(remote_tool, {'remote_task_id': arguments['job_id']})
            raw_status = extract_by_path(raw, self.paths['status'], 'CANCELLED')
            if raw.get('cancel_supported') is False:
                return {'supported': False, 'status': self.status_map.get(str(raw_status).upper(), 'running')}
            return {'supported': True, 'status': self.status_map.get(str(raw_status).upper(), 'cancelled')}
        if name == 'download_logs':
            raw = self.transport.invoke(remote_tool, {'remote_task_id': arguments['job_id']})
            return {'text': str(extract_by_path(raw, self.paths['log_text'], ''))}
        raise ValueError(f'Unsupported normalized tool: {name}')
