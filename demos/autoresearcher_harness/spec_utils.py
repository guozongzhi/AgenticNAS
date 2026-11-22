from __future__ import annotations

import copy
import json
import math
from typing import Any


DIRECTIONS = {'maximize', 'minimize'}


def get_by_path(data: dict[str, Any], path: str) -> Any:
    if path in data:
        return data[path]
    current: Any = data
    for part in path.split('.'):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def has_path(data: dict[str, Any], path: str) -> bool:
    try:
        get_by_path(data, path)
        return True
    except KeyError:
        return False


def set_by_path(data: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    updated = copy.deepcopy(data)
    parts = path.split('.')
    if len(parts) == 1 or path in updated:
        updated[path] = copy.deepcopy(value)
        return updated
    current: Any = updated
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = copy.deepcopy(value)
    return updated


def apply_changes(base_config: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base_config)
    for key, value in changes.items():
        result = set_by_path(result, key, value)
    return result


def extract_by_path(data: Any, path: str, default: Any = None) -> Any:
    if not path:
        return default
    current = data
    for part in path.split('.'):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
    return current


def flatten_leaf_paths(data: dict[str, Any], prefix: str = '') -> dict[str, Any]:
    leaves: dict[str, Any] = {}
    for key, value in data.items():
        full = f'{prefix}.{key}' if prefix else key
        if isinstance(value, dict) and value:
            leaves.update(flatten_leaf_paths(value, full))
        else:
            leaves[full] = value
    return leaves


def count_config_diffs(base_config: dict[str, Any], candidate_config: dict[str, Any]) -> float:
    base_leaves = flatten_leaf_paths(base_config)
    cand_leaves = flatten_leaf_paths(candidate_config)
    keys = set(base_leaves) | set(cand_leaves)
    return float(sum(1 for key in keys if base_leaves.get(key) != cand_leaves.get(key)))


def normalize_primary_metric(acceptance: dict[str, Any]) -> dict[str, Any]:
    raw = acceptance.get('primary_metric')
    if isinstance(raw, dict):
        name = str(raw['name'])
        direction = str(raw.get('direction', 'maximize'))
        if direction not in DIRECTIONS:
            raise ValueError(f'Invalid primary_metric.direction: {direction}')
        return {
            'name': name,
            'unit': str(raw.get('unit', '')),
            'direction': direction,
            'min_gain': float(raw.get('min_gain', 0.0)),
            'tie_tolerance': float(raw.get('tie_tolerance', 0.0)),
            'holdout_target': float(raw['holdout_target']) if raw.get('holdout_target') is not None else None,
            'holdout_min_gain': float(raw['holdout_min_gain']) if raw.get('holdout_min_gain') is not None else None,
            'legacy_counts': False,
        }
    return {
        'name': 'correct',
        'unit': 'cases',
        'direction': 'maximize',
        'min_gain': float(acceptance.get('min_delta', 1)),
        'tie_tolerance': float(acceptance.get('tie_tolerance', 0.0)),
        'holdout_target': float(acceptance['holdout_min_correct']) if 'holdout_min_correct' in acceptance else None,
        'holdout_min_gain': None,
        'legacy_counts': True,
        'dev_total_cases': acceptance.get('dev_total_cases'),
        'holdout_total_cases': acceptance.get('holdout_total_cases'),
    }


def normalize_compute_metric(acceptance: dict[str, Any]) -> dict[str, Any]:
    raw = acceptance.get('compute_metric')
    if isinstance(raw, dict):
        return {
            'name': str(raw['name']),
            'unit': str(raw.get('unit', '')),
            'direction': str(raw.get('direction', 'minimize')),
            'max_value': float(raw['max_value']) if raw.get('max_value') is not None else None,
            'max_ratio': float(raw['max_ratio']) if raw.get('max_ratio') is not None else None,
        }
    return {
        'name': 'inference_flops_m',
        'unit': 'MFLOPs',
        'direction': 'minimize',
        'max_value': float(acceptance['max_inference_flops_m']) if acceptance.get('max_inference_flops_m') is not None else None,
        'max_ratio': float(acceptance['max_flops_ratio']) if acceptance.get('max_flops_ratio') is not None else None,
    }


def normalize_cost_metric(budget: dict[str, Any]) -> dict[str, Any]:
    raw = budget.get('cost_metric')
    if isinstance(raw, dict):
        return {
            'name': str(raw['name']),
            'unit': str(raw.get('unit', '')),
            'max_total': float(raw['max_total']) if raw.get('max_total') is not None else None,
        }
    return {
        'name': 'gpu_seconds',
        'unit': 's',
        'max_total': float(budget['max_gpu_seconds']) if budget.get('max_gpu_seconds') is not None else None,
    }


def compute_gain(
    candidate_value: float,
    baseline_value: float,
    direction: str,
    denominator_override: float | None = None,
) -> tuple[float, float | None]:
    """Return direction-normalized (gain, gain_pct) where positive ALWAYS means better."""
    raw_delta = (candidate_value - baseline_value) if direction == 'maximize' else (baseline_value - candidate_value)
    gain = round(float(raw_delta), 6)
    denom = denominator_override if denominator_override is not None else abs(baseline_value)
    if denom is not None and denom > 1e-12:
        gain_pct = round(gain * 100.0 / denom, 2)
    else:
        gain_pct = None
    return gain, gain_pct


def meets_holdout_target(
    candidate_value: float,
    baseline_value: float | None,
    primary_spec: dict[str, Any],
) -> bool:
    direction = primary_spec['direction']
    target = primary_spec.get('holdout_target')
    if target is not None:
        if direction == 'maximize' and candidate_value < target:
            return False
        if direction == 'minimize' and candidate_value > target:
            return False
    min_gain = primary_spec.get('holdout_min_gain')
    if min_gain is not None:
        if baseline_value is None:
            return False
        gain, _ = compute_gain(candidate_value, baseline_value, direction)
        if gain < min_gain:
            return False
    return True


def is_finite_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)
