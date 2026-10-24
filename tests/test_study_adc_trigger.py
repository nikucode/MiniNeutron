"""Tests for controlled ADC quantization and temporal window links."""

import unittest

import pandas as pd

from analysis.study_adc_trigger import compare_windows, quantize_voltage


class TestADCStudy(unittest.TestCase):
    def test_quantization_matches_round_to_nearest_even(self):
        waveform = pd.DataFrame({"voltage_V": [0.0, 0.5, 1.5, 4.0]})
        codes = quantize_voltage(waveform, vref=4.0, bits=3).adc_raw.tolist()
        self.assertEqual(codes, [0, 1, 3, 7])

    def test_merger_and_adc_only_window_are_visible(self):
        voltage = pd.DataFrame({
            "event_id": [1, 2, 3], "trigger_time_s": [1.0, 1.4, 3.0],
            "end_time_s": [1.3, 1.7, 3.2],
        })
        adc = pd.DataFrame({
            "event_id": [1, 2], "trigger_time_s": [1.1, 2.0],
            "end_time_s": [1.6, 2.2],
        })
        pairs, stats = compare_windows(voltage, adc)
        self.assertEqual(stats["adc_windows_overlapping_multiple_voltage"], 1)
        self.assertEqual(stats["voltage_only"], 1)
        self.assertEqual(stats["adc_only"], 1)
        self.assertEqual(stats["one_to_one_links"], 0)
        self.assertEqual(len(pairs), 4)
        for overlap in pairs.overlap_s.dropna():
            self.assertAlmostEqual(overlap, 0.2)


if __name__ == "__main__":
    unittest.main()
