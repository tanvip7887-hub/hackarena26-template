"""
tracker.py — SORT (Simple Online and Realtime Tracking) implementation
Uses Kalman Filter + Hungarian Algorithm for multi-object tracking.
Assigns unique IDs to detected persons across frames.
"""

import numpy as np
from filterpy.kalman import KalmanFilter
from scipy.optimize import linear_sum_assignment


def iou(bb_test, bb_gt):
    """
    Compute Intersection over Union between two bounding boxes.
    Format: [x1, y1, x2, y2]
    """
    xx1 = max(bb_test[0], bb_gt[0])
    yy1 = max(bb_test[1], bb_gt[1])
    xx2 = min(bb_test[2], bb_gt[2])
    yy2 = min(bb_test[3], bb_gt[3])

    w = max(0.0, xx2 - xx1)
    h = max(0.0, yy2 - yy1)
    intersection = w * h

    area_test = (bb_test[2] - bb_test[0]) * (bb_test[3] - bb_test[1])
    area_gt   = (bb_gt[2]   - bb_gt[0])   * (bb_gt[3]   - bb_gt[1])
    union = area_test + area_gt - intersection

    return intersection / union if union > 0 else 0.0


def convert_bbox_to_z(bbox):
    """Convert [x1,y1,x2,y2] to center-format state [cx,cy,s,r]."""
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    cx = bbox[0] + w / 2.0
    cy = bbox[1] + h / 2.0
    s = w * h          # scale (area)
    r = w / float(h)   # aspect ratio
    return np.array([cx, cy, s, r]).reshape((4, 1))


def convert_x_to_bbox(x, score=None):
    """Convert Kalman state [cx,cy,s,r] back to [x1,y1,x2,y2]."""
    w = np.sqrt(x[2] * x[3])
    h = x[2] / w
    box = [
        x[0] - w / 2.0,
        x[1] - h / 2.0,
        x[0] + w / 2.0,
        x[1] + h / 2.0,
    ]
    if score is None:
        return np.array(box).reshape((1, 4))
    return np.array(box + [score]).reshape((1, 5))


class KalmanBoxTracker:
    """
    Single-object tracker using a Kalman Filter.
    State: [cx, cy, s, r, vx, vy, vs]
    """
    count = 0  # class-level ID counter

    def __init__(self, bbox):
        self.kf = KalmanFilter(dim_x=7, dim_z=4)

        # State transition matrix
        self.kf.F = np.array([
            [1,0,0,0,1,0,0],
            [0,1,0,0,0,1,0],
            [0,0,1,0,0,0,1],
            [0,0,0,1,0,0,0],
            [0,0,0,0,1,0,0],
            [0,0,0,0,0,1,0],
            [0,0,0,0,0,0,1],
        ], dtype=float)

        # Measurement matrix (we observe cx, cy, s, r)
        self.kf.H = np.array([
            [1,0,0,0,0,0,0],
            [0,1,0,0,0,0,0],
            [0,0,1,0,0,0,0],
            [0,0,0,1,0,0,0],
        ], dtype=float)

        self.kf.R[2:, 2:] *= 10.0   # measurement noise
        self.kf.P[4:, 4:] *= 1000.0 # high uncertainty for unobserved velocities
        self.kf.P *= 10.0
        self.kf.Q[-1, -1] *= 0.01
        self.kf.Q[4:, 4:] *= 0.01

        self.kf.x[:4] = convert_bbox_to_z(bbox)

        self.time_since_update = 0
        KalmanBoxTracker.count += 1
        self.id = KalmanBoxTracker.count
        self.history = []
        self.hits = 0
        self.hit_streak = 0
        self.age = 0

    def update(self, bbox):
        """Update tracker with a new detection."""
        self.time_since_update = 0
        self.history = []
        self.hits += 1
        self.hit_streak += 1
        self.kf.update(convert_bbox_to_z(bbox))

    def predict(self):
        """Advance state and return predicted bounding box."""
        if (self.kf.x[6] + self.kf.x[2]) <= 0:
            self.kf.x[6] *= 0.0
        self.kf.predict()
        self.age += 1
        if self.time_since_update > 0:
            self.hit_streak = 0
        self.time_since_update += 1
        self.history.append(convert_x_to_bbox(self.kf.x))
        return self.history[-1]

    def get_state(self):
        """Return current bounding box as [x1, y1, x2, y2]."""
        return convert_x_to_bbox(self.kf.x)


