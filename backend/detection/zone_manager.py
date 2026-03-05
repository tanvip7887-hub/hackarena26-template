# detection/zone_manager.py

import cv2

class ZoneManager:
    def __init__(self):
        self.name = "Server Room"

    def get_zone_coordinates(self, frame):
        """
        Dynamically calculate restricted zone
        based on frame size.
        """
        h, w, _ = frame.shape
  
        # Right side vertical zone (clean proportion)
        x1 = int(w * 0.65)
        y1 = int(h * 0.20)
        x2 = int(w * 0.95)
        y2 = int(h * 0.90)

        return x1, y1, x2, y2

    def is_inside(self, bbox, frame):
        """
        Check if person center is inside restricted zone
        """
        x1, y1, x2, y2 = self.get_zone_coordinates(frame)

        bx1, by1, bx2, by2 = bbox

        cx = int((bx1 + bx2) / 2)
        cy = int((by1 + by2) / 2)

        return x1 < cx < x2 and y1 < cy < y2
    
    def is_near(self, bbox, frame, margin=50):
        """
        Check if person center is near restricted zone (within margin pixels)
        """
        x1, y1, x2, y2 = self.get_zone_coordinates(frame)

        # Expand zone by margin
        x1m = x1 - margin
        y1m = y1 - margin
        x2m = x2 + margin
        y2m = y2 + margin

        bx1, by1, bx2, by2 = bbox
        cx = int((bx1 + bx2) / 2)
        cy = int((by1 + by2) / 2)

        return x1m < cx < x2m and y1m < cy < y2m


    def draw(self, frame):
        """
        Draw restricted zone with overlay
        """
        x1, y1, x2, y2 = self.get_zone_coordinates(frame)

        # Transparent red overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 255), -1)
        cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)

        # Border
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)

        # Label
        cv2.putText(
            frame,
            f"RESTRICTED: {self.name}",
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2
        )