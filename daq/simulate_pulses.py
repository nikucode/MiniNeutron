import argparse
import csv
import math
import random


def voltage_to_adc(voltage, vref, bits):
    max_adc = (2 ** bits) - 1

    voltage = max(0.0, min(voltage, vref))

    return round((voltage / vref) * max_adc)


def gaussian_pulse(t, center, amplitude, sigma):
    return amplitude * math.exp(
        -0.5 * ((t - center) / sigma) ** 2
    )


def main():
    parser = argparse.ArgumentParser(
        description="MiniNeutron DAQ Bench - Pulsed signal simulator"
    )

    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--rate", type=float, default=500.0)

    parser.add_argument("--vref", type=float, default=5.0)
    parser.add_argument("--bits", type=int, default=10)

    parser.add_argument("--baseline", type=float, default=0.5)
    parser.add_argument("--noise", type=float, default=0.03)

    parser.add_argument("--pulses", type=int, default=12)

    parser.add_argument(
        "--output",
        default="daq/data/simulated_pulses.csv"
    )

    args = parser.parse_args()

    total_samples = int(args.duration * args.rate)
    dt = 1.0 / args.rate

    # Generate random pulse parameters.
    pulse_parameters = []

    for _ in range(args.pulses):
        center = random.uniform(
            0.5,
            args.duration - 0.5
        )

        amplitude = random.uniform(
            0.7,
            2.5
        )

        sigma = random.uniform(
            0.015,
            0.040
        )

        pulse_parameters.append(
            (center, amplitude, sigma)
        )

    with open(args.output, "w", newline="") as file:
        writer = csv.writer(file)

        writer.writerow([
            "sample",
            "timestamp_s",
            "adc_raw",
            "voltage_V"
        ])

        for sample in range(total_samples):
            timestamp = sample * dt

            voltage = (
                args.baseline
                + random.gauss(0, args.noise)
            )

            for center, amplitude, sigma in pulse_parameters:
                voltage += gaussian_pulse(
                    timestamp,
                    center,
                    amplitude,
                    sigma
                )

            voltage = max(
                0.0,
                min(voltage, args.vref)
            )

            adc_raw = voltage_to_adc(
                voltage,
                args.vref,
                args.bits
            )

            writer.writerow([
                sample,
                timestamp,
                adc_raw,
                voltage
            ])

    print("MiniNeutron DAQ Bench - Pulsed Signal")
    print()
    print(f"duration: {args.duration} s")
    print(f"sampling rate: {args.rate} Hz")
    print(f"samples: {total_samples}")
    print(f"generated pulses: {args.pulses}")
    print(f"baseline: {args.baseline} V")
    print(f"noise sigma: {args.noise} V")
    print(f"ADC: {args.bits}-bit")
    print(f"Vref: {args.vref} V")
    print()
    print(f"output: {args.output}")


if __name__ == "__main__":
    main()