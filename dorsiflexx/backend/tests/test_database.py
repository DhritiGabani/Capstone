"""
Unit tests for database.py CRUD operations.

Every test uses the test_db fixture (isolated temp SQLite) so the real
dorsiflexx.db is never touched.
"""

import json
import sqlite3
from datetime import datetime, timezone

import pytest

import database


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------

class TestCreateSession:
    def test_returns_hex_session_id(self, test_db):
        session_id, _ = database.create_session()
        assert isinstance(session_id, str)
        assert len(session_id) == 32  # uuid4().hex is always 32 hex chars

    def test_returns_iso_start_time(self, test_db):
        _, start_time = database.create_session()
        # Must be parseable as ISO-8601 UTC
        dt = datetime.fromisoformat(start_time)
        assert dt.tzinfo is not None

    def test_row_exists_in_db(self, test_db):
        session_id, _ = database.create_session()
        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT session_id FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        conn.close()
        assert row is not None

    def test_end_time_is_null_initially(self, test_db):
        session_id, _ = database.create_session()
        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT end_time FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        conn.close()
        assert row[0] is None


class TestSaveRawData:
    def test_inserts_row(self, test_db):
        session_id, _ = database.create_session()
        imu1 = {"samples": [{"sample_idx": 0, "ax_g": 0.1}]}
        imu2 = {"samples": [{"sample_idx": 0, "ax_g": 0.2}]}
        database.save_raw_data(session_id, imu1, imu2)

        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT session_id FROM raw_sensor_data WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        conn.close()
        assert row is not None

    def test_json_round_trips(self, test_db):
        session_id, _ = database.create_session()
        imu1 = {"samples": [{"sample_idx": 0, "ax_g": 1.23}]}
        imu2 = {"samples": [{"sample_idx": 0, "ax_g": 4.56}]}
        database.save_raw_data(session_id, imu1, imu2)

        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT imu1_json, imu2_json FROM raw_sensor_data WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        conn.close()
        assert json.loads(row[0]) == imu1
        assert json.loads(row[1]) == imu2


class TestCompleteSession:
    def test_sets_end_time(self, test_db):
        session_id, _ = database.create_session()
        database.complete_session(session_id, 30.0, {})

        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT end_time FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        conn.close()
        assert row[0] is not None

    def test_stores_duration(self, test_db):
        session_id, _ = database.create_session()
        database.complete_session(session_id, 42.5, {})

        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT duration_s FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        conn.close()
        assert row[0] == 42.5

    def test_stores_analysis_json(self, test_db):
        session_id, _ = database.create_session()
        analysis = {"rep_counts": {"Calf Raises": 5}, "consistency_scores": {}}
        database.complete_session(session_id, 20.0, analysis)

        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT analysis_json FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        conn.close()
        assert json.loads(row[0]) == analysis


class TestSaveFeedback:
    def test_stores_rating_and_comments(self, test_db):
        session_id, _ = database.create_session()
        database.save_feedback(session_id, "good", "Felt great!")

        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT rating, comments FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        conn.close()
        assert row[0] == "good"
        assert row[1] == "Felt great!"

    def test_empty_comments_allowed(self, test_db):
        session_id, _ = database.create_session()
        database.save_feedback(session_id, "okay", "")

        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT comments FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        conn.close()
        assert row[0] == ""

    def test_all_rating_values(self, test_db):
        for rating in ("good", "okay", "bad"):
            session_id, _ = database.create_session()
            database.save_feedback(session_id, rating, "")

            conn = sqlite3.connect(test_db)
            row = conn.execute(
                "SELECT rating FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            conn.close()
            assert row[0] == rating


# ---------------------------------------------------------------------------
# KTW Measurements
# ---------------------------------------------------------------------------

class TestSaveKTWMeasurement:
    def test_returns_integer_row_id(self, test_db):
        row_id = database.save_ktw_measurement(35.7)
        assert isinstance(row_id, int)
        assert row_id >= 1

    def test_auto_increments(self, test_db):
        id1 = database.save_ktw_measurement(30.0)
        id2 = database.save_ktw_measurement(35.0)
        assert id2 > id1

    def test_stores_details_json(self, test_db):
        # Float keys become strings in JSON; compare after the same round-trip
        details = {"angle_over_time": {"0.0": 35.0, "0.5": 36.0}}
        row_id = database.save_ktw_measurement(36.0, details)

        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT details_json FROM ktw_measurements WHERE id = ?", (row_id,)
        ).fetchone()
        conn.close()
        assert json.loads(row[0]) == details

    def test_details_none_is_null(self, test_db):
        row_id = database.save_ktw_measurement(25.0, None)

        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT details_json FROM ktw_measurements WHERE id = ?", (row_id,)
        ).fetchone()
        conn.close()
        assert row[0] is None


