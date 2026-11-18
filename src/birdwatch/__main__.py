"""Entry point: `python -m birdwatch` (or `birdwatch` via [project.scripts])."""

import argparse
import logging
import signal
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING

from birdwatch.alerts import Notify, make_notifier
from birdwatch.detection import load_detector  # TODO: returns Callable[[np.ndarray], bool]
from birdwatch.monitor import run  # TODO: the detect → decide → notify loop
from birdwatch.streaming import LatestFrame, make_server

if TYPE_CHECKING:  # type hints only; never imported at runtime, so the Mac is fine
    from birdwatch.sources.pi import PiCameraSource

log = logging.getLogger("birdwatch")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="birdwatch", description="Notify when the bird leaves the camera's view."
    )
    parser.add_argument(
        "--source", default="pi", help='"pi", "folder:PATH" or "webcam:INDEX" (default: pi)'
    )
    parser.add_argument(
        "--interval", type=float, default=2.0, help="seconds between checks (default: 2)"
    )
    parser.add_argument(
        "--stream", action=argparse.BooleanOptionalAction, default=False,
        help="serve a live MJPEG stream (pi source only)",
    )
    parser.add_argument("--port", type=int, default=8000, help="stream port (default: 8000)")
    parser.add_argument(
        "--notify", action=argparse.BooleanOptionalAction, default=True,
        help="send ntfy notifications (needs BIRDWATCH_NTFY_* environment variables)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    return parser.parse_args(argv)


def parse_source_spec(spec: str) -> tuple[str, str | None]:
    """Split "folder:./x" into ("folder", "./x"). Raises ValueError for unknown specs."""
    kind, _, value = spec.partition(":")
    if kind == "pi" and not value:
        return "pi", None
    if kind in ("folder", "webcam") and value:
        return kind, value
    raise ValueError(f'unknown source "{spec}"; expected pi, folder:PATH or webcam:INDEX')


@contextmanager
def open_source(kind: str, value: str | None, interval_s: float) -> Iterator:
    """Open the chosen frame source. Imports happen inside each branch on purpose."""
    if kind == "pi":
        from birdwatch.sources.pi import PiCameraSource

        with PiCameraSource(interval_seconds=interval_s) as source:
            yield source
    elif kind == "folder":
        from birdwatch.sources.folder import FolderSource  # TODO

        with FolderSource(Path(value)) as source:
            yield source
    else:
        from birdwatch.sources.webcam import WebcamSource  # TODO

        with WebcamSource(int(value), interval_seconds=interval_s) as source:
            yield source


def start_streaming(source: "PiCameraSource", port: int) -> ThreadingHTTPServer:
    latest = LatestFrame()
    source.start_stream(latest)
    httpd = make_server(latest, port)
    threading.Thread(target=httpd.serve_forever, name="stream", daemon=True).start()
    log.info("Streaming on port %d", port)
    return httpd


def notify_safely(notify: Notify, message: str) -> None:
    """A failed notification should never mask what actually happened."""
    try:
        notify(message)
    except OSError as e:
        log.warning("Could not send notification: %s", e)


def _stop_on_sigterm(signum: int, frame: object) -> None:
    raise KeyboardInterrupt  # so `systemctl stop` runs cleanup like Ctrl+C does


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        kind, value = parse_source_spec(args.source)
    except ValueError as e:
        log.error("%s", e)
        return 2
    if args.stream and kind != "pi":
        log.error("--stream only works with the pi source")
        return 2

    signal.signal(signal.SIGTERM, _stop_on_sigterm)
    notify_alert = make_notifier("BIRDWATCH_NTFY_ALERTS_TOPIC", enabled=args.notify)
    notify_system = make_notifier("BIRDWATCH_NTFY_SYSTEM_TOPIC", enabled=args.notify)
    detect = load_detector()  # load the model before taking the camera

    reason = "crashed"
    try:
        with open_source(kind, value, args.interval) as source:
            httpd = start_streaming(source, args.port) if args.stream else None
            try:
                notify_safely(notify_system, f"birdwatch started (source={args.source})")
                reason = run(source.frames(), detect, notify_alert)
            finally:
                if httpd is not None:
                    httpd.shutdown()
                    httpd.server_close()
    except KeyboardInterrupt:
        reason = "stopped"
    finally:
        notify_safely(notify_system, f"birdwatch ended: {reason}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

