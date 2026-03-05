# app.py
import argparse
import cv2
from detection.detector import PersonDetector
from detection.tracker import Tracker  # basic tracker
import numpy as np

# Argument parser
parser = argparse.ArgumentParser(description="Person Detection + Tracking")
parser.add_argument("--mode", choices=["webcam", "video"], default="webcam")
parser.add_argument("--video_path", type=str, default="videos/sample.mp4")
args = parser.parse_args()

# Video capture
cap = cv2.VideoCapture(0) if args.mode == "webcam" else cv2.VideoCapture(args.video_path)

# Initialize detector and tracker
detector = PersonDetector(confidence=0.4)
tracker = Tracker(iou_threshold=0.3)

print(f"[INFO] Running in {args.mode} mode")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Detect persons
    boxes = detector.detect(frame)  # returns [[x1, y1, x2, y2], ...]
    boxes_list = boxes.tolist() if len(boxes) > 0 else []

    # Update tracker
    tracks = tracker.update(boxes_list)

    # Draw tracked boxes
    for x1, y1, x2, y2, track_id in tracks:
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
        cv2.putText(frame, f"ID {track_id}", (int(x1), int(y1)-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    cv2.imshow("Person Detection + Tracking", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()