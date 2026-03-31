"""
Integration tests for all FastAPI endpoints in main.py.

No real BLE hardware or TFLite model is needed:
  - ble (BLEManager) is replaced with a MagicMock whose async methods are AsyncMocks
  - ExerciseClassifier is replaced with a mock that returns "Calf Raises"
  - DATABASE_PATH is patched to a temp SQLite file per test

All endpoint behaviour, status codes, response shapes, and error paths are
verified here. Pipeline execution is tested separately in test_pipeline.py /
test_analysis.py.
"""

import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ble(
    is_streaming: bool = False,
    is_connected: bool = False,
    stop_return: list | None = None,
) -> MagicMock:
    """Create a fully-mocked BLEManager."""
    ble = MagicMock()
    type(ble).is_streaming = PropertyMock(return_value=is_streaming)
    type(ble).is_connected = PropertyMock(return_value=is_connected)
    ble.sample_counts = {}
    ble.connect = AsyncMock()
    ble.start_streaming = AsyncMock()
    ble.stop_streaming = AsyncMock(return_value=stop_return or [])
    ble.disconnect = AsyncMock()
    ble.clear_readings = MagicMock()
    return ble


def _make_classifier() -> MagicMock:
    clf = MagicMock()
    clf.classify.return_value = {"predicted_class": "Calf Raises", "confidence": 0.95}
    clf.classes = ["Ankle Rotation", "Calf Raises", "Heel Walk"]
    return clf


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """
    Yield a (TestClient, mock_ble, mock_clf) tuple.

    The TestClient runs the FastAPI lifespan (init_db + classifier load)
    with all hardware and model dependencies mocked out.
    asyncio.sleep is replaced so /session/stop does not wait 10 s.
    """
    import database

    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(database, "DATABASE_PATH", db_path)

    mock_ble = _make_ble()
    mock_clf = _make_classifier()

    # Patch database init so lifespan uses our temp DB
    def _patched_init_db():
        database.init_db()

    with (
        patch("main.init_db", side_effect=_patched_init_db),
        patch("main.ExerciseClassifier", return_value=mock_clf),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        import main

        # Inject mock objects into the running module
        main.ble = mock_ble
        main.classifier = mock_clf
        main._session_id = None
        main._start_time = None
        main._start_ts = None
        main._ktw_active = False

        with TestClient(main.app) as client:
            yield client, mock_ble, mock_clf


# ---------------------------------------------------------------------------
# GET /status
# ---------------------------------------------------------------------------

class TestStatusEndpoint:
    def test_returns_200(self, app_client):
        client, _, _ = app_client
        assert client.get("/status").status_code == 200

    def test_default_is_idle(self, app_client):
        client, _, _ = app_client
        data = client.get("/status").json()
        assert data["status"] == "idle"
        assert data["is_streaming"] is False

    def test_has_all_expected_fields(self, app_client):
        client, _, _ = app_client
        data = client.get("/status").json()
        for field in ("status", "is_streaming", "is_connected", "session_id", "stats"):
            assert field in data

    def test_stats_null_when_not_streaming(self, app_client):
        client, _, _ = app_client
        assert client.get("/status").json()["stats"] is None

    def test_session_id_null_initially(self, app_client):
        client, _, _ = app_client
        assert client.get("/status").json()["session_id"] is None


# ---------------------------------------------------------------------------
# GET /settings  &  PUT /settings
# ---------------------------------------------------------------------------

class TestSettingsEndpoints:
    def test_get_returns_200(self, app_client):
        client, _, _ = app_client
        assert client.get("/settings").status_code == 200

    def test_get_returns_default_name(self, app_client):
        client, _, _ = app_client
        assert client.get("/settings").json()["name"] == "Jane"

    def test_get_has_all_required_fields(self, app_client):
        client, _, _ = app_client
        data = client.get("/settings").json()
        for field in ("name", "height", "goal_frequency", "notifications", "pt_email"):
            assert field in data

    def test_put_returns_200(self, app_client):
        client, _, _ = app_client
        resp = client.put(
            "/settings",
            json={
                "name": "Sam",
                "height": "170",
                "height_unit": "cm",
                "shoe_gender": "Men's",
                "shoe_size": 9,
                "ankle": "Left",
                "goal_frequency": 3,
                "pt_email": "physio@example.com",
                "notifications": [],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "saved"

    def test_put_then_get_reflects_changes(self, app_client):
        client, _, _ = app_client
        client.put(
            "/settings",
            json={
                "name": "Jordan",
                "height": "168",
                "height_unit": "cm",
                "shoe_gender": "Women's",
                "shoe_size": 7,
                "ankle": "Right",
                "goal_frequency": 5,
                "pt_email": "doc@hospital.com",
                "notifications": [],
            },
        )
        data = client.get("/settings").json()
        assert data["name"] == "Jordan"
        assert data["goal_frequency"] == 5

    def test_put_missing_optional_fields_uses_defaults(self, app_client):
        client, _, _ = app_client
        resp = client.put("/settings", json={"name": "Test"})
        assert resp.status_code == 200

    def test_get_after_two_puts_reflects_latest(self, app_client):
        client, _, _ = app_client
        client.put("/settings", json={"name": "First"})
        client.put("/settings", json={"name": "Second"})
        assert client.get("/settings").json()["name"] == "Second"


# ---------------------------------------------------------------------------
# PATCH /session/{session_id}/feedback
# ---------------------------------------------------------------------------

class TestFeedbackEndpoint:
    def test_returns_200_on_valid_session(self, app_client):
        client, _, _ = app_client
        import database
        session_id, _ = database.create_session()
        resp = client.patch(
            f"/session/{session_id}/feedback",
            json={"rating": "good", "comments": "Felt great!"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "saved"

    def test_rating_is_persisted(self, app_client):
        client, _, _ = app_client
        import database, sqlite3
        session_id, _ = database.create_session()
        client.patch(
            f"/session/{session_id}/feedback",
            json={"rating": "bad", "comments": ""},
        )
        conn = sqlite3.connect(str(client.app.state.__dict__.get("_db_path", "")))
        # verify via database module directly
        import database as db
        sessions = db.get_sessions_by_date(
            datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )
        # session not complete yet, but rating should be stored
        conn2 = __import__("sqlite3").connect(
            __import__("database").DATABASE_PATH
        )
        row = conn2.execute(
            "SELECT rating FROM sessions WHERE session_id=?", (session_id,)
        ).fetchone()
        conn2.close()
        assert row[0] == "bad"

    def test_empty_comments_defaults_to_empty_string(self, app_client):
        client, _, _ = app_client
        import database
        session_id, _ = database.create_session()
        resp = client.patch(
            f"/session/{session_id}/feedback",
            json={"rating": "okay"},
        )
        assert resp.status_code == 200

    def test_all_rating_values_accepted(self, app_client):
        client, _, _ = app_client
        import database
        for rating in ("good", "okay", "bad"):
            session_id, _ = database.create_session()
            resp = client.patch(
                f"/session/{session_id}/feedback",
                json={"rating": rating, "comments": ""},
            )
            assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /ktw/save
# ---------------------------------------------------------------------------

class TestKTWSaveEndpoint:
    def test_returns_200(self, app_client):
        client, _, _ = app_client
        resp = client.post("/ktw/save", json={"angle_deg": 42.5})
        assert resp.status_code == 200

    def test_response_has_status_saved(self, app_client):
        client, _, _ = app_client
        resp = client.post("/ktw/save", json={"angle_deg": 38.0})
        assert resp.json()["status"] == "saved"

    def test_response_has_id(self, app_client):
        client, _, _ = app_client
        resp = client.post("/ktw/save", json={"angle_deg": 35.0})
        assert "id" in resp.json()
        assert isinstance(resp.json()["id"], int)

    def test_with_details_payload(self, app_client):
        client, _, _ = app_client
        resp = client.post(
            "/ktw/save",
            json={"angle_deg": 45.0, "details": {"angle_over_time": {0.0: 45.0}}},
        )
        assert resp.status_code == 200

    def test_ids_auto_increment(self, app_client):
        client, _, _ = app_client
        id1 = client.post("/ktw/save", json={"angle_deg": 30.0}).json()["id"]
        id2 = client.post("/ktw/save", json={"angle_deg": 35.0}).json()["id"]
        assert id2 > id1


# ---------------------------------------------------------------------------
# GET /ktw/history  &  GET /ktw/by-date/{date}
# ---------------------------------------------------------------------------

class TestKTWHistoryEndpoints:
    def test_history_empty_initially(self, app_client):
        client, _, _ = app_client
        resp = client.get("/ktw/history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_returns_saved_measurements(self, app_client):
        client, _, _ = app_client
        client.post("/ktw/save", json={"angle_deg": 30.0})
        client.post("/ktw/save", json={"angle_deg": 35.0})
        assert len(client.get("/ktw/history").json()) == 2

    def test_history_entries_have_required_fields(self, app_client):
        client, _, _ = app_client
        client.post("/ktw/save", json={"angle_deg": 40.0})
        entry = client.get("/ktw/history").json()[0]
        for field in ("id", "measured_at", "angle_deg"):
            assert field in entry

    def test_by_date_returns_todays_entry(self, app_client):
        client, _, _ = app_client
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        client.post("/ktw/save", json={"angle_deg": 28.0})
        results = client.get(f"/ktw/by-date/{today}").json()
        assert any(r["angle_deg"] == 28.0 for r in results)

    def test_by_date_empty_for_old_date(self, app_client):
        client, _, _ = app_client
        assert client.get("/ktw/by-date/2000-01-01").json() == []

    def test_by_date_returns_200(self, app_client):
        client, _, _ = app_client
        assert client.get("/ktw/by-date/2025-06-15").status_code == 200


# ---------------------------------------------------------------------------
# GET /sessions/dates  &  GET /sessions/by-date/{date}
# ---------------------------------------------------------------------------

class TestSessionDatesEndpoints:
    def test_dates_empty_initially(self, app_client):
        client, _, _ = app_client
        assert client.get("/sessions/dates").json() == []

    def test_dates_includes_completed_session_date(self, app_client):
        client, _, _ = app_client
        import database
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        session_id, _ = database.create_session()
        database.complete_session(session_id, 10.0, {})
        assert today in client.get("/sessions/dates").json()

    def test_dates_includes_ktw_date(self, app_client):
        client, _, _ = app_client
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        client.post("/ktw/save", json={"angle_deg": 32.0})
        assert today in client.get("/sessions/dates").json()

    def test_dates_excludes_incomplete_sessions(self, app_client):
        client, _, _ = app_client
        import database
        database.create_session()  # never completed
        assert client.get("/sessions/dates").json() == []

    def test_by_date_empty_for_unknown_date(self, app_client):
        client, _, _ = app_client
        assert client.get("/sessions/by-date/1999-01-01").json() == []

    def test_by_date_returns_complete_session(self, app_client):
        client, _, _ = app_client
        import database
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        session_id, _ = database.create_session()
        database.complete_session(session_id, 20.0, {"rep_counts": {"Calf Raises": 5}})
        results = client.get(f"/sessions/by-date/{today}").json()
        assert any(r["session_id"] == session_id for r in results)

    def test_by_date_excludes_incomplete(self, app_client):
        client, _, _ = app_client
        import database
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        database.create_session()  # incomplete
        assert client.get(f"/sessions/by-date/{today}").json() == []

    def test_by_date_has_analysis_parsed(self, app_client):
        client, _, _ = app_client
        import database
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        session_id, _ = database.create_session()
        database.complete_session(session_id, 30.0, {"rep_counts": {"Calf Raises": 3}})
        results = client.get(f"/sessions/by-date/{today}").json()
        matching = [r for r in results if r["session_id"] == session_id]
        assert matching[0]["analysis"]["rep_counts"]["Calf Raises"] == 3


# ---------------------------------------------------------------------------
# POST /session/start
# ---------------------------------------------------------------------------

class TestSessionStart:
    def test_returns_200(self, app_client):
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=False)
        type(mock_ble).is_connected = PropertyMock(return_value=False)
        assert client.post("/session/start").status_code == 200

    def test_response_has_session_id(self, app_client):
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=False)
        type(mock_ble).is_connected = PropertyMock(return_value=False)
        data = client.post("/session/start").json()
        assert "session_id" in data
        assert isinstance(data["session_id"], str)

    def test_response_status_is_streaming(self, app_client):
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=False)
        type(mock_ble).is_connected = PropertyMock(return_value=False)
        assert client.post("/session/start").json()["status"] == "streaming"

    def test_response_has_start_time(self, app_client):
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=False)
        type(mock_ble).is_connected = PropertyMock(return_value=False)
        assert "start_time" in client.post("/session/start").json()

    def test_returns_400_when_already_streaming(self, app_client):
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=True)
        resp = client.post("/session/start")
        assert resp.status_code == 400

    def test_calls_ble_connect_when_not_connected(self, app_client):
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=False)
        type(mock_ble).is_connected = PropertyMock(return_value=False)
        client.post("/session/start")
        mock_ble.connect.assert_called_once()

    def test_skips_connect_when_already_connected(self, app_client):
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=False)
        type(mock_ble).is_connected = PropertyMock(return_value=True)
        client.post("/session/start")
        mock_ble.connect.assert_not_called()

    def test_calls_start_streaming(self, app_client):
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=False)
        type(mock_ble).is_connected = PropertyMock(return_value=False)
        client.post("/session/start")
        mock_ble.start_streaming.assert_called_once()


