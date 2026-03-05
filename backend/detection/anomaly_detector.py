"""
anomaly_detector.py — FINAL + LLM support
Added:
  - MIN_DISPLACEMENT_FRAC (fraction-based, camera independent)
  - get_current_speed_pxsec()  — for ML features in threat_engine
  - get_freeze_duration()      — for ML features in threat_engine
  - get_anomalies_with_scores() — explicit method for LLM factor list
"""
import math
import time
from collections import deque


def _circular_std(angles_deg):
    """
    Correct std for circular/angular data using mean resultant length.
    Handles wrap-around (e.g. 350° and 10° are close, not 340° apart).
    Returns value in radians: ~0 = consistent direction, >1.2 = erratic.
    """
    if len(angles_deg) < 2:
        return 0.0
    rads     = [math.radians(a) for a in angles_deg]
    sin_mean = sum(math.sin(r) for r in rads) / len(rads)
    cos_mean = sum(math.cos(r) for r in rads) / len(rads)
    R        = math.sqrt(sin_mean**2 + cos_mean**2)
    return math.sqrt(-2 * math.log(max(R, 1e-9)))


class PersonBehaviourTracker:

    HISTORY_FRAMES   = 90

    # FIX: Fraction-based displacement — scales with any camera resolution
    # OLD: MIN_DISPLACEMENT = 8  (broke on 1080p cameras)
    # NEW: 1.2% of frame width
    #   640px  → 7.7px  (similar to old value)
    #   1280px → 15.4px (auto-scales up for higher res)
    MIN_DISPLACEMENT_FRAC = 0.012

    # Speed (normalized — camera independent)
    RUNNING_DIAG_FRAC   = 0.22
    SPRINTING_DIAG_FRAC = 0.40
    SPEED_STILL         = 15     # px/sec for freeze check only

    # Pacing
    PACE_WINDOW       = 40
    PACE_REVERSALS    = 8
    PACE_ANGLE_THRESH = 150

    # Erratic (circular std)
    ERRATIC_CIRC_STD  = 1.2
    ERRATIC_WINDOW    = 20

    # Circling
    CIRCLE_MIN_PATH       = 200
    CIRCLE_ANCHOR_RETURN  = 40
    CIRCLE_ROLLING_RETURN = 25

    # Freeze
    FREEZE_MOVE_FRAC  = 0.18
    FREEZE_HOLD_SECS  = 4.0

    # Prolonged presence
    PRESENCE_SECS     = 180

    # Crouching (personal baseline — adapts to camera angle)
    CROUCH_DROP_FACTOR    = 0.65
    CROUCH_FRAMES_MIN     = 8
    CROUCH_MAX_FRAME_FILL = 0.45

    # Tailgating (dynamic threshold + direction check)
    TAILGATE_FRAME_FRAC = 0.12
    TAILGATE_DIR_THRESH = 60

    # Zone approach
    ZONE_APPROACH_MIN = 4

    def __init__(self, pid):
        self.pid              = pid
        self.positions        = deque(maxlen=self.HISTORY_FRAMES)
        self.norm_speeds      = deque(maxlen=self.HISTORY_FRAMES)
        self.directions       = deque(maxlen=self.HISTORY_FRAMES)
        self.bboxes           = deque(maxlen=30)
        self.anomalies        = []

        # Time-based threat decay (FPS independent)
        self.threat_score     = 0.0
        self._last_decay_time = time.time()

        self.first_seen       = time.time()
        self.still_since      = None
        self.was_fast_before  = False
        self.last_near_zone   = False
        self.zone_approaches  = 0
        self.carrying_object  = False
        self.carrying_label   = ""

        # Frame metrics — updated each frame
        self._frame_diag      = 800.0
        self._frame_h         = 480.0
        self._frame_w         = 640.0
        self._fps             = 30.0

        # Circling anchor — set ONCE on first detection, never changes
        self._circle_anchor   = None

        # Personal crouching baseline — calibrated from first 20 valid frames
        self._baseline_ratios = []
        self._baseline_ratio  = None

    def update(self, bbox, frame_shape=None, near_zone=False,
               other_persons=None, fps=30):
        x1, y1, x2, y2 = bbox
        cx  = (x1 + x2) / 2.0
        cy  = (y1 + y2) / 2.0
        bh  = max(y2 - y1, 1)
        bw  = max(x2 - x1, 1)
        now = time.time()

        # Update frame metrics
        if frame_shape is not None:
            fh, fw           = frame_shape[0], frame_shape[1]
            self._frame_diag = math.sqrt(fw*fw + fh*fh)
            self._frame_h    = fh
            self._frame_w    = fw
        self._fps = max(fps, 1.0)

        # Set circling anchor once on first detection
        if self._circle_anchor is None:
            self._circle_anchor = (cx, cy)

        self.positions.append((cx, cy, now))
        self.bboxes.append((bh, bw, now))

        # Time-based decay (FPS independent)
        delta_time            = now - self._last_decay_time
        self._last_decay_time = now
        self.threat_score    *= math.exp(-0.7 * delta_time)

        self.anomalies = []

        # Collect crouching baseline from first 20 valid frames
        if self._baseline_ratio is None:
            frame_fill = bh / self._frame_h
            if frame_fill < self.CROUCH_MAX_FRAME_FILL:
                self._baseline_ratios.append(bh / bw)
            if len(self._baseline_ratios) >= 20:
                self._baseline_ratio = sum(self._baseline_ratios) / len(
                    self._baseline_ratios)

        if len(self.positions) < 5:
            return

        px, py, pt = self.positions[-2]
        dx, dy     = cx - px, cy - py
        dt         = max(now - pt, 0.001)
        dist       = math.sqrt(dx*dx + dy*dy)

        # JITTER FILTER — fraction-based, scales with any resolution
        min_disp = self._frame_w * self.MIN_DISPLACEMENT_FRAC
        if dist < min_disp:
            self.norm_speeds.append(0.0)
            # No direction update — stationary = no real direction
        else:
            px_per_sec = dist / dt
            self.norm_speeds.append(px_per_sec / self._frame_diag)
            self.directions.append(math.degrees(math.atan2(dy, dx)))

        if len(self.norm_speeds) < 10:
            return

        self._check_running()
        self._check_pacing()
        self._check_erratic()
        self._check_circling()
        self._check_crouching()
        self._check_freeze(now)
        self._check_peripheral_loiter(near_zone)
        self._check_prolonged(now)
        self._check_carrying()
        if other_persons:
            self._check_tailgate(cx, cy, other_persons)

    # ── Behaviour checks ────────────────────────────────────────

    def _check_running(self):
        if len(self.norm_speeds) < 8:
            return
        avg = sum(list(self.norm_speeds)[-8:]) / 8
        if avg >= self.SPRINTING_DIAG_FRAC:
            self._add("SPRINTING", min(int(avg / self.SPRINTING_DIAG_FRAC * 30), 40))
        elif avg >= self.RUNNING_DIAG_FRAC:
            self._add("RUNNING", min(int(avg / self.RUNNING_DIAG_FRAC * 20), 30))

    def _check_pacing(self):
        if len(self.directions) < 20:
            return
        window    = list(self.directions)[-self.PACE_WINDOW:]
        reversals = 0
        for i in range(1, len(window)):
            diff = abs(window[i] - window[i-1])
            if diff > 180: diff = 360 - diff
            if diff > self.PACE_ANGLE_THRESH:
                reversals += 1
        if reversals >= self.PACE_REVERSALS:
            self._add("PACING", min(10 + reversals * 2, 25))

    def _check_erratic(self):
        if len(self.directions) < self.ERRATIC_WINDOW:
            return
        circ_std = _circular_std(list(self.directions)[-self.ERRATIC_WINDOW:])
        if circ_std >= self.ERRATIC_CIRC_STD:
            self._add("ERRATIC MOVEMENT",
                      min(int((circ_std - self.ERRATIC_CIRC_STD) / 0.5 * 8) + 10, 20))

    def _check_circling(self):
        if len(self.positions) < 50:
            return
        total_path = sum(
            math.sqrt((self.positions[i][0]-self.positions[i-1][0])**2 +
                      (self.positions[i][1]-self.positions[i-1][1])**2)
            for i in range(1, len(self.positions))
        )
        if total_path < self.CIRCLE_MIN_PATH:
            return
        cx_now, cy_now, _ = self.positions[-1]

        ax, ay = self._circle_anchor
        if math.sqrt((cx_now-ax)**2 + (cy_now-ay)**2) <= self.CIRCLE_ANCHOR_RETURN:
            self._add("CIRCLING AREA (origin return)", 25)
            return

        ox, oy, _ = self.positions[0]
        if math.sqrt((cx_now-ox)**2 + (cy_now-oy)**2) <= self.CIRCLE_ROLLING_RETURN:
            self._add("CIRCLING AREA (looping)", 20)

    def _check_crouching(self):
        if self._baseline_ratio is None or len(self.bboxes) < 10:
            return
        threshold     = self._baseline_ratio * self.CROUCH_DROP_FACTOR
        crouch_frames = 0
        for bh, bw, _ in list(self.bboxes)[-10:]:
            frame_fill = bh / self._frame_h
            if frame_fill < self.CROUCH_MAX_FRAME_FILL and (bh/bw) < threshold:
                crouch_frames += 1
        if crouch_frames >= self.CROUCH_FRAMES_MIN:
            self._add("CROUCHING", 20)

    def _check_freeze(self, now):
        if len(self.norm_speeds) < 12:
            return
        prev_avg = sum(list(self.norm_speeds)[-12:-4]) / 8
        curr_abs = list(self.norm_speeds)[-1] * self._frame_diag

        if prev_avg >= self.FREEZE_MOVE_FRAC:
            self.was_fast_before = True

        if self.was_fast_before and curr_abs < self.SPEED_STILL:
            if self.still_since is None:
                self.still_since = now
            frozen = now - self.still_since
            if frozen >= self.FREEZE_HOLD_SECS:
                self._add("SUDDEN FREEZE {:.0f}s".format(frozen),
                          min(15 + int(frozen - self.FREEZE_HOLD_SECS) * 2, 30))
        elif curr_abs >= self.SPEED_STILL * 3:
            self.still_since     = None
            self.was_fast_before = False

    def _check_peripheral_loiter(self, near_zone):
        if near_zone and not self.last_near_zone:
            self.zone_approaches += 1
        self.last_near_zone = near_zone
        if self.zone_approaches >= self.ZONE_APPROACH_MIN:
            self._add("ZONE RECON x{}".format(self.zone_approaches),
                      min(10 + self.zone_approaches * 5, 30))

    def _check_prolonged(self, now):
        secs = now - self.first_seen
        if secs >= self.PRESENCE_SECS:
            self._add("PROLONGED PRESENCE {:.0f}min".format(secs/60),
                      min(10 + int((secs - self.PRESENCE_SECS) / 30) * 3, 25))

    def _check_carrying(self):
        if self.carrying_object:
            self._add("CARRYING: " + self.carrying_label, 25)

    def _check_tailgate(self, cx, cy, other_persons):
        threshold = self._frame_w * self.TAILGATE_FRAME_FRAC
        my_dir    = list(self.directions)[-1] if self.directions else None
        for ob in other_persons:
            ox1, oy1, ox2, oy2 = ob
            ocx  = (ox1 + ox2) / 2.0
            ocy  = (oy1 + oy2) / 2.0
            dist = math.sqrt((cx-ocx)**2 + (cy-ocy)**2)
            if dist < threshold:
                if my_dir is None:
                    break
                between = math.degrees(math.atan2(ocy-cy, ocx-cx))
                diff    = abs(my_dir - between)
                if diff > 180: diff = 360 - diff
                if diff <= self.TAILGATE_DIR_THRESH:
                    self._add("TAILGATING", 20)
                    break

    def _add(self, name, score):
        if not any(a[0] == name for a in self.anomalies):
            self.anomalies.append((name, score))
            self.threat_score += score

    # ── Public getters ───────────────────────────────────────────

    def get_anomaly_score(self):
        return min(self.threat_score, 60)

    def get_names(self):
        return [n for n, _ in self.anomalies]

    def get_summary(self):
        return " | ".join(n for n, _ in self.anomalies) if self.anomalies else "Normal"

    def get_fps(self):
        return self._fps

    def get_current_speed_pxsec(self):
        """
        Current speed in pixels/sec.
        Used by threat_engine for ML feature: 'speed'.
        Returns 0.0 if no movement recorded yet.
        """
        if not self.norm_speeds:
            return 0.0
        return self.norm_speeds[-1] * self._frame_diag

    def get_freeze_duration(self):
        """
        How long this person has been frozen in seconds.
        Used by threat_engine for ML feature: 'freeze_time'.
        Returns 0.0 if not currently frozen.
        """
        if self.still_since is not None:
            return time.time() - self.still_since
        return 0.0

    def get_anomalies_with_scores(self):
        """
        Returns copy of active anomalies as [(name, score), ...].
        Used by app.py LLM queue to build factor list for LM Studio prompt.
        Same data as bt.anomalies but accessed via explicit method.
        """
        return list(self.anomalies)