from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt

# Allow running as a standalone script from repo root.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from livnium_engine.energy import home_distance_smooth_energy, neighbor_disagreement_energy  # noqa: E402
from livnium_engine.explorer import explore_anneal_local  # noqa: E402


@dataclass(frozen=True)
class Weights:
    neighbor: float = 1.0
    home: float = 0.2


def make_energy_fn(weights: Weights):
    def energy(engine) -> float:
        return weights.neighbor * float(neighbor_disagreement_energy(engine)) + weights.home * float(
            home_distance_smooth_energy(engine)
        )

    return energy


def exp_cooling(T0: float, Tmin: float, steps: int):
    if steps <= 0:
        raise ValueError("steps must be > 0")
    if T0 < 0 or Tmin < 0:
        raise ValueError("temperatures must be >= 0")
    if Tmin > T0:
        raise ValueError("Tmin must be <= T0")

    # Exponential schedule: T(t) = T0 * r^t, r chosen so T(steps)=Tmin.
    if Tmin == 0:
        r = 0.0
    else:
        r = (Tmin / T0) ** (1.0 / steps) if T0 > 0 else 0.0

    def schedule(step: int) -> float:
        if step <= 0:
            return T0
        if step >= steps:
            return Tmin
        return T0 * (r**step)

    return schedule


def plot_convergence(energies_by_trial: list[list[float]], outpath: Path) -> None:
    # Align lengths (should be steps+1). If not, truncate to min.
    L = min(len(e) for e in energies_by_trial)
    xs = list(range(L))
    mean = []
    std = []
    for t in range(L):
        vals = [e[t] for e in energies_by_trial]
        m = sum(vals) / len(vals)
        v = sum((x - m) ** 2 for x in vals) / len(vals)
        mean.append(m)
        std.append(math.sqrt(v))

    plt.figure(figsize=(8, 4.5))
    plt.plot(xs, mean, label="mean E(t)")
    lo = [m - s for m, s in zip(mean, std)]
    hi = [m + s for m, s in zip(mean, std)]
    plt.fill_between(xs, lo, hi, alpha=0.25, label="±1 std")
    plt.xlabel("step")
    plt.ylabel("energy")
    plt.title("Anneal convergence (mean ± std)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


def plot_final_energy_hist(final_E: list[float], outpath: Path) -> None:
    plt.figure(figsize=(6, 4.5))
    plt.hist(final_E, bins=12)
    plt.xlabel("final energy")
    plt.ylabel("count")
    plt.title("Final energy distribution")
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


def plot_basin_counts(final_hashes: list[str], outpath: Path, top_k: int = 12) -> None:
    counts = Counter(final_hashes)
    items = counts.most_common(top_k)
    labels = [h[:8] for h, _ in items]
    ys = [c for _, c in items]

    plt.figure(figsize=(8, 4.5))
    plt.bar(range(len(items)), ys)
    plt.xticks(range(len(items)), labels, rotation=45, ha="right")
    plt.ylabel("trials")
    plt.title(f"Basin counts by final hash (top {top_k})")
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=5)
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--T0", type=float, default=3.0)
    ap.add_argument("--Tmin", type=float, default=0.05)
    ap.add_argument("--outdir", type=Path, default=Path("artifacts/phase3"))
    args = ap.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    weights = Weights(neighbor=1.0, home=0.2)
    energy_fn = make_energy_fn(weights)
    schedule = exp_cooling(args.T0, args.Tmin, args.steps)

    results = []
    energies_by_trial: list[list[float]] = []
    final_E: list[float] = []
    final_hashes: list[str] = []

    for init_seed in range(args.trials):
        r = explore_anneal_local(
            N=args.N,
            steps=args.steps,
            init_seed=init_seed,
            temp_schedule=schedule,
            energy_fn=energy_fn,
        )
        results.append(r)
        energies_by_trial.append(list(map(float, r["energies"])))
        final_E.append(float(r["E_final"]))
        final_hashes.append(str(r["final_hash"]))

    # Save json summary
    summary = {
        "N": args.N,
        "steps": args.steps,
        "trials": args.trials,
        "T0": args.T0,
        "Tmin": args.Tmin,
        "weights": {"neighbor": weights.neighbor, "home": weights.home},
        "final_energy": final_E,
        "basin_counts": Counter(final_hashes),
        "results": results,
    }

    # Counter not json-serializable by default
    summary["basin_counts"] = dict(summary["basin_counts"])  # type: ignore[assignment]

    (args.outdir / "phase3_summary.json").write_text(json.dumps(summary, indent=2))

    plot_final_energy_hist(final_E, args.outdir / "final_energy_hist.png")
    plot_convergence(energies_by_trial, args.outdir / "convergence_mean_std.png")
    plot_basin_counts(final_hashes, args.outdir / "basin_counts.png")

    # Minimal console report
    basin_ct = Counter(final_hashes)
    print(f"Trials: {args.trials}  N={args.N}  steps={args.steps}")
    print(f"Final energy: mean={sum(final_E)/len(final_E):.3f}  min={min(final_E):.3f}  max={max(final_E):.3f}")
    print(f"Distinct basins (final hashes): {len(basin_ct)}")
    for h, c in basin_ct.most_common(5):
        print(f"  {h[:12]}  count={c}")

    print(f"\nWrote: {args.outdir}/phase3_summary.json")
    print(f"Wrote: {args.outdir}/final_energy_hist.png")
    print(f"Wrote: {args.outdir}/convergence_mean_std.png")
    print(f"Wrote: {args.outdir}/basin_counts.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
