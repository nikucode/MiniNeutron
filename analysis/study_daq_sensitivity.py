"""Run a small one-factor-at-a-time DAQ sensitivity study.

Every case uses the same Geant4 hit CSV. Within a seed, changing only the
trigger or noise sigma preserves generated pulse times. Changing duration
also rescales those times, so that case probes temporal crowding.
"""

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


CASES = {
    "baseline": {},
    "trigger_070": {"trigger": 0.70},
    "trigger_100": {"trigger": 1.00},
    "noise_000": {"noise_sigma": 0.00},
    "noise_060": {"noise_sigma": 0.06},
    "duration_5": {"duration": 5.0},
    "duration_20": {"duration": 20.0},
}
BASE_CONFIG = {
    "gain": 1.0, "duration": 10.0, "rate": 500.0,
    "baseline": 0.5, "noise_sigma": 0.03, "tau": 0.03,
    "vref": 5.0, "bits": 10, "trigger": 0.80,
    "rearm": 0.65, "pre_window": 0.004,
}


def summarize_run(run_dir, case, seed, overrides):
    """Read only the generated CSV tables needed for the study summary."""
    daq = run_dir / "daq"
    truth = pd.read_csv(daq / "truth_reconstruction_comparison.csv")
    reco = pd.read_csv(daq / "reconstructed_event_matches.csv")
    waveform = pd.read_csv(run_dir / "detector_waveform.csv")
    return {
        "case": case,
        "seed": seed,
        "duration_s": overrides.get("duration", BASE_CONFIG["duration"]),
        "noise_sigma_V": overrides.get("noise_sigma", BASE_CONFIG["noise_sigma"]),
        "trigger_V": overrides.get("trigger", BASE_CONFIG["trigger"]),
        "n_truth": len(truth),
        "n_samples": len(waveform),
        "n_reco": len(reco),
        "individual": int(truth.status.eq("individual").sum()),
        "merged": int(truth.status.eq("merged").sum()),
        "missed": int(truth.status.eq("missed").sum()),
        "ambiguous": int(truth.status.eq("ambiguous").sum()),
        "unmatched_reco": int(reco.n_truth_matches.eq(0).sum()),
        "multi_truth_reco": int(reco.n_truth_matches.gt(1).sum()),
        "run_dir": str(run_dir),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-hits", default=str(ROOT / "build/detector_hits.csv"))
    parser.add_argument("--output-root", required=True,
                        help="New empty directory for manifests and study results")
    parser.add_argument("--seeds", type=int, nargs="+",
                        default=[12345, 12346, 12347])
    parser.add_argument("--cases", nargs="+", choices=CASES,
                        default=list(CASES))
    args = parser.parse_args()

    hits = Path(args.input_hits).resolve()
    if not hits.is_file():
        parser.error(f"Input hit CSV not found: {hits}")
    output_root = Path(args.output_root).resolve()
    if output_root.exists() and any(output_root.iterdir()):
        parser.error("--output-root must be empty to keep studies independent")
    output_root.mkdir(parents=True, exist_ok=True)

    study = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "input_hits": str(hits),
        "input_hits_sha256": sha256_file(hits),
        "runner_sha256": sha256_file(Path(__file__)),
        "seeds": args.seeds,
        "cases": {name: CASES[name] for name in args.cases},
        "base_configuration": BASE_CONFIG,
        "method": "one factor at a time; temporal associations, not detector efficiency",
    }
    (output_root / "study.json").write_text(
        json.dumps(study, indent=2) + "\n", encoding="utf-8"
    )

    rows = []
    for case in args.cases:
        overrides = CASES[case]
        for seed in args.seeds:
            label = f"{case}_seed_{seed}"
            case_root = output_root / "runs" / label
            case_root.mkdir(parents=True, exist_ok=True)
            previous = set(case_root.iterdir())
            command = [
                sys.executable, str(ROOT / "run_pipeline.py"),
                "--input-hits", str(hits), "--output-root", str(case_root),
                "--seed", str(seed),
            ]
            for name, value in (BASE_CONFIG | overrides).items():
                command.extend([f"--{name.replace('_', '-')}", str(value)])
            result = subprocess.run(
                command, cwd=ROOT, text=True, capture_output=True, check=False,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            (output_root / f"{label}.log").write_text(
                result.stdout + result.stderr, encoding="utf-8"
            )
            if result.returncode:
                raise RuntimeError(f"{label} failed; inspect its log and manifest")
            created = set(case_root.iterdir()) - previous
            if len(created) != 1:
                raise RuntimeError(f"Expected one pipeline run for {label}")
            row = summarize_run(created.pop(), case, seed, overrides)
            rows.append(row)
            with (output_root / "summary.csv").open("w", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=row.keys())
                writer.writeheader()
                writer.writerows(rows)
            print(f"{label}: reco={row['n_reco']}, missed={row['missed']}, "
                  f"merged={row['merged']}, unmatched={row['unmatched_reco']}",
                  flush=True)
    print(f"Study summary: {output_root / 'summary.csv'}")


if __name__ == "__main__":
    main()
