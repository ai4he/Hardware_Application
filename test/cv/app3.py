import cv2
import mss
import numpy as np
from ultralytics import YOLO

monitor_number = 1
model = YOLO("yolov8_active_window.pt")
sct = mss.mss()
monitor = sct.monitors[monitor_number]
class_type = 6  # window class

tracker = None
frames_since_last_detection = 0
tracker_id = 0  # Initialize tracker ID

while True:
    screenshot = sct.grab(monitor)
    frame = np.array(screenshot)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    if frames_since_last_detection >= 10 or tracker is None:  # Detect objects every 10 frames
        results = model(frame, verbose=False)
        for result in results:
            for index, cls_num in enumerate(result.boxes.cls):
                class_number = int(cls_num)
                if class_number == class_type:
                    bbox = list(map(int, result.boxes.xywh[index]))
                    x_center, y_center, width, height = bbox
                    x = int(x_center - width / 2)
                    y = int(y_center - height / 2)
                    width = int(width)
                    height = int(height)
                    bbox = (x, y, width, height)
                    tracker = cv2.TrackerKCF_create()
                    success = tracker.init(frame, bbox)
                    if success:
                        tracker_id += 1  # Increment tracker ID
                        cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 255, 0), 2)
                        cv2.putText(frame, f"ID: {tracker_id} {model.names[class_number]}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)
        frames_since_last_detection = 0
    else:  # If there is a tracker, update it
        success, bbox = tracker.update(frame)
        if success:
            x, y, w, h = map(int, bbox)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"ID: {tracker_id} {model.names[class_type]}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)
        else:
            tracker = None  # If the tracker fails, clear it

    frames_since_last_detection += 1

    cv2.imshow('Screen Capture', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cv2.destroyAllWindows()
