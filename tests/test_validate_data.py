import tempfile
import unittest
from pathlib import Path

import pandas as pd

from analysis.validate_data import validate_pulse_csv


VALID_ROWS = {
    "sample": [0, 1, 2],
    "timestamp_s": [0.0, 0.002, 0.004],
    "adc_raw": [99, 107, 120],
    "voltage_V": [0.48, 0.52, 0.59],
}


class TestPulseCSVValidation(unittest.TestCase):
    def check_data(self, data):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.csv"
            pd.DataFrame(data).to_csv(path, index=False)
            return validate_pulse_csv(path)

    def test_valid_data(self):
        self.assertEqual(self.check_data(VALID_ROWS), [])

    def test_missing_column(self):
        data = dict(VALID_ROWS)
        del data["voltage_V"]
        self.assertTrue(self.check_data(data))

    def test_non_numeric_value(self):
        data = dict(VALID_ROWS)
        data["voltage_V"] = [0.48, "bad", 0.59]
        self.assertTrue(self.check_data(data))

    def test_repeated_timestamp(self):
        data = dict(VALID_ROWS)
        data["timestamp_s"] = [0.0, 0.002, 0.002]
        self.assertTrue(self.check_data(data))

    def test_adc_out_of_range(self):
        data = dict(VALID_ROWS)
        data["adc_raw"] = [99, 1024, 120]
        self.assertTrue(self.check_data(data))


if __name__ == "__main__":
    unittest.main()
