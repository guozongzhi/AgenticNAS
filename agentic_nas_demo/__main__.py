from __future__ import annotations

import argparse
import json

from .search import run_search


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the clean-room Agentic NAS demo")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--initial-population", type=int, default=6)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--proposals", type=int, default=4)
    parser.add_argument("--trace-dir", default="outputs/demo")
    args = parser.parse_args()

    result = run_search(
        seed=args.seed,
        initial_population=args.initial_population,
        iterations=args.iterations,
        proposals_per_iteration=args.proposals,
        trace_dir=args.trace_dir,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
