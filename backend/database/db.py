"""
db.py - SQLite database layer for ThreatSense AI-DVR.
Updated: insert_alert returns ID, added llm_explanation column.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "threatsense.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Create alerts table if not exists.
    Auto-migrates existing DB to add llm_explanation column.
    Call once at startup.
    """
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT    NOT NULL,
            person_id       INTEGER NOT NULL,
            zone_name       TEXT    NOT NULL,
            loiter_time     REAL    NOT NULL DEFAULT 0.0,
            threat_score    INTEGER NOT NULL,
            risk_level      TEXT    NOT NULL,
            explanation     TEXT    NOT NULL
        )
    """)

    # Migration: safely add llm_explanation to existing databases
    try:
        conn.execute("ALTER TABLE alerts ADD COLUMN llm_explanation TEXT")
        print("[DB] Migrated: added llm_explanation column")
    except Exception:
        pass   # column already exists — fine

    conn.commit()
    conn.close()
    print("[DB] Database ready:", DB_PATH)


def insert_alert(timestamp, person_id, zone_name, loiter_time,
                 threat_score, risk_level, explanation):
    """
    Insert one alert and return its new row ID.
    ID is used by LLM worker to update llm_explanation later.
    """
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO alerts
           (timestamp, person_id, zone_name, loiter_time,
            threat_score, risk_level, explanation)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (timestamp, person_id, zone_name, round(float(loiter_time), 2),
         int(threat_score), risk_level, explanation),
    )
    alert_id = cursor.lastrowid   # capture before close
    conn.commit()
    conn.close()
    return alert_id               # used by LLM queue in app.py


def update_alert_llm_explanation(alert_id, llm_text):
    """
    Called by LLM worker thread after LM Studio generates explanation.
    Updates the llm_explanation field for an existing alert row.
    """
    try:
        conn = get_connection()
        conn.execute(
            "UPDATE alerts SET llm_explanation = ? WHERE id = ?",
            (llm_text, alert_id)
        )
        conn.commit()
        conn.close()
        print("[DB] LLM explanation saved → alert ID", alert_id)
    except Exception as e:
        print("[DB] Failed to save LLM explanation:", e)


def fetch_all_alerts():
    """Return all alerts as list of dicts, most recent first."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM alerts ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def fetch_latest_alert():
    """Return the single most recent alert as a dict, or None."""
    conn = get_connection()
    row  = conn.execute(
        "SELECT * FROM alerts ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None