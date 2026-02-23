from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence

from livnium_engine.core.engine import AxionGridCore


def _random_valid_local_params(
    rng: random.Random, engine: AxionGridCore
) -> tuple[tuple[int, int, int], int]:
    k = engine.coords.k
    radius = rng.choice([1, 2])
    lo = -k + radius
    hi = k - radius
    cx = rng.randint(lo, hi)
    cy = rng.randint(lo, hi)
    cz = rng.randint(lo, hi)
    return (cx, cy, cz), radius


def _temperature(temp_schedule: float | Sequence[float] | Callable[..., float], step: int) -> float:
    if isinstance(temp_schedule, (int, float)):
        return float(temp_schedule)
    if isinstance(temp_schedule, Sequence):
        if step < 0 or step >= len(temp_schedule):
            # If schedule is short, clamp to last.
            return float(temp_schedule[-1])
        return float(temp_schedule[step])
    # callable
    try:
        return float(temp_schedule(step))
    except TypeError:
        # allow temp_schedule(step,)
        return float(temp_schedule(step))


def explore_anneal_local(
    N: int,
    steps: int,
    init_seed: int,
    temp_schedule: float | Sequence[float] | Callable[..., float],
    *,
    energy_fn: Callable[[AxionGridCore], float] | None = None,
    init_grid: list[int] | None = None,
    stop_hash: str | None = None,
    return_hashes: bool = False,
) -> dict:
    """Simulated annealing over *local* moves.

    Proposal: random (op_id, center, radius) local rotation.

    Accept if ΔE <= 0, else accept with probability exp(-ΔE/T).

    Tracking:
    - energies: E(t)
    - unique_state_count
    - first_repeat_step + repeats
    - best_energy + step of best
    - acceptance_rate

    Invariants:
    - Calls engine.audit() after any applied / reverted move.
    - Uses inverse_local() to revert rejected proposals.
    """

    if energy_fn is None:
        raise ValueError("energy_fn is required for annealing")

    rng = random.Random(init_seed)
    engine = AxionGridCore(N)

    if init_grid is not None:
        if len(init_grid) != N**3:
            raise ValueError("init_grid length mismatch")
        engine.grid = list(init_grid)
        engine.last_op_id = None
        engine.last_action = None
        engine.audit()
    else:
        engine.randomize(init_seed)

    first_seen_step: dict[str, int] = {}
    visit_counts: dict[str, int] = {}

    h0 = engine.hash()
    first_seen_step[h0] = 0
    visit_counts[h0] = 1

    hashes: list[str] | None = [h0] if return_hashes else None

    stopped_step: int | None = 0 if (stop_hash is not None and h0 == stop_hash) else None

    E0 = float(energy_fn(engine))
    energies: list[float] = [E0]

    best_E = E0
    best_step = 0
    last_improve_step = 0

    first_repeat_step: int | None = None
    repeats = 0

    accepted = 0
    proposed = 0

    if stopped_step == 0:
        return {
            "N": N,
            "steps": steps,
            "steps_run": 0,
            "init_seed": init_seed,
            "accepted": accepted,
            "proposed": proposed,
            "acceptance_rate": 0.0,
            "energies": energies,
            "E0": E0,
            "E_final": energies[-1],
            "best_energy": best_E,
            "best_step": best_step,
            "last_improve_step": last_improve_step,
            "last_change_step": 0,
            "unique_state_count": len(first_seen_step),
            "first_repeat_step": first_repeat_step,
            "repeat_visits": repeats,
            "final_hash": engine.hash(),
            "final_grid": list(engine.grid),
            "visit_counts": visit_counts,
            "stopped_step": 0,
            **({"hashes": hashes} if hashes is not None else {}),
        }

    for step in range(1, steps + 1):
        proposed += 1

        op_id = rng.randrange(24)
        center, radius = _random_valid_local_params(rng, engine)

        # propose
        engine.apply_local(op_id, center, radius)
        engine.audit()

        E1 = float(energy_fn(engine))
        E_prev = energies[-1]
        dE = E1 - E_prev

        T = _temperature(temp_schedule, step)
        if T < 0:
            raise ValueError("temperature must be >= 0")

        accept = False
        if dE <= 0:
            accept = True
        else:
            if T == 0:
                accept = False
            else:
                p = math.exp(-dE / T)
                accept = rng.random() < p

        if accept:
            accepted += 1
            energies.append(E1)
            if E1 < best_E:
                best_E = E1
                best_step = step
                last_improve_step = step
        else:
            # revert
            inv_op, inv_center, inv_radius = engine.inverse_local(op_id, center, radius)
            engine.apply_local(inv_op, inv_center, inv_radius)
            engine.audit()
            energies.append(E_prev)

        h = engine.hash()
        if hashes is not None:
            hashes.append(h)

        visit_counts[h] = visit_counts.get(h, 0) + 1
        if h in first_seen_step:
            repeats += 1
            if first_repeat_step is None:
                first_repeat_step = step
        else:
            first_seen_step[h] = step

        if stop_hash is not None and h == stop_hash:
            stopped_step = step
            break

    # crude convergence statistic: last time the energy changed
    last_change_step = 0
    for s in range(1, len(energies)):
        if energies[s] != energies[s - 1]:
            last_change_step = s

    steps_run = int(stopped_step) if stopped_step is not None else steps

    out = {
        "N": N,
        "steps": steps,
        "steps_run": steps_run,
        "init_seed": init_seed,
        "accepted": accepted,
        "proposed": proposed,
        "acceptance_rate": accepted / proposed if proposed else 0.0,
        "energies": energies,
        "E0": E0,
        "E_final": energies[-1],
        "best_energy": best_E,
        "best_step": best_step,
        "last_improve_step": last_improve_step,
        "last_change_step": last_change_step,
        "unique_state_count": len(first_seen_step),
        "first_repeat_step": first_repeat_step,
        "repeat_visits": repeats,
        "final_hash": engine.hash(),
        "final_grid": list(engine.grid),
        "visit_counts": visit_counts,
        "stopped_step": stopped_step,
    }

    if hashes is not None:
        out["hashes"] = hashes

    return out
