import io
import time
from collections.abc import Iterator
from datetime import datetime
from typing import Self

import cv2
import numpy as np
from libcamera import controls
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput

from birdwatch.sources.frame import Frame


class PiCameraSource:
    def __init__(
        self, detect_size: tuple[int, int] = (640, 360), interval_seconds: float = 2.0
    ) -> None:
        self._detect_size = detect_size
        self._interval_seconds = interval_seconds
        self._camera: Picamera2 | None = None
        self._encoder: MJPEGEncoder | None = None

    def __enter__(self) -> Self:
        camera = Picamera2()
        camera.configure(
            camera.create_preview_configuration(
                main={"size": (1280, 720), "format": "RGB888"},
                lores={"size": self._detect_size, "format": "YUV420"},
                controls={
                    "AfMode": controls.AfModeEnum.Continuous,
                    "AfRange": controls.AfRangeEnum.Normal,
                },
            )
        )
        camera.start()
        self._camera = camera

        return self

    def __exit__(self, *_: object) -> None:
        self.stop_stream()
        if self._camera is not None:
            self._camera.stop()
            self._camera.close()
            self._camera = None

    def _require_started(self) -> Picamera2:
        if self._camera is None:
            raise RuntimeError("Use PiCameraSource inside a 'with' block")

        return self._camera

    def start_stream(self, output: io.BufferedIOBase) -> None:
        camera = self._require_started()
        if self._encoder is not None:
            raise RuntimeWarning("Stream is already running.")

        encoder = MJPEGEncoder()
        camera.start_encoder(encoder, FileOutput(output), name="main")
        self._encoder = encoder

    def stop_stream(self) -> None:
        if self._encoder is not None and self._camera is not None:
            self._camera.stop_encoder(self._encoder)

        self._encoder = None

    def capture(self) -> Frame:
        camera = self._require_started()
        request = camera.capture_request()
        try:
            yuv = request.make_array("lores")
            captured_at = datetime.now()
        finally:
            request.release()

        return Frame(
            image=_yuv420_to_bgr(yuv, self._detect_size), captured_at=captured_at
        )

    def frames(self) -> Iterator[Frame]:
        while True:
            yield self.capture()
            time.sleep(self._interval_seconds)


def _yuv420_to_bgr(yuv: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    width, height = size
    bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV420p2BGR)
    return bgr[:height, :width]


# Exists purely for testing purposes
if __name__ == "__main__":
    with PiCameraSource() as source:
        frame = source.capture()
    cv2.imwrite("capture.jpg", frame.image)
    print(frame.image.shape, frame.captured_at)
