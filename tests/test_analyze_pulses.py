"""Check that a DAQ run with no trigger still has a readable event table."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


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
                "peak_voltage_V", "peak_adc", "end_time_s", "duration_s"
            ])


if __name__ == "__main__":
    unittest.main()
