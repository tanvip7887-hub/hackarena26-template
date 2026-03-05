"""
db.py - SQLite database layer for ThreatSense AI-DVR.
Handles automatic table creation, alert insertion, and fetching.
"""

import sqlite3
import os

# Database file lives inside the database/ folder
DB_PATH = os.path.join(os.path.dirname(__file__), "threatsense.db")


def get_connection():
    """Open and return a SQLite connection with row_factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Create the alerts table if it does not already exist.
    Call once at application startup.
    """
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp    TEXT    NOT NULL,
            person_id    INTEGER NOT NULL,
            zone_name    TEXT    NOT NULL,
            loiter_time  REAL    NOT NULL DEFAULT 0.0,
            threat_score INTEGER NOT NULL,
            risk_level   TEXT    NOT NULL,
            explanation  TEXT    NOT NULL,
            clip_path    TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("[DB] Database ready:", DB_PATH)


def insert_alert(timestamp, person_id, zone_name, loiter_time,
                 threat_score, risk_level, explanation, clip_path=None):
    """Insert one alert record into the database."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO alerts
           (timestamp, person_id, zone_name, loiter_time,
            threat_score, risk_level, explanation, clip_path)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (timestamp, person_id, zone_name, round(float(loiter_time), 2),
         int(threat_score), risk_level, explanation, clip_path),
    )
    conn.commit()
    conn.close()


def fetch_all_alerts():
    """Return all alerts as a list of dicts, most recent first."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM alerts ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def fetch_latest_alert():
    """Return the single most recent alert as a dict, or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM alerts ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None