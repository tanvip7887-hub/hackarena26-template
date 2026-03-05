import argparse
import cv2
from ultralytics import YOLO
from detection.tracker import Tracker  # import the basic tracker
import numpy as np

# Load YOLOv8 model
model = YOLO("yolov8n.pt")  

# Parse arguments
parser = argparse.ArgumentParser(description="Person Detection Mode")
parser.add_argument(
    "--mode", choices=["webcam", "video"], default="webcam",
    help="Choose 'webcam' for live camera or 'video' for demo video"
)
parser.add_argument(
    "--video_path", type=str, default="videos/sample.mp4",
    help="Path to demo video (used only if mode=video)"
)
args = parser.parse_args()

# Video capture
if args.mode == "webcam":
    cap = cv2.VideoCapture(0) 
else:
    cap = cv2.VideoCapture(args.video_path)  

print(f"[INFO] Running in {args.mode} mode")

# Initialize tracker
tracker = Tracker(iou_threshold=0.3)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Run YOLO detection
    results = model(frame)[0]

    # Collect person boxes
    boxes = []
    for box, score, cls in zip(results.boxes.xyxy, results.boxes.conf, results.boxes.cls):
        if int(cls) == 0:
            x1, y1, x2, y2 = map(int, box)
            boxes.append([x1, y1, x2, y2])

    # Update tracker and get tracked boxes with IDs
    tracks = tracker.update(boxes)

    # Draw tracked boxes
    for x1, y1, x2, y2, track_id in tracks:
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)  # red boxes for tracked IDs
        cv2.putText(frame, f"ID {track_id}", (x1, y1-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    # Show frame
    cv2.imshow("Person Detection + Tracking", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()