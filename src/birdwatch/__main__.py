import argparse
import logging
import signal
import sys
import threading
from collections.abc import Generator, Iterable
from contextlib import contextmanager, nullcontext
from typing import TYPE_CHECKING

from birdwatch.sources.frame import Frame
from birdwatch.streaming import LatestFrame, make_server

if TYPE_CHECKING:  # for type hints only; picamera2 can't be imported off the Pi
    from birdwatch.sources.pi import PiCameraSource

log = logging.getLogger("birdwatch")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="birdwatch", description="Notify when the bird leaves the camera's view."
    )
    parser.add_argument(
        "--interval", type=float, default=2.0, help="seconds between frames (default: 2)"
    )
    parser.add_argument(
        "--stream",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="serve a live MJPEG stream (default: off)",
    )
    parser.add_argument("--port", type=int, default=8000, help="stream port (default: 8000)")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    return parser.parse_args(argv)


@contextmanager
def serve_stream(source: "PiCameraSource", port: int) -> Generator[None]:
    """Stream the camera over HTTP for as long as the with block runs."""
    latest = LatestFrame()
    source.start_stream(latest)
    httpd = make_server(latest, port)
    threading.Thread(target=httpd.serve_forever, name="stream", daemon=True).start()
    log.info("Streaming on port %d", port)
    try:
        yield
    finally:
        httpd.shutdown()
        httpd.server_close()
        source.stop_stream()


def watch(frames: Iterable[Frame]) -> None:
    """Placeholder until detection and presence exist; this becomes monitor.run."""
    for frame in frames:
        log.debug("Frame at %s", frame.captured_at.isoformat(timespec="seconds"))


def run_camera(interval_s: float, stream_port: int | None) -> None:
    from birdwatch.sources.pi import PiCameraSource

    with (
        PiCameraSource(interval_seconds=interval_s) as source,
        serve_stream(source, stream_port) if stream_port is not None else nullcontext(),
    ):
        log.info("Watching every %.1f s", interval_s)
        watch(source.frames())


def _stop_on_sigterm(signum: int, frame: object) -> None:
    raise KeyboardInterrupt


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    signal.signal(signal.SIGTERM, _stop_on_sigterm)

    try:
        run_camera(args.interval, args.port if args.stream else None)
    except KeyboardInterrupt:
        log.info("Stopped")

    return 0


if __name__ == "__main__":
    sys.exit(main())

