# tracker.py 
import numpy as np

class Tracker:
    """
    Very simple multi-object tracker.
    Assigns IDs based on bounding box overlap (IoU).
    """

    def __init__(self, iou_threshold=0.3):
        self.iou_threshold = iou_threshold
        self.tracks = []  
        self.next_id = 1

    def iou(self, box1, box2):
        xx1 = max(box1[0], box2[0])
        yy1 = max(box1[1], box2[1])
        xx2 = min(box1[2], box2[2])
        yy2 = min(box1[3], box2[3])
        w = max(0, xx2 - xx1)
        h = max(0, yy2 - yy1)
        inter = w * h
        area1 = (box1[2]-box1[0])*(box1[3]-box1[1])
        area2 = (box2[2]-box2[0])*(box2[3]-box2[1])
        union = area1 + area2 - inter
        return inter / union if union > 0 else 0

    def update(self, detections):
        """
        detections: list of [x1,y1,x2,y2]
        returns: list of [x1,y1,x2,y2,id]
        """
        updated_tracks = []

        for det in detections:
            matched = False
            for trk in self.tracks:
                if self.iou(det, trk[:4]) > self.iou_threshold:
                    trk[:4] = det 
                    updated_tracks.append(trk)
                    matched = True
                    break
            if not matched:
                trk = list(det) + [self.next_id]
                self.next_id += 1
                updated_tracks.append(trk)

        self.tracks = updated_tracks
        return self.tracks