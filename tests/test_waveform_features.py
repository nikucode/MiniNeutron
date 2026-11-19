"""Controlled tests for the MiniNeutron waveform feature reference."""

import unittest

import numpy as np

from analysis.waveform_features import (
    WaveformConfig,
    analyze_waveform,
    interpolated_rising_crossing,
    normalized_difference_of_exponentials,
)


class TestWaveformFeatures(unittest.TestCase):
    def test_interpolated_crossing_uses_time_axis(self):
        time = np.array([0.0, 0.1, 0.4, 1.0])
        signal = np.array([0.0, 0.0, 0.6, 1.0])
        self.assertAlmostEqual(
            interpolated_rising_crossing(time, signal, 0.3), 0.25
        )

    def test_crossing_can_exclude_baseline_excursion(self):
        time = np.arange(6, dtype=float)
        signal = np.array([0.0, 0.4, 0.0, 0.0, 0.5, 1.0])
        self.assertAlmostEqual(
            interpolated_rising_crossing(
                time, signal, 0.25, start_index=3, stop_index=5
            ),
            3.5,
        )

    def test_known_triangle_recovers_features(self):
        time = np.arange(7, dtype=float)
        voltage = np.array([0.5, 0.5, 0.5, 0.5, 1.0, 1.5, 0.5])
        result = analyze_waveform(
            time,
            voltage,
            WaveformConfig(
                baseline_samples=3,
                threshold_v=0.25,
                cfd_fraction=0.5,
                voltage_min_v=0.0,
                voltage_max_v=2.0,
            ),
        )
        self.assertAlmostEqual(result["baseline_v"], 0.5)
        self.assertAlmostEqual(result["noise_rms_v"], 0.0)
        self.assertAlmostEqual(result["peak_v"], 1.0)
        self.assertAlmostEqual(result["peak_time_s"], 5.0)
        self.assertAlmostEqual(result["threshold_time_s"], 3.5)
        self.assertAlmostEqual(result["cfd_time_s"], 4.0)
        self.assertAlmostEqual(result["signed_area_v_s"], 1.5)
        self.assertEqual(result["saturation_samples"], 0)

    def test_cfd_is_amplitude_invariant_for_same_sampled_shape(self):
        time = np.linspace(0.0, 0.2, 401)
        shape = normalized_difference_of_exponentials(
            time, onset_s=0.06, rise_s=0.006, decay_s=0.03
        )
        times = []
        for amplitude in (0.2, 0.5, 1.0):
            result = analyze_waveform(
                time,
                0.5 + amplitude * shape,
                WaveformConfig(
                    baseline_samples=80,
                    threshold_v=0.1,
                    cfd_fraction=0.5,
                ),
            )
            times.append(result["cfd_time_s"])
        self.assertAlmostEqual(times[0], times[1], places=12)
        self.assertAlmostEqual(times[1], times[2], places=12)

    def test_saturation_and_invalid_time_are_explicit(self):
        time = np.arange(6, dtype=float)
        voltage = np.array([0.5, 0.5, 0.5, 1.0, 3.3, 0.5])
        result = analyze_waveform(
            time,
            voltage,
            WaveformConfig(
                baseline_samples=2,
                threshold_v=0.2,
                voltage_min_v=0.0,
                voltage_max_v=3.3,
            ),
        )
        self.assertEqual(result["saturation_samples"], 1)
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            analyze_waveform(
                [0.0, 0.1, 0.1, 0.2], [0.0, 0.0, 1.0, 0.0],
                WaveformConfig(baseline_samples=2, threshold_v=0.2),
            )


if __name__ == "__main__":
    unittest.main()
