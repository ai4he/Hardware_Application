import cv2
import mss
import numpy as np
from ultralytics import YOLO
import windows_activity as wa
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image

monitor_number = 1
model = YOLO("yolov8_active_window.pt")
sct = mss.mss()
monitor = sct.monitors[monitor_number]
class_type = 6  # window class

tracker_dict = {}
frames_since_last_detection = 0

processor = TrOCRProcessor.from_pretrained('microsoft/trocr-base-printed')
ocr_model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-base-printed')

def ocr_image(src_img):
    pil_img = Image.fromarray(cv2.cvtColor(src_img, cv2.COLOR_BGR2RGB))
    pixel_values = processor(images=pil_img, return_tensors="pt").pixel_values
    generated_ids = ocr_model.generate(pixel_values)
    return processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

while True:
    screenshot = sct.grab(monitor)
    frame = np.array(screenshot)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    if frames_since_last_detection >= 10 or len(tracker_dict) == 0:
        results = model(frame, verbose=False)
        for result in results:
            for index, cls_num in enumerate(result.boxes.cls):
                class_number = int(cls_num)
                if class_number == class_type:
                    bbox = list(map(int, result.boxes.xywh[index]))
                    x, y, width, height = bbox
                    bbox = (x, y, width, height)

                    tracker = cv2.TrackerKCF_create()
                    tracker.init(frame, bbox)

                    tracker_id = len(tracker_dict) + 1
                    tracker_dict[tracker_id] = {"tracker": tracker, "status": "active", "previous_status": "inactive"}

        frames_since_last_detection = 0
    else:
        for tracker_id in list(tracker_dict.keys()):
            tracker_data = tracker_dict[tracker_id]
            tracker = tracker_data["tracker"]
            success, bbox = tracker.update(frame)
            
            if success:
                x, y, w, h = map(int, bbox)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, f"ID: {tracker_id} {model.names[class_type]}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            else:
                tracker_data["status"] = "inactive"

            if tracker_data["status"] == "active" and tracker_data.get("previous_status") == "inactive":
                title_bar = frame[10:50, 50:1920] # Extract the title bar
                window_title = ocr_image(title_bar)
                wa.insert_window_activity(tracker_id, "active", window_title) # Insert new record

            tracker_data["previous_status"] = tracker_data["status"]

    frames_since_last_detection += 1

    cv2.imshow('Screen Capture', frame)
    if cv2.waitKey(1) & 0xFF == 27: # 27 is the ASCII code for the 'ESC' key
        break

cv2.destroyAllWindows()

rows = wa.retrieve_window_activity()
for row in rows:
    print(row)

wa.close_connection()




