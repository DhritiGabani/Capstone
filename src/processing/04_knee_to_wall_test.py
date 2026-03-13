import json
import numpy as np
import pandas as pd
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Ankle angles at or below this value are considered resting (standing upright) and are excluded from analysis
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
    """
    Apply a centered moving average to smooth the ankle angle signal.
    """
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
    Run the Knee to Wall test analysis on the preprocessed signals DataFrame
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
        raise ValueError(
            f"No active test positions detected. All ankle angles are at or "
            f"below the rest threshold ({REST_ANGLE_THRESHOLD}°)."
        )

    smallest_angle = round(float(np.min(ankle_angle_abs[active_mask])), 3)

    session_duration = float(time[-1] - time[0])
    sample_times = np.arange(0, session_duration + 0.5, 0.5)
    sampled_angles = {}

    for t in sample_times:
        abs_t = time[0] + t
        idx = int(np.argmin(np.abs(time - abs_t)))
        sampled_angles[round(float(t), 1)] = round(
            float(ankle_angle_abs[idx]), 3)

    return {
        "smallest_angle_deg":    smallest_angle,
        "angle_over_time":       sampled_angles,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def save_results_json(results: dict, output_path: str) -> None:
    """
    Serialize the results dictionary to a JSON file
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(out, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to {out}")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(signals_df: pd.DataFrame) -> dict:
    """
    Execute the Knee to Wall test analysis pipeline
    """
    return analyze(signals_df)


# ---------------------------------------------------------------------------
# Test entry point
# ---------------------------------------------------------------------------

# if __name__ == "__main__":
#     import json
#     import pprint
#     import importlib
#     preprocessing = importlib.import_module("02_preprocessing")

#     imu1_path = r"C:\Users\mistr\OneDrive\Documents\Rohan\University\4A\BME 461\model\Capstone\output\imu1_data.json"
#     imu2_path = r"C:\Users\mistr\OneDrive\Documents\Rohan\University\4A\BME 461\model\Capstone\output\imu2_data.json"
#     output_path = r"C:\Users\mistr\OneDrive\Documents\Rohan\University\4A\BME 461\model\Capstone\output\ktw_results.json"

#     with open(imu1_path) as f:
#         imu1_json = json.load(f)
#     with open(imu2_path) as f:
#         imu2_json = json.load(f)

#     # IMPORTANT: Do not run segmentation when calling preprocessing just the following functions
#     signals_df = preprocessing.wrangle(imu1_json, imu2_json)
#     signals_df = preprocessing.filter_signals(signals_df)
#     signals_df = preprocessing.extract_features(signals_df)

#     results = run(signals_df)

#     pprint.pprint(results)
#     save_results_json(results, output_path)
