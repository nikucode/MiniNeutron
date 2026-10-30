"""Import an optical bench stream and reuse MiniNeutron's ADC event builder.

Run from the repository root: python -m daq.optical_bench --help.
The explicit source label distinguishes synthetic fixtures from measurements.
"""

import argparse
import hashlib
import io
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.validate_data import validate_pulse_csv

ROOT = Path(__file__).resolve().parents[1]
HEADER = "sample,timestamp_us,adc_raw"
UINT32 = 2 ** 32


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_stream(path, vref=5.0, max_gap_us=1_000_000):
    """Strict 10-bit stream; unwrap micros() with bounded modular differences.

    Sequence gaps are counted, not filled. Resets/repeated timestamps fail.
    A forward modular step over max_gap_us is rejected; never infer multiple
    rollovers or repair a restart. Time is relative to the first received row.
    """
    if not math.isfinite(vref) or vref <= 0:
        raise ValueError("vref must be finite and positive")
    raw = Path(path).read_text(encoding="ascii")
    if not raw.endswith("\n"):
        raise ValueError("Incomplete final line")
    lines = raw.splitlines()
    if not lines or lines[0] != HEADER:
        raise ValueError(f"Expected header: {HEADER}")
    records = []
    for number, line in enumerate(lines[1:], 2):
        fields = line.split(",")
        if len(fields) != 3 or not all(x.isascii() and x.isdigit() for x in fields):
            raise ValueError(f"Malformed integer row at line {number}")
        seq, timestamp, code = map(int, fields)
        if not (0 <= seq < UINT32 and 0 <= timestamp < UINT32 and 0 <= code <= 1023):
            raise ValueError(f"Out-of-range value at line {number}")
        records.append((seq, timestamp, code))
    if len(records) < 2:
        raise ValueError("At least two samples are required")
    seq = np.array([r[0] for r in records], dtype=np.int64)
    ticks = np.array([r[1] for r in records], dtype=np.int64)
    codes = np.array([r[2] for r in records], dtype=np.int64)
    if np.any(np.diff(seq) <= 0):
        raise ValueError("Sample sequence reset, duplicate, or out of order")
    deltas = np.diff(ticks) % UINT32
    if np.any(deltas == 0) or np.any(deltas > max_gap_us):
        raise ValueError("Invalid timestamp gap, order, or device restart")
    elapsed = np.concatenate(([0], np.cumsum(deltas)))
    frame = pd.DataFrame({"sample": seq, "timestamp_s": elapsed / 1e6,
                          "adc_raw": codes, "voltage_V": codes * vref / 1023})
    # voltage_V is an endpoint-scaled display estimate, NOT an analog measurement.
    stats = {
        "samples": len(frame), "missing_sequence_samples": int(np.sum(np.diff(seq) - 1)),
        "micros_rollovers": int(np.sum(np.diff(ticks) < 0)),
        "first_timestamp_us": int(ticks[0]),
        "duration_s": float(elapsed[-1] / 1e6),
        "mean_dt_us": float(np.mean(deltas)), "std_dt_us": float(np.std(deltas)),
        "min_dt_us": int(min(deltas)), "max_dt_us": int(max(deltas)),
        "estimated_sample_rate_hz": float(1e6 / np.mean(deltas)),
        "rail_samples": int(np.sum((codes == 0) | (codes == 1023))),
    }
    return frame, stats


def analyze(raw_path, output, source, trigger=3.0, rearm=2.0, vref=5.0):
    """Validate and analyze a stream in a new directory, preserving its bytes."""
    if source not in ("synthetic", "hardware"):
        raise ValueError("source must be synthetic or hardware")
    if not all(map(math.isfinite, (trigger, rearm, vref))) or not 0 <= rearm < trigger <= vref:
        raise ValueError("Require finite 0 <= rearm < trigger <= vref")
    raw_path, output = Path(raw_path).resolve(), Path(output).resolve()
    frame, stats = read_stream(raw_path, vref)
    output.mkdir(parents=True, exist_ok=False)
    (output / "raw_stream.txt").write_bytes(raw_path.read_bytes())
    waveform = output / "waveform.csv"
    frame.to_csv(waveform, index=False)
    errors = validate_pulse_csv(waveform)
    if errors:
        raise ValueError("; ".join(errors))
    manifest = {
        "schema": "minineutron-optical-bench-v1", "source": source,
        "status": "running", "created_utc": datetime.now(timezone.utc).isoformat(),
        "input_sha256": digest(raw_path), "python": sys.version.split()[0],
        "versions": {"numpy": np.__version__, "pandas": pd.__version__},
        "configuration": {"bits": 10, "vref_V": vref, "trigger_V": trigger,
                          "rearm_V": rearm, "trigger_source": "adc"},
        "script_sha256": {p: digest(ROOT / p) for p in (
            "daq/optical_bench.py", "daq/analyze_pulses.py", "analysis/validate_data.py")},
        "acquisition": stats,
        "limitations": ["Uncalibrated voltage estimate: adc_raw * vref / 1023",
                        "Host reception times are not acquisition timestamps",
                        "No physical neutron efficiency or chopper synchronization claim",
                        "First/last active events can be censored by recording boundaries"],
    }
    manifest_path = output / "manifest.json"
    def save():
        manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    save()
    result = subprocess.run([
        sys.executable, str(ROOT / "daq/analyze_pulses.py"),
        "--input", str(waveform), "--output-dir", str(output),
        "--trigger-source", "adc", "--bits", "10", "--vref", str(vref),
        "--trigger", str(trigger), "--rearm", str(rearm),
    ], capture_output=True, text=True)
    (output / "analysis.log").write_text(result.stdout + result.stderr)
    if result.returncode:
        manifest["status"] = "failed"
        save()
        raise RuntimeError(f"Event analysis failed; see {output / 'analysis.log'}")
    events = pd.read_csv(output / "detected_events.csv")
    manifest["events"] = len(events)
    manifest["status"] = "complete"
    manifest["output_sha256"] = {p: digest(output / p) for p in (
        "waveform.csv", "detected_events.csv", "simulated_pulses.png")}
    save()
    return events, manifest


