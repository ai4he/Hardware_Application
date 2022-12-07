import gi
import time
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib
import numpy as np
import cv2




pipeline = None
bus = None
message = None

# initialize GStreamer
Gst.init(None)

# build the pipeline
pipeline = Gst.parse_launch(
    "pulsesrc device=alsa_input.platform-hdmiin-sound.stereo-fallback ! audioconvert ! autoaudiosink"
)

# start playing
pipeline.set_state(Gst.State.PLAYING)
cap=cv2.VideoCapture(11)
cv2.namedWindow("frame", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("frame", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

while True:
	
	ret, frame = cap.read()
	cv2.imshow('frame', frame)
	if cv2.waitKey(1) == ord('q'):
	   break
	   
cap.release()
cv2.destroyAllWindows()


try:
   while True:
       time.sleep(0.1)
except KeyboardInterrupt:
   pass

pipeline.set_state(Gst.State.NULL)




	   
	   







