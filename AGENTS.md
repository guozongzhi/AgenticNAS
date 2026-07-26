# Repository Guidelines

## Project Structure & Module Organization

`demos/agentic_nas_demo/` contains the runnable reference package. Keep its implementation, `examples/`, `tests/`, and ignored `outputs/` together. The Conv1d Transformer lives in `model.py`, architecture mutations in `search_space.py`, objective/Pareto logic in `pareto.py`, and the Agent JSON contract in `agent.py`.

Keep architecture material in `docs/design/`, integration guides in `docs/guides/`, and paper notes in `research/papers/`. New research runs belong in `experiments/YYYYMMDD-short-topic/`, with experiment-specific `src/`, `tests/`, and ignored `outputs/` directories.

## AgenticNAS Research Focus

This is a clean-room reference for LLM-guided, multi-objective NAS of 4–10-layer Conv1d Transformers. Preserve the evolutionary Pareto baseline and compare Agent proposals under identical candidate, training, GPU, and LLM budgets. Treat `quality_proxy` and `latency_proxy_ms` as control-flow placeholders only; research claims require real measurements. Compare native/random mutation, stateless LLM, and memory-aware policies. Save observation/action/result traces and report hypervolume, action validity, duplication rate, and seed variance.

## Build, Test, and Development Commands

```bash
PYTHONPATH=demos python3 -m unittest discover -s demos/agentic_nas_demo/tests -v
PYTHONPATH=demos python3 -m agentic_nas_demo --iterations 3
python3 -m compileall -q demos/agentic_nas_demo
```

The first command runs the complete test suite. The second runs the provider-free Pareto-search demo and writes replayable Agent observations/actions. The last command catches import and syntax errors without creating a package build. PyTorch 2.0+ and Python 3.10+ are required.

## Coding Style & Naming Conventions

Use four-space indentation, type hints for functions, and `dataclass` objects for serializable search state. Use `snake_case` for functions, fields, modules, and JSON keys; use `PascalCase` for classes (for example, `ArchitectureSpec`). Keep architecture changes declarative: an Agent emits a `MutationAction`, never Python model code. Do not introduce `nn.Linear` into the Conv1d Transformer path. No formatter or linter is configured; match surrounding code and order imports as standard library, third party, then local.

## Testing Guidelines

Use `unittest` and name tests `test_<behavior>`. Keep each test beside its Demo or experiment. Cover valid/rejected mutations, 4/10-layer boundaries, model output shape, Pareto dominance, and replayable traces. Add a regression test for every search constraint or JSON-schema change.

## Commit & Pull Request Guidelines

The existing history uses concise imperative subjects: `Add clean-room Agentic NAS demo`. Follow the same pattern, e.g. `Add latency evaluator` or `Validate Agent actions`. Keep commits focused. PRs should state the search behavior changed, the affected objectives/schema, validation commands, and any compatibility impact on saved traces. Do not commit API keys, internal architecture details, or `outputs/` artifacts.
