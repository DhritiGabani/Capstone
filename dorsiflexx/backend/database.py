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
