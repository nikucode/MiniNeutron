"""Host logic checks only: not an AVR build, flash, or hardware validation."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestFirmwareHost(unittest.TestCase):
    @unittest.skipUnless(shutil.which("g++"), "g++ is required for the host logic check")
    def test_scheduler_wrap_backpressure_and_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "firmware_host"
            result = subprocess.run([
                "g++", "-std=c++20", "-Wall", "-Wextra", "-Werror",
                "-I", str(ROOT / "tests/firmware"),
                str(ROOT / "tests/firmware/optical_bench_host.cpp"),
                "-o", str(target),
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(target)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
