"""Associate generated detector pulses with DAQ events by time.

An association is a candidate, not proof that a pulse caused a trigger.
"""

import argparse
import math
from pathlib import Path

import pandas as pd


TRUTH_REQUIRED = {
    "event", "total_edep_MeV", "response_amplitude_V", "pulse_time_s"
}
RECO_REQUIRED = {
    "event_id", "trigger_time_s", "peak_time_s", "peak_voltage_V",
    "end_time_s", "duration_s"
}
TRUTH_COLUMNS = [
    "event", "pulse_time_s", "total_edep_MeV", "response_amplitude_V",
    "status", "reco_event_id", "n_truth_in_reco", "candidate_reco_event_ids"
]
RECO_COLUMNS = [
    "reco_event_id", "trigger_time_s", "peak_time_s", "peak_voltage_V",
    "end_time_s", "duration_s", "n_truth_matches", "matched_truth_events",
    "matched_total_edep_MeV", "matched_response_amplitude_V",
    "n_ambiguous_truth_matches"
]


def _validated_table(table, required, id_column, name):
    missing = required - set(table.columns)
    if missing:
        raise ValueError(f"Missing {name} columns: {sorted(missing)}")
    table = table.copy()
    for column in required:
        table[column] = pd.to_numeric(table[column], errors="coerce")
        if not table[column].map(math.isfinite).all():
            raise ValueError(f"{name}.{column} must contain finite numbers")
    if (table[id_column] % 1 != 0).any() or table[id_column].duplicated().any():
        raise ValueError(f"{name} IDs must be unique integers")
    table[id_column] = table[id_column].astype(int)
    return table


def compare_events(truth, reco, pre_window=0.004):
    """Return truth and reco tables using inclusive temporal candidate windows."""
    if not math.isfinite(pre_window) or pre_window < 0:
        raise ValueError("pre_window must be finite and nonnegative")
    truth = _validated_table(truth, TRUTH_REQUIRED, "event", "truth")
    reco = _validated_table(reco, RECO_REQUIRED, "event_id", "reconstruction")
    if ((reco["trigger_time_s"] > reco["peak_time_s"]) |
            (reco["peak_time_s"] > reco["end_time_s"]) |
            (reco["duration_s"] < 0)).any():
        raise ValueError("Reconstruction times must satisfy trigger <= peak <= end")

    candidates = {event: [] for event in truth["event"]}
    reco_rows = []
    for row in reco.itertuples(index=False):
        matches = truth.loc[
            truth["pulse_time_s"].between(
                row.trigger_time_s - pre_window, row.end_time_s
            )
        ]
        matched_ids = matches["event"].tolist()
        for event in matched_ids:
            candidates[event].append(row.event_id)
        reco_rows.append({
            "reco_event_id": row.event_id,
            "trigger_time_s": row.trigger_time_s,
            "peak_time_s": row.peak_time_s,
            "peak_voltage_V": row.peak_voltage_V,
            "end_time_s": row.end_time_s,
            "duration_s": row.duration_s,
            "n_truth_matches": len(matched_ids),
            "matched_truth_events": ";".join(map(str, matched_ids)),
            "matched_total_edep_MeV": matches["total_edep_MeV"].sum(),
            "matched_response_amplitude_V": matches["response_amplitude_V"].sum(),
            "n_ambiguous_truth_matches": 0,
        })

    # Candidate counts are final only after every reconstruction window is read.
    for reco_row in reco_rows:
        matched_ids = reco_row["matched_truth_events"].split(";")
        reco_row["n_ambiguous_truth_matches"] = sum(
            len(candidates[int(event)]) > 1
            for event in matched_ids if event
        )

    counts = {row["reco_event_id"]: row["n_truth_matches"] for row in reco_rows}
    truth_rows = []
    for row in truth.itertuples(index=False):
        linked = candidates[row.event]
        if len(linked) > 1:
            status = "ambiguous"
        elif not linked:
            status = "missed"
        elif counts[linked[0]] == 1:
            status = "individual"
        else:
            status = "merged"
        truth_rows.append({
            "event": row.event,
            "pulse_time_s": row.pulse_time_s,
            "total_edep_MeV": row.total_edep_MeV,
            "response_amplitude_V": row.response_amplitude_V,
            "status": status,
            "reco_event_id": linked[0] if len(linked) == 1 else None,
            "n_truth_in_reco": (
                counts[linked[0]] if len(linked) == 1
                else 0 if not linked else None
            ),
            "candidate_reco_event_ids": ";".join(map(str, linked)),
        })

    return (
        pd.DataFrame(truth_rows, columns=TRUTH_COLUMNS),
        pd.DataFrame(reco_rows, columns=RECO_COLUMNS),
    )


def main():
    parser = argparse.ArgumentParser(
        description="Associate Geant4-derived truth pulses with DAQ events"
    )
    parser.add_argument("--truth", default="results/detector/detector_waveform_truth.csv")
    parser.add_argument("--reco", default="results/detector/daq/detected_events.csv")
    parser.add_argument("--output-dir", default="results/detector/daq")
    parser.add_argument("--pre-window", type=float, default=0.004,
                        help="Seconds allowed before trigger for candidate association")
    args = parser.parse_args()

    truth_table, reco_table = compare_events(
        pd.read_csv(args.truth), pd.read_csv(args.reco), args.pre_window
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    truth_path = output_dir / "truth_reconstruction_comparison.csv"
    reco_path = output_dir / "reconstructed_event_matches.csv"
    truth_table.to_csv(truth_path, index=False)
    reco_table.to_csv(reco_path, index=False)

    print("MiniNeutron - Truth vs DAQ Reconstruction")
    print(f"truth events: {len(truth_table)}")
    print(f"reconstructed events: {len(reco_table)}")
    print("Truth-event temporal classification:")
    for status in ("individual", "merged", "missed", "ambiguous"):
        print(f"  {status}: {truth_table['status'].eq(status).sum()}")
    print("Reconstructed-event temporal classification:")
    for label, count in (
        ("single-truth candidates", reco_table["n_truth_matches"].eq(1).sum()),
        ("multi-truth candidates", reco_table["n_truth_matches"].gt(1).sum()),
        ("without truth candidate", reco_table["n_truth_matches"].eq(0).sum()),
    ):
        print(f"  {label}: {count}")
    print("Temporal association is not detector efficiency or causal attribution.")
    print(f"Generated:\n{truth_path}\n{reco_path}")


if __name__ == "__main__":
    main()
