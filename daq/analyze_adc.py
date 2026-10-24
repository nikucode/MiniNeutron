import argparse
from pathlib import Path

import pandas as pd

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(
        description="MiniNeutron DAQ Bench - ADC analysis"
    )

    parser.add_argument(
        "--input",
        default="daq/data/simulated_adc.csv"
    )

    parser.add_argument(
        "--output-dir",
        default="daq/data"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

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

    n_samples = len(df)

    duration_s = (
        df["timestamp_s"].iloc[-1]
        - df["timestamp_s"].iloc[0]
    )

    if n_samples > 1:
        mean_dt = df["timestamp_s"].diff().dropna().mean()
        estimated_rate_hz = 1.0 / mean_dt
    else:
        mean_dt = float("nan")
        estimated_rate_hz = float("nan")

    voltage_mean = df["voltage_V"].mean()
    voltage_min = df["voltage_V"].min()
    voltage_max = df["voltage_V"].max()
    voltage_std = df["voltage_V"].std()

    adc_min = df["adc_raw"].min()
    adc_max = df["adc_raw"].max()
    adc_mean = df["adc_raw"].mean()

    print("MiniNeutron DAQ Bench - Analysis")
    print()
    print(f"input: {input_path}")
    print(f"samples: {n_samples}")
    print(f"duration: {duration_s:.3f} s")
    print(f"estimated rate: {estimated_rate_hz:.3f} Hz")
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

    # ----------------------------------------
    # Voltage vs time
    # ----------------------------------------

    plt.figure(figsize=(10, 5))

    plt.plot(
        df["timestamp_s"],
        df["voltage_V"]
    )

    plt.xlabel("Time [s]")
    plt.ylabel("Voltage [V]")
    plt.title("MiniNeutron DAQ Bench - Voltage vs Time")

    plt.tight_layout()

    voltage_plot = output_dir / "voltage_vs_time.png"

    plt.savefig(
        voltage_plot,
        dpi=150
    )

    plt.close()

    # ----------------------------------------
    # ADC histogram
    # ----------------------------------------

    plt.figure(figsize=(8, 5))

    plt.hist(
        df["adc_raw"],
        bins=40
    )

    plt.xlabel("ADC raw value")
    plt.ylabel("Counts")
    plt.title("MiniNeutron DAQ Bench - ADC Distribution")

    plt.tight_layout()

    adc_plot = output_dir / "adc_histogram.png"

    plt.savefig(
        adc_plot,
        dpi=150
    )

    plt.close()

    print()
    print("Generated:")
    print(voltage_plot)
    print(adc_plot)


if __name__ == "__main__":
    main()
