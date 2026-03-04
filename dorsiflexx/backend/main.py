"""
FastAPI server for dorsiflexx backend.

Endpoints:
  POST /session/start  - connect BLE, start streaming, create DB session
  POST /session/stop   - stop streaming, save readings, run analysis pipeline
  GET  /status         - return streaming state and sample counts
"""

import logging
import time
import traceback
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

log = logging.getLogger(__name__)

from ble_manager import BLEManager
from classifier import ExerciseClassifier
from database import init_db, create_session, save_raw_data, complete_session, save_feedback
from pipeline import preprocess_session, sensor_readings_to_imu_json
from analysis import analyze_session

# ---------------------------------------------------------------------------
# Application state
# ---------------------------------------------------------------------------

ble = BLEManager()
classifier: ExerciseClassifier | None = None

_session_id: str | None = None
_start_time: str | None = None
_start_ts: float | None = None


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
                    "rom": ankle.get("mean_max_angle_deg", 0) if ankle and exercise_type == "Heel Walk" else 0,
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
