from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any
import uuid


def is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def positive_number(value: Any, name: str) -> None:
    if not is_finite_number(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")


def non_negative_number(value: Any, name: str) -> None:
    if not is_finite_number(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative number")


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def write_json_atomic(path: Path, payload: Any) -> None:
    write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def canonical_config_id(config: dict[str, Any]) -> str:
    raw = json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def canonical_change_signature(changes: dict[str, Any]) -> str:
    if not changes:
        return "-"
    return ";".join(
        f"{key}={json.dumps(changes[key], sort_keys=True, ensure_ascii=False)}"
        for key in sorted(changes)
    )


def derive_mutation_family(changes: dict[str, Any]) -> str:
    """Group field edits into a canonical structural/recipe principle family.

    Used to detect Principle-Level Local Optima (where surface values vary
    while search collapses onto a single structural axis).
    """
    if not changes:
        return "baseline"
    axes = sorted({str(key).strip() for key in changes if str(key).strip()})
    return "+".join(axes)


def has_path(mapping: dict[str, Any], dotted_path: str) -> bool:
    cur: Any = mapping
    for part in dotted_path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return True


def get_by_path(mapping: dict[str, Any], dotted_path: str) -> Any:
    cur: Any = mapping
    for part in dotted_path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(dotted_path)
        cur = cur[part]
    return cur


def set_by_path(mapping: dict[str, Any], dotted_path: str, value: Any) -> None:
    parts = dotted_path.split(".")
    cur = mapping
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


def apply_changes(base: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in changes.items():
        if "." in key:
            set_by_path(out, key, copy.deepcopy(value))
        else:
            out[key] = copy.deepcopy(value)
    return out


def flatten_leaf_paths(mapping: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    items: dict[str, Any] = {}
    for key, value in mapping.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict) and value:
            items.update(flatten_leaf_paths(value, path))
        else:
            items[path] = value
    return items


def diff_configs(left_cfg: dict[str, Any], right_cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    left = flatten_leaf_paths(left_cfg)
    right = flatten_leaf_paths(right_cfg)
    diffs: dict[str, dict[str, Any]] = {}
    for key in sorted(set(left) | set(right)):
        if left.get(key) != right.get(key):
            diffs[key] = {"from": left.get(key), "to": right.get(key)}
    return diffs


def count_config_diffs(base: dict[str, Any], candidate: dict[str, Any]) -> int:
    return len(diff_configs(base, candidate))


def compute_gain(candidate: float, reference: float, direction: str) -> tuple[float, float]:
    raw_delta = (candidate - reference) if direction == "maximize" else (reference - candidate)
    denom = abs(reference) if abs(reference) > 1e-12 else 1.0
    return round(raw_delta, 6), round((raw_delta / denom) * 100.0, 4)


def meets_holdout_target(candidate: float, baseline: float | None, primary_spec: dict[str, Any]) -> bool:
    direction = primary_spec["direction"]
    target = primary_spec.get("holdout_target")
    if target is not None:
        return candidate >= target if direction == "maximize" else candidate <= target
    min_gain = float(primary_spec.get("holdout_min_gain", primary_spec.get("min_gain", 0.0)))
    if baseline is None:
        return True
    delta, _ = compute_gain(candidate, baseline, direction)
    return delta >= min_gain


def inverse_simpson_diversity(counts: dict[str, int]) -> tuple[float, str | None, float]:
    """Return (effective_count, dominant_key, dominant_share) over categorical counts."""
    total = sum(v for v in counts.values() if v > 0)
    if total <= 0:
        return 0.0, None, 0.0
    dominant_key = max(counts, key=lambda k: (counts[k], k))
    dominant_share = counts[dominant_key] / total
    sum_sq = sum((v / total) ** 2 for v in counts.values() if v > 0)
    eff = (1.0 / sum_sq) if sum_sq > 0 else 0.0
    return round(eff, 3), dominant_key, round(dominant_share, 4)


def compute_2d_pareto_and_hypervolume(
    trials: list[dict[str, Any]],
    *,
    primary_direction: str,
    compute_direction: str,
    baseline_primary: float | None,
    max_compute_ratio: float | None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], float | None]:
    """Compute 2D Gain-Compute Pareto frontier, Compute-Regime MAP-Elites, and 2D Hypervolume.

    Only full-fidelity succeeded trials without guardrail or compute-cap violations enter
    the frontier and MAP-Elites archive.
    """
    eligible = [
        t for t in trials
        if t.get("fidelity", "full") == "full"
        and t.get("run_status") == "succeeded"
        and t.get("primary_value") is not None
        and t.get("compute_value") is not None
        and not t.get("guardrail_violated", False)
        and not t.get("compute_violated", False)
    ]
    if not eligible:
        return [], {}, None

    def _better_or_eq_p(a: float, b: float) -> bool:
        return a >= b if primary_direction == "maximize" else a <= b

    def _strictly_better_p(a: float, b: float) -> bool:
        return a > b if primary_direction == "maximize" else a < b

    def _better_or_eq_c(a: float, b: float) -> bool:
        return a <= b if compute_direction == "minimize" else a >= b

    def _strictly_better_c(a: float, b: float) -> bool:
        return a < b if compute_direction == "minimize" else a > b

    frontier: list[dict[str, Any]] = []
    for cand in eligible:
        dominated = False
        for other in eligible:
            if other["trial_id"] == cand["trial_id"]:
                continue
            p_ok = _better_or_eq_p(other["primary_value"], cand["primary_value"])
            c_ok = _better_or_eq_c(other["compute_value"], cand["compute_value"])
            strict = (
                _strictly_better_p(other["primary_value"], cand["primary_value"])
                or _strictly_better_c(other["compute_value"], cand["compute_value"])
            )
            if p_ok and c_ok and strict:
                dominated = True
                break
        if not dominated:
            frontier.append({
                "trial_id": cand["trial_id"],
                "config_id": cand["config_id"],
                "primary_value": cand["primary_value"],
                "gain_pct": cand.get("gain_pct"),
                "compute_value": cand["compute_value"],
                "compute_ratio": cand.get("compute_ratio"),
                "complexity_score": cand.get("complexity_score"),
                "operator": cand.get("operator", "baseline" if cand.get("is_baseline") else "refine"),
            })

    frontier.sort(key=lambda item: (
        item["compute_value"] if compute_direction == "minimize" else -item["compute_value"],
        -item["primary_value"] if primary_direction == "maximize" else item["primary_value"],
    ))

    # Compute-regime MAP-Elites cells (stepping stones across compute budgets)
    regimes: dict[str, dict[str, Any]] = {}
    for cand in eligible:
        ratio = cand.get("compute_ratio")
        if ratio is None:
            bucket = "balanced"
        elif ratio < 0.92:
            bucket = "lightweight_sub_0.92x"
        elif ratio <= 1.02:
            bucket = "balanced_0.92_1.02x"
        else:
            bucket = "expanded_above_1.02x"
        cur_best = regimes.get(bucket)
        if cur_best is None or _strictly_better_p(cand["primary_value"], cur_best["primary_value"]):
            regimes[bucket] = {
                "trial_id": cand["trial_id"],
                "config_id": cand["config_id"],
                "primary_value": cand["primary_value"],
                "gain_pct": cand.get("gain_pct"),
                "compute_value": cand["compute_value"],
                "compute_ratio": ratio,
                "decision": cand.get("decision"),
            }

    # Normalized 2D Hypervolume over (gain_pct >= 0, compute_savings_below_cap >= 0)
    # Reference point: gain_pct_ref = -5.0% (allows measuring early baseline coverage),
    # compute_ratio_ref = max_compute_ratio or 1.25.
    hv: float | None = None
    if baseline_primary is not None and compute_direction == "minimize":
        r_cap = float(max_compute_ratio) if max_compute_ratio is not None else 1.25
        gain_floor = -5.0
        pts: list[tuple[float, float]] = []
        for item in frontier:
            r_val = item.get("compute_ratio")
            g_pct = item.get("gain_pct")
            if r_val is None or g_pct is None:
                continue
            if r_val <= r_cap and g_pct >= gain_floor:
                pts.append((float(r_val), float(g_pct)))
        if pts:
            pts.sort(key=lambda x: x[0])  # ascending compute_ratio
            area = 0.0
            best_g = gain_floor
            for i, (r_i, g_i) in enumerate(pts):
                if g_i > best_g:
                    next_r = pts[i + 1][0] if i + 1 < len(pts) else r_cap
                    area += max(0.0, next_r - r_i) * (g_i - gain_floor)
                    best_g = g_i
            hv = round(area, 4)

    return frontier, regimes, hv
