"""Five ideal trimmer settings through the existing acquisition/ADC workflow.

This is a deterministic software fixture, not a circuit or calibrated ADC model.
Run from repository root: python -m daq.demo_trimmer --output-dir results/trimmer_001
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from daq.optical_bench import HEADER, analyze, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    # Finish at baseline so the one high interval is not right-censored.
    fractions = [0.1, 0.3, 0.5, 0.7, 0.9, 0.1]
    levels = np.rint(np.array(fractions) * 1023).astype(int)
    codes = np.repeat(levels, 500)  # six 1-second plateaus at 500 Hz
    raw = args.output_dir / "synthetic_trimmer.txt"
    with raw.open("w") as output:
        output.write(HEADER + "\n")
        for i, code in enumerate(codes):
            output.write(f"{i},{i * 2000},{code}\n")
    events, manifest = analyze(raw, args.output_dir / "analysis", "synthetic")
    frame = pd.read_csv(args.output_dir / "analysis/waveform.csv")
    # Explicit failure rather than silently writing a successful report.
    if not np.array_equal(frame.adc_raw.to_numpy(), codes):
        raise RuntimeError("Round-trip ADC codes changed")
    if len(events) != 1 or events.iloc[0].trigger_time_s != 3.0 or events.iloc[0].end_time_s != 5.0:
        raise RuntimeError("Unexpected hysteresis event for this fixture")
    rows = []
    for i, (fraction, code) in enumerate(zip(fractions, levels)):
        measured = float(frame.iloc[i * 500:(i + 1) * 500].voltage_V.mean())
        rows.append({"plateau": i, "fraction": fraction, "ideal_V": 5 * fraction,
                     "adc_code": int(code), "reconstructed_V": measured,
                     "scale_error_mV": 1000 * (measured - 5 * fraction)})
    report = {"source": "synthetic", "samples": len(frame), "events": len(events),
              "trigger_s": 3.0, "rearm_s": 5.0, "plateaus": rows,
              "raw_sha256": manifest["input_sha256"], "script_sha256": digest(__file__),
              "limitations": "Ideal endpoint scaling; no loading, ADC calibration, noise or hardware measurements"}
    (args.output_dir / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(pd.DataFrame(rows).to_string(index=False))
    print("PASS: 3000 codes preserved; one event from 3 to 5 s (synthetic)")


if __name__ == "__main__":
    main()
