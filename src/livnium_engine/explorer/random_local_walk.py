from __future__ import annotations

import random

from livnium_engine.core.engine import AxionGridCore
from livnium_engine.explorer.random_walk import _visit_entropy


def _random_valid_local_params(rng: random.Random, engine: AxionGridCore) -> tuple[tuple[int, int, int], int]:
    k = engine.coords.k
    radius = rng.choice([1, 2])
    # Choose center that can support this radius: coordinate components in [-k+radius, k-radius]
    lo = -k + radius
    hi = k - radius
    cx = rng.randint(lo, hi)
    cy = rng.randint(lo, hi)
    cz = rng.randint(lo, hi)
    return (cx, cy, cz), radius


def explore_random_local(N: int, steps: int, seed: int = 0, init_seed: int | None = None) -> dict:
    rng = random.Random(seed)
    engine = AxionGridCore(N)
    if init_seed is not None:
        engine.randomize(init_seed)

    first_seen_step: dict[str, int] = {}
    visit_counts: dict[str, int] = {}

    h0 = engine.hash()
    first_seen_step[h0] = 0
    visit_counts[h0] = 1

    first_repeat_step: int | None = None
    cycle_length: int | None = None

    global_ops = 0
    local_ops = 0

    for step in range(1, steps + 1):
        if rng.random() < 0.5:
            op_id = rng.randrange(24)
            engine.apply(op_id)
            global_ops += 1
        else:
            op_id = rng.randrange(24)
            center, radius = _random_valid_local_params(rng, engine)
            engine.apply_local(op_id, center, radius)
            local_ops += 1

        engine.audit()

        h = engine.hash()
        visit_counts[h] = visit_counts.get(h, 0) + 1
        if first_repeat_step is None and h in first_seen_step:
            first_repeat_step = step
            cycle_length = step - first_seen_step[h]
        else:
            first_seen_step.setdefault(h, step)

    return {
        "N": N,
        "steps": steps,
        "seed": seed,
        "init_seed": init_seed,
        "global_ops": global_ops,
        "local_ops": local_ops,
        "first_repeat_step": first_repeat_step,
        "estimated_cycle_length": cycle_length,
        "unique_state_count": len(first_seen_step),
        "entropy_bits": _visit_entropy(visit_counts),
    }
