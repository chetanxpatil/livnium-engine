from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from livnium_engine import explore_random_local  # noqa: E402


def main() -> None:
    N = 5
    steps = 10_000

    # 5 independent runs with different seeds (but fixed init_seed to keep comparable)
    init_seed = 1
    runs = []
    for seed in range(5):
        runs.append(explore_random_local(N, steps, seed=seed, init_seed=init_seed))

    print({
        "N": N,
        "steps": steps,
        "init_seed": init_seed,
        "runs": runs,
        "min_unique": min(r["unique_state_count"] for r in runs),
        "max_unique": max(r["unique_state_count"] for r in runs),
        "avg_unique": sum(r["unique_state_count"] for r in runs) / len(runs),
        "min_entropy_bits": min(r["entropy_bits"] for r in runs),
        "max_entropy_bits": max(r["entropy_bits"] for r in runs),
        "avg_entropy_bits": sum(r["entropy_bits"] for r in runs) / len(runs),
    })


if __name__ == "__main__":
    main()
