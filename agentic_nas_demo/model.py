from __future__ import annotations

import torch
from torch import Tensor, nn
import torch.nn.functional as F

from .search_space import ArchitectureSpec, BlockSpec


class ChannelLayerNorm(nn.Module):
    """LayerNorm over Conv1d channels for tensors shaped [batch, channel, time]."""

    def __init__(self, channels: int) -> None:
        super().__init__()
        self.norm = nn.LayerNorm(channels)

    def forward(self, x: Tensor) -> Tensor:
        return self.norm(x.transpose(1, 2)).transpose(1, 2)


class ConvSelfAttention(nn.Module):
    """Causal self-attention whose QKV and output projections are 1x1 Conv1d."""

    def __init__(self, embed_dim: int, num_heads: int) -> None:
        super().__init__()
        if embed_dim % num_heads != 0:
            raise ValueError("embed_dim must be divisible by num_heads")
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        self.qkv = nn.Conv1d(embed_dim, 3 * embed_dim, kernel_size=1)
        self.output = nn.Conv1d(embed_dim, embed_dim, kernel_size=1)

    def forward(self, x: Tensor) -> Tensor:
        batch, _, steps = x.shape
        qkv = self.qkv(x).reshape(batch, 3, self.num_heads, self.head_dim, steps)
        query, key, value = qkv.unbind(dim=1)
        query = query.transpose(-2, -1)
        key = key.transpose(-2, -1)
        value = value.transpose(-2, -1)
        attended = F.scaled_dot_product_attention(query, key, value, is_causal=True)
        attended = attended.transpose(-2, -1).contiguous().reshape(batch, self.embed_dim, steps)
        return self.output(attended)


class ConvFeedForward(nn.Module):
    """Feed-forward cell implemented with causal Conv1d projections."""

    def __init__(self, embed_dim: int, ratio: int, kernel_size: int, activation: str) -> None:
        super().__init__()
        hidden_dim = embed_dim * ratio
        self.kernel_size = kernel_size
        self.input = nn.Conv1d(embed_dim, hidden_dim, kernel_size=kernel_size)
        self.output = nn.Conv1d(hidden_dim, embed_dim, kernel_size=1)
        self.activation = activation

    def forward(self, x: Tensor) -> Tensor:
        if self.kernel_size > 1:
            x = F.pad(x, (self.kernel_size - 1, 0))
        x = self.input(x)
        x = F.gelu(x) if self.activation == "gelu" else F.silu(x)
        return self.output(x)


class ConvTransformerBlock(nn.Module):
    def __init__(self, embed_dim: int, spec: BlockSpec) -> None:
        super().__init__()
        self.attention_norm = ChannelLayerNorm(embed_dim)
        self.attention = ConvSelfAttention(embed_dim, spec.num_heads)
        self.ffn_norm = ChannelLayerNorm(embed_dim)
        self.ffn = ConvFeedForward(
            embed_dim,
            spec.ffn_ratio,
            spec.ffn_kernel_size,
            spec.activation,
        )

    def forward(self, x: Tensor) -> Tensor:
        x = x + self.attention(self.attention_norm(x))
        return x + self.ffn(self.ffn_norm(x))


class ConvTransformerLM(nn.Module):
    """A 4-10 layer causal Transformer with Conv1d instead of nn.Linear."""

    def __init__(self, spec: ArchitectureSpec) -> None:
        super().__init__()
        spec.validate()
        self.spec = spec
        self.token_embedding = nn.Embedding(spec.vocab_size, spec.embed_dim)
        self.position_embedding = nn.Embedding(spec.max_seq_len, spec.embed_dim)
        self.blocks = nn.ModuleList(
            ConvTransformerBlock(spec.embed_dim, block_spec) for block_spec in spec.blocks
        )
        self.final_norm = ChannelLayerNorm(spec.embed_dim)
        self.lm_head = nn.Conv1d(spec.embed_dim, spec.vocab_size, kernel_size=1, bias=False)

    def forward(self, token_ids: Tensor) -> Tensor:
        if token_ids.ndim != 2:
            raise ValueError("token_ids must have shape [batch, time]")
        _, steps = token_ids.shape
        if steps > self.spec.max_seq_len:
            raise ValueError("sequence length exceeds max_seq_len")
        positions = torch.arange(steps, device=token_ids.device)
        x = self.token_embedding(token_ids) + self.position_embedding(positions)[None, :, :]
        x = x.transpose(1, 2)
        for block in self.blocks:
            x = block(x)
        logits = self.lm_head(self.final_norm(x))
        return logits.transpose(1, 2)
