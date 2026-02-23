# Phase 4 — Memory & Noise Recovery

Phase‑4 is trying to answer one clean scientific question:

**Do Livnium Engine’s low‑energy basins behave like *memory* — i.e., error‑correcting attractors — under noise?**

Goal (operational): after settling into a low‑energy basin, does the system return to the *same* basin after being perturbed by unguided noise?

This phase adds:

- `LivniumEngineCore.perturb(steps, seed)` — an **energy-agnostic** random local-noise operator.
- `recovery_experiment(...)` — a repeatable experiment that:
  1) anneals into a basin,
  2) perturbs for *k* local moves,
  3) anneals again and checks whether it returns to the original basin.
- `scripts/phase4_report.py` — produces plots and a JSON summary.

## Definitions

- **Basin hash**: `engine.hash()` after annealing (a canonical sha256 hash of `(N, grid)`), used as a basin identifier.

- **Recovery (strict / hash recovery):** after perturbing and re‑annealing, the run is considered recovered if the annealer **re‑hits the exact same basin hash at any time during the re‑anneal window**.
  - Implementation detail: the re‑anneal uses **early stopping** (`stop_hash`) and records `stopped_step`.

- **Recovery window:** the re‑anneal runs for at most `anneal_steps` steps. If the original basin hash is not re‑hit within this window, the trial is marked non‑recovered.

- **Noise magnitude**: `perturb_steps = k` (number of random local moves).

- **Recovery probability**: fraction of trials that recover the same basin.

- **Recovery time:** number of anneal steps until the original basin hash is re‑hit (conditioned on recovery).

- **Energy overshoot:** the maximum energy reached during the re‑anneal minus the basin energy.

- **Stability radius (operational)**: the largest `k` such that `P(recover) >= threshold` (default threshold = 0.5).

## Annealing + energy

Annealing uses `explore_anneal_local()` with an explicit exponential temperature schedule:

- `T0 = 3.0`
- `Tmin = 0.05`
- `anneal_steps = 3000`

Default phase-4 energy is the same weighting used in Phase 3:

- `E = neighbor_disagreement_energy + 0.2 * home_distance_smooth_energy`

## How to run

From repo root:

```bash
python scripts/phase4_report.py --N 5 --trials 25
```

Optional:

- start from randomized initial conditions:

```bash
python scripts/phase4_report.py --N 5 --trials 25 --init-seed 0
```

- change perturb grid (include `0` as a determinism / solver-stability control):

```bash
python scripts/phase4_report.py --perturb 0 1 2 5 10 20 50 100
```

Outputs land in:

- `artifacts/phase4/phase4_summary.json`
- `artifacts/phase4/recovery_curve.png`
- `artifacts/phase4/stability_radius.png`
- `artifacts/phase4/example_trajectories.png`

## Notes / invariants

- `perturb()` uses only **local rotations** and calls `audit()` after each move.
- `explore_anneal_local()` gained optional parameters (`init_grid`, `stop_hash`, `return_hashes`) while keeping existing behavior intact for older callers.
- No hierarchy/coupling work is introduced in this phase.
