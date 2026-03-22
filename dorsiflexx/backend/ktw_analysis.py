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

# Smoothing window for ankle angle signal (moving average)
SMOOTHING_WINDOW = 10


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
            "largest_angle_deg": float,
            "angle_over_time": {0.0: angle, 0.5: angle, ...}
        }
    """
    shank_df = signals_df[signals_df["sensor_location"] == "shank"].copy()

    if shank_df.empty:
        raise ValueError("Missing shank sensor data.")

    shank_df = shank_df.sort_values("time").reset_index(drop=True)

    ankle_angle_raw    = 90 - shank_df["pitch"].values
    ankle_angle_smooth = _smooth_signal(ankle_angle_raw)
    ankle_angle_pos    = ankle_angle_smooth
    time               = shank_df["time"].values

    largest_angle = round(float(np.max(ankle_angle_pos)), 3)

    session_duration = float(time[-1] - time[0])
    sample_times     = np.arange(0, session_duration + 0.5, 0.5)
    sampled_angles   = {}

    for t in sample_times:
        abs_t   = time[0] + t
        idx     = int(np.argmin(np.abs(time - abs_t)))
        sampled_angles[round(float(t), 1)] = round(float(ankle_angle_pos[idx]), 3)
    

    return {
        "largest_angle_deg": largest_angle,
        "angle_over_time":   sampled_angles,
    }
