"""
threat_engine.py — Hackathon Final

Scoring system:
  1. Continuous scoring  — values grow gradually, not fixed jumps
  2. Night multiplier    — 1.5x amplifies ALL threats after dark
  3. Synergy bonus       — night + zone = extra +20 on top
"""
import datetime
import joblib
import numpy as np

model = joblib.load("ml/threat_model.pkl")

# ── Base scores (before multiplier) ───────────────────────────
SCORE_HUMAN             = 10

# Zone scores — continuous
SCORE_ZONE_BASE         = 30   # base for being in zone
SCORE_ZONE_LOITER_MAX   = 30   # max extra from loitering in zone
SCORE_ZONE_LOITER_SECS  = 60   # seconds to reach max loiter score

# Peripheral loiter — continuous
SCORE_PERIPHERAL_MAX    = 25   # max from standing near zone
SCORE_PERIPHERAL_SECS   = 60   # seconds to reach max

# Crowd
SCORE_CROWD_PER_PERSON  = 8    # per extra person beyond 1

# Night
NIGHT_MULTIPLIER        = 1.5  # amplifies total score
SYNERGY_BONUS           = 20   # extra if night AND in zone

RISK_THRESHOLDS = {
    "Low":    (0,  35),
    "Medium": (36, 70),
    "High":   (71, 999)
}

CURRENT_MODE = "live"


def is_night_time():
    if CURRENT_MODE == "demo":
        return True
    h = datetime.datetime.now().hour
    return h >= 22 or h < 6


def compute_threat(person_detected, in_zone, loiter_seconds,
                   peripheral_seconds=0.0,
                   crowd_count=1,
                   behaviour_anomalies=None,   # list of (name, score) tuples
                   override_night=None):
    """
    All parameters:
      person_detected     → bool
      in_zone             → bool
      loiter_seconds      → float: seconds inside zone
      peripheral_seconds  → float: seconds near zone but outside
      crowd_count         → int: total persons in frame
      behaviour_anomalies → list of (name, score) from anomaly_detector
      override_night      → bool or None
    """
    if behaviour_anomalies is None:
        behaviour_anomalies = []

    if not person_detected:
        return 0, "Low", "No threat detected."

    score   = 0
    reasons = []

    # 1. Human base
    score += SCORE_HUMAN
    reasons.append(("Human Detected", SCORE_HUMAN))

    # 2. Zone — continuous loiter score
    if in_zone:
        zone_pts = SCORE_ZONE_BASE
        reasons.append(("Zone Entry", SCORE_ZONE_BASE))

        if loiter_seconds > 0:
            loiter_pts = min(
                int(loiter_seconds / SCORE_ZONE_LOITER_SECS * SCORE_ZONE_LOITER_MAX),
                SCORE_ZONE_LOITER_MAX
            )
            if loiter_pts > 0:
                score += loiter_pts
                reasons.append(("Loitering {:.0f}s".format(loiter_seconds),
                                 loiter_pts))
        score += zone_pts

    # 3. Peripheral loiter — continuous
    if not in_zone and peripheral_seconds >= 10:
        periph_pts = min(
            int(peripheral_seconds / SCORE_PERIPHERAL_SECS * SCORE_PERIPHERAL_MAX),
            SCORE_PERIPHERAL_MAX
        )
        if periph_pts > 0:
            score += periph_pts
            reasons.append(("Near Zone {:.0f}s".format(peripheral_seconds),
                             periph_pts))

    # 4. Crowd
    if crowd_count >= 2:
        crowd_pts = (crowd_count - 1) * SCORE_CROWD_PER_PERSON
        score += crowd_pts
        reasons.append(("Crowd {} persons".format(crowd_count), crowd_pts))

    # 5. Behaviour anomalies (already continuously scored by anomaly_detector)
    for name, pts in behaviour_anomalies:
        score += pts
        reasons.append((name, pts))

    # 6. Night multiplier — amplifies EVERYTHING above
    night = is_night_time() if override_night is None else override_night
    if night:
        pre_night  = score
        score      = int(score * NIGHT_MULTIPLIER)
        night_added = score - pre_night
        reasons.append(("Night x1.5", night_added))

        # 7. Synergy bonus — night AND inside zone
        if in_zone:
            score += SYNERGY_BONUS
            reasons.append(("Night+Zone Synergy", SYNERGY_BONUS))

        # ── ML Threat Probability ──────────────────────────────

    speed = 0
    freeze_time = 0

    # Estimate zone approach count
    zone_approach = 1 if in_zone else 0

    # Loitering flag
    loitering = 1 if loiter_seconds > 10 else 0

    crowd = crowd_count

    features = np.array([[speed, zone_approach, freeze_time, loitering, crowd]])

    try:
        prediction = model.predict_proba(features)
        ml_probability = int(prediction[0][1] * 100)
    except:
        ml_probability = 0



    # ── Risk classification ────────────────────────────────────
    final_score = int((score + ml_probability) / 2)

    if final_score <= 35:
      risk = "Low"
    elif final_score <= 70:
       risk = "Medium"
    else:
      risk = "High"

    return score, risk, _explain(risk, reasons, score)


def _explain(risk, reasons, score):
    parts = ", ".join("{} (+{})".format(n, p) for n, p in reasons)
    return "{} Risk: {}. Total: {}.".format(risk, parts, score)