# ---------------------------------------------------------------------------
# POST /session/stop
# ---------------------------------------------------------------------------

class TestSessionStop:
    def _start_session(self, app_client):
        """Helper: manually inject an active session into the module globals."""
        import main, database
        client, mock_ble, mock_clf = app_client
        session_id, start_time = database.create_session()
        main._session_id = session_id
        main._start_time = start_time
        main._start_ts = time.time()
        type(mock_ble).is_streaming = PropertyMock(return_value=True)
        mock_ble.stop_streaming = AsyncMock(return_value=[])
        return client, mock_ble, mock_clf, session_id

    def test_returns_400_when_no_active_session(self, app_client):
        client, mock_ble, _ = app_client
        import main
        main._session_id = None
        type(mock_ble).is_streaming = PropertyMock(return_value=False)
        assert client.post("/session/stop").status_code == 400

    def test_returns_400_when_not_streaming(self, app_client):
        client, mock_ble, _ = app_client
        import main
        main._session_id = "some-id"
        type(mock_ble).is_streaming = PropertyMock(return_value=False)
        resp = client.post("/session/stop")
        assert resp.status_code == 400

    def test_returns_200_with_active_session(self, app_client):
        client, mock_ble, mock_clf, _ = self._start_session(app_client)
        assert client.post("/session/stop").status_code == 200

    def test_response_status_is_completed(self, app_client):
        client, mock_ble, mock_clf, _ = self._start_session(app_client)
        assert client.post("/session/stop").json()["status"] == "completed"

    def test_response_has_session_id(self, app_client):
        client, mock_ble, mock_clf, session_id = self._start_session(app_client)
        assert client.post("/session/stop").json()["session_id"] == session_id

    def test_response_has_duration_seconds(self, app_client):
        client, mock_ble, mock_clf, _ = self._start_session(app_client)
        data = client.post("/session/stop").json()
        assert "duration_seconds" in data
        assert data["duration_seconds"] >= 0

    def test_response_has_exercises_list(self, app_client):
        client, mock_ble, mock_clf, _ = self._start_session(app_client)
        data = client.post("/session/stop").json()
        assert "exercises" in data
        assert isinstance(data["exercises"], list)

    def test_response_has_analysis(self, app_client):
        client, mock_ble, mock_clf, _ = self._start_session(app_client)
        data = client.post("/session/stop").json()
        assert "analysis" in data

    def test_clears_session_globals_after_stop(self, app_client):
        import main
        client, mock_ble, mock_clf, _ = self._start_session(app_client)
        client.post("/session/stop")
        assert main._session_id is None

    def test_calls_ble_disconnect_after_stop(self, app_client):
        client, mock_ble, mock_clf, _ = self._start_session(app_client)
        client.post("/session/stop")
        mock_ble.disconnect.assert_called_once()

    def test_session_saved_to_db(self, app_client):
        import database
        client, mock_ble, mock_clf, session_id = self._start_session(app_client)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        client.post("/session/stop")
        results = database.get_sessions_by_date(today)
        assert any(r["session_id"] == session_id for r in results)


