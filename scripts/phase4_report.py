from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt


def _phi_coefficient(a: int, b: int, c: int, d: int) -> float | None:
    """Phi coefficient for 2x2 table:

        [[a, b],
         [c, d]]

    where rows/cols are binary outcomes.
    """

    denom = (a + b) * (c + d) * (a + c) * (b + d)
    if denom <= 0:
        return None
    return (a * d - b * c) / (denom**0.5)


def _contingency_hash_vs_energy(per_trial: list[dict], *, eps: float) -> dict:
    """Compute contingency between strict hash recovery and energy recovery."""

    a = b = c = d = 0
    for tr in per_trial:
        same_hash = bool(tr["recovered_same_hash"])
        basin_E = float(tr["basin_energy"])
        final_E = float(tr["final_energy"])
        energy_rec = final_E <= basin_E + eps
        if same_hash and energy_rec:
            a += 1
        elif same_hash and (not energy_rec):
            b += 1
        elif (not same_hash) and energy_rec:
            c += 1
        else:
            d += 1

    phi = _phi_coefficient(a, b, c, d)
    n = a + b + c + d
    return {
        "eps": eps,
        "n": n,
        "table": {"same_hash&energy": a, "same_hash&not_energy": b, "diff_hash&energy": c, "diff_hash&not_energy": d},
        "phi": phi,
        "hash_recovery_rate": (a + b) / n if n else None,
        "energy_recovery_rate": (a + c) / n if n else None,
    }

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


def plot_recovery_time_distribution(curve: list[dict], outpath: Path) -> None:
    """Boxplot of recovery_steps (only recovered trials) vs perturb level."""

    xs: list[int] = []
    data: list[list[float]] = []
    for r in curve:
        ps = int(r["perturb_steps"])
        per_trial = list(r.get("per_trial", []))
        times = [float(tr["recovery_steps"]) for tr in per_trial if tr.get("recovery_steps") is not None]
        if times:
            xs.append(ps)
            data.append(times)

    plt.figure(figsize=(7.5, 4.2))
    if data:
        plt.boxplot(data, positions=list(range(len(xs))), showfliers=False)
        plt.xticks(list(range(len(xs))), [str(x) for x in xs])
        plt.xlabel("perturb steps (k)")
        plt.ylabel("recovery steps (only recovered trials)")
        plt.title("Recovery time distribution")
        plt.grid(True, axis="y", alpha=0.25)
    else:
        plt.text(0.5, 0.5, "No recovered trials; no recovery time distribution to plot", ha="center", va="center")
        plt.axis("off")

    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


