"""Reusable waveform features for MiniNeutron synthetic signals.

All public functions use seconds and volts.  The module contains no DRS4
data, file format, acquisition constant, or detector-specific calibration.
It is a small reference implementation for controlled truth/reconstruction
studies inside MiniNeutron.
"""

from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class WaveformConfig:
    """Configuration for one positive-pulse waveform."""

    baseline_samples: int
    threshold_v: float
    cfd_fraction: float = 0.5
    baseline_method: str = "mean"
    voltage_min_v: float | None = None
    voltage_max_v: float | None = None

    def validate(self):
        if self.baseline_samples < 2:
            raise ValueError("baseline_samples must be at least 2")
        if not math.isfinite(self.threshold_v) or self.threshold_v <= 0:
            raise ValueError("threshold_v must be finite and positive")
        if not math.isfinite(self.cfd_fraction) or not 0 < self.cfd_fraction < 1:
            raise ValueError("cfd_fraction must be between 0 and 1")
        if self.baseline_method not in {"mean", "median"}:
            raise ValueError("baseline_method must be 'mean' or 'median'")
        for name, value in (
            ("voltage_min_v", self.voltage_min_v),
            ("voltage_max_v", self.voltage_max_v),
        ):
            if value is not None and not math.isfinite(value):
                raise ValueError(f"{name} must be finite when provided")
        if (self.voltage_min_v is not None
                and self.voltage_max_v is not None
                and self.voltage_min_v >= self.voltage_max_v):
            raise ValueError("voltage_min_v must be lower than voltage_max_v")


def _validated_arrays(time_s, voltage_v):
    time = np.asarray(time_s, dtype=float)
    voltage = np.asarray(voltage_v, dtype=float)
    if time.ndim != 1 or voltage.ndim != 1 or time.size != voltage.size:
        raise ValueError("time_s and voltage_v must be equal-length 1D arrays")
    if time.size < 3:
        raise ValueError("at least three waveform samples are required")
    if not np.isfinite(time).all() or not np.isfinite(voltage).all():
        raise ValueError("waveform values must be finite")
    if not np.all(np.diff(time) > 0):
        raise ValueError("time_s must be strictly increasing")
    return time, voltage


def interpolated_rising_crossing(
    time_s, signal_v, level_v, start_index=1, stop_index=None
):
    """Return the first linearly interpolated rising crossing, or ``None``."""

    time, signal = _validated_arrays(time_s, signal_v)
    if not math.isfinite(level_v):
        raise ValueError("level_v must be finite")
    start = int(start_index)
    stop = len(signal) - 1 if stop_index is None else int(stop_index)
    if start < 1 or start >= len(signal):
        raise ValueError("start_index must select a valid crossing interval")
    if stop < start or stop >= len(signal):
        raise ValueError("stop_index must not precede start_index")
    for index in range(start, stop + 1):
        before = signal[index - 1]
        after = signal[index]
        if before < level_v <= after:
            if after == before:
                return float(time[index])
            fraction = (level_v - before) / (after - before)
            return float(time[index - 1] + fraction * (time[index] - time[index - 1]))
    return None


def analyze_waveform(time_s, voltage_v, config):
    """Extract baseline, noise, area, amplitude, and three timing estimates.

    Threshold and CFD levels are relative to the estimated baseline.  Area is
    integrated from the end of the baseline region to the final sample.  The
    returned values describe the sampled waveform; they are not calibrated
    detector observables.
    """

    if not isinstance(config, WaveformConfig):
        raise TypeError("config must be a WaveformConfig")
    config.validate()
    time, voltage = _validated_arrays(time_s, voltage_v)
    if config.baseline_samples >= len(voltage) - 1:
        raise ValueError("baseline region must leave at least two signal samples")

    baseline_region = voltage[:config.baseline_samples]
    if config.baseline_method == "mean":
        baseline = float(np.mean(baseline_region))
    else:
        baseline = float(np.median(baseline_region))
    noise_rms = float(np.std(baseline_region, ddof=1))
    corrected = voltage - baseline

    signal_start = config.baseline_samples
    peak_index = signal_start + int(np.argmax(corrected[signal_start:]))
    peak_v = float(corrected[peak_index])
    peak_time_s = float(time[peak_index])
    threshold_time_s = interpolated_rising_crossing(
        time, corrected, config.threshold_v,
        start_index=signal_start, stop_index=peak_index
    )
    cfd_time_s = None
    if peak_v > 0:
        cfd_time_s = interpolated_rising_crossing(
            time, corrected, config.cfd_fraction * peak_v,
            start_index=signal_start, stop_index=peak_index,
        )

    signal_time = time[signal_start:]
    signal_voltage = corrected[signal_start:]
    signed_area_v_s = float(np.trapezoid(signal_voltage, signal_time))
    positive_area_v_s = float(np.trapezoid(
        np.maximum(signal_voltage, 0.0), signal_time
    ))
    saturation_samples = 0
    if config.voltage_min_v is not None:
        saturation_samples += int(np.count_nonzero(voltage <= config.voltage_min_v))
    if config.voltage_max_v is not None:
        saturation_samples += int(np.count_nonzero(voltage >= config.voltage_max_v))

    return {
        "baseline_v": baseline,
        "noise_rms_v": noise_rms,
        "peak_v": peak_v,
        "peak_time_s": peak_time_s,
        "threshold_time_s": threshold_time_s,
        "cfd_time_s": cfd_time_s,
        "signed_area_v_s": signed_area_v_s,
        "positive_area_v_s": positive_area_v_s,
        "saturation_samples": saturation_samples,
        "peak_at_edge": peak_index in {signal_start, len(voltage) - 1},
        "threshold_found": threshold_time_s is not None,
        "cfd_found": cfd_time_s is not None,
    }


def normalized_difference_of_exponentials(time_s, onset_s, rise_s, decay_s):
    """Return a causal pulse shape with an analytical unit-height maximum."""

    time = np.asarray(time_s, dtype=float)
    if time.ndim != 1 or not np.isfinite(time).all():
        raise ValueError("time_s must be a finite 1D array")
    if not all(math.isfinite(value) and value > 0 for value in (rise_s, decay_s)):
        raise ValueError("rise_s and decay_s must be finite and positive")
    if not math.isfinite(onset_s):
        raise ValueError("onset_s must be finite")
    elapsed = time - onset_s
    shape = np.zeros_like(time)
    active = elapsed >= 0
    shape[active] = (
        (1.0 - np.exp(-elapsed[active] / rise_s))
        * np.exp(-elapsed[active] / decay_s)
    )
    peak_elapsed = rise_s * math.log1p(decay_s / rise_s)
    peak_shape = (
        (1.0 - math.exp(-peak_elapsed / rise_s))
        * math.exp(-peak_elapsed / decay_s)
    )
    return shape / peak_shape
