"""Protocol, timing and end-to-end checks; no serial hardware required."""

import io
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from daq.capture_serial import receive
from daq.optical_bench import HEADER, UINT32, analyze, match_edges, read_stream, synthetic_stream


class TestOpticalProtocol(unittest.TestCase):
    def parse(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stream.txt"
            path.write_text(text)
            return read_stream(path)

    def test_timestamp_rollover_and_sequence_gaps(self):
        frame, stats = self.parse(HEADER + f"\n7,{UINT32 - 1000},0\n9,3000,1023\n")
        self.assertEqual(frame.timestamp_s.tolist(), [0, 0.004])
        self.assertEqual(frame.voltage_V.tolist(), [0, 5])
        self.assertEqual(stats["micros_rollovers"], 1)
        self.assertEqual(stats["missing_sequence_samples"], 1)

    def test_bad_streams_fail_instead_of_repairing(self):
        invalid = [
            "wrong\n0,0,100\n1,2000,200\n",
            HEADER + "\n0,0,100\n1,2000,200",  # truncated final record
            HEADER + "\n0,0,100\n1,2000,nan\n",
            HEADER + "\n0,0,100\n1,2000,1024\n",
            HEADER + "\n0,0,100\n1,2000,-1\n",
            HEADER + "\n0,0,100\n1,2000,1.5\n",
            HEADER + "\n0,0,100\n0,2000,200\n",  # reset
            HEADER + "\n0,2000,100\n1,1000,200\n",  # time reversal
            HEADER + "\n0,0,100\n1,0,200\n",
            HEADER + "\n0,0,100\n1,1000001,200\n",
            HEADER + "\n0,0,100\n",  # not enough samples
        ]
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.parse(text)

    def test_synthetic_stream_is_reproducible(self):
        a, truth = synthetic_stream()
        b, _ = synthetic_stream()
        c, _ = synthetic_stream(seed=7)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        frame, stats = self.parse(a)
        self.assertEqual(len(truth), 20)
        self.assertEqual(len(frame), 5000)
        self.assertEqual(stats["missing_sequence_samples"], 0)
        self.assertGreater(stats["std_dt_us"], 0)

    def test_invalid_noise_rejected(self):
        for noise in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                synthetic_stream(noise_codes=noise)


class TestEdgeMatching(unittest.TestCase):
    def test_one_to_one_and_unmatched(self):
        result = match_edges([1, 2, 3], [1.001, 1.002, 2.001, 4])
        self.assertEqual((result["matched"], result["missed"], result["unmatched_triggers"]), (2, 1, 2))
        self.assertAlmostEqual(result["max_abs_error_ms"], 1)

    def test_no_detection_has_no_invented_timing(self):
        result = match_edges([1, 2], [])
        self.assertEqual(result["missed"], 2)
        self.assertIsNone(result["mean_error_ms"])
        self.assertIsNone(result["max_abs_error_ms"])

    def test_invalid_matching_inputs(self):
        for truth, detected, tolerance in [([2, 1], [], .1), ([1], [1, 1], .1),
                                            ([float("nan")], [], .1), ([1], [], -1)]:
            with self.assertRaises(ValueError):
                match_edges(truth, detected, tolerance)


class FragmentedStream:
    def __init__(self, data, width=3):
        self.stream = io.BytesIO(data)
        self.width = width

    def read(self, size):
        return self.stream.read(min(size, self.width))


class TestSerialCapture(unittest.TestCase):
    def test_fragmented_reads_and_exact_row_count(self):
        data = (HEADER + "\r\n0,1000,100\n1,3000,900\n2,5000,100\n").encode()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "raw.txt"
            self.assertEqual(receive(FragmentedStream(data), path, 2, 1), 2)
            frame, _ = read_stream(path)
            self.assertEqual(frame.adc_raw.tolist(), [100, 900])
            with self.assertRaises(FileExistsError):
                receive(FragmentedStream(data), path, 2, 1)

    def test_timeout_keeps_partial_bytes(self):
        clock = iter([0, 0.1, 2]).__next__
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "raw.txt"
            with self.assertRaises(TimeoutError):
                receive(FragmentedStream(b"sam"), path, 2, 1, clock=clock)
            self.assertEqual(path.read_bytes(), b"sam")

    def test_unexpected_header_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                receive(FragmentedStream(b"bad\n"), Path(directory) / "raw.txt", 2, 1)


class TestOpticalIntegration(unittest.TestCase):
    def test_clean_fixture_uses_existing_adc_trigger(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw, truth = synthetic_stream()
            source = root / "input.txt"
            source.write_text(raw)
            events, manifest = analyze(source, root / "run", "synthetic")
            metrics = match_edges(truth, events.trigger_time_s.to_numpy())
            self.assertEqual(metrics["matched"], 20)
            self.assertEqual(metrics["unmatched_triggers"], 0)
            self.assertLessEqual(metrics["max_abs_error_ms"], 2.2)
            self.assertEqual(manifest["source"], "synthetic")
            self.assertEqual(manifest["status"], "complete")
            self.assertTrue(events.trigger_source.eq("adc").all())
            self.assertEqual((root / "run/raw_stream.txt").read_bytes(), source.read_bytes())
            with self.assertRaises(FileExistsError):
                analyze(source, root / "run", "synthetic")

    def test_no_trigger_and_recording_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.txt"
            source.write_text(HEADER + "\n0,0,100\n1,2000,100\n")
            events, _ = analyze(source, root / "empty", "synthetic")
            self.assertTrue(events.empty)
            source.write_text(HEADER + "\n0,0,900\n1,2000,900\n")
            events, manifest = analyze(source, root / "censored", "synthetic")
            self.assertEqual(len(events), 1)
            self.assertEqual(events.iloc[0].trigger_time_s, 0)
            self.assertIn("censored", " ".join(manifest["limitations"]))

    def test_provenance_and_thresholds_required(self):
        with self.assertRaises(ValueError):
            analyze("unused", "unused", "unknown")
        for trigger, rearm in [(2, 3), (float("nan"), 1), (6, 1), (2, -1)]:
            with self.assertRaises(ValueError):
                analyze("unused", "unused", "synthetic", trigger, rearm)


if __name__ == "__main__":
    unittest.main()
