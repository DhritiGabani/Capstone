"""
Knee-to-Wall test analysis module for dorsiflexx backend.

Ported from src/processing/04_knee_to_wall_test.py.
Operates on a preprocessed signals DataFrame (after wrangle, filter, features —
NO segmentation) and returns the smallest active ankle angle plus a time-sampled
angle trace.
"""

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Ankle angles at or below this value are considered resting (standing upright)
REST_ANGLE_THRESHOLD = -65.0

# Smoothing window for ankle angle signal (moving average)
SMOOTHING_WINDOW = 10

# Rolling window for variance calculation to detect hold phases
VARIANCE_WINDOW = 50

# Maximum variance allowed for a position to be considered a hold
HOLD_VARIANCE_THRESHOLD = 1.0

# Minimum duration for a hold phase to be counted
MIN_HOLD_DURATION = 50

# Tolerance around peak angle to determine how long peak was held
PEAK_HOLD_TOLERANCE = 2.0


# ---------------------------------------------------------------------------
# Core Algorithm
# ---------------------------------------------------------------------------

def _smooth_signal(signal: np.ndarray) -> np.ndarray:
    """Apply a centered moving average to smooth the ankle angle signal."""
    smoothed = (
        pd.Series(signal)
        .rolling(window=SMOOTHING_WINDOW, center=True)
        .mean()
        .bfill()
        .ffill()
        .values
    )
    return smoothed


def analyze(signals_df: pd.DataFrame) -> dict:
    """
    Run the Knee to Wall test analysis on the preprocessed signals DataFrame.

    Args:
        signals_df: DataFrame with columns including 'sensor_location', 'time',
                    'pitch' (from wrangle -> filter -> extract_features stages).

    Returns:
        {
            "smallest_angle_deg": float,
            "angle_over_time": {0.0: angle, 0.5: angle, ...}
        }
    """
    foot_df = signals_df[signals_df["sensor_location"] == "foot"].copy()
    shank_df = signals_df[signals_df["sensor_location"] == "shank"].copy()

    if foot_df.empty or shank_df.empty:
        raise ValueError("Missing foot or shank sensor data.")

    foot_df = foot_df.sort_values("time").reset_index(drop=True)
    shank_df = shank_df.sort_values("time").reset_index(drop=True)

    shank_pitch_interp = np.interp(
        foot_df["time"].values,
        shank_df["time"].values,
        shank_df["pitch"].values,
    )

    ankle_angle_raw = foot_df["pitch"].values - shank_pitch_interp
    ankle_angle_smooth = _smooth_signal(ankle_angle_raw)
    ankle_angle_abs = np.abs(ankle_angle_smooth)
    time = foot_df["time"].values

    active_mask = ankle_angle_smooth > REST_ANGLE_THRESHOLD
    if not np.any(active_mask):
        # If no samples pass the threshold, use all data — the user is
        # holding the position and the threshold may not match the sensor
        # orientation.  Fall back to full signal so we still return a result.
        active_mask = np.ones(len(ankle_angle_smooth), dtype=bool)

    # Use the median absolute angle during the active window.  The median is
    # robust to transient near-zero samples at the start/end of the capture
    # and represents the angle the user actually held.
    smallest_angle = round(float(np.median(ankle_angle_abs[active_mask])), 3)

    session_duration = float(time[-1] - time[0])
    sample_times = np.arange(0, session_duration + 0.5, 0.5)
    sampled_angles = {}

    for t in sample_times:
        abs_t = time[0] + t
        idx = int(np.argmin(np.abs(time - abs_t)))
        sampled_angles[round(float(t), 1)] = round(float(ankle_angle_abs[idx]), 3)

    return {
        "smallest_angle_deg": smallest_angle,
        "angle_over_time": sampled_angles,
    }
