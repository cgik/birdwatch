from collections import namedtuple
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pytest

import gather_samples

GIB = 2**30
FIRST_CAPTURE_AT = datetime(2026, 11, 16, 9, 0, 0)

DiskUsage = namedtuple("DiskUsage", "total used free")


class FakeClock:
    """Stands in for the time module: sleeping advances the clock instantly."""

    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


@dataclass
class FakeFrame:
    captured_at: datetime
    image: np.ndarray


class FakeSource:
    """Stands in for PiCameraSource: returns a tiny black image stamped with the fake time."""

    def __init__(self, clock):
        self.clock = clock
        self.capture_count = 0

    def capture(self):
        self.capture_count += 1
        return FakeFrame(
            captured_at=FIRST_CAPTURE_AT + timedelta(seconds=self.clock.now),
            image=np.zeros((2, 2, 3), dtype=np.uint8),
        )


@pytest.fixture
def clock(monkeypatch):
    fake_clock = FakeClock()
    monkeypatch.setattr(gather_samples, "time", fake_clock)
    return fake_clock


@pytest.fixture
def healthy_disk(monkeypatch):
    monkeypatch.setattr(gather_samples, "system_healthy", lambda path: True)


def test_saves_one_picture_per_interval_until_duration_reached(
    clock, healthy_disk, tmp_path
):
    source = FakeSource(clock)

    result = gather_samples.gather_sample(
        source, tmp_path, interval_s=10, duration_s=30
    )

    assert result == (3, "duration reached")
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "2026-11-16T09-00-00.jpg",
        "2026-11-16T09-00-10.jpg",
        "2026-11-16T09-00-20.jpg",
    ]


def test_stops_without_capturing_when_disk_space_is_low(clock, monkeypatch, tmp_path):
    monkeypatch.setattr(gather_samples, "system_healthy", lambda path: False)
    source = FakeSource(clock)

    result = gather_samples.gather_sample(
        source, tmp_path, interval_s=10, duration_s=30
    )

    assert result == (0, "low disk space")
    assert source.capture_count == 0


def test_reports_write_failure_when_picture_cannot_be_saved(
    clock, healthy_disk, tmp_path
):
    missing_directory = tmp_path / "does-not-exist"

    result = gather_samples.gather_sample(
        FakeSource(clock), missing_directory, interval_s=10, duration_s=30
    )

    assert result == (0, "write failed")


@pytest.mark.parametrize(
    ("free_gib", "expected"),
    [(50, True), (1, False)],
)
def test_system_healthy_requires_free_disk_space(
    monkeypatch, tmp_path, free_gib, expected
):
    usage = DiskUsage(total=100 * GIB, used=0, free=free_gib * GIB)
    monkeypatch.setattr(gather_samples.shutil, "disk_usage", lambda path: usage)

    assert gather_samples.system_healthy(tmp_path) is expected

