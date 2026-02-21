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


def _detect_hold_phases(
    ankle_angle_smooth: np.ndarray,
    time: np.ndarray,
) -> list[dict]:
    """
    Detect hold phases where the subject is maintaining a position.

    A hold phase is a continuous period where the rolling variance of the
    ankle angle stays below HOLD_VARIANCE_THRESHOLD. Phases shorter than
    MIN_HOLD_DURATION samples and phases where the mean angle is at or
    below REST_ANGLE_THRESHOLD are excluded.
    """
    variance = (
        pd.Series(ankle_angle_smooth)
        .rolling(window=VARIANCE_WINDOW, center=True)
        .std()
        .fillna(0)
        .values
    )

    is_holding = variance < HOLD_VARIANCE_THRESHOLD

    hold_phases = []
    in_hold     = False
    hold_start  = None

    for i in range(len(is_holding)):
        if is_holding[i] and not in_hold:
            hold_start = i
            in_hold    = True
        elif not is_holding[i] and in_hold:
            if i - hold_start >= MIN_HOLD_DURATION:
                hold_phases.append((hold_start, i))
            in_hold = False

    if in_hold and len(ankle_angle_smooth) - hold_start >= MIN_HOLD_DURATION:
        hold_phases.append((hold_start, len(ankle_angle_smooth) - 1))

    active_phases = []
    for start, end in hold_phases:
        mean_angle = float(np.mean(ankle_angle_smooth[start:end]))

        if mean_angle <= REST_ANGLE_THRESHOLD:
            continue

        duration = float(time[end] - time[start])

        active_phases.append({
            "start_idx":     start,
            "end_idx":       end,
            "mean_angle_deg": round(mean_angle, 3),
            "duration_s":    round(duration, 3),
        })

    return active_phases


def _find_peak_hold_duration(
    ankle_angle_smooth: np.ndarray,
    time: np.ndarray,
    peak_angle: float,
) -> float:
    """
    Calculate how long the ankle angle was held within PEAK_HOLD_TOLERANCE
    """
    near_peak = np.abs(ankle_angle_smooth - peak_angle) <= PEAK_HOLD_TOLERANCE

    # Find the longest continuous region near the peak
    max_duration = 0.0
    in_region    = False
    region_start = None

    for i in range(len(near_peak)):
        if near_peak[i] and not in_region:
            region_start = i
            in_region    = True
        elif not near_peak[i] and in_region:
            duration     = float(time[i] - time[region_start])
            max_duration = max(max_duration, duration)
            in_region    = False

    if in_region:
        duration     = float(time[-1] - time[region_start])
        max_duration = max(max_duration, duration)

    return round(max_duration, 3)


def analyze(signals_df: pd.DataFrame) -> dict:
    """
    Run the Knee to Wall test analysis on the preprocessed signals DataFrame
    """
    foot_df  = signals_df[signals_df["sensor_location"] == "foot"].copy()
    shank_df = signals_df[signals_df["sensor_location"] == "shank"].copy()

    if foot_df.empty or shank_df.empty:
        raise ValueError("Missing foot or shank sensor data.")

    foot_df  = foot_df.sort_values("time").reset_index(drop=True)
    shank_df = shank_df.sort_values("time").reset_index(drop=True)

    shank_pitch_interp = np.interp(
        foot_df["time"].values,
        shank_df["time"].values,
        shank_df["pitch"].values,
    )

    ankle_angle_raw    = foot_df["pitch"].values - shank_pitch_interp
    ankle_angle_smooth = _smooth_signal(ankle_angle_raw)
    time               = foot_df["time"].values

    active_mask = ankle_angle_smooth > REST_ANGLE_THRESHOLD
    if not np.any(active_mask):
        raise ValueError(
            f"No active test positions detected. All ankle angles are at or "
            f"below the rest threshold ({REST_ANGLE_THRESHOLD}°)."
        )

    peak_angle    = float(np.max(ankle_angle_smooth[active_mask]))
    peak_held_for = _find_peak_hold_duration(ankle_angle_smooth, time, peak_angle)

    hold_phases = _detect_hold_phases(ankle_angle_smooth, time)

    if not hold_phases:
        raise ValueError(
            "No active hold phases detected. The subject may not have held "
            "a position long enough, or all holds were below the rest threshold."
        )

    longest_phase = max(hold_phases, key=lambda p: p["duration_s"])

    peak_idx          = int(np.argmax(ankle_angle_smooth))
    longest_has_peak  = (
        longest_phase["start_idx"] <= peak_idx <= longest_phase["end_idx"]
    )

    if longest_has_peak:
        longest_hold_angle    = None
        longest_hold_duration = None
    else:
        longest_hold_angle    = longest_phase["mean_angle_deg"]
        longest_hold_duration = longest_phase["duration_s"]

    return {
        "highest_angle_deg":      round(peak_angle, 3),
        "highest_angle_held_for_s": peak_held_for,
        "longest_hold_angle_deg": longest_hold_angle,
        "longest_hold_duration_s": longest_hold_duration,
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

if __name__ == "__main__":
    import json
    import pprint
    import importlib
    preprocessing = importlib.import_module("02_preprocessing")

    imu1_path = r"C:\Users\mistr\OneDrive\Documents\Rohan\University\4A\BME 461\model\Capstone\output\imu1_data.json"
    imu2_path = r"C:\Users\mistr\OneDrive\Documents\Rohan\University\4A\BME 461\model\Capstone\output\imu2_data.json"
    output_path = r"C:\Users\mistr\OneDrive\Documents\Rohan\University\4A\BME 461\model\Capstone\output\ktw_results.json"

    with open(imu1_path) as f:
        imu1_json = json.load(f)
    with open(imu2_path) as f:
        imu2_json = json.load(f)

    signals_df = preprocessing.wrangle(imu1_json, imu2_json)
    signals_df = preprocessing.filter_signals(signals_df)
    signals_df = preprocessing.extract_features(signals_df)

    results = run(signals_df)

    pprint.pprint(results)
    save_results_json(results, output_path)