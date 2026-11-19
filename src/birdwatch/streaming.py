import io
import logging
from http import server
from threading import Condition

log = logging.getLogger(__name__)

PAGE = b"""<html><body style="margin:0;background:#000">
<img src="stream.mjpg" style="width:100%">
</body></html>"""


class LatestFrame(io.BufferedIOBase):
    """Holds the newest JPEG and wakes every waiting viewer when it changes."""

    def __init__(self) -> None:
        self._frame: bytes | None = None
        self._condition = Condition()

    def write(self, buf) -> int:
        with self._condition:
            self._frame = bytes(buf)
            self._condition.notify_all()
        return len(buf)

    def wait_for_next(self, timeout_s: float = 5.0) -> bytes | None:
        with self._condition:
            if not self._condition.wait(timeout_s):
                return None
            return self._frame


def make_server(latest: LatestFrame, port: int) -> server.ThreadingHTTPServer:
    class Handler(server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/":
                self._send_page()
            elif self.path == "/stream.mjpg":
                self._send_stream()
            else:
                self.send_error(404)

        def _send_page(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(PAGE)))
            self.end_headers()
            self.wfile.write(PAGE)

        def _send_stream(self) -> None:
            self.send_response(200)
            self.send_header("Cache-Control", "no-cache, private")
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=FRAME")
            self.end_headers()
            try:
                while True:
                    frame = latest.wait_for_next()
                    if frame is None:
                        continue
                    self.wfile.write(b"--FRAME\r\nContent-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode())
                    self.wfile.write(frame + b"\r\n")
            except (BrokenPipeError, ConnectionResetError):
                log.debug("Viewer %s disconnected", self.client_address)

        def log_message(self, format: str, *args) -> None:
            log.debug(format, *args)

    return server.ThreadingHTTPServer(("", port), Handler)
