from __future__ import annotations

import random

import pytest

from livnium_engine.core.engine import AxionGridCore


@pytest.mark.parametrize("N", [3, 5])
def test_audit_non_mutating(N: int):
    eng = AxionGridCore(N)
    eng.randomize(42)
    eng.apply(0)
    h0 = eng.hash()
    eng.audit()
    assert eng.hash() == h0


@pytest.mark.parametrize("N", [3, 5])
def test_audit_detects_bad_permutation(N: int):
    eng = AxionGridCore(N)
    eng.grid[0] = eng.grid[1]  # collision
    with pytest.raises(AssertionError):
        eng.audit()


@pytest.mark.parametrize("N", [3, 5])
def test_audit_inverse_check_when_last_op_present(N: int):
    eng = AxionGridCore(N)
    eng.randomize(7)
    eng.apply(3)
    eng.audit()  # should pass


@pytest.mark.parametrize("N", [3, 5])
def test_audit_skips_inverse_check_when_no_last_op(N: int):
    eng = AxionGridCore(N)
    eng.randomize(7)
    eng.audit()  # should pass
