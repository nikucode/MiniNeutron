"""Tests for the paired CFD-fraction study."""

import unittest

import numpy as np
import pandas as pd

from analysis.study_cfd_fraction import (
    aggregate_seeds,
    analyze_fractions,
    mark_pareto,
)


class TestCFDFractionStudy(unittest.TestCase):
    def test_all_fractions_share_waveform_features(self):
        time = np.linspace(0.0, 0.2, 401)
        voltage = np.full_like(time, 0.5)
        voltage[120:141] += np.linspace(0.0, 1.0, 21)
        voltage[141:] += np.exp(-np.arange(len(time) - 141) / 20)
        rows = analyze_fractions(
            time, voltage, baseline_samples=80,
            settings={"threshold_v": 0.1, "vref_v": 3.3},
            fractions=[0.2, 0.5, 0.8],
        )
        self.assertEqual(len(rows), 3)
        self.assertEqual({row["peak_v"] for row in rows}, {1.0})
        self.assertEqual({row["noise_rms_v"] for row in rows}, {0.0})
        self.assertLess(rows[0]["estimate_s"], rows[1]["estimate_s"])
        self.assertLess(rows[1]["estimate_s"], rows[2]["estimate_s"])

    def test_pareto_rejects_only_dominated_fraction(self):
        data = pd.DataFrame({
            "rate_hz": [500.0] * 3,
            "noise_sigma_v": [0.01] * 3,
            "cfd_fraction": [0.2, 0.4, 0.6],
            "mean_time_walk_ms": [0.30, 0.20, 0.15],
            "mean_worst_jitter_ms": [0.40, 0.30, 0.45],
            "minimum_crossing_fraction": [1.0, 1.0, 1.0],
        })
        flags = mark_pareto(data)
        self.assertEqual(flags.tolist(), [False, True, True])

    def test_seed_aggregation_keeps_both_objectives(self):
        per_seed = pd.DataFrame({
            "seed": [1, 2],
            "rate_hz": [1000.0, 1000.0],
            "noise_sigma_v": [0.01, 0.01],
            "cfd_fraction": [0.5, 0.5],
            "time_walk_ms": [0.1, 0.2],
            "mean_jitter_ms": [0.3, 0.4],
            "worst_jitter_ms": [0.5, 0.7],
            "minimum_crossing_fraction": [1.0, 0.9],
        })
        result = aggregate_seeds(per_seed).iloc[0]
        self.assertAlmostEqual(result.mean_time_walk_ms, 0.15)
        self.assertAlmostEqual(result.mean_worst_jitter_ms, 0.6)
        self.assertAlmostEqual(result.minimum_crossing_fraction, 0.9)
        self.assertTrue(result.pareto_nondominated)


if __name__ == "__main__":
    unittest.main()
