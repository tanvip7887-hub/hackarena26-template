"""
detector.py — YOLOv8 person detection wrapper.
Uses the lightweight yolov8n.pt model (auto-downloaded on first run).
Only detects class 0 = 'person' to keep it fast on CPU.
"""

import numpy as np
from ultralytics import YOLO


class PersonDetector:
    """
    Wraps YOLOv8n for person-only detection.
    Returns bounding boxes as [[x1, y1, x2, y2], ...].
    """

    # COCO class index for 'person'
    PERSON_CLASS_ID = 0

    def __init__(self, model_path: str = "yolov8n.pt", confidence: float = 0.4):
        """
        Args:
            model_path: Path or name of the YOLOv8 model weights.
                        'yolov8n.pt' will be downloaded automatically.
            confidence: Minimum detection confidence (0–1).
        """
        print(f"[Detector] Loading YOLOv8 model: {model_path}")
        self.model = YOLO(model_path)
        self.confidence = confidence
        print("[Detector] Model ready.")

    def detect(self, frame: np.ndarray) -> np.ndarray:
        """
        Run inference on a single BGR frame.

        Args:
            frame: OpenCV BGR image (H x W x 3).

        Returns:
            np.ndarray of shape (N, 4): [[x1, y1, x2, y2], ...]
            Returns empty array if no persons detected.
        """
        # Run inference — verbose=False suppresses per-frame logs
        results = self.model(
            frame,
            classes=[self.PERSON_CLASS_ID],
            conf=self.confidence,
            verbose=False,
        )

        boxes = []
        for result in results:
            for box in result.boxes:
                cls = int(box.cls[0])
                if cls == self.PERSON_CLASS_ID:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    boxes.append([x1, y1, x2, y2])

        return np.array(boxes, dtype=float) if boxes else np.empty((0, 4))