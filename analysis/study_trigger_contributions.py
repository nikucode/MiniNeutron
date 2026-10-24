"""Apply trigger contribution diagnostics to a completed DAQ sweep."""

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


DIAGNOSE = Path(__file__).resolve().with_name("diagnose_trigger_contributions.py")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-summary", required=True,
                        help="summary.csv from study_daq_sensitivity.py")
    parser.add_argument("--output-root", required=True,
                        help="New empty directory for counterfactual runs")
    args = parser.parse_args()
    source = Path(args.study_summary).resolve()
    output_root = Path(args.output_root).resolve()
    if output_root.exists() and any(output_root.iterdir()):
        parser.error("--output-root must be empty")
    output_root.mkdir(parents=True, exist_ok=True)
    study = pd.read_csv(source)
    required = {"case", "seed", "run_dir"}
    if required - set(study.columns):
        raise ValueError(f"Missing study columns: {sorted(required - set(study.columns))}")
    if study.duplicated(["case", "seed"]).any():
        raise ValueError("Study case and seed pairs must be unique")
    (output_root / "study.json").write_text(json.dumps({
        "source_summary": str(source),
        "source_summary_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "diagnostic_script_sha256": hashlib.sha256(DIAGNOSE.read_bytes()).hexdigest(),
        "method": "Two complete DAQ counterfactual runs per source run, plus sample diagnostics",
    }, indent=2) + "\n")

    rows = []
    for item in study.itertuples(index=False):
        label = f"{item.case}_seed_{item.seed}"
        source_run = Path(item.run_dir)
        if not source_run.is_absolute():
            source_run = source.parent / source_run
        destination = output_root / "runs" / label
        command = [
            sys.executable, str(DIAGNOSE),
            "--run-dir", str(source_run), "--output-dir", str(destination),
        ]
        result = subprocess.run(command, capture_output=True, text=True,
                                check=False)
        (output_root / f"{label}.log").write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(f"{label} failed; inspect {label}.log")
        summary = json.loads((destination / "summary.json").read_text())
        row = {
            "case": item.case,
            "seed": item.seed,
            "observed_reco": summary["observed_reco"],
            "no_noise_reco": summary["counterfactual_reco"]["no_noise"],
            "no_pulses_reco": summary["counterfactual_reco"]["no_pulses"],
            "noise_required_at_trigger_sample": summary[
                "noise_required_at_trigger_sample"
            ],
            "pulses_required_at_trigger_sample": summary[
                "pulses_required_at_trigger_sample"
            ],
            "unmatched_with_noise_required_at_sample": summary[
                "unmatched_with_noise_required_at_sample"
            ],
        }
        rows.append(row)
        with (output_root / "summary.csv").open("w", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=row.keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"{label}: observed={row['observed_reco']}, "
              f"no_noise={row['no_noise_reco']}, "
              f"no_pulses={row['no_pulses_reco']}", flush=True)
    print(f"Summary: {output_root / 'summary.csv'}")


if __name__ == "__main__":
    main()
