"""Check that a DAQ run with no trigger still has a readable event table."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from daq.analyze_pulses import adc_threshold_codes


ROOT = Path(__file__).resolve().parents[1]


class TestNoTriggerOutput(unittest.TestCase):
    def test_empty_event_csv_keeps_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            waveform = directory / "waveform.csv"
            pd.DataFrame({
                "sample": [0, 1, 2],
                "timestamp_s": [0.0, 0.002, 0.004],
                "adc_raw": [102, 102, 102],
                "voltage_V": [0.5, 0.5, 0.5],
            }).to_csv(waveform, index=False)
            result = subprocess.run([
                sys.executable, str(ROOT / "daq/analyze_pulses.py"),
                "--input", str(waveform), "--output-dir", str(directory),
                "--trigger", "0.8", "--rearm", "0.65",
            ], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            events = pd.read_csv(directory / "detected_events.csv")
            self.assertTrue(events.empty)
            self.assertEqual(list(events.columns), [
                "event_id", "trigger_time_s", "peak_time_s",
                "peak_voltage_V", "peak_adc", "end_time_s", "duration_s",
                "trigger_source"
            ])


class TestADCTrigger(unittest.TestCase):
    def test_inclusive_code_boundaries(self):
        self.assertEqual(adc_threshold_codes(2.1, 1.0, 4.0, 3), (4, 1))
        self.assertEqual(adc_threshold_codes(4.0, 2.0, 7.0, 3), (4, 2))

    def test_quantization_changes_trigger_decision_and_peak_value(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            waveform = directory / "waveform.csv"
            pd.DataFrame({
                "sample": [0, 1, 2, 3],
                "timestamp_s": [0.0, 0.1, 0.2, 0.3],
                "adc_raw": [2, 4, 1, 2],
                "voltage_V": [1.0, 2.05, 0.5, 1.0],
            }).to_csv(waveform, index=False)

            def run(source, threshold):
                output = directory / f"{source}_{threshold}"
                result = subprocess.run([
                    sys.executable, str(ROOT / "daq/analyze_pulses.py"),
                    "--input", str(waveform), "--output-dir", str(output),
                    "--trigger-source", source, "--trigger", str(threshold),
                    "--rearm", "1.0", "--vref", "4.0", "--bits", "3",
                ], capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                return pd.read_csv(output / "detected_events.csv")

            self.assertTrue(run("voltage", 2.1).empty)
            adc_events = run("adc", 2.1)
            self.assertEqual(len(adc_events), 1)
            self.assertEqual(adc_events.loc[0, "peak_adc"], 4)
            self.assertAlmostEqual(adc_events.loc[0, "peak_voltage_V"], 4 * 4 / 7)
            self.assertEqual(adc_events.loc[0, "trigger_source"], "adc")
            second_waveform = pd.read_csv(waveform)
            second_waveform.loc[1, "voltage_V"] = 2.35
            second_waveform.to_csv(waveform, index=False)
            self.assertEqual(len(run("voltage", 2.3)), 1)
            self.assertTrue(run("adc", 2.3).empty)


if __name__ == "__main__":
    unittest.main()
