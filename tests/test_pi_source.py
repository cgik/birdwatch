import pytest

# skips this whole file if ran on not a raspberry pi with picamera 2 installed
pytest.importorskip("picamera2")

from birdwatch.sources.pi import PiCameraSource


def test_capture_returns_bgr_frame_of_requested_size():
    with PiCameraSource(detect_size=(640, 360)) as source:
        frame = source.capture()
    assert frame.image.shape == (360, 640, 3)
    assert frame.image.dtype.name == "uint8"


def test_camera_is_released_after_with_block():
    with PiCameraSource() as source:
        source.capture()
    with PiCameraSource() as source:
        source.capture()