def synthetic_stream(seed=20261030, noise_codes=8.0):
    """10 s at nominal 500 Hz, 20 rectangular interruptions, known rising edges.

    A software fixture, not a sensor, ADC or optical response model. Bounded
    timestamp perturbations exercise nonuniform sampling; 4 us grid is chosen
    for an Uno R3 reference, not an assertion of measured timing performance.
    """
    if not math.isfinite(noise_codes) or noise_codes < 0:
        raise ValueError("noise_codes must be finite and nonnegative")
    rng = np.random.default_rng(seed)
    ticks = np.arange(5000, dtype=np.int64) * 2000
    ticks[1:] += rng.integers(-25, 26, len(ticks) - 1) * 4
    times = ticks / 1e6
    truth = np.arange(20) * 0.5 + 0.251
    signal = np.full(len(times), 150.0)
    for edge in truth:
        signal[(times >= edge) & (times < edge + 0.08)] = 850.0
    codes = np.clip(np.rint(signal + rng.normal(0, noise_codes, len(times))), 0, 1023).astype(int)
    stream = io.StringIO()
    stream.write(HEADER + "\n")
    for i, (tick, code) in enumerate(zip(ticks, codes)):
        stream.write(f"{i},{tick},{code}\n")
    return stream.getvalue(), truth


def match_edges(truth, detected, tolerance_s=0.01):
    """Chronological one-to-one nearest unused edge within a fixed tolerance.

    Suitable for this fixture's isolated edges (separation 0.5 s), not causal
    attribution of overlapping neutron pulses. Extra triggers remain unmatched.
    """
    truth, detected = np.asarray(truth, dtype=float), np.asarray(detected, dtype=float)
    if (not math.isfinite(tolerance_s) or tolerance_s < 0
            or not np.isfinite(truth).all() or not np.isfinite(detected).all()
            or np.any(np.diff(truth) <= 0) or np.any(np.diff(detected) <= 0)):
        raise ValueError("Require finite ordered times and nonnegative tolerance")
    available = set(range(len(detected)))
    errors = []
    for t in truth:
        candidates = [i for i in available if abs(detected[i] - t) <= tolerance_s]
        if candidates:
            i = min(candidates, key=lambda j: (abs(detected[j] - t), j))
            available.remove(i)
            errors.append(float(detected[i] - t))
    return {
        "truth_edges": len(truth), "detected_events": len(detected),
        "matched": len(errors), "missed": len(truth) - len(errors),
        "unmatched_triggers": len(available), "tolerance_s": tolerance_s,
        "mean_error_ms": float(np.mean(errors) * 1e3) if errors else None,
        "max_abs_error_ms": float(np.max(np.abs(errors)) * 1e3) if errors else None,
    }


def study(output):
    """Paired thresholds on identical streams, with 3 fixed seeds and 2 noises."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for seed in (20261030, 20261031, 20261032):
        for noise in (8, 120):
            raw, truth = synthetic_stream(seed, noise)
            raw_path = output / f"synthetic_{seed}_noise{noise}.txt"
            raw_path.write_text(raw)
            for trigger, rearm in ((1.5, 1.0), (3.0, 2.0), (4.8, 4.0)):
                run_dir = output / f"seed{seed}_noise{noise}_trigger{trigger}"
                events, manifest = analyze(raw_path, run_dir, "synthetic", trigger, rearm)
                metrics = match_edges(truth, events.trigger_time_s.to_numpy())
                rows.append({"seed": seed, "noise_codes": noise, "trigger_V": trigger,
                             "rearm_V": rearm, "source": "synthetic",
                             "input_sha256": manifest["input_sha256"], **metrics})
    pd.DataFrame(rows).to_csv(output / "summary.csv", index=False)
    report = {"source": "synthetic", "seed_policy": "3 fixed paired seeds",
              "truth_edge_times_s": truth.tolist(), "runs": rows,
              "script_sha256": digest(Path(__file__)),
              "limitations": "Rectangular isolated pulses; no hardware or neutron validation"}
    (output / "study.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("analyze")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--source", choices=("synthetic", "hardware"), required=True)
    p.add_argument("--trigger", type=float, default=3.0)
    p.add_argument("--rearm", type=float, default=2.0)
    p.add_argument("--vref", type=float, default=5.0)
    p = sub.add_parser("study")
    p.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "study":
        rows = study(args.output_dir)
        print(pd.DataFrame(rows).drop(columns="input_sha256").to_string(index=False))
    else:
        _, manifest = analyze(args.input, args.output_dir, args.source,
                              args.trigger, args.rearm, args.vref)
        print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
