# Repository Guidelines

## Project Structure & Module Organization

`demos/agentic_nas_demo/` contains the runnable NAS reference package. `demos/llm_paper_analysis/` prepares page-labeled local PDF evidence for Codex; it must not require another LLM API. Keep each Demo's implementation, `examples/`, `tests/`, and ignored `outputs/` together.

Keep architecture material in `docs/design/`, integration guides in `docs/guides/`, and paper notes in `research/papers/`. New research runs belong in `experiments/YYYYMMDD-short-topic/`, with experiment-specific `src/`, `tests/`, and ignored `outputs/` directories.

## AgenticNAS Research Focus

This is a clean-room reference for LLM-guided, multi-objective NAS of 4–10-layer Conv1d Transformers. Preserve the evolutionary Pareto baseline and compare Agent proposals under identical candidate, training, GPU, and LLM budgets. Treat `quality_proxy` and `latency_proxy_ms` as control-flow placeholders only; research claims require real measurements. Compare native/random mutation, stateless LLM, and memory-aware policies. Save observation/action/result traces and report hypervolume, action validity, duplication rate, and seed variance.

## Independent NAS and HPO Tracks

Treat `LLM × NAS` and `LLM × HPO` as independent research topics until each has a reproducible baseline:

- NAS changes architecture variables such as depth, width, block/cell/op, operators, and connectivity. Keep the training recipe, data split, training budget, and evaluator fixed. Compare random/native mutation, evolutionary NAS, stateless LLM, and memory-aware LLM under matched budgets.
- HPO changes the training recipe of a fixed architecture, such as learning rate, weight decay, batch size, dropout, optimizer, warmup, schedule, augmentation, and epochs. Keep depth, width, heads, operators, connectivity, data split, and final evaluator fixed. Compare random search, TPE, CMA-ES, pure LLM proposals, and an LLM-plus-classical hybrid.
- Do not add joint architecture/recipe search, NAS-candidate HPO reranking, a shared NAS/HPO archive, shared rewards, joint Pareto objectives, or a manager that coordinates both tracks. Record these only as future work after both tracks have budget-matched results with at least three seeds.
- Do not transfer claims across tracks. A mixed search space containing structural fields is not evidence for the repository's training-only HPO track; label it `mixed-search-space` and use it only as adjacent methodological evidence.

For HPO comparisons, use attempted trials as the primary search budget, give every trial the same sample/token and wall-time caps, count failed trials, and report actual GPU and LLM costs separately. Record best-so-far, regret, invalid/OOM/divergence rates, and the exact model, prompt, sampling, and seed settings.

## Paper Evidence and Status

Use search results only to discover papers. Support research claims with the official paper, proceedings page, author repository, or other primary source. Deduplicate by normalized title plus DOI/arXiv ID.

- `inbox` means collected but not read; `codex_draft` means a page-labeled draft awaiting human verification; only `retained` or `reproduced` notes may support stable related-work claims.
- Store original notes in `research/papers/parsed/`, link them from `research/papers/INDEX.md`, and keep ignored PDF reading copies plus page count and SHA-256 in `research/papers/pdfs/README.md`.
- Every parsed note must distinguish the search object, fixed variables, Agent loop, baselines, trial/training/GPU/LLM budgets, failure handling, evidence locators, and generalization limits.
- Do not present paper-reported numbers as repository results. If a table, figure, source version, or comparison budget has not been checked, mark the gap explicitly instead of inferring a value.

## Build, Test, and Development Commands

```bash
PYTHONPATH=demos python3 -m unittest discover -s demos/agentic_nas_demo/tests -v
PYTHONPATH=demos python3 -m agentic_nas_demo --iterations 3
PYTHONPATH=demos/llm_paper_analysis python3 -m unittest discover -s demos/llm_paper_analysis/tests -v
python3 -m compileall -q demos/agentic_nas_demo demos/llm_paper_analysis
```

The first and third commands run each Demo's tests. The second runs the provider-free Pareto search. The last command catches import and syntax errors. Python 3.10+ and PyTorch 2.0+ are required; paper extraction additionally needs `pypdf`, PyMuPDF, or Poppler's `pdftotext`.

## Coding Style & Naming Conventions

Use four-space indentation, type hints for functions, and `dataclass` objects for serializable search state. Use `snake_case` for functions, fields, modules, and JSON keys; use `PascalCase` for classes (for example, `ArchitectureSpec`). Keep architecture changes declarative: an Agent emits a `MutationAction`, never Python model code. Do not introduce `nn.Linear` into the Conv1d Transformer path. No formatter or linter is configured; match surrounding code and order imports as standard library, third party, then local.

## Testing Guidelines

Use `unittest` and name tests `test_<behavior>`. Keep each test beside its Demo or experiment. Cover valid/rejected mutations, 4/10-layer boundaries, model output shape, Pareto dominance, and replayable traces. Add a regression test for every search constraint or JSON-schema change.

## Commit & Pull Request Guidelines

The existing history uses concise imperative subjects: `Add clean-room Agentic NAS demo`. Follow the same pattern, e.g. `Add latency evaluator` or `Validate Agent actions`. Keep commits focused. PRs should state the search behavior changed, the affected objectives/schema, validation commands, and any compatibility impact on saved traces. Do not commit API keys, internal architecture details, or `outputs/` artifacts.
