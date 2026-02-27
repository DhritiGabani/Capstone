"""
SQLite persistence for dorsiflexx backend.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from config import DATABASE_PATH
from sensor import SensorReading


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = _get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id   TEXT PRIMARY KEY,
            start_time   TEXT NOT NULL,
            end_time     TEXT,
            duration_s   REAL,
            analysis_json TEXT,
            rating       TEXT,
            comments     TEXT
        );

        CREATE TABLE IF NOT EXISTS sensor_readings (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id   TEXT NOT NULL REFERENCES sessions(session_id),
            device       TEXT NOT NULL,
            timestamp_us INTEGER NOT NULL,
            ax           REAL NOT NULL,
            ay           REAL NOT NULL,
            az           REAL NOT NULL,
            gx           REAL NOT NULL,
            gy           REAL NOT NULL,
            gz           REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_readings_session
            ON sensor_readings(session_id);
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


def save_readings(session_id: str, readings: list[SensorReading]) -> None:
    """Bulk-insert sensor readings for a session."""
    conn = _get_connection()
    conn.executemany(
        """INSERT INTO sensor_readings
           (session_id, device, timestamp_us, ax, ay, az, gx, gy, gz)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (session_id, r.device, r.timestamp_us, r.ax, r.ay, r.az, r.gx, r.gy, r.gz)
            for r in readings
        ],
    )
    conn.commit()
    conn.close()


def save_feedback(session_id: str, rating: str, comments: str) -> None:
    """Update a session with user feedback (rating + comments)."""
    conn = _get_connection()
    conn.execute(
        "UPDATE sessions SET rating = ?, comments = ? WHERE session_id = ?",
        (rating, comments, session_id),
    )
    conn.commit()
    conn.close()


def complete_session(
    session_id: str,
    duration_s: float,
    analysis: dict,
) -> None:
    """Mark session as complete with end time, duration, and analysis results."""
    end_time = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    conn.execute(
        """UPDATE sessions
           SET end_time = ?, duration_s = ?, analysis_json = ?
           WHERE session_id = ?""",
        (end_time, duration_s, json.dumps(analysis), session_id),
    )
    conn.commit()
    conn.close()
