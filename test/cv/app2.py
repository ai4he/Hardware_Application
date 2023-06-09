import cv2
import numpy as np

# Load the image and the templates
image = cv2.imread('screenshot.png')
template_inactive = cv2.imread('template_inactive.png', cv2.IMREAD_COLOR)
template_active = cv2.imread('template_active.png', cv2.IMREAD_COLOR)

# Check if the image and templates have been correctly loaded
if image is None:
    print("Could not open or find the image")
elif template_inactive is None:
    print("Could not open or find the inactive template")
elif template_active is None:
    print("Could not open or find the active template")
else:
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply Canny edge detection
    edges = cv2.Canny(gray, 50, 200)

    # Find contours
    contours, _ = cv2.findContours(edges.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        # Get approximate polygon
        epsilon = 0.02 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)

        if len(approx) == 4:  # If the contour has four points, it might be a window
            x, y, w, h = cv2.boundingRect(approx)

            # Check if the rectangle is larger than 2x the inactive template image
            if w > 2*template_inactive.shape[1] and h > 2*template_inactive.shape[0]:
                roi = image[y:y+h, x:x+w]  # Region of Interest where we'll look for the templates

                # Apply template Matching for the inactive template
                res_inactive = cv2.matchTemplate(roi, template_inactive, cv2.TM_CCOEFF_NORMED)
                threshold = 0.8

                # If a match is found, draw a bounding box and add a label
                if np.any(res_inactive >= threshold):
                    cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(image, 'INACTIVE_WINDOW', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36,255,12), 2)

                # Apply template Matching for the active template
                res_active = cv2.matchTemplate(roi, template_active, cv2.TM_CCOEFF_NORMED)

                # If a match is found, draw a bounding box and add a label
                if np.any(res_active >= threshold):
                    cv2.rectangle(image, (x, y), (x + w, y + h), (0, 0, 255), 2)
                    cv2.putText(image, 'ACTIVE_WINDOW', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36,255,12), 2)

    cv2.imshow('Detected',image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
