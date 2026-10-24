"""Inspect trigger samples and rerun DAQ on controlled waveforms.

The sample-level flags describe threshold crossings at the recorded trigger
sample. Counterfactual event counts are separate full DAQ runs; neither result
alone establishes a unique physical cause for an observed event.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTIC_COLUMNS = [
    "reco_event_id", "trigger_time_s", "observed_voltage_V",
    "ideal_voltage_V", "noise_V", "noise_only_voltage_V",
    "pulse_sum_V", "dominant_truth_event", "dominant_pulse_V",
    "time_since_dominant_pulse_s", "n_truth_candidates",
    "noise_required_at_trigger_sample", "pulses_required_at_trigger_sample",
]


def diagnose_samples(waveform, truth, reco, matches, baseline, tau,
                     trigger, vref):
    """Calculate modeled pulse contributions at each observed trigger sample."""
    if tau <= 0 or vref <= 0:
        raise ValueError("tau and vref must be positive")
    for name, table, required in (
        ("waveform", waveform, {"timestamp_s", "voltage_ideal_V", "noise_V", "voltage_V"}),
        ("truth", truth, {"event", "pulse_time_s", "response_amplitude_V"}),
        ("reconstruction", reco, {"event_id", "trigger_time_s"}),
        ("matches", matches, {"reco_event_id", "n_truth_matches"}),
    ):
        missing = required - set(table.columns)
        if missing:
            raise ValueError(f"{name} is missing columns: {sorted(missing)}")

    sample_times = waveform["timestamp_s"].to_numpy(dtype=float)
    if len(sample_times) == 0 or np.diff(sample_times).min(initial=1) <= 0:
        raise ValueError("waveform timestamps must be nonempty and increasing")
    pulse_times = truth["pulse_time_s"].to_numpy(dtype=float)
    amplitudes = truth["response_amplitude_V"].to_numpy(dtype=float)
    truth_ids = truth["event"].to_numpy()
    candidate_counts = matches.set_index("reco_event_id")["n_truth_matches"]
    if candidate_counts.index.has_duplicates:
        raise ValueError("reconstructed match IDs must be unique")

    rows = []
    for event in reco.itertuples(index=False):
        index = int(np.searchsorted(sample_times, event.trigger_time_s))
        if index >= len(sample_times) or not np.isclose(
            sample_times[index], event.trigger_time_s, rtol=0, atol=1e-9
        ):
            raise ValueError(f"Trigger {event.event_id} is not on a waveform sample")
        sample = waveform.iloc[index]
        delays = event.trigger_time_s - pulse_times
        contributions = np.where(
            delays >= 0,
            amplitudes * np.exp(-np.maximum(delays, 0) / tau),
            0.0,
        )
        pulse_sum = float(contributions.sum())
        ideal = float(sample.voltage_ideal_V)
        noise = float(sample.noise_V)
        observed = float(sample.voltage_V)
        noise_only = float(np.clip(baseline + noise, 0, vref))
        if not np.isclose(ideal, baseline + pulse_sum, rtol=0, atol=1e-8):
            raise ValueError("Truth pulses do not reproduce ideal waveform at trigger")
        if not np.isclose(observed, np.clip(ideal + noise, 0, vref),
                          rtol=0, atol=1e-8):
            raise ValueError("Ideal signal plus noise does not reproduce observed sample")
        if event.event_id not in candidate_counts:
            raise ValueError(f"No temporal match row for reco {event.event_id}")
        dominant_index = int(np.argmax(contributions)) if pulse_sum > 0 else None
        rows.append({
            "reco_event_id": event.event_id,
            "trigger_time_s": event.trigger_time_s,
            "observed_voltage_V": observed,
            "ideal_voltage_V": ideal,
            "noise_V": noise,
            "noise_only_voltage_V": noise_only,
            "pulse_sum_V": pulse_sum,
            "dominant_truth_event": (
                truth_ids[dominant_index] if dominant_index is not None else None
            ),
            "dominant_pulse_V": (
                contributions[dominant_index] if dominant_index is not None else 0.0
            ),
            "time_since_dominant_pulse_s": (
                delays[dominant_index] if dominant_index is not None else None
            ),
            "n_truth_candidates": int(candidate_counts.loc[event.event_id]),
            "noise_required_at_trigger_sample": ideal < trigger <= observed,
            "pulses_required_at_trigger_sample": noise_only < trigger <= observed,
        })
    return pd.DataFrame(rows, columns=DIAGNOSTIC_COLUMNS)


def run_counterfactual(waveform, output_dir, variant, config):
    """Run the existing DAQ script on a waveform with one component removed."""
    destination = output_dir / variant
    destination.mkdir(parents=True, exist_ok=True)
    modified = waveform.copy()
    if variant == "no_noise":
        modified["noise_V"] = 0.0
    elif variant == "no_pulses":
        modified["voltage_ideal_V"] = config["baseline"]
    else:
        raise ValueError(f"Unknown counterfactual: {variant}")
    voltage = np.clip(
        modified["voltage_ideal_V"] + modified["noise_V"],
        0, config["vref"],
    )
    modified["voltage_V"] = voltage
    modified["adc_raw"] = np.rint(
        voltage / config["vref"] * (2 ** config["bits"] - 1)
    ).astype(int)
    input_path = destination / "waveform.csv"
    modified.to_csv(input_path, index=False)
    command = [
        sys.executable, str(ROOT / "daq/analyze_pulses.py"),
        "--input", str(input_path), "--output-dir", str(destination),
        "--trigger", str(config["trigger"]), "--rearm", str(config["rearm"]),
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                            check=False)
    (destination / "daq.log").write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"DAQ failed for {variant}: {result.stderr}")
    return len(pd.read_csv(destination / "detected_events.csv"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True,
                        help="Completed run_pipeline.py output directory")
    parser.add_argument("--output-dir", required=True,
                        help="New empty directory for diagnostic outputs")
    args = parser.parse_args()
    run_dir = Path(args.run_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        parser.error("--output-dir must be empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    if manifest.get("status") != "completed":
        raise ValueError("Input pipeline run is not completed")
    config = manifest["configuration"]
    if config.get("trigger_source", "voltage") != "voltage":
        raise ValueError(
            "Trigger contribution diagnostics require voltage trigger mode"
        )
    waveform_path = run_dir / "detector_waveform.csv"
    waveform = pd.read_csv(waveform_path)
    truth = pd.read_csv(run_dir / "detector_waveform_truth.csv")
    reco = pd.read_csv(run_dir / "daq/detected_events.csv")
    matches = pd.read_csv(run_dir / "daq/reconstructed_event_matches.csv")
    diagnostics = diagnose_samples(
        waveform, truth, reco, matches, config["baseline"], config["tau"],
        config["trigger"], config["vref"],
    )
    diagnostics.to_csv(output_dir / "trigger_samples.csv", index=False)
    counts = {
        variant: run_counterfactual(waveform, output_dir, variant, config)
        for variant in ("no_noise", "no_pulses")
    }
    provenance = {
        "input_run": str(run_dir),
        "input_hits_sha256": manifest["input_hits_sha256"],
        "waveform_sha256": hashlib.sha256(waveform_path.read_bytes()).hexdigest(),
        "configuration": config,
        "observed_reco": len(reco),
        "counterfactual_reco": counts,
        "noise_required_at_trigger_sample": int(
            diagnostics["noise_required_at_trigger_sample"].sum()
        ),
        "pulses_required_at_trigger_sample": int(
            diagnostics["pulses_required_at_trigger_sample"].sum()
        ),
        "unmatched_with_noise_required_at_sample": int((
            diagnostics["n_truth_candidates"].eq(0)
            & diagnostics["noise_required_at_trigger_sample"]
        ).sum()),
        "interpretation": (
            "Sample flags are local threshold statements; event counts come from "
            "full DAQ reruns and do not identify one-to-one causal events."
        ),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n"
    )
    print(json.dumps({key: provenance[key] for key in (
        "observed_reco", "counterfactual_reco",
        "noise_required_at_trigger_sample",
        "pulses_required_at_trigger_sample",
        "unmatched_with_noise_required_at_sample",
    )}, indent=2))


if __name__ == "__main__":
    main()
