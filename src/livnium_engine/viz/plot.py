from __future__ import annotations

from collections.abc import Sequence

import matplotlib.pyplot as plt

from livnium_engine.core.engine import AxionGridCore


def plot_scatter(engine: AxionGridCore, *, ax=None, title: str | None = None):
    """Minimal visualization: 3D scatter of coordinates colored by token id."""
    if ax is None:
        fig = plt.figure()
        ax = fig.add_subplot(111, projection="3d")

    coords: Sequence[tuple[int, int, int]] = engine.coords.index_to_coord
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    zs = [c[2] for c in coords]
    colors = engine.grid

    sc = ax.scatter(xs, ys, zs, c=colors, cmap="viridis", s=30)
    plt.colorbar(sc, ax=ax, shrink=0.7, pad=0.1)

    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.set_title(title or f"Livnium Engine N={engine.N}")
    ax.set_box_aspect((1, 1, 1))
    return ax
