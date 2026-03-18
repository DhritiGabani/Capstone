"""
FastAPI server for dorsiflexx backend.

Endpoints:
  POST /session/start  - connect BLE, start streaming, create DB session
  POST /session/stop   - stop streaming, save readings, run analysis pipeline
  GET  /status         - return streaming state and sample counts
"""

import asyncio
import logging
import os
import time
import traceback
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel

log = logging.getLogger(__name__)

from ble_manager import BLEManager
from classifier import ExerciseClassifier
from database import (
    init_db, create_session, save_raw_data, complete_session, save_feedback,
    save_ktw_measurement, get_ktw_measurements, get_ktw_measurements_by_date,
    get_ktw_leaderboard, get_session_dates, get_sessions_by_date,
)
from pipeline import preprocess_session, sensor_readings_to_imu_json, wrangle, filter_signals, extract_features
from analysis import analyze_session
import ktw_analysis

# ---------------------------------------------------------------------------
# Application state
# ---------------------------------------------------------------------------

ble = BLEManager()
classifier: ExerciseClassifier | None = None

_session_id: str | None = None
_start_time: str | None = None
_start_ts: float | None = None
_ktw_active: bool = False

# SSE clients waiting for leaderboard updates
_sse_clients: set[asyncio.Queue] = set()


def _broadcast_leaderboard_update() -> None:
    """Push a notification to all connected leaderboard SSE clients."""
    dead: set[asyncio.Queue] = set()
    for q in list(_sse_clients):
        try:
            q.put_nowait("update")
        except asyncio.QueueFull:
            dead.add(q)
    _sse_clients -= dead


@asynccontextmanager
async def lifespan(app: FastAPI):
    global classifier
    init_db()
    classifier = ExerciseClassifier()
    yield