def plot_basin_switch_histogram(curve: list[dict], outpath: Path) -> None:
    """Show counts of basin switches and number of unique final basins per k."""

    ks: list[int] = []
    switches: list[int] = []
    unique_finals: list[int] = []

    for r in curve:
        ps = int(r["perturb_steps"])
        per_trial = list(r.get("per_trial", []))
        switch_count = sum(1 for tr in per_trial if str(tr["final_hash"]) != str(tr["basin_hash"]))
        uniq = len({str(tr["final_hash"]) for tr in per_trial})
        ks.append(ps)
        switches.append(int(switch_count))
        unique_finals.append(int(uniq))

    xs = list(range(len(ks)))

    plt.figure(figsize=(7.5, 4.2))
    plt.bar(xs, switches, label="# trials switched basin (final_hash != basin_hash)", alpha=0.8)
    plt.plot(xs, unique_finals, marker="o", color="black", linewidth=1.2, label="# unique final hashes")
    plt.xticks(xs, [str(k) for k in ks])
    plt.xlabel("perturb steps (k)")
    plt.ylabel("count")
    plt.title("Basin switches vs perturb")
    plt.grid(True, axis="y", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


def plot_hash_vs_energy_recovery(curve: list[dict], *, eps: float, outpath: Path) -> dict:
    """Correlation plot + returns per-k & overall contingency metrics."""

    per_k: list[dict] = []
    overall_trials: list[dict] = []

    for r in curve:
        per_trial = list(r.get("per_trial", []))
        overall_trials.extend(per_trial)
        metrics = _contingency_hash_vs_energy(per_trial, eps=eps)
        metrics["perturb_steps"] = int(r["perturb_steps"])
        per_k.append(metrics)

    overall = _contingency_hash_vs_energy(overall_trials, eps=eps)

    ks = [m["perturb_steps"] for m in per_k]
    hash_rates = [m["hash_recovery_rate"] for m in per_k]
    energy_rates = [m["energy_recovery_rate"] for m in per_k]

    plt.figure(figsize=(6.0, 5.0))
    plt.scatter(hash_rates, energy_rates)
    for k, x, y in zip(ks, hash_rates, energy_rates):
        if x is None or y is None:
            continue
        plt.annotate(str(k), (x, y), textcoords="offset points", xytext=(5, 5), fontsize=8)

    plt.xlabel("P(recovered same hash)")
    plt.ylabel(f"P(energy recovered; E_final <= E_basin + eps, eps={eps:g})")
    plt.title("Hash recovery vs energy recovery")
    plt.grid(True, alpha=0.25)
    plt.xlim(-0.02, 1.02)
    plt.ylim(-0.02, 1.02)
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()

    return {"eps": eps, "per_k": per_k, "overall": overall}


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
    ap.add_argument(
        "--energy-eps",
        type=float,
        default=1e-6,
        help="Energy recovery epsilon: energy_recovered := (E_final <= E_basin + eps)",
    )
    ap.add_argument(
        "--repeat-check",
        action="store_true",
        help="Run the same experiment twice and assert identical phase4_summary.json bytes (determinism check)",
    )
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

    # Validation: k=0 control should recover essentially always.
    if 0 in xs:
        idx0 = xs.index(0)
        y0 = float(ys[idx0])
        if y0 < 0.99:
            raise AssertionError(f"k=0 recovery_rate too low: {y0:.3f} (expected ~1.0)")

    # New Phase-4.1 analyses/plots.
    energy_recovery = plot_hash_vs_energy_recovery(
        curve,
        eps=float(args.energy_eps),
        outpath=args.outdir / "hash_vs_energy_recovery.png",
    )
    plot_recovery_time_distribution(curve, args.outdir / "recovery_time_distribution.png")
    plot_basin_switch_histogram(curve, args.outdir / "basin_switch_histogram.png")

    summary = {
        "N": args.N,
        "trials": args.trials,
        "seed": args.seed,
        "init_seed": args.init_seed,
        "curve": curve,
        "xs": xs,
        "ys": ys,
        "energy_recovery": energy_recovery,
    }

    # Determinism check: re-run and assert identical bytes.
    if args.repeat_check:
        curve2 = []
        for ps in args.perturb:
            r2 = recovery_experiment(
                N=args.N,
                trials=args.trials,
                perturb_steps=ps,
                seed=args.seed,
                init_seed=args.init_seed,
            )
            curve2.append(r2)
        xs2 = [int(r["perturb_steps"]) for r in curve2]
        ys2 = [float(r["recovery_rate"]) for r in curve2]
        energy_recovery2 = {
            "eps": float(args.energy_eps),
            "per_k": [
                {**_contingency_hash_vs_energy(list(r.get("per_trial", [])), eps=float(args.energy_eps)), "perturb_steps": int(r["perturb_steps"])}
                for r in curve2
            ],
            "overall": _contingency_hash_vs_energy(
                [tr for r in curve2 for tr in list(r.get("per_trial", []))],
                eps=float(args.energy_eps),
            ),
        }
        summary2 = {
            "N": args.N,
            "trials": args.trials,
            "seed": args.seed,
            "init_seed": args.init_seed,
            "curve": curve2,
            "xs": xs2,
            "ys": ys2,
            "energy_recovery": energy_recovery2,
        }

        b1 = json.dumps(summary, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        b2 = json.dumps(summary2, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if b1 != b2:
            raise AssertionError("--repeat-check failed: summary JSON bytes differ between two runs")

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
    print(f"Wrote: {args.outdir}/recovery_time_distribution.png")
    print(f"Wrote: {args.outdir}/basin_switch_histogram.png")
    print(f"Wrote: {args.outdir}/hash_vs_energy_recovery.png")
    if radius is not None:
        print(f"Stability radius @ threshold {args.threshold:.2f}: {radius} perturb steps")
    else:
        print(f"Stability radius @ threshold {args.threshold:.2f}: none")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
