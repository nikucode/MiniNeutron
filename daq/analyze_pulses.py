import argparse
import math
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path

import pandas as pd

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt


def adc_threshold_codes(trigger_v, rearm_v, vref, bits):
    """Convert voltage thresholds to inclusive integer ADC comparisons.

    Trigger uses ``adc_raw >= ceil(trigger/Vref * ADCmax)``. Rearm uses
    ``adc_raw <= floor(rearm/Vref * ADCmax)``. Decimal arithmetic avoids
    moving an exact code boundary by one count due to binary float rounding.
    """
    if bits < 1 or bits > 24 or not math.isfinite(vref) or vref <= 0:
        raise ValueError("bits must be 1–24 and Vref must be positive")
    if not all(map(math.isfinite, (trigger_v, rearm_v))):
        raise ValueError("thresholds must be finite")
    if rearm_v < 0 or rearm_v >= trigger_v:
        raise ValueError("thresholds must satisfy 0 <= rearm < trigger")
    scale = Decimal(2 ** bits - 1) / Decimal(str(vref))
    trigger_code = int((Decimal(str(trigger_v)) * scale).to_integral_value(
        rounding=ROUND_CEILING
    ))
    rearm_code = int((Decimal(str(rearm_v)) * scale).to_integral_value(
        rounding=ROUND_FLOOR
    ))
    return trigger_code, rearm_code


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
    parser.add_argument(
        "--trigger-source", choices=("voltage", "adc"), default="voltage",
        help="Use sampled analog voltage or quantized ADC counts for DAQ decisions"
    )
    parser.add_argument("--vref", type=float, default=5.0)
    parser.add_argument("--bits", type=int, default=10)

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

    trigger_code, rearm_code = adc_threshold_codes(
        trigger_threshold_V, rearm_threshold_V, args.vref, args.bits
    )
    adc_maximum = 2 ** args.bits - 1
    if args.trigger_source == "adc":
        adc_values = pd.to_numeric(df["adc_raw"], errors="coerce")
        if (not adc_values.map(math.isfinite).all()
                or (adc_values % 1 != 0).any()
                or ((adc_values < 0) | (adc_values > adc_maximum)).any()):
            raise ValueError("ADC samples must be integer codes within range")
        df["daq_signal"] = adc_values.astype(int)
        df["plot_signal_V"] = df["daq_signal"] * args.vref / adc_maximum
        trigger_level = trigger_code
        rearm_level = rearm_code
        plot_trigger_V = trigger_code * args.vref / adc_maximum
        plot_rearm_V = rearm_code * args.vref / adc_maximum
    else:
        df["daq_signal"] = df["voltage_V"]
        df["plot_signal_V"] = df["voltage_V"]
        trigger_level = trigger_threshold_V
        rearm_level = rearm_threshold_V
        plot_trigger_V = trigger_threshold_V
        plot_rearm_V = rearm_threshold_V

    def peak_voltage(level):
        return (level * args.vref / adc_maximum
                if args.trigger_source == "adc" else level)

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
    peak_level = None

    for index, row in df.iterrows():
        level = row["daq_signal"]

        # Start a new event
        if armed and level >= trigger_level:
            event_id += 1

            armed = False
            event_active = True

            trigger_index = index
            trigger_time = row["timestamp_s"]

            peak_index = index
            peak_level = level

        # Track the pulse maximum while the event is active
        if event_active:
            if level > peak_level:
                peak_level = level
                peak_index = index

            # Close the event once the signal falls below
            # the rearm threshold
            if (
                index > trigger_index
                and level <= rearm_level
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
                    "peak_voltage_V": peak_voltage(peak_level),
                    "peak_adc": peak_adc,
                    "end_time_s": end_time,
                    "duration_s": duration,
                    "trigger_source": args.trigger_source,
                })

                event_active = False
                armed = True

                trigger_index = None
                trigger_time = None
                peak_index = None
                peak_level = None

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
            "peak_voltage_V": peak_voltage(peak_level),
            "peak_adc": peak_adc,
            "end_time_s": end_time,
            "duration_s": duration,
            "trigger_source": args.trigger_source,
        })

    events_df = pd.DataFrame(built_events, columns=[
        "event_id", "trigger_time_s", "peak_time_s", "peak_voltage_V",
        "peak_adc", "end_time_s", "duration_s", "trigger_source"
    ])

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
    print(f"source: {args.trigger_source}")
    print(
        f"trigger threshold: "
        f"{trigger_threshold_V:.3f} V"
    )
    print(
        f"rearm threshold: "
        f"{rearm_threshold_V:.3f} V"
    )
    if args.trigger_source == "adc":
        print(f"ADC: {args.bits} bits, Vref = {args.vref:.3f} V")
        print(f"trigger code: >= {trigger_code} ({plot_trigger_V:.6f} V)")
        print(f"rearm code: <= {rearm_code} ({plot_rearm_V:.6f} V)")
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

    # Show the voltage actually used by the selected trigger mode.
    plt.plot(
        df["timestamp_s"],
        df["plot_signal_V"],
        label=("ADC reconstructed signal" if args.trigger_source == "adc"
               else "Signal")
    )

    # Trigger threshold
    plt.axhline(
        plot_trigger_V,
        linestyle="--",
        label=(
            f"Trigger = {plot_trigger_V:.3f} V"
        )
    )

    # Rearm threshold
    plt.axhline(
        plot_rearm_V,
        linestyle=":",
        label=(
            f"Rearm = {plot_rearm_V:.3f} V"
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
                trigger_row["plot_signal_V"]
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