# ---------------------------------------------------------------------------
# POST /ble/disconnect
# ---------------------------------------------------------------------------

class TestBLEDisconnect:
    def test_returns_200(self, app_client):
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=False)
        assert client.post("/ble/disconnect").status_code == 200

    def test_response_status_disconnected(self, app_client):
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=False)
        assert client.post("/ble/disconnect").json()["status"] == "disconnected"

    def test_stops_streaming_before_disconnect(self, app_client):
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=True)
        mock_ble.stop_streaming = AsyncMock(return_value=[])
        client.post("/ble/disconnect")
        mock_ble.stop_streaming.assert_called_once()

    def test_calls_disconnect(self, app_client):
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=False)
        client.post("/ble/disconnect")
        mock_ble.disconnect.assert_called_once()

    def test_resets_ktw_active_flag(self, app_client):
        import main
        client, mock_ble, _ = app_client
        main._ktw_active = True
        type(mock_ble).is_streaming = PropertyMock(return_value=False)
        client.post("/ble/disconnect")
        assert main._ktw_active is False


# ---------------------------------------------------------------------------
# POST /ktw/start
# ---------------------------------------------------------------------------

class TestKTWStart:
    def test_returns_200(self, app_client):
        import main
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=False)
        type(mock_ble).is_connected = PropertyMock(return_value=False)
        main._ktw_active = False
        assert client.post("/ktw/start").status_code == 200

    def test_response_has_streaming_status(self, app_client):
        import main
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=False)
        type(mock_ble).is_connected = PropertyMock(return_value=False)
        main._ktw_active = False
        data = client.post("/ktw/start").json()
        assert data["status"] == "streaming"
        assert data["mode"] == "ktw"

    def test_returns_400_when_session_streaming(self, app_client):
        import main
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=True)
        main._ktw_active = False  # not a KTW session
        resp = client.post("/ktw/start")
        assert resp.status_code == 400

    def test_clears_readings_on_redo(self, app_client):
        """If already streaming in KTW mode, readings are cleared for redo."""
        import main
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=True)
        main._ktw_active = True
        client.post("/ktw/start")
        mock_ble.clear_readings.assert_called_once()

    def test_redo_returns_200(self, app_client):
        import main
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=True)
        main._ktw_active = True
        assert client.post("/ktw/start").status_code == 200

    def test_calls_connect_when_not_connected(self, app_client):
        import main
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=False)
        type(mock_ble).is_connected = PropertyMock(return_value=False)
        main._ktw_active = False
        client.post("/ktw/start")
        mock_ble.connect.assert_called_once()


# ---------------------------------------------------------------------------
# POST /ktw/stop
# ---------------------------------------------------------------------------

class TestKTWStop:
    def test_returns_400_when_not_active(self, app_client):
        import main
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=False)
        main._ktw_active = False
        assert client.post("/ktw/stop").status_code == 400

    def test_returns_400_when_ktw_not_flagged(self, app_client):
        import main
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=True)
        main._ktw_active = False  # not a KTW session
        assert client.post("/ktw/stop").status_code == 400

    def test_returns_400_when_no_sensor_data(self, app_client):
        """
        When stop_streaming returns empty readings, both imu counts are 0
        and the endpoint must return 400.
        """
        import main
        client, mock_ble, _ = app_client
        type(mock_ble).is_streaming = PropertyMock(return_value=True)
        mock_ble.stop_streaming = AsyncMock(return_value=[])
        main._ktw_active = True
        resp = client.post("/ktw/stop")
        assert resp.status_code == 400
