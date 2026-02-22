from __future__ import annotations

import random

import pytest

from livnium_engine.core.engine import AxionGridCore
from livnium_engine.core.rotations import ROTATIONS, ROTATION_INDEX, det3, transpose
from livnium_engine.invariants.rotation_group import build_compose_table


def test_rotations_count_and_det():
    assert len(ROTATIONS) == 24
    assert len(set(ROTATIONS)) == 24
    for m in ROTATIONS:
        assert det3(m) == 1


def test_rotation_inverses_exist():
    for i, m in enumerate(ROTATIONS):
        inv = transpose(m)
        assert inv in ROTATION_INDEX
        j = ROTATION_INDEX[inv]
        # inv(inv(m)) == m
        assert ROTATIONS[j] == inv
        assert ROTATIONS[ROTATION_INDEX[transpose(inv)]] == m


@pytest.mark.parametrize("N", [3, 5])
def test_index_maps_bijection(N: int):
    eng = AxionGridCore(N)
    n3 = N**3
    for op in range(24):
        mp = eng.rot_index_map[op]
        assert len(mp) == n3
        assert set(mp) == set(range(n3))


@pytest.mark.parametrize("N", [3, 5])
def test_apply_inverse_roundtrip_random_states(N: int):
    eng = AxionGridCore(N)
    rng = random.Random(123)
    for _ in range(25):
        eng.randomize(rng.randrange(1_000_000))
        before = eng.hash()
        for op in range(24):
            eng.apply(op)
            inv = eng.inverse_op(op)
            eng.apply(inv)
            assert eng.hash() == before


def test_rotation_composition_closure():
    grp = build_compose_table()
    # Verify table entries are all valid ops.
    for a in range(24):
        for b in range(24):
            c = grp.compose_table[a][b]
            assert 0 <= c < 24
