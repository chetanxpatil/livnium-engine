from __future__ import annotations

from livnium_engine.core.engine import AxionGridCore


def neighbor_disagreement_energy(engine: AxionGridCore) -> int:
    """Count 6-neighbor *disagreements* between tokens.

    Interpretation:
    - Each token id corresponds to its "home" coordinate in the solved state.
    - For each undirected 6-neighbor edge between lattice sites a~b,
      we ask whether the *home coordinates* of the tokens currently occupying
      a and b are themselves 6-neighbors.

    Energy = number of edges that disagree (0 is best; identity arrangement gives 0).

    Notes:
    - Uses 6-neighbor adjacency in the lattice (Manhattan distance 1).
    - Non-mutating.
    """
    idx_to_coord = engine.coords.index_to_coord
    coord_to_idx = engine.coords.coord_to_index

    # Precompute token -> home coordinate (token is original index).
    # In the identity state, token t sits at index t.
    token_home = idx_to_coord

    E = 0
    # Count each undirected edge once by only looking in +x,+y,+z directions.
    for i, tok in enumerate(engine.grid):
        x, y, z = idx_to_coord[i]
        ha = token_home[tok]
        for dx, dy, dz in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            nb = (x + dx, y + dy, z + dz)
            j = coord_to_idx.get(nb)
            if j is None:
                continue
            hb = token_home[engine.grid[j]]
            # Are home coords 6-neighbors?
            if abs(ha[0] - hb[0]) + abs(ha[1] - hb[1]) + abs(ha[2] - hb[2]) != 1:
                E += 1
    return E


def home_distance_smooth_energy(engine: AxionGridCore) -> float:
    """Smooth "distance-to-home" energy.

    Sum over tokens of squared Euclidean distance between current coordinate and
    the token's home coordinate.

    - 0 is best; identity arrangement gives 0.
    - Non-mutating.
    """
    idx_to_coord = engine.coords.index_to_coord

    token_home = idx_to_coord

    E = 0.0
    for i, tok in enumerate(engine.grid):
        x, y, z = idx_to_coord[i]
        hx, hy, hz = token_home[tok]
        dx = x - hx
        dy = y - hy
        dz = z - hz
        E += float(dx * dx + dy * dy + dz * dz)
    return E
