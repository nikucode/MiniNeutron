"""Capture raw Uno R3 optical data; pyserial is optional for offline analyses."""

import argparse
import hashlib
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

from daq.optical_bench import HEADER, read_stream


def receive(stream, destination, samples, timeout_s, clock=time.monotonic):
    """Accumulate fragmented reads; preserve bytes even on timeout/failure.

    Serial stream must have a finite read timeout. Header is part of the
    protocol; boot noise is never silently accepted. No board clock is replaced
    with the host clock. Stops exactly at a newline after the requested rows.
    """
    if samples < 2 or not math.isfinite(timeout_s) or timeout_s <= 0:
        raise ValueError("Require samples >= 2 and a finite positive timeout")
    deadline = clock() + timeout_s
    buffer = b""
    lines = 0
    with Path(destination).open("xb") as output:
        while lines < samples + 1:
            if clock() >= deadline:
                output.write(buffer)
                raise TimeoutError("Capture timed out; partial raw bytes retained")
            buffer += stream.read(256)
            if len(buffer) > 4096 and b"\n" not in buffer:
                output.write(buffer)
                raise ValueError("Serial record exceeds 4096 bytes")
            while b"\n" in buffer and lines < samples + 1:
                line, buffer = buffer.split(b"\n", 1)
                output.write(line + b"\n")
                if lines == 0 and line.rstrip(b"\r") != HEADER.encode("ascii"):
                    raise ValueError("Unexpected serial header")
                lines += 1
    return lines - 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="Explicit device, e.g. /dev/ttyACM0")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=5000)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    if args.samples < 2 or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("Require samples >= 2 and finite positive --timeout")
    try:
        import serial
    except ImportError:
        parser.error("Install optional dependency: python -m pip install pyserial==3.5")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    raw = args.output_dir / "raw_stream.txt"
    manifest = {"source": "hardware", "status": "running", "port": args.port,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "baud": 115200, "requested_samples": args.samples,
                "timeout_s": args.timeout, "pyserial": serial.__version__,
                "firmware": "optical_bench protocol v1; actual flashed version must be recorded"}
    try:
        with serial.Serial(args.port, 115200, timeout=0.2, write_timeout=1) as device:
            # Uno commonly resets on opening USB serial. The firmware waits for 's'.
            time.sleep(2)
            device.reset_input_buffer()
            try:
                device.write(b"s")
                receive(device, raw, args.samples, args.timeout)
            finally:
                device.write(b"x")
        _, manifest["acquisition"] = read_stream(raw)
        manifest["status"] = "complete"
    except Exception as exc:
        manifest["status"] = "failed"
        manifest["error"] = str(exc)
        raise
    finally:
        if raw.exists():
            manifest["raw_sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
        (args.output_dir / "capture.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Captured {args.samples} samples: {raw}")


if __name__ == "__main__":
    main()
