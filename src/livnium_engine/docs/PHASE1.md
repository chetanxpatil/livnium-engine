# Livnium Engine (AxionGrid)  Phase-1

Implements:
- Odd N cubic lattice coordinate indexing
- State as permutation of tokens over coordinates
- Exactly 24 proper cube rotations (det=+1)
- Deterministic hashing + non-mutating audit
- Random explorer walk

Run tests:
```bash
python -m pytest
```

Run random explorer demo:
```bash
python3 scripts/explore_demo.py
```

Run mixed (global + local) explorer demo:
```bash
python3 scripts/explore_local_demo.py
```

(If you prefer importing directly, use `PYTHONPATH=src`.)
