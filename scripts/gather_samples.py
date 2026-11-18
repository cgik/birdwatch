#!/usr/bin/env python3

# Without tmux run: systemd-run --user --same-dir --unit=gather -- uv run python scripts/gather_samples.py --duration 12
# Check if running: systemctl --user status gather
# Check logs: journalctl --user -u gather -f
# Stop: systemctl --user stop gather

import argparse
import shutil
import signal
import sys
import time
from pathlib import Path
from typing import Literal

import cv2

INTERVAL = 60
StopReason = Literal["duration reached", "low disk space", "write failed"]


def _stop_on_sigterm(signum, _frame):
    raise KeyboardInterrupt


def system_healthy(path: Path) -> bool:
    disk = shutil.disk_usage(path)
    free_space = disk.free / (2**30)

    return free_space >= 5.0


def gather_sample(
    source, path: Path, interval_s: float, duration_s: float
) -> tuple[int, StopReason]:
    start = time.monotonic()
    end = start + duration_s
    next_capture = start
    saved = 0

    while (now := time.monotonic()) < end:
        if now < next_capture:
            time.sleep(min(next_capture - now, end - now))
            continue

        if not system_healthy(path):
            return saved, "low disk space"

        frame = source.capture()
        name = frame.captured_at.strftime("%Y-%m-%dT%H-%M-%S") + ".jpg"

        if not cv2.imwrite(str(f"{path}/{name}"), frame.image):
            return saved, "write failed"

        saved += 1
        print(f"Saving picture to: {name}", flush=True)

        next_capture += interval_s

        while next_capture <= time.monotonic():
            next_capture += interval_s

    return saved, "duration reached"


def main(argv: list[str] | None = None) -> int:
    from birdwatch.sources.pi import PiCameraSource

    signal.signal(signal.SIGTERM, _stop_on_sigterm)

    parser = argparse.ArgumentParser(prog="gather samples")

    parser.add_argument(
        "--duration",
        type=float,
        default=12,
        help="Amount of time to run script for in hours. (default: 12)",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("~/birdwatch-data"),
        help="Path to store images for sorting (default: ~/birdwatch-data)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Time between captures for identification or training",
    )

    args = parser.parse_args(argv)

    path = args.path.expanduser()
    path.mkdir(parents=True, exist_ok=True)
    duration_s = args.duration * 3600

    if not system_healthy(path):
        print("Not enough free disk space; stopping.", file=sys.stderr)
        return 1

    with PiCameraSource() as source:
        try:
            gather_sample(source, path, args.interval, duration_s)
        except KeyboardInterrupt:
            print("Stopped early.")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
