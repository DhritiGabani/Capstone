"""
SQLite persistence for dorsiflexx backend.
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone

from config import DATABASE_PATH

log = logging.getLogger(__name__)


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = _get_connection()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id    TEXT PRIMARY KEY,
            start_time    TEXT NOT NULL,
            end_time      TEXT,
            duration_s    REAL,
            analysis_json TEXT,
            rating        TEXT,
            comments      TEXT
        );

        CREATE TABLE IF NOT EXISTS raw_sensor_data (
            session_id  TEXT PRIMARY KEY,
            imu1_json   TEXT,
            imu2_json   TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );

        CREATE TABLE IF NOT EXISTS ktw_measurements (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            measured_at   TEXT NOT NULL,
            angle_deg     REAL NOT NULL,
            details_json  TEXT
        );

        CREATE TABLE IF NOT EXISTS user_settings (
            id            INTEGER PRIMARY KEY CHECK (id = 1),
            settings_json TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def create_session() -> tuple[str, str]:
    """Create a new session row and return (session_id, start_time)."""
    session_id = uuid.uuid4().hex
    start_time = datetime.now(timezone.utc).isoformat()

    conn = _get_connection()
    conn.execute(
        "INSERT INTO sessions (session_id, start_time) VALUES (?, ?)",
        (session_id, start_time),
    )
    conn.commit()
    conn.close()
    return session_id, start_time


def save_raw_data(session_id: str, imu1_json: dict, imu2_json: dict) -> None:
    """Save raw IMU data to the raw_sensor_data table."""
    imu1_str = json.dumps(imu1_json)
    imu2_str = json.dumps(imu2_json)
    log.info("save_raw_data: session=%s imu1_len=%d imu2_len=%d", session_id, len(imu1_str), len(imu2_str))
    conn = _get_connection()
    conn.execute(
        "INSERT INTO raw_sensor_data (session_id, imu1_json, imu2_json) VALUES (?, ?, ?)",
        (session_id, imu1_str, imu2_str),
    )
    conn.commit()
    conn.close()
    log.info("save_raw_data: committed successfully")


def complete_session(
    session_id: str,
    duration_s: float,
    analysis: dict,
) -> None:
    """Mark session as complete with end time, duration, and analysis results."""
    end_time = datetime.now(timezone.utc).isoformat()
    analysis_str = json.dumps(analysis)
    log.info("complete_session: session=%s duration=%.2f analysis_len=%d", session_id, duration_s, len(analysis_str))
    conn = _get_connection()
    conn.execute(
        """UPDATE sessions
           SET end_time = ?, duration_s = ?, analysis_json = ?
           WHERE session_id = ?""",
        (end_time, duration_s, analysis_str, session_id),
    )
    conn.commit()
    conn.close()
    log.info("complete_session: committed successfully")


def save_feedback(session_id: str, rating: str, comments: str) -> None:
    """Update a session with user feedback (rating + comments)."""
    conn = _get_connection()
    conn.execute(
        "UPDATE sessions SET rating = ?, comments = ? WHERE session_id = ?",
        (rating, comments, session_id),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# KTW Measurements
# ---------------------------------------------------------------------------

def save_ktw_measurement(angle_deg: float, details: dict | None = None) -> int:
    """Save a KTW measurement and return the new row id."""
    measured_at = datetime.now(timezone.utc).isoformat()
    details_str = json.dumps(details) if details else None

    conn = _get_connection()
    cursor = conn.execute(
        "INSERT INTO ktw_measurements (measured_at, angle_deg, details_json) VALUES (?, ?, ?)",
        (measured_at, angle_deg, details_str),
    )
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id


def get_ktw_measurements() -> list[dict]:
    """Return all KTW measurements ordered by date."""
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, measured_at, angle_deg, details_json FROM ktw_measurements ORDER BY measured_at"
    ).fetchall()
    conn.close()

    results = []
    for row in rows:
        entry = {
            "id": row["id"],
            "measured_at": row["measured_at"],
            "angle_deg": row["angle_deg"],
        }
        if row["details_json"]:
            entry["details"] = json.loads(row["details_json"])
        results.append(entry)
    return results


# ---------------------------------------------------------------------------
# Session Queries (for history / exercise summary)
# ---------------------------------------------------------------------------

def get_session_dates() -> list[str]:
    """Return distinct dates (YYYY-MM-DD) that have completed sessions or KTW measurements."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT DISTINCT date_str FROM ("
        "  SELECT substr(start_time, 1, 10) AS date_str "
        "  FROM sessions "
        "  WHERE analysis_json IS NOT NULL "
        "  AND analysis_json LIKE '%rep_counts%' "
        "  UNION "
        "  SELECT substr(measured_at, 1, 10) AS date_str "
        "  FROM ktw_measurements"
        ") ORDER BY date_str"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_ktw_measurements_by_date(date_str: str) -> list[dict]:
    """Return KTW measurements for a given date (YYYY-MM-DD)."""
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, measured_at, angle_deg, details_json "
        "FROM ktw_measurements "
        "WHERE substr(measured_at, 1, 10) = ? "
        "ORDER BY measured_at",
        (date_str,),
    ).fetchall()
    conn.close()

    results = []
    for row in rows:
        entry = {
            "id": row["id"],
            "measured_at": row["measured_at"],
            "angle_deg": row["angle_deg"],
        }
        if row["details_json"]:
            entry["details"] = json.loads(row["details_json"])
        results.append(entry)
    return results


# ---------------------------------------------------------------------------
# User Settings
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS = {
    "name": "Jane",
    "height": "165",
    "height_unit": "cm",
    "shoe_gender": "Women's",
    "shoe_size": 7,
    "ankle": "Right",
    "goal_frequency": 2,
    "goal_period": "Day",
    "notifications": [
        {"id": 1, "days": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], "time_hour": 8, "time_minute": 15},
        {"id": 2, "days": ["Mon", "Tue", "Wed", "Thu", "Fri"], "time_hour": 18, "time_minute": 30},
    ],
}


def get_settings() -> dict:
    """Return user settings, seeding defaults if no row exists yet."""
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT settings_json FROM user_settings WHERE id = 1").fetchone()
    conn.close()
    if row is None:
        return DEFAULT_SETTINGS
    return json.loads(row["settings_json"])


def save_settings(settings: dict) -> None:
    """Upsert user settings."""
    conn = _get_connection()
    conn.execute(
        "INSERT INTO user_settings (id, settings_json) VALUES (1, ?) "
        "ON CONFLICT(id) DO UPDATE SET settings_json = excluded.settings_json",
        (json.dumps(settings),),
    )
    conn.commit()
    conn.close()


def get_sessions_by_date(date_str: str) -> list[dict]:
    """Return sessions with parsed analysis for a given date (YYYY-MM-DD).

    Only includes sessions that completed with real analysis data
    (i.e. have rep_counts, not just an error or empty dict).
    """
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT session_id, start_time, end_time, duration_s, analysis_json "
        "FROM sessions "
        "WHERE substr(start_time, 1, 10) = ? "
        "AND analysis_json IS NOT NULL "
        "AND analysis_json LIKE '%rep_counts%' "
        "ORDER BY start_time",
        (date_str,),
    ).fetchall()
    conn.close()

    results = []
    for row in rows:
        entry = {
            "session_id": row["session_id"],
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "duration_s": row["duration_s"],
        }
        if row["analysis_json"]:
            entry["analysis"] = json.loads(row["analysis_json"])
        results.append(entry)
    return results
