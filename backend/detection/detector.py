import argparse
import cv2
from ultralytics import YOLO

# 1️⃣ Load YOLOv8 model
model = YOLO("yolov8n.pt")  # nano model, downloads automatically

# 2️⃣ Parse command-line arguments
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

# 3️⃣ Open video or webcam
if args.mode == "webcam":
    cap = cv2.VideoCapture(0)  # live camera
else:
    cap = cv2.VideoCapture(args.video_path)  # demo video

print(f"[INFO] Running in {args.mode} mode")

# 4️⃣ Detection loop
while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame)[0]

    for box, score, cls in zip(results.boxes.xyxy, results.boxes.conf, results.boxes.cls):
        if int(cls) == 0:
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{score:.2f}", (x1, y1-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    cv2.imshow("Person Detection", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()