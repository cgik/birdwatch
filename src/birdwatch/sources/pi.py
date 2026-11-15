import time
from datetime import datetime
from collections.abc import Iterator
from typing import Self

from picamera2 import Picamera2
import numpy as np
import cv2

from birdwatch.sources.frame import Frame

class PiCameraSource:
    def __init__(self, detect_size: tuple[int, int] = (640, 360), interval_seconds: float = 2.0) -> None:
        self._detect_size = detect_size
        self._interval_seconds = interval_seconds
        self._camera: Picamera2 | None = None

    def __enter__(self) -> Self:
        camera = Picamera2()
        camera.configure(
                camera.create_preview_configuration(
                    main={"size": (1280, 720), "format": "RGB888"},
                    lores={"size": self._detect_size, "format": "YUV420"},
                )
        )
        camera.start()
        self._camera = camera

        return self

    def __exit__(self, *_: object) -> None:
        if self._camera is not None:
            self._camera.stop()
            self._camera.close()
            self._camera = None

    def _require_started(self) -> Picamera2:
        if self._camera is None:
            raise RuntimeError("Use PiCameraSource inside a 'with' block")

        return self._camera

    def capture(self) -> Frame:
        camera = self._require_started()
        request = camera.capture_request()
        try:
            yuv = request.make_array("lores")
            captured_at = datetime.now()
        finally:
            request.release()

        return Frame(image=_yuv420_to_bgr(yuv, self._detect_size), captured_at=captured_at)

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
