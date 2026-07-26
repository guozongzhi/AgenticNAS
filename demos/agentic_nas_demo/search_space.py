from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import random
from typing import Any, Literal


MIN_DEPTH = 4
MAX_DEPTH = 10
EMBED_DIMS = (64, 96, 128)
NUM_HEADS = (2, 4, 8)
FFN_RATIOS = (2, 3, 4)
FFN_KERNELS = (1, 3, 5)
ACTIVATIONS = ("gelu", "silu")

SearchLevel = Literal["block", "cell", "op"]


@dataclass(frozen=True)
class BlockSpec:
    """One Transformer block: attention cell + Conv1d feed-forward cell."""

    num_heads: int
    ffn_ratio: int
    ffn_kernel_size: int
    activation: str

    def validate(self, embed_dim: int) -> None:
        if self.num_heads not in NUM_HEADS or embed_dim % self.num_heads != 0:
            raise ValueError("num_heads must be supported and divide embed_dim")
        if self.ffn_ratio not in FFN_RATIOS:
            raise ValueError(f"ffn_ratio must be one of {FFN_RATIOS}")
        if self.ffn_kernel_size not in FFN_KERNELS:
            raise ValueError(f"ffn_kernel_size must be one of {FFN_KERNELS}")
        if self.activation not in ACTIVATIONS:
            raise ValueError(f"activation must be one of {ACTIVATIONS}")

    def to_dict(self) -> dict[str, int | str]:
        return {
            "num_heads": self.num_heads,
            "ffn_ratio": self.ffn_ratio,
            "ffn_kernel_size": self.ffn_kernel_size,
            "activation": self.activation,
        }


@dataclass(frozen=True)
class ArchitectureSpec:
    """Serializable architecture description independent of any NAS engine."""

    embed_dim: int
    blocks: tuple[BlockSpec, ...]
    vocab_size: int = 256
    max_seq_len: int = 128

    @property
    def depth(self) -> int:
        return len(self.blocks)

    @property
    def arch_id(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]

    def validate(self) -> None:
        if self.embed_dim not in EMBED_DIMS:
            raise ValueError(f"embed_dim must be one of {EMBED_DIMS}")
        if not MIN_DEPTH <= self.depth <= MAX_DEPTH:
            raise ValueError(f"depth must be in [{MIN_DEPTH}, {MAX_DEPTH}]")
        if self.vocab_size < 2 or self.max_seq_len < 1:
            raise ValueError("vocab_size and max_seq_len must be positive")
        for block in self.blocks:
            block.validate(self.embed_dim)

    def to_dict(self) -> dict[str, Any]:
        return {
            "embed_dim": self.embed_dim,
            "depth": self.depth,
            "vocab_size": self.vocab_size,
            "max_seq_len": self.max_seq_len,
            "blocks": [block.to_dict() for block in self.blocks],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArchitectureSpec:
        blocks = tuple(BlockSpec(**block) for block in data["blocks"])
        spec = cls(
            embed_dim=int(data["embed_dim"]),
            blocks=blocks,
            vocab_size=int(data.get("vocab_size", 256)),
            max_seq_len=int(data.get("max_seq_len", 128)),
        )
        if "depth" in data and int(data["depth"]) != spec.depth:
            raise ValueError("depth does not match the number of blocks")
        spec.validate()
        return spec


@dataclass(frozen=True)
class MutationAction:
    """An Agent action over the block/cell/op hierarchy."""

    parent_id: str
    level: SearchLevel
    field: str
    value: int | str
    target_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "parent_id": self.parent_id,
            "level": self.level,
            "target_index": self.target_index,
            "field": self.field,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MutationAction:
        action = cls(
            parent_id=str(data["parent_id"]),
            level=data["level"],
            field=str(data["field"]),
            value=data["value"],
            target_index=data.get("target_index"),
        )
        if action.level not in ("block", "cell", "op"):
            raise ValueError("level must be block, cell, or op")
        return action


def _random_block(embed_dim: int, rng: random.Random) -> BlockSpec:
    valid_heads = [heads for heads in NUM_HEADS if embed_dim % heads == 0]
    return BlockSpec(
        num_heads=rng.choice(valid_heads),
        ffn_ratio=rng.choice(FFN_RATIOS),
        ffn_kernel_size=rng.choice(FFN_KERNELS),
        activation=rng.choice(ACTIVATIONS),
    )


def random_spec(rng: random.Random) -> ArchitectureSpec:
    embed_dim = rng.choice(EMBED_DIMS)
    depth = rng.randint(MIN_DEPTH, MAX_DEPTH)
    spec = ArchitectureSpec(
        embed_dim=embed_dim,
        blocks=tuple(_random_block(embed_dim, rng) for _ in range(depth)),
    )
    spec.validate()
    return spec


def random_action(spec: ArchitectureSpec, rng: random.Random) -> MutationAction:
    level = rng.choice(("block", "cell", "op"))
    if level == "block":
        choices = [depth for depth in range(MIN_DEPTH, MAX_DEPTH + 1) if depth != spec.depth]
        return MutationAction(spec.arch_id, "block", "depth", rng.choice(choices))

    target_index = rng.randrange(spec.depth)
    block = spec.blocks[target_index]
    if level == "cell":
        field = rng.choice(("num_heads", "ffn_ratio"))
        candidates = NUM_HEADS if field == "num_heads" else FFN_RATIOS
        if field == "num_heads":
            candidates = tuple(value for value in candidates if spec.embed_dim % value == 0)
        current = getattr(block, field)
        return MutationAction(
            spec.arch_id,
            "cell",
            field,
            rng.choice([value for value in candidates if value != current]),
            target_index,
        )

    field = rng.choice(("ffn_kernel_size", "activation"))
    candidates = FFN_KERNELS if field == "ffn_kernel_size" else ACTIVATIONS
    current = getattr(block, field)
    return MutationAction(
        spec.arch_id,
        "op",
        field,
        rng.choice([value for value in candidates if value != current]),
        target_index,
    )


def apply_action(spec: ArchitectureSpec, action: MutationAction) -> ArchitectureSpec:
    if action.parent_id != spec.arch_id:
        raise ValueError("action parent_id does not match architecture")

    blocks = list(spec.blocks)
    if action.level == "block":
        if action.field != "depth" or not isinstance(action.value, int):
            raise ValueError("block action must set an integer depth")
        if not MIN_DEPTH <= action.value <= MAX_DEPTH or action.value == spec.depth:
            raise ValueError("new depth must be different and within the search range")
        if action.value < spec.depth:
            blocks = blocks[: action.value]
        else:
            while len(blocks) < action.value:
                blocks.append(blocks[-1])
    else:
        if action.target_index is None or not 0 <= action.target_index < spec.depth:
            raise ValueError("cell/op action requires a valid target_index")
        old = blocks[action.target_index]
        values = old.to_dict()
        allowed = {
            "cell": {"num_heads", "ffn_ratio"},
            "op": {"ffn_kernel_size", "activation"},
        }[action.level]
        if action.field not in allowed:
            raise ValueError(f"{action.field} is not valid for level {action.level}")
        if values[action.field] == action.value:
            raise ValueError("mutation must change the selected field")
        values[action.field] = action.value
        blocks[action.target_index] = BlockSpec(**values)

    child = ArchitectureSpec(
        embed_dim=spec.embed_dim,
        blocks=tuple(blocks),
        vocab_size=spec.vocab_size,
        max_seq_len=spec.max_seq_len,
    )
    child.validate()
    return child
