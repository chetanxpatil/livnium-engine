from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt

# Allow running as a standalone script from repo root.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from livnium_engine.core.engine import LivniumEngineCore  # noqa: E402
from livnium_engine.energy import home_distance_smooth_energy, neighbor_disagreement_energy  # noqa: E402
from livnium_engine.explorer import explore_anneal_local, recovery_experiment  # noqa: E402


def default_energy(engine: LivniumEngineCore) -> float:
    return float(neighbor_disagreement_energy(engine)) + 0.2 * float(home_distance_smooth_energy(engine))


def exp_cooling(T0: float, Tmin: float, steps: int):
    if steps <= 0:
        raise ValueError("steps must be > 0")
    if T0 < 0 or Tmin < 0:
        raise ValueError("temperatures must be >= 0")
    if Tmin > T0:
        raise ValueError("Tmin must be <= T0")

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


def _set_xscale_for_perturb(xs: list[int]) -> str:
    """Choose a readable x-scale.

    If 0 is present (control point), log-scale is invalid; use symlog.
    """

    return "symlog" if xs and min(xs) <= 0 else "log"


def plot_recovery_curve(xs: list[int], ys: list[float], outpath: Path) -> None:
    plt.figure(figsize=(6.5, 4.2))
    plt.plot(xs, ys, marker="o")

    xscale = _set_xscale_for_perturb(xs)
    if xscale == "symlog":
        plt.xscale("symlog", linthresh=1)
        xlabel = "perturb steps (symlog; includes 0 control)"
    else:
        plt.xscale("log")
        xlabel = "perturb steps (log scale)"

    plt.ylim(-0.02, 1.02)
    plt.xlabel(xlabel)
    plt.ylabel("recovery probability")
    plt.title("Basin recovery vs noise magnitude")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


def plot_stability_radius(xs: list[int], ys: list[float], threshold: float, outpath: Path) -> int | None:
    # radius = max perturb_steps with p(recover) >= threshold
    radius: int | None = None
    for x, y in zip(xs, ys):
        if y >= threshold:
            radius = x

    plt.figure(figsize=(6.5, 4.2))
    plt.plot(xs, ys, marker="o", label="recovery")
    plt.axhline(threshold, linestyle="--", color="gray", label=f"threshold={threshold:.2f}")
    if radius is not None:
        plt.axvline(radius, linestyle=":", color="black", label=f"radius={radius}")

    xscale = _set_xscale_for_perturb(xs)
    if xscale == "symlog":
        plt.xscale("symlog", linthresh=1)
        xlabel = "perturb steps (symlog; includes 0 control)"
    else:
        plt.xscale("log")
        xlabel = "perturb steps (log scale)"

    plt.ylim(-0.02, 1.02)
    plt.xlabel(xlabel)
    plt.ylabel("recovery probability")
    plt.title("Stability radius")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()

    return radius


def plot_example_trajectories(N: int, perturb_steps_list: list[int], outpath: Path, *, seed: int, init_seed: int | None):
    anneal_steps = 3000
    schedule = exp_cooling(3.0, 0.05, anneal_steps)

    plt.figure(figsize=(7.5, 4.5))

    for idx, ps in enumerate(perturb_steps_list):
        # one deterministic example (trial 0)
        init_engine = LivniumEngineCore(N)
        if init_seed is not None:
            init_engine.randomize(init_seed)
        init_grid = list(init_engine.grid)

        a1 = explore_anneal_local(
            N=N,
            steps=anneal_steps,
            init_seed=seed + 10_000,
            temp_schedule=schedule,
            energy_fn=default_energy,
            init_grid=init_grid,
            return_hashes=False,
        )
        basin_hash = str(a1["final_hash"])

        noisy = LivniumEngineCore(N)
        noisy.grid = list(a1["final_grid"])
        noisy.last_action = None
        noisy.last_op_id = None
        noisy.audit()
        noisy.perturb(ps, seed=seed + 20_000)

        a2 = explore_anneal_local(
            N=N,
            steps=anneal_steps,
            init_seed=seed + 30_000,
            temp_schedule=schedule,
            energy_fn=default_energy,
            init_grid=list(noisy.grid),
            stop_hash=basin_hash,
            return_hashes=False,
        )

        energies = list(map(float, a2["energies"]))
        steps_run = int(a2.get("steps_run", len(energies) - 1))
        xs = list(range(len(energies)))
        label = f"k={ps} (run={steps_run})"
        plt.plot(xs, energies, linewidth=1.2, label=label)

        if idx >= 2:
            # keep plot readable
            break

    plt.xlabel("anneal step")
    plt.ylabel("energy")
    plt.title("Example recovery trajectories (re-anneal after perturb)")
    plt.legend()
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=5)
    ap.add_argument("--trials", type=int, default=25)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--init-seed", type=int, default=None)
    ap.add_argument(
        "--perturb",
        type=int,
        nargs="+",
        default=[0, 1, 2, 5, 10, 20, 50, 100],
        help="perturb steps to evaluate (include 0 as a determinism control)",
    )
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--outdir", type=Path, default=Path("artifacts/phase4"))
    args = ap.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    curve = []
    for ps in args.perturb:
        r = recovery_experiment(
            N=args.N,
            trials=args.trials,
            perturb_steps=ps,
            seed=args.seed,
            init_seed=args.init_seed,
        )
        curve.append(r)

    xs = [int(r["perturb_steps"]) for r in curve]
    ys = [float(r["recovery_rate"]) for r in curve]

    summary = {
        "N": args.N,
        "trials": args.trials,
        "seed": args.seed,
        "init_seed": args.init_seed,
        "curve": curve,
        "xs": xs,
        "ys": ys,
    }
    (args.outdir / "phase4_summary.json").write_text(json.dumps(summary, indent=2))

    plot_recovery_curve(xs, ys, args.outdir / "recovery_curve.png")
    radius = plot_stability_radius(xs, ys, args.threshold, args.outdir / "stability_radius.png")

    # Example trajectories: smallest + largest perturb
    ps_examples = [min(xs), max(xs)] if xs else [1, 100]
    plot_example_trajectories(
        args.N,
        ps_examples,
        args.outdir / "example_trajectories.png",
        seed=args.seed,
        init_seed=args.init_seed,
    )

    print(f"Wrote: {args.outdir}/phase4_summary.json")
    print(f"Wrote: {args.outdir}/recovery_curve.png")
    print(f"Wrote: {args.outdir}/stability_radius.png")
    print(f"Wrote: {args.outdir}/example_trajectories.png")
    if radius is not None:
        print(f"Stability radius @ threshold {args.threshold:.2f}: {radius} perturb steps")
    else:
        print(f"Stability radius @ threshold {args.threshold:.2f}: none")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
