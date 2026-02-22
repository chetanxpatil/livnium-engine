# PHASE 3 — Energy + Attractors

This phase adds **scalar energy functions** over AxionGrid states and an **energy-guided explorer** (simulated annealing) to probe emergence / attractor basins.

## What shipped

### 1) `livnium_engine.energy`
Location: `src/livnium_engine/energy/`

Two energies are provided (both are **non-mutating** and return **0 for the identity / solved state**):

1. **Neighbor-disagreement energy** (6-neighbor)
   - `neighbor_disagreement_energy(engine) -> int`
   - For each undirected 6-neighbor edge between lattice sites, check whether the *home coordinates* of the two tokens are also 6-neighbors.
   - Energy counts the number of disagreeing edges.

2. **Home-distance smooth energy**
   - `home_distance_smooth_energy(engine) -> float`
   - Sum over tokens of squared Euclidean distance between the token’s current coordinate and its home coordinate.

> Token “home” is derived from the engine convention: token id `t` corresponds to the lattice index `t` in the identity state, so its home coordinate is `engine.coords.index_to_coord[t]`.

### 2) `explore_anneal_local(...)`
Location: `src/livnium_engine/explorer/anneal_local.py`

`explore_anneal_local(N, steps, init_seed, temp_schedule, *, energy_fn=...) -> dict`

- Proposes **random local moves**: `(op_id, center, radius)`
- Accept rule:
  - accept if `ΔE <= 0`
  - else accept with probability `exp(-ΔE / T)`
- Tracks:
  - energy trace `energies[t]`
  - unique states visited, repeats / first repeat step
  - acceptance rate
  - best energy + step
  - final hash (for basin clustering)

**Invariant safety:**
- Uses `engine.inverse_local(...)` to revert rejected proposals.
- Calls `engine.audit()` after any apply / revert.

### 3) Experiments + plots
Location: `scripts/phase3_report.py`

- Runs **20 trials** at `N=5` by default.
- Produces:
  - final energy histogram
  - convergence curves (mean ± std energy vs step)
  - basin counts (clustered by final state hash)

Outputs are written under `artifacts/phase3/`.

## How to run

From repo root:

```bash
python -m scripts.phase3_report
```

Optional flags:

```bash
python -m scripts.phase3_report --steps 4000 --trials 20 --N 5
```

## Notes / next steps

- Energies are intentionally simple and local; they’re meant to be *diagnostic* rather than “true physics”.
- If we want stronger attractor structure, consider:
  - weighting / rescaling energies
  - adding multi-objective annealing or reheating schedules
  - experimenting with only radius=1 vs mixed radii
