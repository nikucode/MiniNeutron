import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(
        description=(
            "MiniNeutron - analysis of energy-depositing "
            "steps inside the virtual detector"
        )
    )

    parser.add_argument(
        "--input",
        default="build/detector_hits.csv",
        help="Input detector_hits.csv file"
    )

    parser.add_argument(
        "--output-dir",
        default="results/detector",
        help="Directory for detector-analysis outputs"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------

    df = pd.read_csv(input_path)

    required_columns = {
        "event",
        "track_id",
        "parent_id",
        "particle",
        "time_ns",
        "x_mm",
        "y_mm",
        "z_mm",
        "edep_MeV",
        "process"
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if df.empty:
        raise ValueError(
            "The detector hit dataset is empty."
        )

    # --------------------------------------------------
    # BASIC STATISTICS
    # --------------------------------------------------

    n_records = len(df)
    n_events = df["event"].nunique()
    n_tracks = (
        df[["event", "track_id"]]
        .drop_duplicates()
        .shape[0]
    )

    total_edep = df["edep_MeV"].sum()
    mean_edep_step = df["edep_MeV"].mean()
    max_edep_step = df["edep_MeV"].max()

    # --------------------------------------------------
    # EVENT SUMMARY
    #
    # Each row of detector_hits.csv is currently one
    # energy-depositing Geant4 step inside the detector.
    #
    # Here we combine all deposits belonging to the same
    # Geant4 event.
    # --------------------------------------------------

    event_summary = (
        df.groupby("event")
        .agg(
            n_hits=("edep_MeV", "size"),
            n_tracks=("track_id", "nunique"),
            total_edep_MeV=("edep_MeV", "sum"),
            first_hit_time_ns=("time_ns", "min"),
            last_hit_time_ns=("time_ns", "max")
        )
        .reset_index()
    )

    event_summary["time_span_ns"] = (
        event_summary["last_hit_time_ns"]
        - event_summary["first_hit_time_ns"]
    )

    # --------------------------------------------------
    # PARTICLE SUMMARY
    # --------------------------------------------------

    particle_summary = (
        df.groupby("particle")
        .agg(
            n_hits=("edep_MeV", "size"),
            n_events=("event", "nunique"),
            total_edep_MeV=("edep_MeV", "sum"),
            mean_edep_MeV=("edep_MeV", "mean"),
            max_edep_MeV=("edep_MeV", "max")
        )
        .reset_index()
        .sort_values(
            "total_edep_MeV",
            ascending=False
        )
    )

    # --------------------------------------------------
    # PROCESS SUMMARY
    # --------------------------------------------------

    process_summary = (
        df.groupby("process")
        .agg(
            n_hits=("edep_MeV", "size"),
            total_edep_MeV=("edep_MeV", "sum")
        )
        .reset_index()
        .sort_values(
            "total_edep_MeV",
            ascending=False
        )
    )

    # --------------------------------------------------
    # SAVE TABLES
    # --------------------------------------------------

    event_output = (
        output_dir
        / "detector_event_summary.csv"
    )

    particle_output = (
        output_dir
        / "detector_particle_summary.csv"
    )

    process_output = (
        output_dir
        / "detector_process_summary.csv"
    )

    event_summary.to_csv(
        event_output,
        index=False
    )

    particle_summary.to_csv(
        particle_output,
        index=False
    )

    process_summary.to_csv(
        process_output,
        index=False
    )

    # --------------------------------------------------
    # TERMINAL SUMMARY
    # --------------------------------------------------

    print(
        "MiniNeutron - Virtual Detector Analysis"
    )

    print()

    print(f"input: {input_path}")
    print(f"energy-depositing steps: {n_records}")
    print(f"events with deposited energy: {n_events}")
    print(f"tracks contributing energy: {n_tracks}")

    print()

    print("Energy deposition")
    print(
        f"total deposited energy: "
        f"{total_edep:.6f} MeV"
    )
    print(
        f"mean deposit per step: "
        f"{mean_edep_step:.6e} MeV"
    )
    print(
        f"maximum deposit in one step: "
        f"{max_edep_step:.6f} MeV"
    )

    print()

    print("Event summary")
    print(
        f"mean deposited energy per event: "
        f"{event_summary['total_edep_MeV'].mean():.6f} MeV"
    )
    print(
        f"median deposited energy per event: "
        f"{event_summary['total_edep_MeV'].median():.6f} MeV"
    )
    print(
        f"maximum deposited energy in one event: "
        f"{event_summary['total_edep_MeV'].max():.6f} MeV"
    )

    print()

    print("Particles contributing deposited energy")
    print(
        particle_summary.to_string(
            index=False
        )
    )

    print()

    print("Processes contributing deposited energy")
    print(
        process_summary.to_string(
            index=False
        )
    )

    # --------------------------------------------------
    # PLOT 1:
    # TOTAL DEPOSITED ENERGY PER EVENT
    # --------------------------------------------------

    plt.figure(
        figsize=(9, 5)
    )

    plt.hist(
        event_summary["total_edep_MeV"],
        bins=40
    )

    plt.xlabel(
        "Total deposited energy per event [MeV]"
    )

    plt.ylabel(
        "Events"
    )

    plt.title(
        "MiniNeutron - Detector Energy Deposition"
    )

    plt.tight_layout()

    edep_plot = (
        output_dir
        / "detector_event_edep_distribution.png"
    )

    plt.savefig(
        edep_plot,
        dpi=150
    )

    plt.close()

    # --------------------------------------------------
    # PLOT 1B:
    # LOG-SPACED ENERGY DISTRIBUTION
    # --------------------------------------------------

    positive_edep = event_summary[
        event_summary["total_edep_MeV"] > 0
    ]["total_edep_MeV"]

    min_edep = positive_edep.min()
    max_edep = positive_edep.max()

    log_bins = np.logspace(
        np.log10(min_edep),
        np.log10(max_edep),
        41
    )

    plt.figure(
        figsize=(9, 5)
    )

    plt.hist(
        positive_edep,
        bins=log_bins
    )

    plt.xscale("log")

    plt.xlabel(
        "Total deposited energy per event [MeV]"
    )

    plt.ylabel(
        "Events"
    )

    plt.title(
        "MiniNeutron - Detector Energy Deposition (log-spaced bins)"
    )

    plt.tight_layout()

    edep_log_plot = (
        output_dir
        / "detector_event_edep_log_distribution.png"
    )

    plt.savefig(
        edep_log_plot,
        dpi=150
    )

    plt.close()

    # --------------------------------------------------
    # PLOT 2:
    # DEPOSITED ENERGY BY PARTICLE TYPE
    # --------------------------------------------------

    plt.figure(
        figsize=(10, 5)
    )

    plt.bar(
        particle_summary["particle"],
        particle_summary["total_edep_MeV"]
    )

    plt.xlabel(
        "Particle"
    )

    plt.ylabel(
        "Total deposited energy [MeV]"
    )

    plt.title(
        "MiniNeutron - Deposited Energy by Particle"
    )

    plt.xticks(
        rotation=45,
        ha="right"
    )

    plt.tight_layout()

    particle_plot = (
        output_dir
        / "detector_edep_by_particle.png"
    )

    plt.savefig(
        particle_plot,
        dpi=150
    )

    plt.close()

    # --------------------------------------------------
    # OUTPUT SUMMARY
    # ---------------------------------------------------------------------------------------------------

    print()

    print("Generated:")
    print(event_output)
    print(particle_output)
    print(process_output)
    print(edep_plot)
    print(edep_log_plot)
    print(particle_plot)


if __name__ == "__main__":
    main()