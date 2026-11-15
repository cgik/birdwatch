# birdwatch

## hardware
- [Raspberry Pi 4](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/)
- [Camera Module 3 -- Wide](https://www.raspberrypi.com/products/camera-module-3/)
- Official Raspberry Pi 15W USB-C power supply

Requires 64-bit Raspberry Pi OS.

## depedencies
```shell
sudo apt install python3-picamera2
```
[uv](https://docs.astral.sh/uv/)

## setup
```shell
git clone <repo-url>
cd birdwatch
uv venv --python /usr/bin/python3 --system-site-packages
uv sync
cp config.example .env
```

## run
```shell
uv run python -m birdwatch
```

## tests
```shell
uv run pytest
```
