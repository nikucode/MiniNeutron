"""Compare analog and ADC DAQ decisions on identical sampled waveforms.

Each seed is generated once by run_pipeline.py. ADC resolutions are then
recomputed from the same saved voltage samples; Geant4 hits, pulse times,
noise, and the truth table remain fixed within that seed.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATHS = (
    "run_pipeline.py", "analysis/study_adc_trigger.py",
    "analysis/build_detector_waveform.py", "daq/analyze_pulses.py",
    "analysis/compare_truth_reco.py",
)
PAIR_COLUMNS = [
    "voltage_event_id", "adc_event_id", "voltage_trigger_s", "voltage_end_s",
    "adc_trigger_s", "adc_end_s", "overlap_s",
]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def quantize_voltage(waveform, vref, bits):
    """Use the same round-to-nearest-even rule as build_detector_waveform.py."""
    if not 1 <= bits <= 24 or not np.isfinite(vref) or vref <= 0:
        raise ValueError("bits must be 1–24 and Vref must be positive")
    voltage = pd.to_numeric(waveform["voltage_V"], errors="coerce").to_numpy()
    if not np.isfinite(voltage).all() or ((voltage < 0) | (voltage > vref)).any():
        raise ValueError("voltage_V must be finite and within [0, Vref]")
    result = waveform.copy()
    result["adc_raw"] = np.rint(voltage / vref * (2 ** bits - 1)).astype(int)
    return result


def compare_windows(voltage_events, adc_events):
    """Link DAQ windows with positive overlap, independent of event IDs."""
    rows = []
    voltage_degree = {int(row.event_id): 0 for row in voltage_events.itertuples()}
    adc_degree = {int(row.event_id): 0 for row in adc_events.itertuples()}
    for v in voltage_events.itertuples(index=False):
        for a in adc_events.itertuples(index=False):
            overlap = min(v.end_time_s, a.end_time_s) - max(
                v.trigger_time_s, a.trigger_time_s
            )
            if overlap > 0:
                voltage_degree[int(v.event_id)] += 1
                adc_degree[int(a.event_id)] += 1
                rows.append({
                    "voltage_event_id": int(v.event_id),
                    "adc_event_id": int(a.event_id),
                    "voltage_trigger_s": v.trigger_time_s,
                    "voltage_end_s": v.end_time_s,
                    "adc_trigger_s": a.trigger_time_s,
                    "adc_end_s": a.end_time_s,
                    "overlap_s": overlap,
                })
    for v in voltage_events.itertuples(index=False):
        if voltage_degree[int(v.event_id)] == 0:
            rows.append({"voltage_event_id": int(v.event_id),
                         "voltage_trigger_s": v.trigger_time_s,
                         "voltage_end_s": v.end_time_s})
    for a in adc_events.itertuples(index=False):
        if adc_degree[int(a.event_id)] == 0:
            rows.append({"adc_event_id": int(a.event_id),
                         "adc_trigger_s": a.trigger_time_s,
                         "adc_end_s": a.end_time_s})
    pairs = pd.DataFrame(rows, columns=PAIR_COLUMNS)
    return pairs, {
        "voltage_only": sum(degree == 0 for degree in voltage_degree.values()),
        "adc_only": sum(degree == 0 for degree in adc_degree.values()),
        "voltage_windows_overlapping_multiple_adc": sum(
            degree > 1 for degree in voltage_degree.values()
        ),
        "adc_windows_overlapping_multiple_voltage": sum(
            degree > 1 for degree in adc_degree.values()
        ),
        "one_to_one_links": sum(
            voltage_degree[int(row["voltage_event_id"])] == 1
            and adc_degree[int(row["adc_event_id"])] == 1
            for row in rows if "overlap_s" in row
        ),
    }


def run(command, log_path):
    result = subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True, check=False
    )
    log_path.write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}); inspect {log_path}")


def summarize_truth(table):
    return {f"truth_{status}": int(table.status.eq(status).sum())
            for status in ("individual", "merged", "missed", "ambiguous")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-hits", default=str(ROOT / "build/detector_hits.csv"))
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--seeds", nargs="+", type=int,
                        default=[12345, 12346, 12347])
    parser.add_argument("--bits", nargs="+", type=int, default=[4, 6, 8, 10])
    args = parser.parse_args()
    if len(set(args.seeds)) != len(args.seeds) or len(set(args.bits)) != len(args.bits):
        parser.error("seeds and bits must not contain duplicates")
    if any(not 1 <= bits <= 24 for bits in args.bits):
        parser.error("bits must be between 1 and 24")
    hits = Path(args.input_hits).resolve()
    if not hits.is_file():
        parser.error(f"Input hit CSV not found: {hits}")
    output_root = Path(args.output_root).resolve()
    if output_root.exists() and any(output_root.iterdir()):
        parser.error("--output-root must be empty")
    output_root.mkdir(parents=True, exist_ok=True)
    provenance = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "input_hits": str(hits), "input_hits_sha256": sha256(hits),
        "seeds": args.seeds, "bits": args.bits,
        "script_sha256": {path: sha256(ROOT / path) for path in SCRIPT_PATHS},
        "method": "One analog waveform per seed; only ADC quantization varies within seed",
        "runs": [],
    }
    study_path = output_root / "study.json"

    def save_study():
        study_path.write_text(json.dumps(provenance, indent=2) + "\n",
                              encoding="utf-8")

    save_study()
    summary = []
    for seed in args.seeds:
        seed_root = output_root / "runs" / f"seed_{seed}"
        run([sys.executable, str(ROOT / "run_pipeline.py"),
             "--input-hits", str(hits), "--output-root", str(seed_root),
             "--seed", str(seed), "--trigger-source", "voltage"],
            output_root / f"seed_{seed}_pipeline.log")
        run_dirs = [path for path in seed_root.iterdir() if path.is_dir()]
        if len(run_dirs) != 1:
            raise RuntimeError(f"Expected one pipeline run for seed {seed}")
        source = run_dirs[0]
        manifest = json.loads((source / "manifest.json").read_text())
        if manifest["status"] != "completed":
            raise RuntimeError(f"Pipeline did not complete for seed {seed}")
        config = manifest["configuration"]
        waveform_path = source / "detector_waveform.csv"
        waveform = pd.read_csv(waveform_path)
        voltage_events = pd.read_csv(source / "daq/detected_events.csv")
        voltage_truth = pd.read_csv(source / "daq/truth_reconstruction_comparison.csv")
        record = {"seed": seed, "pipeline_run": str(source),
                  "waveform_sha256": sha256(waveform_path),
                  "configuration": config, "variants": []}
        provenance["runs"].append(record)
        save_study()
        for bits in args.bits:
            variant = output_root / "adc" / f"seed_{seed}_bits_{bits}"
            variant.mkdir(parents=True)
            adc_waveform_path = variant / "waveform.csv"
            digitized = quantize_voltage(waveform, config["vref"], bits)
            if bits == config["bits"] and not digitized.adc_raw.equals(waveform.adc_raw):
                raise RuntimeError("Requantization disagrees with source ADC codes")
            digitized.to_csv(adc_waveform_path, index=False)
            run([sys.executable, str(ROOT / "daq/analyze_pulses.py"),
                 "--input", str(adc_waveform_path), "--output-dir", str(variant),
                 "--trigger-source", "adc", "--trigger", str(config["trigger"]),
                 "--rearm", str(config["rearm"]), "--vref", str(config["vref"]),
                 "--bits", str(bits)], variant / "daq.log")
            run([sys.executable, str(ROOT / "analysis/compare_truth_reco.py"),
                 "--truth", str(source / "detector_waveform_truth.csv"),
                 "--reco", str(variant / "detected_events.csv"),
                 "--output-dir", str(variant),
                 "--pre-window", str(config["pre_window"])],
                variant / "comparison.log")
            adc_events = pd.read_csv(variant / "detected_events.csv")
            adc_truth = pd.read_csv(variant / "truth_reconstruction_comparison.csv")
            pairs, window_stats = compare_windows(voltage_events, adc_events)
            pairs.to_csv(variant / "window_pairs.csv", index=False)
            changed_truth = int((
                voltage_truth.set_index("event").status
                != adc_truth.set_index("event").status
            ).sum())
            row = {
                "seed": seed, "bits": bits, "n_truth": len(voltage_truth),
                "n_voltage": len(voltage_events), "n_adc": len(adc_events),
                **window_stats, "truth_status_changed": changed_truth,
                **{f"voltage_{key}": value for key, value in
                   summarize_truth(voltage_truth).items()},
                **{f"adc_{key}": value for key, value in
                   summarize_truth(adc_truth).items()},
                "variant_dir": str(variant),
            }
            summary.append(row)
            pd.DataFrame(summary).to_csv(output_root / "summary.csv", index=False)
            record["variants"].append({"bits": bits, "dir": str(variant),
                                       "waveform_sha256": sha256(adc_waveform_path)})
            save_study()
            print(f"seed={seed} bits={bits}: voltage={len(voltage_events)} "
                  f"ADC={len(adc_events)} changed_truth={changed_truth}", flush=True)
    provenance["finished_at"] = datetime.now(timezone.utc).isoformat()
    save_study()
    print(f"Summary: {output_root / 'summary.csv'}")


if __name__ == "__main__":
    main()
