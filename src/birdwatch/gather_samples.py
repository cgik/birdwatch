from picamera2 import Picamera2
import cv2

picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (1536, 864), "format": "RGB888"},
    lores={"size": (384, 216), "format": "YUV420"},
)
picam2.configure(config)
picam2.start()

request = picam2.capture_request()
try:
    main = request.make_array("main")
    lores_yuv = request.make_array("lores")
finally:
    request.release()

picam2.stop()

lores = cv2.cvtColor(lores_yuv, cv2.COLOR_YUV420p2BGR)

print("main:", main.shape, "lores raw:", lores_yuv.shape, "lores converted:", lores.shape)
cv2.imwrite("main.jpg", main)
cv2.imwrite("lores.jpg", lores)
