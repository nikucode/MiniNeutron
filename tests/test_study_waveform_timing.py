"""Tests for the controlled synthetic timing study."""

import unittest

import numpy as np
import pandas as pd

from analysis.study_waveform_timing import (
    aggregate_time_walk,
    calculate_time_walk,
    quantize,
    summarize,
)


class TestWaveformTimingStudy(unittest.TestCase):
    def test_quantization_has_bounded_codes_and_endpoints(self):
        values = quantize(np.array([-1.0, 0.0, 1.65, 3.3, 4.0]), 3.3, 2)
        np.testing.assert_allclose(values, [0.0, 0.0, 2.2, 3.3, 3.3])

    def test_summary_keeps_failed_detection_visible(self):
        trials = pd.DataFrame({
            "seed": [1, 1],
            "rate_hz": [500.0, 500.0],
            "noise_sigma_v": [0.0, 0.0],
            "amplitude_v": [0.2, 0.2],
            "method": ["cfd", "cfd"],
            "latency_from_onset_s": [0.01, None],
        })
        result = summarize(trials).iloc[0]
        self.assertEqual(result.trials, 2)
        self.assertEqual(result.detected, 1)
        self.assertEqual(result.detection_fraction, 0.5)
        self.assertAlmostEqual(result.mean_latency_ms, 10.0)

    def test_time_walk_is_range_across_amplitudes(self):
        summary = pd.DataFrame({
            "seed": [1, 1, 1],
            "rate_hz": [500.0, 500.0, 500.0],
            "noise_sigma_v": [0.01, 0.01, 0.01],
            "amplitude_v": [0.2, 0.5, 1.0],
            "method": ["fixed_threshold"] * 3,
            "mean_latency_ms": [6.0, 4.0, 3.5],
            "detection_fraction": [0.9, 1.0, 1.0],
        })
        result = calculate_time_walk(summary).iloc[0]
        self.assertAlmostEqual(result.time_walk_ms, 2.5)
        self.assertAlmostEqual(result.minimum_detection_fraction, 0.9)

    def test_seed_aggregation_reports_variation(self):
        per_seed = pd.DataFrame({
            "seed": [1, 2, 3],
            "rate_hz": [500.0] * 3,
            "noise_sigma_v": [0.01] * 3,
            "method": ["cfd"] * 3,
            "time_walk_ms": [0.1, 0.2, 0.3],
            "minimum_detection_fraction": [1.0, 0.9, 1.0],
        })
        result = aggregate_time_walk(per_seed).iloc[0]
        self.assertEqual(result.seeds, 3)
        self.assertAlmostEqual(result.mean_time_walk_ms, 0.2)
        self.assertAlmostEqual(result.std_time_walk_ms, 0.1)
        self.assertAlmostEqual(result.minimum_detection_fraction, 0.9)


if __name__ == "__main__":
    unittest.main()
