import argparse
import mss
import mss.tools
import cv2
import numpy as np
# import pyautogui
import time
import pytesseract
import sqlite3

def setup_db():
    conn = sqlite3.connect('windows_events.sqlite')
    c = conn.cursor()

    # Create table
    c.execute('''
        CREATE TABLE IF NOT EXISTS windows_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            x INTEGER,
            y INTEGER,
            width INTEGER,
            height INTEGER,
            window_name TEXT,
            document_name TEXT,
            event_name TEXT
        )
    ''')

    conn.commit()
    return conn

def insert_event(conn, x, y, w, h, window_name, document_name, event_name):
    c = conn.cursor()
    
    # Insert a row of data
    c.execute("INSERT INTO windows_events (timestamp, x, y, width, height, window_name, document_name, event_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (time.time(), x, y, w, h, window_name, document_name, event_name))
    
    # Save (commit) the changes
    conn.commit()

def split_title(title):
    parts = title.split('-')
    window_name = parts[0].strip()
    document_name = parts[1].strip() if len(parts) > 1 else ''
    return window_name, document_name

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Monitor Number')
parser.add_argument('--monitor', type=int, default=0, help='Monitor number (starting from 0)')
args = parser.parse_args()

monitor_number = args.monitor

# Load the templates
template_inactive = cv2.imread('template_inactive.png', cv2.IMREAD_COLOR)
template_inactive = cv2.cvtColor(template_inactive, cv2.COLOR_BGR2GRAY)

template_active = cv2.imread('template_active.png', cv2.IMREAD_COLOR)
template_active = cv2.cvtColor(template_active, cv2.COLOR_BGR2GRAY)

# Create a dictionary to store trackers and their IDs
trackers = {}

# Create a dictionary to store tracker states (active or inactive)
tracker_states = {}
tracker_titles = {}

# Initialize a counter for window IDs
window_id = 1
threshold = 0.8
title_bar_height = 50

conn = setup_db()

# Check if templates have been correctly loaded
if template_inactive is None:
    print("Could not open or find the inactive template")
elif template_active is None:
    print("Could not open or find the active template")
else:
    start_time = time.time()
    last_detection_time = time.time()
    # Detection interval in seconds
    detection_interval = 1.0  # adjust as needed

    # Create an instance of mss
    sct = mss.mss()

    # Get information of all monitors
    monitors = sct.monitors

    # Choose a monitor (index 1 is the first monitor, index 2 is the second, etc.)
    monitor = monitors[monitor_number]
    
    while True:
        # Capture screenshot
        # screenshot = pyautogui.screenshot()
        screenshot = sct.grab(monitor)
        # Convert the image into numpy array representation
        frame = np.array(screenshot)
        # Convert the BGR image into RGB image
        #frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        # Update location of the tracked windows
        # In the tracking block:
        for id, tracker in list(trackers.items()):
            success, box = tracker.update(frame)
            if success:
                p1 = (int(box[0]), int(box[1]))
                p2 = (int(box[0] + box[2]), int(box[1] + box[3]))

                cv2.rectangle(frame, p1, p2, (0,255,0), 2, 1)

                # Get region of interest
                if (int(box[0]) >= 0 and int(box[1]) >= 0 and 
                    int(box[2]) > 0 and int(box[3]) > 0 and 
                    int(box[1] + box[3]) <= frame.shape[0] and 
                    int(box[0] + box[2]) <= frame.shape[1]): 

                    roi = frame[int(box[1]):int(box[1] + box[3]), int(box[0]):int(box[0] + box[2])]
                    roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

                    # Check if ROI is large enough for template matching
                    if roi_gray.shape[0] >= template_inactive.shape[0] and roi_gray.shape[1] >= template_inactive.shape[1]:
                        res_inactive = cv2.matchTemplate(roi_gray, template_inactive, cv2.TM_CCOEFF_NORMED)
                        loc_inactive = np.where(res_inactive >= threshold)

                    if roi_gray.shape[0] >= template_active.shape[0] and roi_gray.shape[1] >= template_active.shape[1]:
                        res_active = cv2.matchTemplate(roi_gray, template_active, cv2.TM_CCOEFF_NORMED)
                        loc_active = np.where(res_active >= threshold)

                    if loc_inactive is not None and len(loc_inactive[0]) > 0:
                        tracker_states[id] = "INACTIVE"

                    elif loc_active is not None and len(loc_active[0]) > 0:
                        tracker_states[id] = "ACTIVE"



                    
                else:
                    pass
                    # print("Error: Bounding box is out of frame dimensions or has invalid dimensions.")


                # Retrieve the title from the dictionary
                title = tracker_titles[id]

                # The rest of the code remains the same...
                window_name, document_name = split_title(title)

                cv2.putText(frame, 'ID: ' + str(id) + ' - ' + tracker_states[id] + " Title: " + title, p1, cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36,255,12), 2)

            else:
                # remove tracker if it's not successful
                del trackers[id]
                del tracker_states[id]  # also remove from tracker_states
                 # Insert event into database
                window_name, document_name = split_title(title)
                insert_event(conn, int(box[0]), int(box[1]), int(box[2]), int(box[3]), window_name, document_name, 'APPLICATION_CLOSE')



        # Detect new windows if no windows are currently being tracked
        # if not trackers:
        if time.time() - last_detection_time > detection_interval:
            last_detection_time = time.time()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            ret, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                # get rectangle bounding contour
                [x, y, w, h] = cv2.boundingRect(contour)

                # discard areas that are too large
                if h > 500 and w > 500:
                    continue

                # discard areas that are too small
                if h < 40 or w < 40:
                    continue

                # Assume this window is new
                is_new_window = True

                # Check if this window overlaps with a tracked window
                for id, tracker in trackers.items():
                    # box = tracker.get_position()
                    success, box = tracker.update(frame)
                    if success:
                        # The rectangle of the tracked window
                        tracked_rect = (int(box[0]), int(box[1]), int(box[0] + box[2]), int(box[1] + box[3]))

                        # The rectangle of the new window
                        new_rect = (x, y, x + w, y + h)

                        # Check if the rectangles overlap
                        # The rectangles overlap if the intersection area is more than half of the new window area
                        # and more than half of the tracked window area
                        x_overlap = max(0, min(tracked_rect[2], new_rect[2]) - max(tracked_rect[0], new_rect[0]))
                        y_overlap = max(0, min(tracked_rect[3], new_rect[3]) - max(tracked_rect[1], new_rect[1]))
                        overlap_area = x_overlap * y_overlap
                        if overlap_area > 0.5 * w * h or overlap_area > 0.5 * box[2] * box[3]:
                            is_new_window = False
                            break

                if not is_new_window:
                    continue

                # check if the window has the OS action buttons
                roi = frame[y:y + h, x:x + w]
                roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

                loc_inactive = loc_active = None

                # Check if ROI is large enough for template matching
                if roi_gray.shape[0] >= template_inactive.shape[0] and roi_gray.shape[1] >= template_inactive.shape[1]:
                    res_inactive = cv2.matchTemplate(roi_gray, template_inactive, cv2.TM_CCOEFF_NORMED)
                    loc_inactive = np.where(res_inactive >= threshold)

                if roi_gray.shape[0] >= template_active.shape[0] and roi_gray.shape[1] >= template_active.shape[1]:
                    res_active = cv2.matchTemplate(roi_gray, template_active, cv2.TM_CCOEFF_NORMED)
                    loc_active = np.where(res_active >= threshold)


                # In the detection block:
                if loc_inactive is not None and len(loc_inactive[0]) > 0:
                    # add a tracker for the new window
                    tracker = cv2.legacy.TrackerMOSSE_create()
                    tracker.init(frame, (x, y, w, h))
                    trackers[window_id] = tracker
                    tracker_states[window_id] = "INACTIVE"  # set tracker state
                    
                    # Extract the title bar of the window
                    title_bar = frame[y:y + title_bar_height, x:x + w]

                    # Convert the title bar to grayscale
                    title_bar_gray = cv2.cvtColor(title_bar, cv2.COLOR_BGR2GRAY)

                    # Use Tesseract to do OCR on the title bar
                    title = pytesseract.image_to_string(title_bar_gray)

                    # Store the title in the dictionary
                    tracker_titles[window_id] = title

                    window_name, document_name = split_title(title)
                    insert_event(conn, x, y, w, h, window_name, document_name, 'APPLICATION_OPEN')
                    window_id += 1

                elif loc_active is not None and len(loc_active[0]) > 0:
                    # add a tracker for the new window
                    tracker = cv2.legacy.TrackerMOSSE_create()
                    tracker.init(frame, (x, y, w, h))
                    trackers[window_id] = tracker
                    tracker_states[window_id] = "ACTIVE"  # set tracker state

                    # Extract the title bar of the window
                    title_bar = frame[y:y + title_bar_height, x:x + w]

                    # Convert the title bar to grayscale
                    title_bar_gray = cv2.cvtColor(title_bar, cv2.COLOR_BGR2GRAY)

                    # Use Tesseract to do OCR on the title bar
                    title = pytesseract.image_to_string(title_bar_gray)

                    # Store the title in the dictionary
                    tracker_titles[window_id] = title
                    
                    window_name, document_name = split_title(title)
                    insert_event(conn, x, y, w, h, window_name, document_name, 'APPLICATION_OPEN')
                    window_id += 1

        # Display the resulting frame
        cv2.imshow('Screen Capture', frame)

        # Break the loop on 'q' press or after 60 seconds
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()
