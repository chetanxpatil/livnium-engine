from __future__ import annotations

import itertools

Matrix3 = tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]


def det3(m: Matrix3) -> int:
    (a, b, c), (d, e, f), (g, h, i) = m
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def mat_mul(a: Matrix3, b: Matrix3) -> Matrix3:
    # integer 3x3 multiply
    out = []
    for r in range(3):
        row = []
        for c in range(3):
            s = 0
            for k in range(3):
                s += a[r][k] * b[k][c]
            row.append(s)
        out.append(tuple(row))
    return (out[0], out[1], out[2])  # type: ignore[return-value]


def mat_vec(m: Matrix3, v: tuple[int, int, int]) -> tuple[int, int, int]:
    x, y, z = v
    return (
        m[0][0] * x + m[0][1] * y + m[0][2] * z,
        m[1][0] * x + m[1][1] * y + m[1][2] * z,
        m[2][0] * x + m[2][1] * y + m[2][2] * z,
    )


def transpose(m: Matrix3) -> Matrix3:
    return (
        (m[0][0], m[1][0], m[2][0]),
        (m[0][1], m[1][1], m[2][1]),
        (m[0][2], m[1][2], m[2][2]),
    )


def generate_proper_rotations() -> list[Matrix3]:
    """Generate the 24 proper cube rotations as signed axis permutations with det=+1."""
    mats: list[Matrix3] = []
    axes = [
        (1, 0, 0),
        (0, 1, 0),
        (0, 0, 1),
    ]

    # A signed axis permutation matrix has exactly one non-zero entry (+/-1) per row/col.
    # Construct by choosing a permutation of basis vectors for rows and signs per row.
    for perm in itertools.permutations(axes, 3):
        for signs in itertools.product([1, -1], repeat=3):
            rows = []
            for r in range(3):
                px, py, pz = perm[r]
                s = signs[r]
                rows.append((s * px, s * py, s * pz))
            m = (rows[0], rows[1], rows[2])  # type: ignore[assignment]
            if det3(m) == 1:
                mats.append(m)

    # Ensure uniqueness and stable ordering.
    uniq = list(dict.fromkeys(mats))
    if len(uniq) != 24:
        raise AssertionError(f"expected 24 proper rotations, got {len(uniq)}")

    # Deterministic ordering: lexicographic over rows.
    uniq.sort()
    return uniq


ROTATIONS: list[Matrix3] = generate_proper_rotations()
ROTATION_INDEX: dict[Matrix3, int] = {m: i for i, m in enumerate(ROTATIONS)}


def inverse_rotation_index(op_id: int) -> int:
    m = ROTATIONS[op_id]
    inv = transpose(m)  # orthonormal => inverse == transpose
    return ROTATION_INDEX[inv]
