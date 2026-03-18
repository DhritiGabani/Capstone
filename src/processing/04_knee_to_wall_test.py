import json
import numpy as np
import pandas as pd
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Smoothing window for ankle angle signal (moving average)
SMOOTHING_WINDOW = 10  


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
    shank_df = signals_df[signals_df["sensor_location"] == "shank"].copy()

    if shank_df.empty or shank_df.empty:
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
        "largest_angle_deg":     largest_angle,
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