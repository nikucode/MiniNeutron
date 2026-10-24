#!/usr/bin/env python3
"""Reproducible MiniNeutron analysis pipeline."""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha256_file(path):
    """Hash a file in chunks so large Geant4 CSV inputs remain manageable."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the MiniNeutron detector-analysis pipeline."
    )
    parser.add_argument(
        "--input-hits", default="build/detector_hits.csv",
        help="Geant4 detector-hit CSV"
    )
    parser.add_argument(
        "--output-root", default="results/pipeline_runs",
        help="Root directory for independent runs"
    )
    parser.add_argument("--gain", type=float, default=1.0)
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--rate", type=float, default=500.0)
    parser.add_argument("--baseline", type=float, default=0.5)
    parser.add_argument("--noise-sigma", type=float, default=0.03)
    parser.add_argument("--tau", type=float, default=0.03)
    parser.add_argument("--vref", type=float, default=5.0)
    parser.add_argument("--bits", type=int, default=10)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--trigger", type=float, default=0.80)
    parser.add_argument("--rearm", type=float, default=0.65)
    parser.add_argument("--pre-window", type=float, default=0.004,
                        help="Truth association window before trigger, in seconds")
    args = parser.parse_args()

    if args.bits < 1 or args.bits > 24:
        parser.error("--bits must be between 1 and 24")
    for name in ("duration", "rate", "vref", "tau"):
        if getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if args.noise_sigma < 0:
        parser.error("--noise-sigma cannot be negative")
    if args.rearm >= args.trigger:
        parser.error("--rearm must be lower than --trigger")
    if args.pre_window < 0:
        parser.error("--pre-window cannot be negative")

    return args


def main():
    args = parse_args()
    input_hits = Path(args.input_hits)
    if not input_hits.is_absolute():
        input_hits = ROOT / input_hits
    input_hits = input_hits.resolve()

    if not input_hits.is_file():
        print(f"ERROR: input file not found: {input_hits}", file=sys.stderr)
        return 2

    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = ROOT / output_root
    output_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    run_dir = output_root / timestamp
    suffix = 1
    while run_dir.exists():
        run_dir = output_root / f"{timestamp}_{suffix}"
        suffix += 1
    run_dir.mkdir(parents=True)

    response_csv = run_dir / "detector_response_events.csv"
    waveform_csv = run_dir / "detector_waveform.csv"
    adc_max = 2 ** args.bits - 1

    manifest = {
        "pipeline": "MiniNeutron",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "input_hits": str(input_hits),
        "input_hits_sha256": sha256_file(input_hits),
        "python_version": sys.version.split()[0],
        "run_directory": str(run_dir),
        "configuration": {
            key: getattr(args, key)
            for key in (
                "gain", "duration", "rate", "baseline", "noise_sigma",
                "tau", "vref", "bits", "seed", "trigger", "rearm",
                "pre_window"
            )
        },
        "adc_max": adc_max,
        "stages": [],
        "outputs": [],
    }
    manifest_path = run_dir / "manifest.json"

    def save_manifest():
        manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    stages = [
        (
            "analyze_hits",
            [
                "analysis/analyze_detector_hits.py",
                "--input", str(input_hits),
                "--output-dir", str(run_dir),
            ],
        ),
        (
            "detector_response",
            [
                "analysis/detector_response.py",
                "--input", str(run_dir / "detector_event_summary.csv"),
                "--output", str(response_csv),
                "--gain", str(args.gain),
            ],
        ),
        (
            "build_waveform",
            [
                "analysis/build_detector_waveform.py",
                "--input", str(response_csv),
                "--output-dir", str(run_dir),
                "--duration", str(args.duration),
                "--rate", str(args.rate),
                "--baseline", str(args.baseline),
                "--noise-sigma", str(args.noise_sigma),
                "--tau", str(args.tau),
                "--vref", str(args.vref),
                "--bits", str(args.bits),
                "--seed", str(args.seed),
            ],
        ),
        (
            "validate_waveform",
            [
                "analysis/validate_data.py",
                str(waveform_csv),
                "--adc-max", str(adc_max),
            ],
        ),
        (
            "reconstruct_pulses",
            [
                "daq/analyze_pulses.py",
                "--input", str(waveform_csv),
                "--output-dir", str(run_dir / "daq"),
                "--trigger", str(args.trigger),
                "--rearm", str(args.rearm),
            ],
        ),
        (
            "compare_truth_reco",
            [
                "analysis/compare_truth_reco.py",
                "--truth", str(run_dir / "detector_waveform_truth.csv"),
                "--reco", str(run_dir / "daq" / "detected_events.csv"),
                "--output-dir", str(run_dir / "daq"),
                "--pre-window", str(args.pre_window),
            ],
        ),
    ]
    manifest["script_sha256"] = {
        script: sha256_file(ROOT / script)
        for script in ["run_pipeline.py", *(args[0] for _, args in stages)]
    }
    save_manifest()

    print(f"MiniNeutron pipeline\nInput: {input_hits}")
    print(f"Run directory: {run_dir}\n")

    for name, script_args in stages:
        command = [sys.executable, *script_args]
        stage = {
            "name": name,
            "command": command,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "running",
        }
        manifest["stages"].append(stage)
        save_manifest()
        print(f"\n=== {name} ===")

        try:
            result = subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                check=False,
            )
            stage["return_code"] = result.returncode
            stage["status"] = (
                "completed" if result.returncode == 0 else "failed"
            )
        except OSError as exc:
            stage["status"] = "failed"
            stage["error"] = str(exc)
            stage["return_code"] = None

        stage["finished_at"] = datetime.now(timezone.utc).isoformat()
        save_manifest()

        if stage["status"] != "completed":
            manifest["status"] = "failed"
            manifest["failed_stage"] = name
            manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
            save_manifest()
            print(f"\nPipeline stopped at stage: {name}", file=sys.stderr)
            print(f"Manifest: {manifest_path}", file=sys.stderr)
            return 1

    manifest["status"] = "completed"
    manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
    manifest["outputs"] = [
        str(path.relative_to(run_dir))
        for path in sorted(run_dir.rglob("*"))
        if path.is_file() and path != manifest_path
    ]
    save_manifest()

    print("\nPipeline completed successfully.")
    print(f"Results: {run_dir}")
    print(f"Manifest: {manifest_path}")
    print(f"Reconstructed events: {run_dir / 'daq/detected_events.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
