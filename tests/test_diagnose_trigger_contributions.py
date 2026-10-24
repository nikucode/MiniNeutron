"""Controlled checks of trigger-sample decomposition and its limits."""

import math
import unittest

import pandas as pd

from analysis.diagnose_trigger_contributions import diagnose_samples


class TestTriggerSampleDiagnosis(unittest.TestCase):
    def setUp(self):
        pulse = 0.2 * math.exp(-0.1)
        self.waveform = pd.DataFrame({
            "timestamp_s": [0.0, 0.1],
            "voltage_ideal_V": [0.7, 0.5 + pulse],
            "noise_V": [0.0, 0.15],
            "voltage_V": [0.7, 0.5 + pulse + 0.15],
        })
        self.truth = pd.DataFrame({
            "event": [5], "pulse_time_s": [0.0],
            "response_amplitude_V": [0.2],
        })
        self.reco = pd.DataFrame({"event_id": [1], "trigger_time_s": [0.1]})
        self.matches = pd.DataFrame({
            "reco_event_id": [1], "n_truth_matches": [0],
        })

    def diagnose(self, waveform=None, reco=None, matches=None):
        return diagnose_samples(
            self.waveform if waveform is None else waveform,
            self.truth,
            self.reco if reco is None else reco,
            self.matches if matches is None else matches,
            baseline=0.5, tau=1.0, trigger=0.8, vref=5.0,
        )

    def test_tail_and_noise_cross_threshold_without_temporal_candidate(self):
        row = self.diagnose().iloc[0]
        self.assertEqual(row.dominant_truth_event, 5)
        self.assertAlmostEqual(row.pulse_sum_V, 0.2 * math.exp(-0.1))
        self.assertAlmostEqual(row.time_since_dominant_pulse_s, 0.1)
        self.assertEqual(row.n_truth_candidates, 0)
        self.assertTrue(row.noise_required_at_trigger_sample)
        self.assertTrue(row.pulses_required_at_trigger_sample)

    def test_inconsistent_waveform_is_rejected(self):
        waveform = self.waveform.copy()
        waveform.loc[1, "voltage_ideal_V"] += 0.01
        with self.assertRaisesRegex(ValueError, "do not reproduce"):
            self.diagnose(waveform=waveform)

    def test_no_reconstruction_keeps_diagnostic_columns(self):
        result = self.diagnose(
            reco=self.reco.iloc[0:0], matches=self.matches.iloc[0:0]
        )
        self.assertTrue(result.empty)
        self.assertIn("noise_required_at_trigger_sample", result.columns)


if __name__ == "__main__":
    unittest.main()
