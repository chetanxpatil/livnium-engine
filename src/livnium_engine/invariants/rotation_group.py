from __future__ import annotations

from dataclasses import dataclass

from livnium_engine.core.rotations import ROTATIONS, ROTATION_INDEX, Matrix3, mat_mul


@dataclass(frozen=True, slots=True)
class RotationGroup:
    compose_table: list[list[int]]


def build_compose_table() -> RotationGroup:
    table: list[list[int]] = [[-1] * 24 for _ in range(24)]
    for a in range(24):
        for b in range(24):
            # Apply b then a (matrix multiplication for coordinate transforms)
            cmat: Matrix3 = mat_mul(ROTATIONS[a], ROTATIONS[b])
            try:
                c = ROTATION_INDEX[cmat]
            except KeyError as e:
                raise AssertionError("rotation closure violated") from e
            table[a][b] = c
    return RotationGroup(compose_table=table)
