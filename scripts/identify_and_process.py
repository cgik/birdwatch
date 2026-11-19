#!/local/user/bin python3
# pyright: basic

from pathlib import Path

from ultralytics import YOLO

BIRD_CLASS_ID = 14  # "bird" in the COCO category list these models are trained on

# download's this model, do NOT run on the pi unless your pi is powerful i suppose
model = YOLO("yolo11n.pt")
samples = sorted(Path("~/birdwatch-data").expanduser().glob("*.jpg"))

results = model.predict(samples, classes=[BIRD_CLASS_ID], conf=0.25, save=True)

found = sum(1 for result in results if len(result.boxes) > 0)

print(f"Bird detected in {found} of {len(samples)} images")
