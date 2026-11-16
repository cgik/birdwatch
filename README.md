# birdwatch

## Hardware
- [Raspberry Pi 4](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/)
- [Camera Module 3 -- Wide](https://www.raspberrypi.com/products/camera-module-3/)
- Official Raspberry Pi 15W USB-C power supply


## Depedencies
- [uv](https://docs.astral.sh/uv/)

### On the Pi itself, for the camera
```shell
sudo apt install python3-picamera2
```
Personally ran on: 64-bit Raspberry Pi OS.

## setup
```shell
git clone https://github.com/cgik/birdwatch.git
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
