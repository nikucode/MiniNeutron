import argparse
from pathlib import Path

import pandas as pd

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(
        description="MiniNeutron DAQ Bench - Pulsed signal analysis"
    )

    parser.add_argument(
        "--input",
        default="daq/data/simulated_pulses.csv"
    )

    parser.add_argument(
        "--output-dir",
        default="daq/data"
    )

    parser.add_argument(
        "--trigger",
        type=float,
        default=0.80,
        help="Trigger threshold in volts"
    )

    parser.add_argument(
        "--rearm",
        type=float,
        default=0.65,
        help="Rearm threshold in volts"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------
    # Load data
    # --------------------------------------------------

    df = pd.read_csv(input_path)

    required_columns = {
        "sample",
        "timestamp_s",
        "adc_raw",
        "voltage_V"
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if len(df) < 2:
        raise ValueError(
            "At least two samples are required for analysis."
        )

    trigger_threshold_V = args.trigger
    rearm_threshold_V = args.rearm

    if rearm_threshold_V >= trigger_threshold_V:
        raise ValueError(
            "Rearm threshold must be lower than trigger threshold."
        )

    # --------------------------------------------------
    # Basic signal statistics
    # --------------------------------------------------

    n_samples = len(df)

    mean_dt = (
        df["timestamp_s"]
        .diff()
        .dropna()
        .mean()
    )

    estimated_rate_hz = 1.0 / mean_dt

    duration_s = (
        df["timestamp_s"].iloc[-1]
        - df["timestamp_s"].iloc[0]
    )

    voltage_mean = df["voltage_V"].mean()
    voltage_std = df["voltage_V"].std()
    voltage_min = df["voltage_V"].min()
    voltage_max = df["voltage_V"].max()

    adc_mean = df["adc_raw"].mean()
    adc_min = df["adc_raw"].min()
    adc_max = df["adc_raw"].max()

    # --------------------------------------------------
    # Trigger + hysteresis event builder
    #
    # Event opens when the signal crosses the trigger
    # threshold while armed.
    #
    # Event closes when the signal falls below the
    # rearm threshold.
    #
    # While the event is active, the highest sample
    # is stored as the pulse peak.
    # --------------------------------------------------

    built_events = []

    armed = True
    event_active = False

    event_id = 0

    trigger_index = None
    trigger_time = None

    peak_index = None
    peak_voltage = None

    for index, row in df.iterrows():
        voltage = row["voltage_V"]

        # Start a new event
        if armed and voltage >= trigger_threshold_V:
            event_id += 1

            armed = False
            event_active = True

            trigger_index = index
            trigger_time = row["timestamp_s"]

            peak_index = index
            peak_voltage = voltage

        # Track the pulse maximum while the event is active
        if event_active:
            if voltage > peak_voltage:
                peak_voltage = voltage
                peak_index = index

            # Close the event once the signal falls below
            # the rearm threshold
            if (
                index > trigger_index
                and voltage <= rearm_threshold_V
            ):
                peak_time = df.loc[
                    peak_index,
                    "timestamp_s"
                ]

                peak_adc = df.loc[
                    peak_index,
                    "adc_raw"
                ]

                end_time = row["timestamp_s"]

                duration = (
                    end_time
                    - trigger_time
                )

                built_events.append({
                    "event_id": event_id,
                    "trigger_time_s": trigger_time,
                    "peak_time_s": peak_time,
                    "peak_voltage_V": peak_voltage,
                    "peak_adc": peak_adc,
                    "end_time_s": end_time,
                    "duration_s": duration
                })

                event_active = False
                armed = True

                trigger_index = None
                trigger_time = None
                peak_index = None
                peak_voltage = None

    # --------------------------------------------------
    # Handle an event that remains active at the end
    # of the dataset
    # --------------------------------------------------

    if event_active:
        peak_time = df.loc[
            peak_index,
            "timestamp_s"
        ]

        peak_adc = df.loc[
            peak_index,
            "adc_raw"
        ]

        end_time = df[
            "timestamp_s"
        ].iloc[-1]

        duration = (
            end_time
            - trigger_time
        )

        built_events.append({
            "event_id": event_id,
            "trigger_time_s": trigger_time,
            "peak_time_s": peak_time,
            "peak_voltage_V": peak_voltage,
            "peak_adc": peak_adc,
            "end_time_s": end_time,
            "duration_s": duration
        })

    events_df = pd.DataFrame(built_events)

    n_events = len(events_df)

    # --------------------------------------------------
    # Save event table
    # --------------------------------------------------

    events_output = (
        output_dir
        / "detected_events.csv"
    )

    events_df.to_csv(
        events_output,
        index=False
    )

    # --------------------------------------------------
    # Terminal summary
    # --------------------------------------------------

    print(
        "MiniNeutron DAQ Bench - Pulsed Signal Analysis"
    )

    print()

    print(f"input: {input_path}")
    print(f"samples: {n_samples}")
    print(f"duration: {duration_s:.3f} s")
    print(
        f"estimated rate: "
        f"{estimated_rate_hz:.3f} Hz"
    )

    print()

    print("Voltage")
    print(f"mean: {voltage_mean:.4f} V")
    print(f"std:  {voltage_std:.4f} V")
    print(f"min:  {voltage_min:.4f} V")
    print(f"max:  {voltage_max:.4f} V")

    print()

    print("ADC")
    print(f"mean: {adc_mean:.2f}")
    print(f"min:  {adc_min}")
    print(f"max:  {adc_max}")

    print()

    print("Trigger configuration")
    print(
        f"trigger threshold: "
        f"{trigger_threshold_V:.3f} V"
    )
    print(
        f"rearm threshold: "
        f"{rearm_threshold_V:.3f} V"
    )
    print(
        f"built events: "
        f"{n_events}"
    )

    print()

    print("Built events")

    if n_events > 0:
        print(
            events_df.to_string(
                index=False
            )
        )
    else:
        print("No events detected.")

    # --------------------------------------------------
    # Plot
    # --------------------------------------------------

    plt.figure(
        figsize=(12, 5)
    )

    # Full digitized waveform
    plt.plot(
        df["timestamp_s"],
        df["voltage_V"],
        label="Signal"
    )

    # Trigger threshold
    plt.axhline(
        trigger_threshold_V,
        linestyle="--",
        label=(
            f"Trigger = "
            f"{trigger_threshold_V:.2f} V"
        )
    )

    # Rearm threshold
    plt.axhline(
        rearm_threshold_V,
        linestyle=":",
        label=(
            f"Rearm = "
            f"{rearm_threshold_V:.2f} V"
        )
    )

    # Event trigger points
    if n_events > 0:
        trigger_times = (
            events_df["trigger_time_s"]
        )

        trigger_voltages = []

        for trigger_time in trigger_times:
            trigger_row = df[
                df["timestamp_s"]
                == trigger_time
            ].iloc[0]

            trigger_voltages.append(
                trigger_row["voltage_V"]
            )

        plt.scatter(
            trigger_times,
            trigger_voltages,
            label="Detected events",
            zorder=3
        )

        # Pulse peaks
        plt.scatter(
            events_df["peak_time_s"],
            events_df["peak_voltage_V"],
            marker="x",
            label="Pulse peaks",
            zorder=4
        )

    plt.xlabel("Time [s]")
    plt.ylabel("Voltage [V]")

    plt.title(
        "MiniNeutron DAQ Bench - "
        "Simulated Pulsed Signal"
    )

    plt.legend()

    plt.tight_layout()

    output_plot = (
        output_dir
        / "simulated_pulses.png"
    )

    plt.savefig(
        output_plot,
        dpi=150
    )

    plt.close()

    # --------------------------------------------------
    # Output summary
    # --------------------------------------------------

    print()

    print("Generated:")
    print(output_plot)
    print(events_output)


if __name__ == "__main__":
    main()