class TestGetKTWMeasurements:
    def test_empty_when_none_saved(self, test_db):
        assert database.get_ktw_measurements() == []

    def test_returns_all_entries(self, test_db):
        database.save_ktw_measurement(30.0)
        database.save_ktw_measurement(35.0)
        database.save_ktw_measurement(40.0)
        results = database.get_ktw_measurements()
        assert len(results) == 3

    def test_each_entry_has_required_fields(self, test_db):
        database.save_ktw_measurement(32.5)
        results = database.get_ktw_measurements()
        entry = results[0]
        assert "id" in entry
        assert "measured_at" in entry
        assert "angle_deg" in entry

    def test_details_included_when_present(self, test_db):
        # Float keys serialise as strings in JSON
        details = {"angle_over_time": {"0.0": 32.5}}
        database.save_ktw_measurement(32.5, details)
        results = database.get_ktw_measurements()
        assert results[0]["details"] == details

    def test_ordered_by_date(self, test_db):
        database.save_ktw_measurement(10.0)
        database.save_ktw_measurement(20.0)
        results = database.get_ktw_measurements()
        dates = [r["measured_at"] for r in results]
        assert dates == sorted(dates)


class TestGetKTWMeasurementsByDate:
    def test_returns_todays_measurements(self, test_db):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        database.save_ktw_measurement(40.0)
        results = database.get_ktw_measurements_by_date(today)
        assert len(results) >= 1
        assert results[-1]["angle_deg"] == 40.0

    def test_returns_empty_for_past_date(self, test_db):
        results = database.get_ktw_measurements_by_date("2000-01-01")
        assert results == []

    def test_filters_by_exact_date(self, test_db):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        database.save_ktw_measurement(55.0)
        results_today = database.get_ktw_measurements_by_date(today)
        results_past = database.get_ktw_measurements_by_date("1999-12-31")
        assert len(results_today) >= 1
        assert len(results_past) == 0


# ---------------------------------------------------------------------------
# Session Queries
# ---------------------------------------------------------------------------

class TestGetSessionDates:
    def test_empty_when_no_data(self, test_db):
        assert database.get_session_dates() == []

    def test_includes_completed_session_date(self, test_db):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        session_id, _ = database.create_session()
        database.complete_session(session_id, 15.0, {})
        dates = database.get_session_dates()
        assert today in dates

    def test_includes_ktw_date(self, test_db):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        database.save_ktw_measurement(30.0)
        dates = database.get_session_dates()
        assert today in dates

    def test_excludes_incomplete_sessions(self, test_db):
        database.create_session()  # No end_time set
        dates = database.get_session_dates()
        assert dates == []

    def test_no_duplicate_dates(self, test_db):
        for _ in range(3):
            session_id, _ = database.create_session()
            database.complete_session(session_id, 10.0, {})
        dates = database.get_session_dates()
        assert len(dates) == len(set(dates))


class TestGetSessionsByDate:
    def test_empty_for_unknown_date(self, test_db):
        results = database.get_sessions_by_date("2000-01-01")
        assert results == []

    def test_excludes_incomplete_sessions(self, test_db):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        database.create_session()  # incomplete
        results = database.get_sessions_by_date(today)
        assert results == []

    def test_includes_completed_session(self, test_db):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        session_id, _ = database.create_session()
        database.complete_session(session_id, 25.0, {"rep_counts": {"Calf Raises": 3}})
        results = database.get_sessions_by_date(today)
        assert len(results) == 1
        assert results[0]["session_id"] == session_id
        assert results[0]["duration_s"] == 25.0

    def test_analysis_is_parsed_from_json(self, test_db):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        session_id, _ = database.create_session()
        analysis = {"rep_counts": {"Calf Raises": 5}}
        database.complete_session(session_id, 30.0, analysis)
        results = database.get_sessions_by_date(today)
        assert results[0]["analysis"] == analysis

    def test_ordered_by_start_time(self, test_db):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for _ in range(3):
            sid, _ = database.create_session()
            database.complete_session(sid, 10.0, {})
        results = database.get_sessions_by_date(today)
        times = [r["start_time"] for r in results]
        assert times == sorted(times)


# ---------------------------------------------------------------------------
# User Settings
# ---------------------------------------------------------------------------

class TestGetSettings:
    def test_returns_defaults_when_empty(self, test_db):
        settings = database.get_settings()
        assert settings["name"] == "Jane"
        assert settings["goal_frequency"] == 2
        assert isinstance(settings["notifications"], list)

    def test_default_has_expected_keys(self, test_db):
        settings = database.get_settings()
        for key in ("name", "height", "height_unit", "shoe_gender",
                    "shoe_size", "ankle", "goal_frequency", "pt_email", "notifications"):
            assert key in settings


class TestSaveSettings:
    def test_persists_values(self, test_db):
        new_settings = {
            "name": "Alex",
            "height": "175",
            "height_unit": "cm",
            "shoe_gender": "Men's",
            "shoe_size": 10,
            "ankle": "Left",
            "goal_frequency": 4,
            "pt_email": "pt@clinic.com",
            "notifications": [],
        }
        database.save_settings(new_settings)
        retrieved = database.get_settings()
        assert retrieved["name"] == "Alex"
        assert retrieved["pt_email"] == "pt@clinic.com"
        assert retrieved["goal_frequency"] == 4

    def test_upsert_overwrites_previous(self, test_db):
        database.save_settings({"name": "First"})
        database.save_settings({"name": "Second"})
        retrieved = database.get_settings()
        assert retrieved["name"] == "Second"

    def test_stores_notification_list(self, test_db):
        notifications = [
            {"id": 1, "days": ["Mon"], "time_hour": 8, "time_minute": 0}
        ]
        database.save_settings({"notifications": notifications})
        retrieved = database.get_settings()
        assert retrieved["notifications"] == notifications
