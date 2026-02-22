from __future__ import annotations

import random

import pytest

from livnium_engine.core.engine import AxionGridCore


@pytest.mark.parametrize("N", [5])
def test_apply_local_inverse_roundtrip(N: int):
    eng = AxionGridCore(N)
    eng.randomize(123)
    rng = random.Random(0)

    k = eng.coords.k
    for _ in range(50):
        op = rng.randrange(24)
        radius = rng.choice([1, 2])
        # pick center that fits radius
        lo, hi = -k + radius, k - radius
        center = (rng.randint(lo, hi), rng.randint(lo, hi), rng.randint(lo, hi))

        before = eng.hash()
        eng.apply_local(op, center, radius)
        inv_op, c2, r2 = eng.inverse_local(op, center, radius)
        eng.apply_local(inv_op, c2, r2)
        assert eng.hash() == before


@pytest.mark.parametrize("N", [5])
def test_apply_local_keeps_outside_region_unchanged_for_identity_rotation(N: int):
    # Find an op_id that is identity by checking that applying it globally preserves coords.
    eng = AxionGridCore(N)
    # identity op must map all indices to themselves
    identity_ops = [op for op in range(24) if eng.rot_index_map[op] == list(range(N**3))]
    assert len(identity_ops) == 1
    op_id = identity_ops[0]

    eng.randomize(99)
    before = list(eng.grid)

    center = (0, 0, 0)
    radius = 1
    eng.apply_local(op_id, center, radius)
    assert eng.grid == before


@pytest.mark.parametrize("N", [5])
def test_apply_local_does_not_change_outside_region(N: int):
    eng = AxionGridCore(N)
    eng.randomize(2026)

    # choose a clearly-valid region
    center = (0, 0, 0)
    radius = 1

    # pick a non-identity op
    identity_ops = [op for op in range(24) if eng.rot_index_map[op] == list(range(N**3))]
    assert len(identity_ops) == 1
    op_id = next(op for op in range(24) if op != identity_ops[0])

    before = list(eng.grid)
    mapping = eng._local_index_mapping(op_id, center, radius)
    region_indices = set(mapping.keys())  # == set(mapping.values())

    eng.apply_local(op_id, center, radius)

    for i in range(N**3):
        if i not in region_indices:
            assert eng.grid[i] == before[i]


@pytest.mark.parametrize("N", [5])
def test_apply_local_rejects_out_of_bounds(N: int):
    eng = AxionGridCore(N)
    with pytest.raises(ValueError):
        eng.apply_local(0, (0, 0, 0), 0)
    with pytest.raises(ValueError):
        eng.apply_local(0, (999, 0, 0), 1)
    # radius too big for corner
    k = eng.coords.k
    with pytest.raises(ValueError):
        eng.apply_local(0, (k, k, k), 1)


@pytest.mark.parametrize("N", [5])
def test_audit_non_mutating_after_local(N: int):
    eng = AxionGridCore(N)
    eng.randomize(7)
    eng.apply_local(3, (0, 0, 0), 2)
    h0 = eng.hash()
    eng.audit()
    assert eng.hash() == h0
