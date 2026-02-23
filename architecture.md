# Livnium Engine — Architecture

This document is a factual map of what exists in the repo today: the core substrate, the invariants, and the experiment pipeline built across Phase‑1 → Phase‑4.

Repo: https://github.com/chetanxpatil/livnium-engine

---

## 0) Design principles (non-negotiable)

- **Determinism:** seeded randomness only; identical seeds → identical behavior.
- **Reversibility:** every operation has an inverse; inverse roundtrips restore exact state.
- **Permutation state:** the lattice state is always a permutation of tokens (no creation/destruction).
- **Strict auditing:** `audit()` is **non-mutating** (hash-in == hash-out) and hard-fails on invariant violations.

---

## 1) Core model

### 1.1 Lattice / coordinates
- Lattice size: odd `N >= 3`.
- Coordinate domain: `x,y,z ∈ [-k, +k]` with `k = N//2`.
- Canonical indexing: lexicographic `(x, y, z)`.

Implementation:
- `src/livnium_engine/core/coords.py`
  - `Coords` structure
  - `index_to_coord` and `coord_to_index`

### 1.2 State representation
- Token set: `{0..N^3-1}`.
- State: `grid: list[int]` length `N^3`.
  - `grid[i]` = token at coordinate `index_to_coord[i]`.

### 1.3 Hashing
- Canonical bytes: little-endian uint32 `[N] + grid`.
- Hash: `sha256(canonical_bytes).hexdigest()`.

---

## 2) Operations

### 2.1 Phase‑1: 24 proper cube rotations (global)
- Exactly the 24 proper rotations (det=+1).
- Precomputed index maps:
  - `rot_index_map[op_id][old_i] -> new_i` (bijection).
- Apply semantics:
  - `new_grid[new_i] = old_grid[old_i]`.

Implementation:
- `src/livnium_engine/core/rotations.py`
- `src/livnium_engine/core/engine.py` (`apply`, `inverse_op`)

### 2.2 Phase‑2: local reversible rotations
- `apply_local(op_id, center, radius)` rotates only a Chebyshev sub-cube:
  - region = `{(x,y,z) | max(|x-cx|,|y-cy|,|z-cz|) <= radius}`
- Region must be fully in-bounds.
- Tokens outside the region remain unchanged.

Implementation:
- `src/livnium_engine/core/engine.py`
  - `apply_local`
  - `inverse_local`

### 2.3 Phase‑4: unguided perturbation (noise)
- `perturb(steps, seed)` applies random local moves (no energy guidance), auditing each step.

Implementation:
- `src/livnium_engine/core/engine.py`

---

## 3) Auditing / invariants

### 3.1 `audit()` (strictly non-mutating)
`audit()` must leave the engine exactly as found:
- snapshot canonical bytes / hash
- perform checks
- restore any temporary state
- verify hash unchanged

Checks include:
- grid is a valid permutation
- mapping bijections (global or local context)
- inverse correctness (roundtrip restores exact bytes)

Implementation:
- `src/livnium_engine/core/engine.py`

Rotation group closure sanity:
- Compose tables for the 24 rotations to verify closure.

Implementation:
- `src/livnium_engine/invariants/rotation_group.py`

---

## 4) Exploration pipeline (experiments)

### 4.1 Phase‑1 explorer: global random walk
- `explore_random(N, steps, seed, init_seed)`.

Implementation:
- `src/livnium_engine/explorer/random_walk.py`

### 4.2 Phase‑2 explorer: mixed global+local random walk
- `explore_random_local(N, steps, seed, init_seed)`.
- 50/50 global vs local step choice.
- Tracks recurrence + entropy (visit distribution entropy).

Implementation:
- `src/livnium_engine/explorer/random_local_walk.py`

### 4.3 Phase‑3: energy + annealing (attractors)
Energy functions:
- Neighbor disagreement energy (6-neighbor edge check).
- Home-distance smooth energy (sum of squared distances to token home coords).

Implementation:
- `src/livnium_engine/energy/energies.py`

Annealing explorer:
- `explore_anneal_local(...)`
  - proposes random local move
  - Metropolis accept: accept if `ΔE<=0` else accept with `exp(-ΔE/T)`
  - on reject, uses inverse local op to revert
  - audits after apply/revert
  - returns energy trace + basin hash

Implementation:
- `src/livnium_engine/explorer/anneal_local.py`

Reporting script:
- `scripts/phase3_report.py`
  - runs multiple trials
  - writes plots + `phase3_summary.json`
  - output directory: `artifacts/phase3/`

### 4.4 Phase‑4: memory & noise recovery
Core question: after settling into a basin, does the system return to the *same basin hash* after perturbation?

Recovery experiment:
- `recovery_experiment(N, trials, perturb_steps, seed=0, init_seed=None)`
  - anneal → basin hash
  - perturb k steps
  - re-anneal with early-stop on original hash
  - metrics: recovery rate, recovery time, energy overshoot, basin changes

Implementation:
- `src/livnium_engine/explorer/recovery.py`

Reporting script:
- `scripts/phase4_report.py`
  - runs a perturbation sweep and produces:
    - `phase4_summary.json`
    - `recovery_curve.png`
    - `stability_radius.png`
    - `example_trajectories.png`
  - output directory: `artifacts/phase4/`

Docs:
- `docs/PHASE4.md`

---

## 5) Visualization

Minimal viz (human inspection):
- 3D scatter plot of tokens / coordinates.

Implementation:
- `src/livnium_engine/viz/plot.py`

---

## 6) Tests and trust

Unit tests cover:
- 24 rotations are proper (det=+1) and closed under composition
- bijections for index maps
- inverse correctness (global + local)
- local ops do not affect outside-region tokens
- audit non-mutating behavior

Location:
- `tests/`

CI:
- GitHub Actions runs tests on Python 3.11 / 3.12.
- Workflow: `.github/workflows/tests.yml`

---

## 7) Packaging, naming, and repo hygiene

- Python import package: `livnium_engine`
- Primary public core class: `LivniumEngineCore`
- Back-compat alias: `AxionGridCore`

Key repo files:
- `README.md`
- `LICENSE` (research-only)
- `pyproject.toml`

---

## 8) Reproducibility notes

- Most scripts bootstrap `sys.path` to allow running from repo root without installation.
- For a cleaner developer workflow, you can also do:

```bash
pip install -e .
```

---

## 9) Phase summary (what we built)

- **Phase‑1:** deterministic reversible global rotation engine + strict non-mutating audit.
- **Phase‑2:** local reversible operators + mixed local/global exploration; state space expands.
- **Phase‑3:** energy functions + annealing explorer; attractors/basins become measurable.
- **Phase‑4:** perturb + recovery experiments; basin stability vs noise (memory hypothesis test).
