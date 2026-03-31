"""
Shared fixtures and helpers for dorsiflexx backend tests.

All tests run without real BLE hardware or a live TFLite model by using:
  - make_sensor_readings()  — synthetic IMU data with sinusoidal motion
  - mock_classifier fixture — MagicMock that returns "Calf Raises" at 0.95
  - test_db fixture         — isolated temp SQLite database
"""

import os
import sys

import numpy as np
import pytest

# Make the backend package importable from any working directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensor import SensorReading

SAMPLE_RATE_HZ = 160


def make_sensor_readings(
    n_samples: int = 480,
    n_reps: int = 3,
    amp_deg: float = 25.0,
) -> list[SensorReading]:
    """
    Generate synthetic SensorReading objects that simulate ankle dorsiflexion.

    The accelerometer values are chosen so that the pipeline's pitch formula
        pitch = arctan2(-ax, sqrt(ay² + az²))
    recovers ≈ ±amp_deg degrees at a cadence of n_reps full cycles over
    n_samples samples (at 160 Hz).

    Peak-to-trough prominence is ~2 * amp_deg degrees (≫ PEAK_MIN_PROMINENCE=15),
    and inter-peak distance is n_samples/n_reps samples (≫ PEAK_MIN_DISTANCE=30),
    so segmentation always detects reps.
    """
    readings: list[SensorReading] = []
    dt_us = int(1_000_000 / SAMPLE_RATE_HZ)
    period = n_samples / n_reps

    for i in range(n_samples):
        angle_rad = np.radians(amp_deg * np.sin(2 * np.pi * i / period))
        ax = float(-np.sin(angle_rad))
        ay = 0.0
        az = float(np.cos(angle_rad))

        for dev in ("imu1", "imu2"):
            readings.append(
                SensorReading(
                    device=dev,
                    timestamp_us=i * dt_us,
                    ax=ax, ay=ay, az=az,
                    gx=0.0, gy=0.0, gz=0.0,
                )
            )

    return readings


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def synthetic_readings() -> list[SensorReading]:
    """480 samples / 3 reps of synthetic dorsiflexion for each IMU."""
    return make_sensor_readings()


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """
    Isolated SQLite database for each test.

    Patches database.DATABASE_PATH so every CRUD call in the test hits a
    fresh temp file rather than the real dorsiflexx.db.
    """
    import database

    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(database, "DATABASE_PATH", db_path)
    database.init_db()
    return db_path


@pytest.fixture
def mock_classifier():
    """
    Deterministic stand-in for ExerciseClassifier.
    Always returns "Calf Raises" with 0.95 confidence so analysis tests
    can assert on deterministic output without a real TFLite model.
    """
    from unittest.mock import MagicMock

    clf = MagicMock()
    clf.classify.return_value = {
        "predicted_class": "Calf Raises",
        "confidence": 0.95,
    }
    clf.classes = ["Ankle Rotation", "Calf Raises", "Heel Walk"]
    return clf
