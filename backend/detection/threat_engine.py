"""
threat_engine.py — Hackathon Final

Scoring system:
  1. Continuous scoring  — values grow gradually, not fixed jumps
  2. Night multiplier    — 1.5x amplifies ALL threats after dark
  3. Synergy bonus       — night + zone = extra +20 on top
  4. Explainable AI      — interprets key behavior factors
"""

import datetime
import joblib
import pandas as pd

from detection.explainable_ai import analyze_behavior, build_explanation

# Load trained ML model
model = joblib.load("ml/threat_model.pkl")

# ── Base scores ───────────────────────────
SCORE_HUMAN = 10

# Zone scores
SCORE_ZONE_BASE = 30
SCORE_ZONE_LOITER_MAX = 30
SCORE_ZONE_LOITER_SECS = 60

# Peripheral
SCORE_PERIPHERAL_MAX = 25
SCORE_PERIPHERAL_SECS = 60

# Crowd
SCORE_CROWD_PER_PERSON = 8

# Night
NIGHT_MULTIPLIER = 1.5
SYNERGY_BONUS = 20

CURRENT_MODE = "live"


def is_night_time():
    if CURRENT_MODE == "demo":
        return True
    h = datetime.datetime.now().hour
    return h >= 22 or h < 6


def compute_threat(person_detected, in_zone, loiter_seconds,
                   peripheral_seconds=0.0,
                   crowd_count=1,
                   behaviour_anomalies=None,
                   override_night=None):

    if behaviour_anomalies is None:
        behaviour_anomalies = []

    if not person_detected:
        return 0, "Low", "No threat detected."

    score = 0
    reasons = []

    # 1. Human base
    score += SCORE_HUMAN
    reasons.append(("Human Detected", SCORE_HUMAN))

    # 2. Zone score
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
                reasons.append((f"Loitering {loiter_seconds:.0f}s", loiter_pts))

        score += zone_pts

    # 3. Peripheral loiter
    if not in_zone and peripheral_seconds >= 10:

        periph_pts = min(
            int(peripheral_seconds / SCORE_PERIPHERAL_SECS * SCORE_PERIPHERAL_MAX),
            SCORE_PERIPHERAL_MAX
        )

        if periph_pts > 0:
            score += periph_pts
            reasons.append((f"Near Zone {peripheral_seconds:.0f}s", periph_pts))

    # 4. Crowd
    if crowd_count >= 2:
        crowd_pts = (crowd_count - 1) * SCORE_CROWD_PER_PERSON
        score += crowd_pts
        reasons.append((f"Crowd {crowd_count} persons", crowd_pts))

    # 5. Behaviour anomalies
    for name, pts in behaviour_anomalies:
        score += pts
        reasons.append((name, pts))

    # 6. Night multiplier
    night = is_night_time() if override_night is None else override_night

    if night:
        pre_night = score
        score = int(score * NIGHT_MULTIPLIER)
        night_added = score - pre_night

        reasons.append(("Night x1.5", night_added))

        if in_zone:
            score += SYNERGY_BONUS
            reasons.append(("Night+Zone Synergy", SYNERGY_BONUS))

    # ── ML Threat Probability ──────────────────────────────
    speed = 0
    freeze_time = 0
    zone_approach = 1 if in_zone else 0
    loitering_flag = 1 if loiter_seconds > 10 else 0
    crowd = crowd_count

    features = pd.DataFrame([{
        "speed": speed,
        "zone_approach": zone_approach,
        "freeze_time": freeze_time,
        "loitering": loitering_flag,
        "crowd": crowd
    }])

    try:
        prediction = model.predict_proba(features)
        ml_probability = int(prediction[0][1] * 100)
    except Exception as e:
        print("ML prediction error:", e)
        ml_probability = 0

    # ── Final Score ──────────────────────────────
    final_score = int((score + ml_probability) / 2)

    if final_score <= 35:
        risk = "Low"
    elif final_score <= 70:
        risk = "Medium"
    else:
        risk = "High"

    # ── Explainable AI ───────────────────────────
    ai_features = {
        "speed": speed,
        "zone_approach": zone_approach,
        "freeze_time": freeze_time,
        "loitering": loitering_flag,
        "crowd": crowd
    }

    insights = analyze_behavior(ai_features)
    ai_explanation = build_explanation(final_score, insights)

    base_explanation = _explain(risk, reasons, score)

    final_explanation = base_explanation + "\n\n" + ai_explanation

    return final_score, risk, final_explanation


def _explain(risk, reasons, score):
    parts = ", ".join(f"{n} (+{p})" for n, p in reasons)
    return f"{risk} Risk: {parts}. Total: {score}."