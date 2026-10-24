#!/usr/bin/env python3
"""Validate CSV files containing digitized detector pulses."""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "sample",
    "timestamp_s",
    "adc_raw",
    "voltage_V",
}


def validate_pulse_csv(path, adc_max=1023):
    """Return a list of validation errors; empty means valid."""
    errors = []

    try:
        df = pd.read_csv(path)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        return [f"Cannot read CSV: {exc}"]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        return [f"Missing columns: {sorted(missing)}"]

    if df.empty:
        return ["CSV contains no data rows"]

    numeric_columns = [
        "sample", "timestamp_s", "adc_raw", "voltage_V"
    ]

    for column in numeric_columns:
        values = pd.to_numeric(df[column], errors="coerce")

        if not np.isfinite(values.to_numpy(dtype=float)).all():
            errors.append(
                f"{column}: contains missing or non-numeric values"
            )
            continue

        if column == "timestamp_s":
            if not values.is_monotonic_increasing:
                errors.append("Timestamps are not ordered")
            if values.diff().iloc[1:].le(0).any():
                errors.append("Timestamps must be strictly increasing")

        elif column == "sample":
            if (values % 1 != 0).any():
                errors.append("Sample indices must be integers")
            if values.diff().iloc[1:].le(0).any():
                errors.append("Sample indices must be strictly increasing")

        elif column == "adc_raw":
            if (values % 1 != 0).any():
                errors.append("ADC values must be integers")
            if ((values < 0) | (values > adc_max)).any():
                errors.append(f"ADC values must be between 0 and {adc_max}")

    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Validate a digitized detector-pulse CSV"
    )
    parser.add_argument(
        "csv",
        nargs="?",
        default="daq/data/simulated_pulses.csv",
        help="CSV path (default: simulated_pulses.csv)",
    )
    parser.add_argument("--adc-max", type=int, default=1023)
    args = parser.parse_args()

    if args.adc_max < 1:
        parser.error("--adc-max must be positive")

    errors = validate_pulse_csv(args.csv, args.adc_max)

    if errors:
        print(f"INVALID: {args.csv}")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"VALID: {args.csv}")
    print("Required columns, numeric values, timestamps and ADC range passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