app = FastAPI(title="dorsiflexx", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# POST /session/start
# ---------------------------------------------------------------------------

@app.post("/session/start")
async def session_start():
    global _session_id, _start_time, _start_ts

    if ble.is_streaming:
        raise HTTPException(400, "A session is already in progress.")

    if not ble.is_connected:
        await ble.connect()
    await ble.start_streaming()

    _session_id, _start_time = create_session()
    _start_ts = time.time()

    return {
        "session_id": _session_id,
        "status": "streaming",
        "start_time": _start_time,
    }


# ---------------------------------------------------------------------------
# POST /session/stop
# ---------------------------------------------------------------------------

@app.post("/session/stop")
async def session_stop():
    global _session_id, _start_time, _start_ts

    if not ble.is_streaming or _session_id is None:
        raise HTTPException(400, "No active session to stop.")

    session_id = _session_id
    start_ts = _start_ts

    readings = await ble.stop_streaming()
    duration_s = round(time.time() - start_ts, 2)

    # Convert readings to per-device JSON and save immediately
    imu1_json = sensor_readings_to_imu_json(readings, "imu1")
    imu2_json = sensor_readings_to_imu_json(readings, "imu2")

    imu1_count = len(imu1_json.get("samples", []))
    imu2_count = len(imu2_json.get("samples", []))
    log.info("Session stopped: %d readings (imu1=%d, imu2=%d)", len(readings), imu1_count, imu2_count)

    # Save raw IMU data even if analysis fails
    save_raw_data(session_id, imu1_json, imu2_json)

    # Run analysis pipeline only if we have data from both sensors
    exercises = []
    analysis = {}

    if imu1_count > 0 and imu2_count > 0:
        try:
            log.info("Running preprocessing pipeline...")
            pipeline_result = preprocess_session(readings)
            log.info("Preprocessing done: X shape=%s, %d reps", pipeline_result["X"].shape, len(set(pipeline_result["rep_indices"])))

            log.info("Running analysis...")
            analysis = analyze_session(
                X=pipeline_result["X"],
                rep_indices=pipeline_result["rep_indices"],
                sensor_locations=pipeline_result["sensor_locations"],
                segmented_df=pipeline_result["segmented_df"],
                classifier=classifier,
            )
            log.info("Analysis done: %s", list(analysis.keys()))

            # Build exercise list matching SessionStopResponse shape
            rep_counts = analysis.get("rep_counts", {})
            consistency = analysis.get("consistency_scores", {})
            durations = analysis.get("rep_durations", {})
            ankle = analysis.get("ankle_angles")

            for exercise_type, rep_count in rep_counts.items():
                ex = {
                    "exercise_type": exercise_type,
                    "rep_count": rep_count,
                    "rom": ankle.get("mean_min_angle_deg", 0) if ankle and exercise_type == "Heel Walk" else 0,
                    "tempo_consistency": durations.get(exercise_type, {}).get("mean_duration_s", 0),
                    "movement_consistency": consistency.get(exercise_type, 0) or 0,
                }
                exercises.append(ex)
        except Exception as e:
            log.error("Analysis pipeline failed: %s\n%s", e, traceback.format_exc())
            analysis = {"error": str(e)}
    else:
        log.warning("Skipping analysis: imu1_count=%d, imu2_count=%d", imu1_count, imu2_count)

    complete_session(session_id, duration_s, analysis)

    _session_id = None
    _start_time = None
    _start_ts = None

    return {
        "session_id": session_id,
        "status": "completed",
        "duration_seconds": duration_s,
        "total_samples": len(readings),
        "exercises": exercises,
        "analysis": analysis,
    }


# ---------------------------------------------------------------------------
# GET /status
# ---------------------------------------------------------------------------

@app.get("/status")
async def status():
    return {
        "status": "streaming" if ble.is_streaming else "idle",
        "is_streaming": ble.is_streaming,
        "is_connected": ble.is_connected,
        "session_id": _session_id,
        "stats": ble.sample_counts if ble.is_streaming else None,
    }


# ---------------------------------------------------------------------------
# PATCH /session/{session_id}/feedback
# ---------------------------------------------------------------------------

class FeedbackBody(BaseModel):
    rating: str
    comments: str = ""


@app.patch("/session/{session_id}/feedback")
async def session_feedback(session_id: str, body: FeedbackBody):
    save_feedback(session_id, body.rating, body.comments)
    return {"status": "saved"}


# ---------------------------------------------------------------------------
# POST /ble/disconnect
# ---------------------------------------------------------------------------

@app.post("/ble/disconnect")
async def ble_disconnect():
    """Disconnect from sensors. Called by the frontend after the user saves their results."""
    global _ktw_active
    if ble.is_streaming:
        await ble.stop_streaming()
    await ble.disconnect()
    _ktw_active = False
    return {"status": "disconnected"}


# ---------------------------------------------------------------------------
# POST /ktw/start
# ---------------------------------------------------------------------------

@app.post("/ktw/start")
async def ktw_start():
    global _ktw_active

    # If already streaming in KTW mode, clear buffered readings so only
    # data from the upcoming countdown window is captured.
    if ble.is_streaming and _ktw_active:
        ble.clear_readings()
        return {"status": "streaming", "mode": "ktw"}

    if ble.is_streaming:
        raise HTTPException(400, "A session is already in progress.")

    # Sensors may still be connected from a previous measurement (redo case).
    # Only scan/connect if not already connected.
    if not ble.is_connected:
        await ble.connect()
    await ble.start_streaming()
    _ktw_active = True

    return {"status": "streaming", "mode": "ktw"}


# ---------------------------------------------------------------------------
# POST /ktw/stop
# ---------------------------------------------------------------------------

@app.post("/ktw/stop")
async def ktw_stop():
    global _ktw_active

    if not ble.is_streaming or not _ktw_active:
        raise HTTPException(400, "No active KTW session to stop.")

    readings = await ble.stop_streaming()
    _ktw_active = False

    imu1_json = sensor_readings_to_imu_json(readings, "imu1")
    imu2_json = sensor_readings_to_imu_json(readings, "imu2")

    imu1_count = len(imu1_json.get("samples", []))
    imu2_count = len(imu2_json.get("samples", []))
    log.info("KTW stopped: %d readings (imu1=%d, imu2=%d)", len(readings), imu1_count, imu2_count)

    if imu1_count == 0 or imu2_count == 0:
        raise HTTPException(400, "No sensor data received from one or both IMUs.")

    try:
        # Run pipeline stages 0-3 only (wrangle, filter, features — NO segmentation)
        signals_df = wrangle(imu1_json, imu2_json)
        filtered_df = filter_signals(signals_df)
        featured_df = extract_features(filtered_df)

        result = ktw_analysis.analyze(featured_df)
        log.info("KTW analysis done: largest_angle=%.3f", result["largest_angle_deg"])
        return result
    except Exception as e:
        log.error("KTW analysis failed: %s\n%s", e, traceback.format_exc())
        raise HTTPException(500, f"KTW analysis failed: {e}")


# ---------------------------------------------------------------------------
# POST /ktw/save
# ---------------------------------------------------------------------------

class KTWSaveBody(BaseModel):
    angle_deg: float
    details: dict | None = None
    name: str = "Anonymous"


@app.post("/ktw/save")
async def ktw_save(body: KTWSaveBody):
    try:
        row_id = save_ktw_measurement(body.angle_deg, body.details, body.name)
    except Exception as e:
        log.error("ktw_save failed: %s\n%s", e, traceback.format_exc())
        raise HTTPException(500, f"Could not save measurement: {e}")
    try:
        _broadcast_leaderboard_update()
    except Exception as e:
        log.warning("SSE broadcast failed (non-fatal): %s", e)
    return {"status": "saved", "id": row_id}


# ---------------------------------------------------------------------------
# GET /ktw/history
# ---------------------------------------------------------------------------

@app.get("/ktw/history")
async def ktw_history():
    return get_ktw_measurements()


# ---------------------------------------------------------------------------
# GET /ktw/by-date/{date}
# ---------------------------------------------------------------------------

@app.get("/ktw/by-date/{date}")
async def ktw_by_date(date: str):
    return get_ktw_measurements_by_date(date)


# ---------------------------------------------------------------------------
# GET /sessions/dates
# ---------------------------------------------------------------------------

@app.get("/sessions/dates")
async def sessions_dates():
    return get_session_dates()


# ---------------------------------------------------------------------------
# GET /sessions/by-date/{date}
# ---------------------------------------------------------------------------

@app.get("/sessions/by-date/{date}")
async def sessions_by_date(date: str):
    return get_sessions_by_date(date)


# ---------------------------------------------------------------------------
# GET /ktw/leaderboard/stream  (SSE — push update when new row is saved)
# ---------------------------------------------------------------------------

@app.get("/ktw/leaderboard/stream")
async def leaderboard_stream(request: Request):
    queue: asyncio.Queue = asyncio.Queue(maxsize=5)
    _sse_clients.add(queue)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield "data: update\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"   # keep-alive comment, ignored by client
        finally:
            _sse_clients.discard(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# GET /ktw/leaderboard  (JSON data)
# ---------------------------------------------------------------------------

@app.get("/ktw/leaderboard")
async def ktw_leaderboard():
    return get_ktw_leaderboard()


# ---------------------------------------------------------------------------
# GET /logo.png  (brand logo for leaderboard page)
# ---------------------------------------------------------------------------

@app.get("/logo.png")
async def serve_logo():
    logo_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "assets", "images", "logo.png")
    )
    return FileResponse(logo_path, media_type="image/png")


# ---------------------------------------------------------------------------
# GET /leaderboard  (HTML page)
# ---------------------------------------------------------------------------

@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page():
    html_path = os.path.join(os.path.dirname(__file__), "leaderboard.html")
    with open(html_path, encoding="utf-8") as f:
        return f.read()
