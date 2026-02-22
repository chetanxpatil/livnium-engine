from __future__ import annotations

import random

from livnium_engine.core.engine import AxionGridCore


def _visit_entropy(visit_counts: dict[str, int]) -> float:
    """Shannon entropy (bits) of state visit distribution."""
    import math

    total = sum(visit_counts.values())
    if total == 0:
        return 0.0
    h = 0.0
    for c in visit_counts.values():
        p = c / total
        h -= p * math.log2(p)
    return h


def explore_random(N: int, steps: int, seed: int = 0, init_seed: int | None = None) -> dict:
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

    for step in range(1, steps + 1):
        op_id = rng.randrange(24)
        engine.apply(op_id)
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
        "first_repeat_step": first_repeat_step,
        "estimated_cycle_length": cycle_length,
        "unique_state_count": len(first_seen_step),
        "entropy_bits": _visit_entropy(visit_counts),
    }
