# Without tmux run: systemd-run --user --unit=gather -- uv run python scripts/gather_samples.py --interval 60 --duration 12
# Check if running: systemctl --user status gather
# Check logs: journalctl --user -u gather -f
# Stop: systemctl --user stop gather

import time
import sys
import argparse
import shutil
from pathlib import Path

from birdwatch.sources.pi import PiCameraSource
import cv2

INTERVAL=60

def system_healthy(path: str = "/") -> bool:
    disk = shutil.disk_usage("/")
    free_space = disk.free / (2**30)

    if free_space <= 5.0:
        return False

    return True


def gather_sample(source, path: str, interval_s: float, duration_s: float) -> None:
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

        file_name_time = time.strftime("%m-%u_%H-%M-%S")
        
        frame = source.capture()
        cv2.imwrite(f"{path}/{file_name_time}.jpg", frame.image) 
        print(f"Saving picture to: {path}/{file_name_time}.jpg", flush=True)
        
        next_capture += interval_s
        while next_capture <= time.monotonic():
            next_capture += interval_s

    return saved

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gather samples")
    parser.add_argument("--duration", type=float, default=12, help="Amount of time to run script for in hours. (default: 12)")
    parser.add_argument("--path", type=Path, default=Path("~/birdwatch-data"), help="Path to store images for sorting (default: ~/birdwatch-data)")

    args = parser.parse_args(argv)
   
    path = args.path.expanduser()
    path.mkdir(parents=True, exist_ok=True)
    duration_s = args.duration * 3600

    if not system_healthy(path):
        print("Not enough free disk space; stopping.", file=sys.stderr)
        return 1
    
    with PiCameraSource() as source:
        try:
            saved = gather_sample(source, path, INTERVAL, duration_s)
        except KeyboardInterrupt:
            print("Stopped early.")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

