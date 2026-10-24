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
            "MiniNeutron - build a synthetic waveform "
            "from Geant4 detector-response events"
        )
    )

    parser.add_argument(
        "--input",
        default=(
            "results/detector/"
            "detector_response_events.csv"
        ),
        help="Detector response event CSV"
    )

    parser.add_argument(
        "--output-dir",
        default="results/detector",
        help="Output directory"
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="Synthetic acquisition duration in seconds"
    )

    parser.add_argument(
        "--rate",
        type=float,
        default=500.0,
        help="Sampling rate in Hz"
    )

    parser.add_argument(
        "--baseline",
        type=float,
        default=0.5,
        help="Waveform baseline in volts"
    )

    parser.add_argument(
        "--noise-sigma",
        type=float,
        default=0.03,
        help="Gaussian noise sigma in volts"
    )

    parser.add_argument(
        "--tau",
        type=float,
        default=0.03,
        help="Pulse decay constant in seconds"
    )

    parser.add_argument(
        "--vref",
        type=float,
        default=5.0,
        help="ADC reference voltage"
    )

    parser.add_argument(
        "--bits",
        type=int,
        default=10,
        help="ADC resolution in bits"
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=12345,
        help="Random seed for reproducibility"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------
    # LOAD DETECTOR RESPONSE EVENTS
    # --------------------------------------------------

    events = pd.read_csv(
        input_path
    )

    required_columns = {
        "event",
        "total_edep_MeV",
        "first_hit_time_ns",
        "response_amplitude_V"
    }

    missing = (
        required_columns
        - set(events.columns)
    )

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if events.empty:
        raise ValueError(
            "Detector response event dataset is empty."
        )

    # --------------------------------------------------
    # SYNTHETIC EXPERIMENTAL TIMELINE
    #
    # Geant4 event times are local to each event.
    # Therefore we generate an independent experimental
    # source time for every event.
    #
    # This timeline is synthetic and does NOT represent
    # a calibrated physical neutron-source rate.
    # --------------------------------------------------

    rng = np.random.default_rng(
        args.seed
    )

    margin = 0.25

    if args.duration <= 2 * margin:
        raise ValueError(
            "Duration is too short for the selected margin."
        )

    source_times = rng.uniform(
        margin,
        args.duration - margin,
        size=len(events)
    )

    source_times.sort()

    events = events.copy()

    events["source_time_s"] = (
        source_times
    )

    # Preserve the Geant4 internal first-hit delay.
    #
    # pulse_time =
    # synthetic source time
    # +
    # Geant4 first-hit time converted from ns to s

    events["pulse_time_s"] = (
        events["source_time_s"]
        +
        events["first_hit_time_ns"] * 1e-9
    )

    # --------------------------------------------------
    # SAMPLING AXIS
    # --------------------------------------------------

    n_samples = int(
        args.duration
        * args.rate
    )

    time_s = (
        np.arange(n_samples)
        / args.rate
    )

    ideal_signal = np.zeros(
        n_samples,
        dtype=float
    )

    # --------------------------------------------------
    # BUILD PULSES
    #
    # v0.1:
    #
    # Vpulse(t) =
    # A * exp(-(t - t0) / tau)
    #
    # for t >= t0
    #
    # A comes from detector_response.py.
    # --------------------------------------------------

    for row in events.itertuples():
        t0 = row.pulse_time_s
        amplitude = row.response_amplitude_V

        mask = (
            time_s >= t0
        )

        ideal_signal[mask] += (
            amplitude
            * np.exp(
                -(
                    time_s[mask]
                    - t0
                )
                / args.tau
            )
        )

    # --------------------------------------------------
    # BASELINE + NOISE
    # --------------------------------------------------

    noise = rng.normal(
        loc=0.0,
        scale=args.noise_sigma,
        size=n_samples
    )

    voltage_before_clip = (
        args.baseline
        + ideal_signal
        + noise
    )

    voltage = np.clip(
        voltage_before_clip,
        0.0,
        args.vref
    )

    # --------------------------------------------------
    # ADC QUANTIZATION
    # --------------------------------------------------

    adc_max = (
        2 ** args.bits
        - 1
    )

    adc_raw = np.rint(
        voltage
        / args.vref
        * adc_max
    ).astype(int)

    # --------------------------------------------------
    # WAVEFORM TABLE
    # --------------------------------------------------

    waveform = pd.DataFrame(
        {
            "sample": np.arange(
                n_samples
            ),
            "timestamp_s": time_s,
            "voltage_ideal_V": (
                args.baseline
                + ideal_signal
            ),
            "noise_V": noise,
            "voltage_V": voltage,
            "adc_raw": adc_raw
        }
    )

    waveform_output = (
        output_dir
        / "detector_waveform.csv"
    )

    waveform.to_csv(
        waveform_output,
        index=False
    )

    # --------------------------------------------------
    # EVENT TRUTH TABLE
    #
    # This will later let us compare:
    #
    # generated Geant4-derived events
    # vs
    # reconstructed DAQ events
    # --------------------------------------------------

    truth_columns = [
        "event",
        "total_edep_MeV",
        "first_hit_time_ns",
        "response_amplitude_V",
        "source_time_s",
        "pulse_time_s"
    ]

    truth = events[
        truth_columns
    ].copy()

    truth_output = (
        output_dir
        / "detector_waveform_truth.csv"
    )

    truth.to_csv(
        truth_output,
        index=False
    )

    # --------------------------------------------------
    # PLOT
    # --------------------------------------------------

    plt.figure(
        figsize=(12, 5)
    )

    plt.plot(
        waveform["timestamp_s"],
        waveform["voltage_V"],
        linewidth=0.8
    )

    plt.xlabel(
        "Time [s]"
    )

    plt.ylabel(
        "Voltage [V]"
    )

    plt.title(
        "MiniNeutron - Geant4-derived Synthetic Detector Waveform"
    )

    plt.tight_layout()

    plot_output = (
        output_dir
        / "detector_waveform.png"
    )

    plt.savefig(
        plot_output,
        dpi=150
    )

    plt.close()

    # --------------------------------------------------
    # SUMMARY
    # --------------------------------------------------

    n_clipped_high = int(
        np.sum(
            voltage_before_clip
            > args.vref
        )
    )

    n_clipped_low = int(
        np.sum(
            voltage_before_clip
            < 0.0
        )
    )

    print(
        "MiniNeutron - Detector Waveform Builder"
    )

    print()

    print(f"input: {input_path}")
    print(f"events used: {len(events)}")

    print()

    print("Synthetic acquisition")
    print(
        f"duration: {args.duration:.3f} s"
    )
    print(
        f"sampling rate: {args.rate:.1f} Hz"
    )
    print(
        f"samples: {n_samples}"
    )

    print()

    print("Pulse model")
    print(
        f"decay tau: {args.tau:.6f} s"
    )
    print(
        f"baseline: {args.baseline:.3f} V"
    )
    print(
        f"noise sigma: {args.noise_sigma:.3f} V"
    )

    print()

    print("ADC")
    print(
        f"resolution: {args.bits} bits"
    )
    print(
        f"reference: {args.vref:.3f} V"
    )
    print(
        f"range: 0 to {adc_max}"
    )

    print()

    print("Waveform")
    print(
        f"minimum voltage: "
        f"{voltage.min():.6f} V"
    )
    print(
        f"mean voltage: "
        f"{voltage.mean():.6f} V"
    )
    print(
        f"maximum voltage: "
        f"{voltage.max():.6f} V"
    )
    print(
        f"high-clipped samples: "
        f"{n_clipped_high}"
    )
    print(
        f"low-clipped samples: "
        f"{n_clipped_low}"
    )

    print()

    print("Generated:")
    print(waveform_output)
    print(truth_output)
    print(plot_output)


if __name__ == "__main__":
    main()