def associate_detections_to_trackers(detections, trackers, iou_threshold=0.3):
    """
    Match detections to existing trackers using the Hungarian algorithm.
    Returns: matched pairs, unmatched detections, unmatched trackers.
    """
    if len(trackers) == 0:
        return (
            np.empty((0, 2), dtype=int),
            np.arange(len(detections)),
            np.empty(0, dtype=int),
        )

    iou_matrix = np.zeros((len(detections), len(trackers)), dtype=float)
    for d, det in enumerate(detections):
        for t, trk in enumerate(trackers):
            iou_matrix[d, t] = iou(det, trk)

    # Hungarian assignment (maximise IoU → minimise -IoU)
    row_ind, col_ind = linear_sum_assignment(-iou_matrix)
    matched_indices = np.stack([row_ind, col_ind], axis=1)

    unmatched_detections = [
        d for d in range(len(detections))
        if d not in matched_indices[:, 0]
    ]
    unmatched_trackers = [
        t for t in range(len(trackers))
        if t not in matched_indices[:, 1]
    ]

    # Filter out low-IoU matches
    matches = []
    for m in matched_indices:
        if iou_matrix[m[0], m[1]] < iou_threshold:
            unmatched_detections.append(m[0])
            unmatched_trackers.append(m[1])
        else:
            matches.append(m.reshape(1, 2))

    if len(matches) == 0:
        matches = np.empty((0, 2), dtype=int)
    else:
        matches = np.concatenate(matches, axis=0)

    return matches, np.array(unmatched_detections), np.array(unmatched_trackers)


class SORTTracker:
    """
    SORT multi-object tracker.
    Call .update(detections) each frame; returns active tracks as
    [[x1, y1, x2, y2, track_id], ...].
    """

    def __init__(self, max_age=30, min_hits=2, iou_threshold=0.3):
        self.max_age = max_age          # frames to keep a lost track alive
        self.min_hits = min_hits        # min detections before track is reported
        self.iou_threshold = iou_threshold
        self.trackers: list[KalmanBoxTracker] = []
        self.frame_count = 0

    def reset_ids(self):
        """Reset ID counter (call between mode switches)."""
        KalmanBoxTracker.count = 0
        self.trackers = []
        self.frame_count = 0

    def update(self, dets: np.ndarray) -> np.ndarray:
        """
        dets: np.ndarray shape (N, 4) — [[x1,y1,x2,y2], ...]
        Returns: np.ndarray shape (M, 5) — [[x1,y1,x2,y2,id], ...]
        """
        self.frame_count += 1

        # Predict positions for all existing trackers
        trks = np.zeros((len(self.trackers), 4))
        to_del = []
        for t, trk in enumerate(self.trackers):
            pos = trk.predict()[0]
            trks[t] = pos
            if np.any(np.isnan(pos)):
                to_del.append(t)
        trks = np.ma.compress_rows(np.ma.masked_invalid(trks))
        for t in reversed(to_del):
            self.trackers.pop(t)

        matched, unmatched_dets, unmatched_trks = associate_detections_to_trackers(
            dets, trks, self.iou_threshold
        )

        # Update matched trackers
        for m in matched:
            self.trackers[m[1]].update(dets[m[0]])

        # Create new trackers for unmatched detections
        for i in unmatched_dets:
            self.trackers.append(KalmanBoxTracker(dets[i]))

        # Collect active tracks
        results = []
        for trk in reversed(self.trackers):
            d = trk.get_state()[0]
            if (trk.time_since_update < 1) and (
                trk.hit_streak >= self.min_hits or self.frame_count <= self.min_hits
            ):
                results.append([d[0], d[1], d[2], d[3], trk.id])

        # Remove dead trackers
        self.trackers = [
            t for t in self.trackers if t.time_since_update <= self.max_age
        ]

        return np.array(results) if results else np.empty((0, 5))