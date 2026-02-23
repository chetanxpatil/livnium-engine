from __future__ import annotations

import statistics
from collections import Counter

from livnium_engine.core.engine import LivniumEngineCore
from livnium_engine.energy import home_distance_smooth_energy, neighbor_disagreement_energy
from livnium_engine.explorer.anneal_local import explore_anneal_local


def _default_energy(engine: LivniumEngineCore) -> float:
    # Phase-3 weights (kept fixed for reproducibility across reports)
    return float(neighbor_disagreement_energy(engine)) + 0.2 * float(home_distance_smooth_energy(engine))


def _exp_cooling(T0: float, Tmin: float, steps: int):
    if steps <= 0:
        raise ValueError("steps must be > 0")
    if T0 < 0 or Tmin < 0:
        raise ValueError("temperatures must be >= 0")
    if Tmin > T0:
        raise ValueError("Tmin must be <= T0")

    # Exponential schedule: T(t) = T0 * r^t, r chosen so T(steps)=Tmin.
    if Tmin == 0:
        r = 0.0
    else:
        r = (Tmin / T0) ** (1.0 / steps) if T0 > 0 else 0.0

    def schedule(step: int) -> float:
        if step <= 0:
            return T0
        if step >= steps:
            return Tmin
        return T0 * (r**step)

    return schedule


def _stats(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    v_sorted = sorted(values)
    return {
        "n": len(values),
        "mean": sum(values) / len(values),
        "median": float(statistics.median(v_sorted)),
        "min": float(v_sorted[0]),
        "max": float(v_sorted[-1]),
    }


def recovery_experiment(
    N: int,
    trials: int,
    perturb_steps: int,
    *,
    seed: int = 0,
    init_seed: int | None = None,
) -> dict:
    """Run a basin recovery experiment under unguided local perturbations.

    Per trial:
    - initialize engine (identity, or randomize if init_seed provided)
    - anneal to a low-energy basin using explore_anneal_local
    - snapshot: (hash, energy)
    - apply `perturb_steps` random local moves (no energy guidance)
    - anneal again, stopping early if the original basin hash is recovered
    - record recovery metrics

    Returns aggregate metrics + per-trial details.
    """

    if N < 1:
        raise ValueError("N must be >= 1")
    if trials < 1:
        raise ValueError("trials must be >= 1")
    if perturb_steps < 0:
        raise ValueError("perturb_steps must be >= 0")

    # Keep this explicit (Phase-4 requirement).
    anneal_steps = 3000
    schedule = _exp_cooling(T0=3.0, Tmin=0.05, steps=anneal_steps)

    basin_changes: Counter[tuple[str, str]] = Counter()

    per_trial: list[dict] = []
    recovered_flags: list[bool] = []
    recovery_times: list[float] = []

    final_minus_basin: list[float] = []
    perturbed_minus_basin: list[float] = []
    overshoots: list[float] = []

    for t in range(trials):
        # 1) Init state (grid)
        init_engine = LivniumEngineCore(N)
        if init_seed is not None:
            init_engine.randomize(init_seed + t)
        init_grid = list(init_engine.grid)

        # 2) Anneal into a basin
        a1 = explore_anneal_local(
            N=N,
            steps=anneal_steps,
            init_seed=seed + 10_000 + t,
            temp_schedule=schedule,
            energy_fn=_default_energy,
            init_grid=init_grid,
            return_hashes=False,
        )

        basin_hash = str(a1["final_hash"])
        basin_energy = float(a1["E_final"])
        basin_grid = list(a1["final_grid"])

        # 3) Perturb (unguided)
        noisy = LivniumEngineCore(N)
        noisy.grid = list(basin_grid)
        noisy.last_op_id = None
        noisy.last_action = None
        noisy.audit()
        noisy.perturb(perturb_steps, seed=seed + 20_000 + t)
        E_after_noise = float(_default_energy(noisy))

        # 4) Re-anneal; early stop if we re-hit the same basin hash
        a2 = explore_anneal_local(
            N=N,
            steps=anneal_steps,
            init_seed=seed + 30_000 + t,
            temp_schedule=schedule,
            energy_fn=_default_energy,
            init_grid=list(noisy.grid),
            stop_hash=basin_hash,
            return_hashes=False,
        )

        recovered = bool(a2.get("stopped_step") is not None) or (str(a2["final_hash"]) == basin_hash)
        rec_steps = a2.get("stopped_step")
        final_hash = str(a2["final_hash"])
        final_energy = float(a2["E_final"])

        energies2 = list(map(float, a2["energies"]))
        overshoot = (max(energies2) - basin_energy) if energies2 else 0.0

        basin_changes[(basin_hash, final_hash)] += 1

        recovered_flags.append(recovered)
        if recovered and rec_steps is not None:
            recovery_times.append(float(rec_steps))

        final_minus_basin.append(final_energy - basin_energy)
        perturbed_minus_basin.append(E_after_noise - basin_energy)
        overshoots.append(float(overshoot))

        per_trial.append(
            {
                "trial": t,
                "basin_hash": basin_hash,
                "basin_energy": basin_energy,
                "E_after_noise": E_after_noise,
                "perturb_steps": perturb_steps,
                "recovered_same_hash": recovered,
                "recovery_steps": rec_steps,
                "final_hash": final_hash,
                "final_energy": final_energy,
                "energy_overshoot": float(overshoot),
            }
        )

    recovery_rate = sum(1 for x in recovered_flags if x) / len(recovered_flags)

    basin_changes_dict = {f"{a[:12]}->{b[:12]}": int(c) for (a, b), c in basin_changes.items()}

    return {
        "N": N,
        "trials": trials,
        "perturb_steps": perturb_steps,
        "anneal_steps": anneal_steps,
        "temperature": {"T0": 3.0, "Tmin": 0.05, "schedule": "exp"},
        "energy": {"neighbor": 1.0, "home": 0.2},
        "recovery_rate": recovery_rate,
        "recovery_time": {
            "mean": float(sum(recovery_times) / len(recovery_times)) if recovery_times else None,
            "median": float(statistics.median(recovery_times)) if recovery_times else None,
            "n": len(recovery_times),
        },
        "energy_deltas": {
            "final_minus_basin": _stats(final_minus_basin),
            "perturbed_minus_basin": _stats(perturbed_minus_basin),
            "overshoot": _stats(overshoots),
        },
        "basin_changes": basin_changes_dict,
        "per_trial": per_trial,
    }
