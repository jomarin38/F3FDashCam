from picamera2.encoders import H264Encoder, Quality
from picamera2 import Picamera2
import time
from datetime import datetime
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration())
encoder = H264Encoder()
while True:
    filename = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')+'.h264'
    picam2.start_recording(encoder, filename, quality=Quality.HIGH)
    time.sleep(60)
    picam2.stop_recording()
