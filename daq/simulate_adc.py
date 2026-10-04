import argparse
import csv
import math
import random


def voltage_to_adc(voltage, vref, bits):
    max_adc = (2 ** bits) - 1

    voltage = max(0.0, min(voltage, vref))

    return round((voltage / vref) * max_adc)


def main():
    parser = argparse.ArgumentParser(
        description="MiniNeutron DAQ Bench - ADC simulator"
    )

    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--rate", type=float, default=50.0)
    parser.add_argument("--vref", type=float, default=5.0)
    parser.add_argument("--bits", type=int, default=10)
    parser.add_argument(
        "--output",
        default="daq/data/simulated_adc.csv"
    )

    args = parser.parse_args()

    total_samples = int(args.duration * args.rate)
    dt = 1.0 / args.rate

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

            # señal analógica ficticia:
            # nivel medio + oscilación lenta + ruido
            voltage = (
                2.5
                + 1.0 * math.sin(2 * math.pi * 0.5 * timestamp)
                + random.gauss(0, 0.05)
            )

            voltage = max(0.0, min(voltage, args.vref))

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

    print("MiniNeutron DAQ Bench")
    print(f"samples: {total_samples}")
    print(f"rate: {args.rate} Hz")
    print(f"ADC: {args.bits}-bit")
    print(f"Vref: {args.vref} V")
    print(f"output: {args.output}")


if __name__ == "__main__":
    main()