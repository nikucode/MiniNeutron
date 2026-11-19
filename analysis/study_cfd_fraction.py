"""Explore digital CFD fractions on paired synthetic MiniNeutron waveforms.

Every fraction sees exactly the same waveform in a trial.  The study reports
time walk, timing jitter, and crossing availability separately; it does not
define an arbitrary combined score or a universal optimum.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.study_waveform_timing import quantize
from analysis.waveform_features import (
    WaveformConfig,
    analyze_waveform,
    normalized_difference_of_exponentials,
)


DEFAULT_FRACTIONS = (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8)
DEFAULT_AMPLITUDES_V = (0.2, 0.5, 1.0)
DEFAULT_NOISE_V = (0.0, 0.01, 0.03)
DEFAULT_RATES_HZ = (500.0, 1000.0, 2000.0)
DEFAULT_SEEDS = (20261119, 20261120, 20261121, 20261122, 20261123)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_waveform(rate_hz, amplitude_v, noise_sigma_v, rng, settings):
    time_s = np.arange(int(settings["duration_s"] * rate_hz)) / rate_hz
    onset_s = settings["nominal_onset_s"] + rng.uniform(0.0, 1.0 / rate_hz)
    shape = normalized_difference_of_exponentials(
        time_s, onset_s, settings["rise_s"], settings["decay_s"]
    )
    analog_v = (
        settings["baseline_v"]
        + amplitude_v * shape
        + rng.normal(0.0, noise_sigma_v, size=len(time_s))
    )
    return onset_s, time_s, quantize(
        analog_v, settings["vref_v"], settings["adc_bits"]
    )


def analyze_fractions(time_s, voltage_v, baseline_samples, settings, fractions):
    """Analyze one immutable waveform with every requested CFD fraction."""

    if not fractions or len(set(fractions)) != len(fractions):
        raise ValueError("fractions must be a non-empty list of unique values")
    rows = []
    for fraction in fractions:
        features = analyze_waveform(
            time_s,
            voltage_v,
            WaveformConfig(
                baseline_samples=baseline_samples,
                threshold_v=settings["threshold_v"],
                cfd_fraction=fraction,
                voltage_min_v=0.0,
                voltage_max_v=settings["vref_v"],
            ),
        )
        rows.append({
            "cfd_fraction": fraction,
            "estimate_s": features["cfd_time_s"],
            "peak_v": features["peak_v"],
            "noise_rms_v": features["noise_rms_v"],
            "saturation_samples": features["saturation_samples"],
        })
    return rows


def run_study(fractions, amplitudes_v, noise_values_v, rates_hz,
              trials, seeds, settings):
    if trials < 2:
        raise ValueError("trials must be at least 2")
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be a non-empty list of unique integers")
    rows = []
    for seed in seeds:
        rng = np.random.default_rng(seed)
        for rate_hz in rates_hz:
            baseline_samples = max(2, int(settings["baseline_duration_s"] * rate_hz))
            for noise_sigma_v in noise_values_v:
                for amplitude_v in amplitudes_v:
                    for trial in range(trials):
                        onset_s, time_s, voltage_v = generate_waveform(
                            rate_hz, amplitude_v, noise_sigma_v, rng, settings
                        )
                        for result in analyze_fractions(
                            time_s, voltage_v, baseline_samples, settings, fractions
                        ):
                            estimate_s = result.pop("estimate_s")
                            rows.append({
                                "seed": seed,
                                "rate_hz": rate_hz,
                                "noise_sigma_v": noise_sigma_v,
                                "amplitude_v": amplitude_v,
                                "trial": trial,
                                "onset_s": onset_s,
                                "estimate_s": estimate_s,
                                "latency_from_onset_s": (
                                    None if estimate_s is None else estimate_s - onset_s
                                ),
                                **result,
                            })
    return pd.DataFrame(rows)


def summarize_trials(trials):
    rows = []
    columns = [
        "seed", "rate_hz", "noise_sigma_v", "amplitude_v", "cfd_fraction"
    ]
    for keys, group in trials.groupby(columns, sort=True):
        detected = group.latency_from_onset_s.dropna() * 1000.0
        rows.append({
            **dict(zip(columns, keys)),
            "trials": len(group),
            "crossings_found": len(detected),
            "crossing_fraction": len(detected) / len(group),
            "mean_latency_ms": detected.mean(),
            "jitter_std_ms": detected.std(ddof=1),
        })
    return pd.DataFrame(rows)


def summarize_tradeoffs(summary):
    rows = []
    columns = ["seed", "rate_hz", "noise_sigma_v", "cfd_fraction"]
    for keys, group in summary.groupby(columns, sort=True):
        latencies = group.mean_latency_ms.dropna()
        jitters = group.jitter_std_ms.dropna()
        rows.append({
            **dict(zip(columns, keys)),
            "amplitudes_compared": len(latencies),
            "time_walk_ms": latencies.max() - latencies.min(),
            "mean_jitter_ms": jitters.mean(),
            "worst_jitter_ms": jitters.max(),
            "minimum_crossing_fraction": group.crossing_fraction.min(),
        })
    return pd.DataFrame(rows)


def aggregate_seeds(per_seed):
    rows = []
    columns = ["rate_hz", "noise_sigma_v", "cfd_fraction"]
    for keys, group in per_seed.groupby(columns, sort=True):
        rows.append({
            **dict(zip(columns, keys)),
            "seeds": group.seed.nunique(),
            "mean_time_walk_ms": group.time_walk_ms.mean(),
            "std_time_walk_ms": group.time_walk_ms.std(ddof=1),
            "mean_of_mean_jitter_ms": group.mean_jitter_ms.mean(),
            "mean_worst_jitter_ms": group.worst_jitter_ms.mean(),
            "std_worst_jitter_ms": group.worst_jitter_ms.std(ddof=1),
            "minimum_crossing_fraction": group.minimum_crossing_fraction.min(),
        })
    result = pd.DataFrame(rows)
    result["pareto_nondominated"] = mark_pareto(result)
    return result


def mark_pareto(summary):
    """Mark fractions not dominated in time walk, worst jitter, and crossings."""

    flags = pd.Series(False, index=summary.index, dtype=bool)
    for _, group in summary.groupby(["rate_hz", "noise_sigma_v"]):
        for index, candidate in group.iterrows():
            dominated = False
            for other_index, other in group.iterrows():
                if other_index == index:
                    continue
                no_worse = (
                    other.mean_time_walk_ms <= candidate.mean_time_walk_ms
                    and other.mean_worst_jitter_ms <= candidate.mean_worst_jitter_ms
                    and other.minimum_crossing_fraction
                    >= candidate.minimum_crossing_fraction
                )
                strictly_better = (
                    other.mean_time_walk_ms < candidate.mean_time_walk_ms
                    or other.mean_worst_jitter_ms < candidate.mean_worst_jitter_ms
                    or other.minimum_crossing_fraction
                    > candidate.minimum_crossing_fraction
                )
                if no_worse and strictly_better:
                    dominated = True
                    break
            flags.loc[index] = not dominated
    return flags


def plot_fraction_sweep(summary, destination):
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharey=True)
    for axis, rate_hz in zip(axes, sorted(summary.rate_hz.unique())):
        subset = summary[summary.rate_hz == rate_hz]
        for noise_v in sorted(subset.noise_sigma_v.unique()):
            values = subset[subset.noise_sigma_v == noise_v]
            axis.errorbar(
                values.cfd_fraction,
                values.mean_time_walk_ms,
                yerr=values.std_time_walk_ms,
                marker="o", capsize=3, label=f"{noise_v * 1000:g} mV",
            )
        axis.set_title(f"{rate_hz:g} Hz")
        axis.set_xlabel("Fracción CFD")
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("Time walk medio [ms]")
    axes[-1].legend(title="Ruido", frameon=False)
    fig.suptitle("MiniNeutron: barrido pareado de fracción CFD")
    fig.tight_layout()
    fig.savefig(destination, dpi=180)
    plt.close(fig)


def plot_tradeoff(summary, destination):
    fig, axes = plt.subplots(3, 3, figsize=(11, 10))
    rates = sorted(summary.rate_hz.unique())
    noises = sorted(summary.noise_sigma_v.unique())
    for row, noise_v in enumerate(noises):
        for column, rate_hz in enumerate(rates):
            axis = axes[row, column]
            values = summary[
                (summary.noise_sigma_v == noise_v) & (summary.rate_hz == rate_hz)
            ]
            for point in values.itertuples():
                marker = "o" if point.pareto_nondominated else "x"
                axis.scatter(
                    point.mean_time_walk_ms, point.mean_worst_jitter_ms,
                    marker=marker, color="tab:green" if marker == "o" else "0.55",
                )
                axis.annotate(
                    f"{point.cfd_fraction:.1f}",
                    (point.mean_time_walk_ms, point.mean_worst_jitter_ms),
                    xytext=(3, 3), textcoords="offset points", fontsize=8,
                )
            axis.grid(alpha=0.25)
            if row == 0:
                axis.set_title(f"{rate_hz:g} Hz")
            if column == 0:
                axis.set_ylabel(f"{noise_v * 1000:g} mV\nPeor jitter medio [ms]")
            if row == len(noises) - 1:
                axis.set_xlabel("Time walk medio [ms]")
    fig.suptitle("Compromiso CFD: no dominados (círculo) y dominados (x)")
    fig.tight_layout()
    fig.savefig(destination, dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--trials", type=int, default=200)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(DEFAULT_SEEDS))
    parser.add_argument("--summary-tsv")
    parser.add_argument("--manifest-copy")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        parser.error("--output-dir must be empty")
    output_dir.mkdir(parents=True, exist_ok=True)

    settings = {
        "duration_s": 0.20,
        "nominal_onset_s": 0.060,
        "baseline_duration_s": 0.040,
        "baseline_v": 0.5,
        "rise_s": 0.006,
        "decay_s": 0.030,
        "vref_v": 3.3,
        "adc_bits": 12,
        "threshold_v": 0.10,
    }
    trials = run_study(
        DEFAULT_FRACTIONS, DEFAULT_AMPLITUDES_V, DEFAULT_NOISE_V,
        DEFAULT_RATES_HZ, args.trials, args.seeds, settings,
    )
    summary = summarize_trials(trials)
    per_seed = summarize_tradeoffs(summary)
    aggregate = aggregate_seeds(per_seed)
    trials.to_csv(output_dir / "trials.csv", index=False)
    summary.to_csv(output_dir / "summary.csv", index=False)
    per_seed.to_csv(output_dir / "tradeoffs_per_seed.csv", index=False)
    aggregate.to_csv(output_dir / "tradeoffs_summary.csv", index=False)
    plot_fraction_sweep(aggregate, output_dir / "fraction_vs_time_walk.png")
    plot_tradeoff(aggregate, output_dir / "tradeoff_pareto.png")

    manifest = {
        "scope": "paired synthetic CFD fraction study; no DRS4 data or calibration",
        "fractions": list(DEFAULT_FRACTIONS),
        "amplitudes_v": list(DEFAULT_AMPLITUDES_V),
        "noise_sigma_v": list(DEFAULT_NOISE_V),
        "rates_hz": list(DEFAULT_RATES_HZ),
        "seeds": args.seeds,
        "trials_per_configuration": args.trials,
        "settings": settings,
        "script_sha256": sha256_file(Path(__file__)),
        "feature_module_sha256": sha256_file(
            Path(__file__).with_name("waveform_features.py")
        ),
        "method": (
            "all CFD fractions analyze each identical waveform; Pareto marks "
            "tradeoffs without an arbitrary combined score"
        ),
    }
    (output_dir / "study.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    if args.summary_tsv:
        destination = Path(args.summary_tsv)
        destination.parent.mkdir(parents=True, exist_ok=True)
        aggregate.to_csv(destination, sep="\t", index=False)
    if args.manifest_copy:
        destination = Path(args.manifest_copy)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
    print(f"Waveforms: {len(trials) // len(DEFAULT_FRACTIONS)}")
    print(f"CFD estimates: {len(trials)}")
    print(f"Per-seed tradeoff rows: {len(per_seed)}")
    print(f"Aggregated tradeoff rows: {len(aggregate)}")
    print(f"Results: {output_dir}")


if __name__ == "__main__":
    main()
