import argparse
from pathlib import Path

import pandas as pd


def main():
    parser = argparse.ArgumentParser(
        description=(
            "MiniNeutron - simplified detector response model"
        )
    )

    parser.add_argument(
        "--input",
        default=(
            "results/detector/"
            "detector_event_summary.csv"
        ),
        help="Detector event summary CSV"
    )

    parser.add_argument(
        "--output",
        default=(
            "results/detector/"
            "detector_response_events.csv"
        ),
        help="Output detector response CSV"
    )

    parser.add_argument(
        "--gain",
        type=float,
        default=1.0,
        help="Simplified response gain in V/MeV"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------
    # LOAD EVENT-LEVEL ENERGY DEPOSITION
    # --------------------------------------------------

    df = pd.read_csv(input_path)

    required_columns = {
        "event",
        "n_hits",
        "n_tracks",
        "total_edep_MeV",
        "first_hit_time_ns",
        "last_hit_time_ns",
        "time_span_ns"
    }

    missing = (
        required_columns
        - set(df.columns)
    )

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    # --------------------------------------------------
    # SIMPLIFIED RESPONSE MODEL
    #
    # v0.1:
    #
    # amplitude = gain * deposited energy
    #
    # This is an educational transfer model.
    # It is NOT yet a calibrated model of a
    # specific scintillator, SiPM or electronics chain.
    # --------------------------------------------------

    df["response_amplitude_V"] = (
        args.gain
        * df["total_edep_MeV"]
    )

    df["response_gain_V_per_MeV"] = (
        args.gain
    )

    # --------------------------------------------------
    # OUTPUT
    # --------------------------------------------------

    output_columns = [
        "event",
        "n_hits",
        "n_tracks",
        "total_edep_MeV",
        "first_hit_time_ns",
        "last_hit_time_ns",
        "time_span_ns",
        "response_gain_V_per_MeV",
        "response_amplitude_V"
    ]

    response_df = df[
        output_columns
    ].copy()

    response_df.to_csv(
        output_path,
        index=False
    )

    # --------------------------------------------------
    # SUMMARY
    # --------------------------------------------------

    print(
        "MiniNeutron - Simplified Detector Response"
    )

    print()

    print(f"input: {input_path}")
    print(f"output: {output_path}")
    print(f"events: {len(response_df)}")
    print(f"gain: {args.gain:.3f} V/MeV")

    print()

    print("Response amplitude")

    print(
        f"minimum: "
        f"{response_df['response_amplitude_V'].min():.6e} V"
    )

    print(
        f"median: "
        f"{response_df['response_amplitude_V'].median():.6e} V"
    )

    print(
        f"mean: "
        f"{response_df['response_amplitude_V'].mean():.6e} V"
    )

    print(
        f"maximum: "
        f"{response_df['response_amplitude_V'].max():.6f} V"
    )


if __name__ == "__main__":
    main()