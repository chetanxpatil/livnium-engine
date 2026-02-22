# Livnium Engine (AxionGrid)  Phase-2 — Local Rotation Operators

## What was added

### Local reversible operations
- `AxionGridCore.apply_local(op_id, center, radius)`
  - Rotates *only* the sub-cube region defined by Chebyshev radius around `center`.
  - Tokens outside the region are unchanged.
  - Region must lie fully inside lattice bounds; otherwise raises `ValueError`.
- `AxionGridCore.inverse_local(op_id, center, radius)`
  - Returns `(inverse_op_id, center, radius)`.

### Invariants preserved
`audit()` remains strictly non-mutating (hash in == hash out) and now additionally validates local operations when the last action was local:
- global token permutation validity
- local mapping domain/image in range
- local mapping bijection on the region (`set(domain) == set(image)`, no collisions)
- inverse correctness roundtrip for local operations

### Explorer upgrade
- `explore_random_local(N, steps, seed, init_seed)` performs a mixed walk:
  - 50% probability: global rotation
  - 50% probability: local rotation (radius 1 or 2, with valid random center)
  - tracks unique states, first recurrence estimate, and Shannon entropy (same as Phase-1)

## How to run

```bash
python3 -m pytest
python3 scripts/explore_local_demo.py
python3 scripts/phase2_report.py
```

## Metrics (completion run)

Environment: deterministic PRNG, `init_seed=1`.

Single demo run (`python3 scripts/explore_local_demo.py`):
- `N=5`, `steps=10_000`
- global ops: 5011, local ops: 4989
- unique states: **8796** (≫ 24)
- entropy: **13.036 bits**

5-run aggregate (`python3 scripts/phase2_report.py`, seeds 0..4):
- unique states: min **8723**, max **8829**, avg **8770.8**
- entropy: min **13.020 bits**, max **13.043 bits**, avg **13.030 bits**

Invariant violations: **0** (tests + audits during exploration).
