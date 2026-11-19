"""Compare three timing estimators on controlled MiniNeutron waveforms.

The study uses only synthetic signals with known onset.  It does not ingest
DRS4 records and is not a detector calibration.  The reported quantity is
estimator latency relative to pulse onset, not neutron time of flight.
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

from analysis.waveform_features import (
    WaveformConfig,
    analyze_waveform,
    normalized_difference_of_exponentials,
)


DEFAULT_AMPLITUDES_V = (0.2, 0.5, 1.0)
DEFAULT_NOISE_V = (0.0, 0.01, 0.03)
DEFAULT_RATES_HZ = (500.0, 1000.0, 2000.0)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quantize(voltage_v, vref_v, bits):
    if not np.isfinite(voltage_v).all():
        raise ValueError("voltage must be finite")
    if not np.isfinite(vref_v) or vref_v <= 0 or bits < 1 or bits > 24:
        raise ValueError("vref_v must be positive and bits must be 1-24")
    adc_max = 2 ** bits - 1
    codes = np.rint(np.clip(voltage_v, 0.0, vref_v) / vref_v * adc_max)
    return codes * vref_v / adc_max


def one_waveform(rate_hz, amplitude_v, noise_sigma_v, rng, settings):
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
    sampled_v = quantize(analog_v, settings["vref_v"], settings["adc_bits"])
    baseline_samples = max(2, int(settings["baseline_duration_s"] * rate_hz))
    features = analyze_waveform(
        time_s,
        sampled_v,
        WaveformConfig(
            baseline_samples=baseline_samples,
            threshold_v=settings["threshold_v"],
            cfd_fraction=settings["cfd_fraction"],
            voltage_min_v=0.0,
            voltage_max_v=settings["vref_v"],
        ),
    )
    return onset_s, features


def run_study(amplitudes_v, noise_values_v, rates_hz, trials, seeds, settings):
    if trials < 2:
        raise ValueError("trials must be at least 2")
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be a non-empty list of unique integers")
    rows = []
    methods = {
        "peak": "peak_time_s",
        "fixed_threshold": "threshold_time_s",
        "cfd": "cfd_time_s",
    }
    for seed in seeds:
        rng = np.random.default_rng(seed)
        for rate_hz in rates_hz:
            for noise_sigma_v in noise_values_v:
                for amplitude_v in amplitudes_v:
                    for trial in range(trials):
                        onset_s, features = one_waveform(
                            rate_hz, amplitude_v, noise_sigma_v, rng, settings
                        )
                        for method, field in methods.items():
                            estimate_s = features[field]
                            rows.append({
                                "seed": seed,
                                "rate_hz": rate_hz,
                                "noise_sigma_v": noise_sigma_v,
                                "amplitude_v": amplitude_v,
                                "trial": trial,
                                "method": method,
                                "onset_s": onset_s,
                                "estimate_s": estimate_s,
                                "latency_from_onset_s": (
                                    None if estimate_s is None else estimate_s - onset_s
                                ),
                                "peak_v": features["peak_v"],
                                "noise_rms_v": features["noise_rms_v"],
                                "saturation_samples": features["saturation_samples"],
                            })
    return pd.DataFrame(rows)


def summarize(trials):
    rows = []
    groups = trials.groupby(
        ["seed", "rate_hz", "noise_sigma_v", "amplitude_v", "method"],
        sort=True,
    )
    for keys, group in groups:
        detected = group.latency_from_onset_s.dropna()
        latency_ms = detected * 1000.0
        rows.append({
            "seed": keys[0],
            "rate_hz": keys[1],
            "noise_sigma_v": keys[2],
            "amplitude_v": keys[3],
            "method": keys[4],
            "trials": len(group),
            "detected": len(detected),
            "detection_fraction": len(detected) / len(group),
            "mean_latency_ms": latency_ms.mean(),
            "jitter_std_ms": latency_ms.std(ddof=1),
            "median_latency_ms": latency_ms.median(),
            "q05_latency_ms": latency_ms.quantile(0.05),
            "q95_latency_ms": latency_ms.quantile(0.95),
        })
    return pd.DataFrame(rows)


def calculate_time_walk(summary):
    rows = []
    for keys, group in summary.groupby(
        ["seed", "rate_hz", "noise_sigma_v", "method"]
    ):
        valid = group.mean_latency_ms.dropna()
        rows.append({
            "seed": keys[0],
            "rate_hz": keys[1],
            "noise_sigma_v": keys[2],
            "method": keys[3],
            "amplitudes_compared": len(valid),
            "time_walk_ms": valid.max() - valid.min() if len(valid) else None,
            "minimum_detection_fraction": group.detection_fraction.min(),
        })
    return pd.DataFrame(rows)


def aggregate_time_walk(time_walk):
    rows = []
    for keys, group in time_walk.groupby(["rate_hz", "noise_sigma_v", "method"]):
        values = group.time_walk_ms.dropna()
        rows.append({
            "rate_hz": keys[0],
            "noise_sigma_v": keys[1],
            "method": keys[2],
            "seeds": len(values),
            "mean_time_walk_ms": values.mean(),
            "std_time_walk_ms": values.std(ddof=1),
            "min_time_walk_ms": values.min(),
            "max_time_walk_ms": values.max(),
            "minimum_detection_fraction": group.minimum_detection_fraction.min(),
        })
    return pd.DataFrame(rows)


def plot_time_walk(time_walk_summary, destination):
    methods = {
        "peak": "Tiempo del máximo",
        "fixed_threshold": "Umbral fijo",
        "cfd": "CFD 50 %",
    }
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharey=True)
    for axis, rate_hz in zip(axes, sorted(time_walk_summary.rate_hz.unique())):
        subset = time_walk_summary[time_walk_summary.rate_hz == rate_hz]
        for method, label in methods.items():
            values = subset[subset.method == method].sort_values("noise_sigma_v")
            axis.errorbar(
                values.noise_sigma_v * 1000.0,
                values.mean_time_walk_ms,
                yerr=values.std_time_walk_ms,
                marker="o",
                capsize=3,
                label=label,
            )
        axis.set_title(f"{rate_hz:g} Hz")
        axis.set_xlabel("Ruido $\\sigma$ [mV]")
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("Time walk entre amplitudes [ms]")
    axes[-1].legend(frameon=False)
    fig.suptitle("MiniNeutron: sensibilidad temporal de estimadores sintéticos")
    fig.tight_layout()
    fig.savefig(destination, dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--trials", type=int, default=200)
    parser.add_argument(
        "--seeds", type=int, nargs="+",
        default=[20261119, 20261120, 20261121, 20261122, 20261123],
    )
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
        "cfd_fraction": 0.50,
    }
    trials = run_study(
        DEFAULT_AMPLITUDES_V,
        DEFAULT_NOISE_V,
        DEFAULT_RATES_HZ,
        args.trials,
        args.seeds,
        settings,
    )
    summary = summarize(trials)
    time_walk = calculate_time_walk(summary)
    time_walk_summary = aggregate_time_walk(time_walk)
    trials.to_csv(output_dir / "trials.csv", index=False)
    summary.to_csv(output_dir / "summary.csv", index=False)
    time_walk.to_csv(output_dir / "time_walk.csv", index=False)
    time_walk_summary.to_csv(output_dir / "time_walk_summary.csv", index=False)
    plot_time_walk(time_walk_summary, output_dir / "time_walk.png")

    manifest = {
        "scope": "synthetic MiniNeutron timing study; not DRS4 analysis or calibration",
        "seeds": args.seeds,
        "trials_per_configuration": args.trials,
        "amplitudes_v": list(DEFAULT_AMPLITUDES_V),
        "noise_sigma_v": list(DEFAULT_NOISE_V),
        "rates_hz": list(DEFAULT_RATES_HZ),
        "settings": settings,
        "script_sha256": sha256_file(Path(__file__)),
        "feature_module_sha256": sha256_file(
            Path(__file__).with_name("waveform_features.py")
        ),
        "interpretation": (
            "latency is relative to synthetic pulse onset; time_walk is the "
            "range of mean latency across amplitudes at fixed rate/noise"
        ),
    }
    (output_dir / "study.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    if args.summary_tsv:
        evidence = Path(args.summary_tsv)
        evidence.parent.mkdir(parents=True, exist_ok=True)
        time_walk_summary.to_csv(evidence, sep="\t", index=False)
    if args.manifest_copy:
        destination = Path(args.manifest_copy)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
    print(f"Waveforms: {len(trials) // 3}")
    print(f"Estimator rows: {len(trials)}")
    print(f"Summary rows: {len(summary)}")
    print(f"Per-seed time-walk rows: {len(time_walk)}")
    print(f"Aggregated time-walk rows: {len(time_walk_summary)}")
    print(f"Results: {output_dir}")


if __name__ == "__main__":
    main()
