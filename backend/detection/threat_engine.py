"""
threat_engine.py — Hackathon Final v5

Scoring system:
  1. Continuous scoring  — values grow gradually, not fixed jumps
  2. Night multiplier    — 1.5x amplifies ALL threats after dark
  3. Synergy bonus       — night + zone = extra +10
  4. ML boost            — adds UP TO 20% on top (does not replace rule score)
  5. Explainable AI      — human-readable breakdown of every factor
"""

import datetime
import joblib
import os
import pandas as pd

from detection.explainable_ai import analyze_behavior, build_explanation

# ── Load ML model safely ───────────────────────────────────────
# If model file missing, ML boost = 0 and system still works perfectly
_model      = None
_model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "ml", "threat_model.pkl")
try:
    _model = joblib.load(_model_path)
    print("[ThreatEngine] ML model loaded OK →", _model_path)
except Exception as e:
    print("[ThreatEngine] ML model not found — rule-based scoring only. ({})".format(e))

# ── Base scores ────────────────────────────────────────────────
SCORE_HUMAN            = 10

SCORE_ZONE_BASE        = 30   # entering restricted zone
SCORE_ZONE_LOITER_MAX  = 30   # max extra from loitering inside zone
SCORE_ZONE_LOITER_SECS = 60   # seconds to reach max loiter score

SCORE_PERIPHERAL_MAX   = 25   # max from standing near zone
SCORE_PERIPHERAL_SECS  = 60   # seconds to reach max peripheral score

SCORE_CROWD_PER_PERSON = 8    # per extra person beyond 1

# ── Night ──────────────────────────────────────────────────────
NIGHT_MULTIPLIER = 1.5        # amplifies all base scores
SYNERGY_BONUS    = 10         # FIX 1: was 20, reduced to prevent false High

# ── ML boost cap ──────────────────────────────────────────────
# ML adds AT MOST this many points on top of rule score.
# Never replaces rule score — only supplements it.
ML_BOOST_MAX = 20

# ── Risk thresholds ────────────────────────────────────────────
THRESH_MEDIUM = 36
THRESH_HIGH   = 80            # FIX 2: restored from v4 (was missing)

CURRENT_MODE = "live"


def is_night_time():
    if CURRENT_MODE == "demo":
        return True
    h = datetime.datetime.now().hour
    return h >= 18 or h < 6   # night from 6 PM


def compute_threat(person_detected, in_zone, loiter_seconds,
                   peripheral_seconds=0.0,
                   crowd_count=1,
                   behaviour_anomalies=None,
                   override_night=None,
                   # FIX 3: accept real motion values for ML
                   avg_speed=0.0,
                   freeze_time=0.0):
    """
    Parameters:
      person_detected     → bool
      in_zone             → bool
      loiter_seconds      → float
      peripheral_seconds  → float
      crowd_count         → int
      behaviour_anomalies → list of (name, score) tuples from anomaly_detector
      override_night      → bool or None
      avg_speed           → float: normalised speed from anomaly_detector
      freeze_time         → float: seconds frozen from anomaly_detector
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

    # 2. Zone entry + loitering — continuous
    if in_zone:
        score += SCORE_ZONE_BASE
        reasons.append(("Zone Entry", SCORE_ZONE_BASE))

        if loiter_seconds > 0:
            loiter_pts = min(
                int(loiter_seconds / SCORE_ZONE_LOITER_SECS * SCORE_ZONE_LOITER_MAX),
                SCORE_ZONE_LOITER_MAX
            )
            if loiter_pts > 0:
                score += loiter_pts
                reasons.append(("Loitering {:.0f}s".format(loiter_seconds), loiter_pts))

    # 3. Peripheral loiter — continuous
    if not in_zone and peripheral_seconds >= 10:
        periph_pts = min(
            int(peripheral_seconds / SCORE_PERIPHERAL_SECS * SCORE_PERIPHERAL_MAX),
            SCORE_PERIPHERAL_MAX
        )
        if periph_pts > 0:
            score += periph_pts
            reasons.append(("Near Zone {:.0f}s".format(peripheral_seconds), periph_pts))

    # 4. Crowd
    if crowd_count >= 2:
        crowd_pts = (crowd_count - 1) * SCORE_CROWD_PER_PERSON
        score += crowd_pts
        reasons.append(("Crowd {} persons".format(crowd_count), crowd_pts))

    # 5. Behaviour anomalies from anomaly_detector
    for name, pts in behaviour_anomalies:
        pts = int(pts)   # FIX 6: decay returns float, ensure int
        score += pts
        reasons.append((name, pts))

    # 6. Night multiplier — amplifies everything above
    night = is_night_time() if override_night is None else override_night
    if night:
        pre_night   = score
        score       = int(score * NIGHT_MULTIPLIER)
        night_added = score - pre_night
        reasons.append(("Night x1.5", night_added))

        # Synergy: night AND zone together = extra penalty
        if in_zone:
            score += SYNERGY_BONUS
            reasons.append(("Night+Zone Synergy", SYNERGY_BONUS))

    # ── Rule-based score is now final ─────────────────────────
    rule_score = score

    # 7. ML boost — supplements rule score, never replaces it
    # FIX 4: ML adds AT MOST ML_BOOST_MAX points, not average with rule score
    ml_probability = 0
    ml_boost       = 0

    if _model is not None:
        try:
            features = pd.DataFrame([{
                "speed":        round(avg_speed, 4),      # FIX 3: real speed
                "zone_approach": 1 if in_zone else 0,
                "freeze_time":  round(freeze_time, 2),    # FIX 3: real freeze
                "loitering":    round(loiter_seconds, 1),
                "crowd":        crowd_count
            }])
            ml_probability = int(_model.predict_proba(features)[0][1] * 100)
            # Scale ML probability to max ML_BOOST_MAX bonus points
            ml_boost = int(ml_probability / 100 * ML_BOOST_MAX)
            if ml_boost > 0:
                score += ml_boost
                reasons.append(("ML Boost", ml_boost))
        except Exception as e:
            print("[ThreatEngine] ML prediction error:", e)

    # FIX 5: If ML failed, score = rule_score (not halved)
    final_score = score

    # 8. Risk classification
    if final_score >= THRESH_HIGH:
        risk = "High"
    elif final_score >= THRESH_MEDIUM:
        risk = "Medium"
    else:
        risk = "Low"

    # 9. Explainable AI narrative
    ai_features = {
        "speed":        avg_speed,
        "zone_approach": 1 if in_zone else 0,
        "freeze_time":  freeze_time,
        "loitering":    loiter_seconds,
        "crowd":        crowd_count
    }

    insights = analyze_behavior(ai_features)

    for name, pts in behaviour_anomalies:
        insights.append({
            "priority": 5,
            "factor":   name,
            "reason":   "Detected behaviour anomaly contributing +{} risk.".format(int(pts))
        })

    ai_explanation   = build_explanation(final_score, insights)
    base_explanation = _explain(risk, reasons, final_score)
    final_explanation = base_explanation + "\n\n" + ai_explanation

    return final_score, risk, final_explanation


def _explain(risk, reasons, score):
    parts = ", ".join("{} (+{})".format(n, p) for n, p in reasons)
    return "{} Risk: {}. Total: {}.".format(risk, parts, score)