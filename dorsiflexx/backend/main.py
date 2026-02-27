"""
FastAPI server for dorsiflexx backend (cloud deployment).

Endpoints:
  POST  /session/start               - create DB session
  POST  /session/{session_id}/analyze - receive readings, run analysis pipeline
  GET   /status                       - health check
  PATCH /session/{session_id}/feedback - save user feedback
"""

import logging
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

log = logging.getLogger(__name__)

from classifier import ExerciseClassifier
from database import init_db, create_session, save_readings, complete_session, save_feedback
from pipeline import preprocess_session
from analysis import analyze_session
from sensor import SensorReading

# ---------------------------------------------------------------------------
# Application state
# ---------------------------------------------------------------------------

classifier: ExerciseClassifier | None = None


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
    session_id, start_time = create_session()
    return {
        "session_id": session_id,
        "start_time": start_time,
    }


# ---------------------------------------------------------------------------
# POST /session/{session_id}/analyze
# ---------------------------------------------------------------------------

class AnalyzeBody(BaseModel):
    readings: List[List[float]]  # [[device_idx, timestamp_us, ax, ay, az, gx, gy, gz], ...]
    duration_seconds: float


@app.post("/session/{session_id}/analyze")
async def session_analyze(session_id: str, body: AnalyzeBody):
    if not body.readings:
        raise HTTPException(400, "No readings provided.")

    # Convert compact array-of-arrays to SensorReading objects
    device_map = {1: "imu1", 2: "imu2"}
    readings = []
    for row in body.readings:
        if len(row) < 8:
            continue
        device_idx = int(row[0])
        readings.append(SensorReading(
            device=device_map.get(device_idx, f"imu{device_idx}"),
            timestamp_us=int(row[1]),
            ax=row[2],
            ay=row[3],
            az=row[4],
            gx=row[5],
            gy=row[6],
            gz=row[7],
        ))

    imu1_count = sum(1 for r in readings if r.device == "imu1")
    imu2_count = sum(1 for r in readings if r.device == "imu2")
    log.info("Analyze: %d readings (imu1=%d, imu2=%d)", len(readings), imu1_count, imu2_count)

    # Save raw readings
    if readings:
        save_readings(session_id, readings)

    # Run analysis pipeline only if we have data from both sensors
    exercises = []
    analysis = {}

    if imu1_count > 0 and imu2_count > 0:
        try:
            pipeline_result = preprocess_session(readings)

            analysis = analyze_session(
                X=pipeline_result["X"],
                rep_indices=pipeline_result["rep_indices"],
                sensor_locations=pipeline_result["sensor_locations"],
                segmented_df=pipeline_result["segmented_df"],
                classifier=classifier,
            )

            # Build exercise list matching AnalyzeResponse shape
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
            log.warning("Analysis pipeline failed: %s", e)
            analysis = {"error": str(e)}

    complete_session(session_id, body.duration_seconds, analysis)

    return {
        "session_id": session_id,
        "status": "completed",
        "duration_seconds": body.duration_seconds,
        "total_samples": len(readings),
        "exercises": exercises,
        "analysis": analysis,
    }


# ---------------------------------------------------------------------------
# GET /status
# ---------------------------------------------------------------------------

@app.get("/status")
async def status():
    return {"status": "ok"}


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
