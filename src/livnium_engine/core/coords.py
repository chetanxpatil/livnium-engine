from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Coords:
    N: int
    k: int
    index_to_coord: list[tuple[int, int, int]]
    coord_to_index: dict[tuple[int, int, int], int]


def build_coords(N: int) -> Coords:
    if N < 3 or (N % 2) != 1:
        raise ValueError("N must be odd and >= 3")
    k = N // 2
    coords = [(x, y, z) for x in range(-k, k + 1) for y in range(-k, k + 1) for z in range(-k, k + 1)]
    coords.sort(key=lambda t: (t[0], t[1], t[2]))
    index_to_coord = coords
    coord_to_index = {c: i for i, c in enumerate(index_to_coord)}
    if len(coord_to_index) != N**3:
        raise AssertionError("coordinate indexing mismatch")
    return Coords(N=N, k=k, index_to_coord=index_to_coord, coord_to_index=coord_to_index)
