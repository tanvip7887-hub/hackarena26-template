"""
llm_client.py
Calls LM Studio local server for natural language threat explanations.
Non-blocking — called from background worker thread only.
"""
import requests

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
TIMEOUT_SECS  = 8   # don't wait longer than this per call


def generate_llm_explanation(risk_level, factors, person_id, timestamp):
    """
    Generates a concise natural language threat explanation.

    Parameters:
      risk_level : "Medium" or "High"
      factors    : list of strings e.g. ["Zone Entry (+30)", "Pacing (+20)"]
      person_id  : int
      timestamp  : ISO string

    Returns:
      str explanation, or None if LM Studio unavailable
    """
    factor_text = ", ".join(factors) if factors else "general suspicious presence"

    prompt = (
        "You are a concise security analyst AI. "
        "Person ID P{pid} triggered a {risk} risk alert at {ts}. "
        "Detected factors: {factors}. "
        "In 2 sentences, explain why this is suspicious and what security "
        "staff should do. Be direct and factual."
    ).format(
        pid=person_id,
        risk=risk_level,
        ts=timestamp,
        factors=factor_text
    )

    payload = {
        "model":       "local-model",
        "messages":    [{"role": "user", "content": prompt}],
        "max_tokens":  120,
        "temperature": 0.4,
    }

    try:
        resp = requests.post(LM_STUDIO_URL, json=payload, timeout=TIMEOUT_SECS)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        print("[LLM] LM Studio not running — skipping explanation")
        return None
    except Exception as e:
        print("[LLM] Error:", e)
        return None