from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from livnium_engine import explore_random  # noqa: E402


def main() -> None:
    print(explore_random(3, 10_000, seed=0, init_seed=1))
    print(explore_random(5, 10_000, seed=0, init_seed=1))


if __name__ == "__main__":
    main()
