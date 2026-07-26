import json
from pathlib import Path
import random
import tempfile
import unittest

import torch
from torch import nn

from agentic_nas_demo.agent import CallableJsonAgent
from agentic_nas_demo.model import ConvTransformerLM
from agentic_nas_demo.pareto import Evaluation, pareto_frontier
from agentic_nas_demo.search import run_search
from agentic_nas_demo.search_space import (
    ArchitectureSpec,
    BlockSpec,
    MAX_DEPTH,
    MIN_DEPTH,
    apply_action,
    random_action,
    random_spec,
)


class ModelTests(unittest.TestCase):
    def test_forward_and_no_linear_layers(self) -> None:
        block = BlockSpec(num_heads=4, ffn_ratio=2, ffn_kernel_size=3, activation="gelu")
        spec = ArchitectureSpec(embed_dim=64, blocks=(block,) * MIN_DEPTH, max_seq_len=16)
        model = ConvTransformerLM(spec)
        tokens = torch.randint(0, spec.vocab_size, (2, 12))
        self.assertEqual(model(tokens).shape, (2, 12, spec.vocab_size))
        self.assertFalse(any(isinstance(module, nn.Linear) for module in model.modules()))


class SearchSpaceTests(unittest.TestCase):
    def test_random_specs_and_actions_stay_valid(self) -> None:
        rng = random.Random(3)
        for _ in range(20):
            spec = random_spec(rng)
            self.assertTrue(MIN_DEPTH <= spec.depth <= MAX_DEPTH)
            child = apply_action(spec, random_action(spec, rng))
            child.validate()
            self.assertNotEqual(spec.arch_id, child.arch_id)

    def test_json_round_trip(self) -> None:
        spec = random_spec(random.Random(11))
        restored = ArchitectureSpec.from_dict(json.loads(json.dumps(spec.to_dict())))
        self.assertEqual(spec, restored)
        self.assertEqual(spec.arch_id, restored.arch_id)


class ParetoTests(unittest.TestCase):
    def test_frontier_removes_dominated_candidate(self) -> None:
        evaluations = [
            Evaluation("a", quality_proxy=0.8, params_m=1.0, latency_proxy_ms=1.0),
            Evaluation("b", quality_proxy=0.7, params_m=1.2, latency_proxy_ms=1.1),
            Evaluation("c", quality_proxy=0.9, params_m=2.0, latency_proxy_ms=1.5),
        ]
        self.assertEqual([item.arch_id for item in pareto_frontier(evaluations)], ["a", "c"])


class SearchTests(unittest.TestCase):
    def test_search_writes_replayable_trace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_search(
                seed=5,
                initial_population=3,
                iterations=1,
                proposals_per_iteration=2,
                trace_dir=directory,
            )
            self.assertGreaterEqual(len(result.evaluations), 3)
            self.assertTrue(result.frontier_ids)
            self.assertTrue(Path(directory, "iteration_01_observation.json").exists())
            self.assertTrue(Path(directory, "iteration_01_actions.json").exists())
            self.assertTrue(Path(directory, "search_result.json").exists())

    def test_callable_json_agent_uses_the_same_search_contract(self) -> None:
        def completion(request: dict) -> str:
            parent = request["pareto_frontier"][0]
            block = parent["architecture"]["blocks"][0]
            new_ratio = 3 if block["ffn_ratio"] != 3 else 4
            return json.dumps(
                {
                    "actions": [
                        {
                            "parent_id": parent["evaluation"]["arch_id"],
                            "level": "cell",
                            "target_index": 0,
                            "field": "ffn_ratio",
                            "value": new_ratio,
                        }
                    ]
                }
            )

        result = run_search(
            policy=CallableJsonAgent(completion),
            seed=13,
            initial_population=3,
            iterations=1,
            proposals_per_iteration=1,
        )
        self.assertEqual(len(result.evaluations), 4)
        self.assertEqual(result.rejected_actions, 0)


if __name__ == "__main__":
    unittest.main()
