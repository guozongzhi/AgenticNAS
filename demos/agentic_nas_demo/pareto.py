from __future__ import annotations

from dataclasses import dataclass, asdict
from math import log10
from typing import Iterable

from torch import nn

from .model import ConvTransformerLM
from .search_space import ArchitectureSpec


@dataclass(frozen=True)
class Evaluation:
    arch_id: str
    quality_proxy: float
    params_m: float
    latency_proxy_ms: float

    def to_dict(self) -> dict[str, float | str]:
        return asdict(self)


def evaluate(spec: ArchitectureSpec) -> Evaluation:
    """Cheap deterministic proxies for demonstrating the search loop, not research metrics."""

    model = ConvTransformerLM(spec)
    params = sum(parameter.numel() for parameter in model.parameters())
    avg_ratio = sum(block.ffn_ratio for block in spec.blocks) / spec.depth
    kernel_diversity = len({block.ffn_kernel_size for block in spec.blocks})
    quality = (
        0.28
        + 0.11 * log10(max(params, 10_000) / 10_000)
        + 0.012 * spec.depth
        + 0.008 * avg_ratio
        + 0.004 * kernel_diversity
    )
    latency = (
        0.025 * spec.depth
        + 0.0000015 * spec.embed_dim * spec.embed_dim * spec.depth
        + 0.006 * sum(block.ffn_kernel_size for block in spec.blocks)
    )
    return Evaluation(
        arch_id=spec.arch_id,
        quality_proxy=round(min(quality, 0.99), 6),
        params_m=round(params / 1_000_000, 6),
        latency_proxy_ms=round(latency, 6),
    )


def dominates(left: Evaluation, right: Evaluation) -> bool:
    no_worse = (
        left.quality_proxy >= right.quality_proxy
        and left.params_m <= right.params_m
        and left.latency_proxy_ms <= right.latency_proxy_ms
    )
    strictly_better = (
        left.quality_proxy > right.quality_proxy
        or left.params_m < right.params_m
        or left.latency_proxy_ms < right.latency_proxy_ms
    )
    return no_worse and strictly_better


def pareto_frontier(evaluations: Iterable[Evaluation]) -> list[Evaluation]:
    candidates = list(evaluations)
    return sorted(
        [
            candidate
            for candidate in candidates
            if not any(
                dominates(other, candidate)
                for other in candidates
                if other.arch_id != candidate.arch_id
            )
        ],
        key=lambda item: (item.params_m, -item.quality_proxy),
    )
