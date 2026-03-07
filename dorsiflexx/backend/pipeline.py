"""
Preprocessing pipeline for dorsiflexx backend.

Ports the signal processing logic from src/processing/02_preprocessing.py
and statistical feature extraction from src/processing/03_analysis.py.

Pipeline stages:
  1. Convert SensorReading buffer to IMU JSON format
  2. Wrangle into aligned foot/shank DataFrames
  3. Butterworth lowpass filtering
  4. Roll and pitch computation
  5. Rep segmentation with per-rep normalization
  6. Statistical feature extraction (8 signals x 8 stats = 64 features)
"""

import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt, find_peaks

from sensor import SensorReading

# ---------------------------------------------------------------------------
# Constants (matching src/processing/02_preprocessing.py)
# ---------------------------------------------------------------------------

SAMPLE_RATE_HZ = 100
SAMPLE_PERIOD_S = 1.0 / SAMPLE_RATE_HZ

COLUMN_MAPPING = {
    "ax_g":   "acc_x",
    "ay_g":   "acc_y",
    "az_g":   "acc_z",
    "gx_dps": "gyr_x",
    "gy_dps": "gyr_y",
    "gz_dps": "gyr_z",
}

SIGNAL_COLUMNS = ["acc_x", "acc_y", "acc_z", "gyr_x", "gyr_y", "gyr_z"]

FEATURES_TO_NORMALIZE = [
    "acc_x", "acc_y", "acc_z",
    "gyr_x", "gyr_y", "gyr_z",
    "roll",  "pitch",
]

# Lowpass filter parameters
FILTER_CUTOFF_HZ = 5
FILTER_ORDER = 2

# Rep boundary detection parameters
PEAK_MIN_DISTANCE = 30
PEAK_MIN_PROMINENCE = 30

# Per-rep normalization baseline window
BASELINE_SAMPLES = 5

# Statistical feature extraction columns (normalized signals)
STATISTICAL_FEATURE_COLS = [
    "acc_x_norm", "acc_y_norm", "acc_z_norm",
    "gyr_x_norm", "gyr_y_norm", "gyr_z_norm",
    "roll_norm",  "pitch_norm",
]


# ---------------------------------------------------------------------------
# Stage 0 — Convert SensorReading buffer to IMU JSON
# ---------------------------------------------------------------------------

def sensor_readings_to_imu_json(
    readings: list[SensorReading],
    device: str,
) -> dict:
    """
    Convert a list of SensorReading objects for a specific device
    into the IMU JSON format expected by the preprocessing pipeline.

    Returns:
        {"samples": [{"sample_idx": i, "ax_g": ..., ...}, ...]}
    """
    device_readings = [r for r in readings if r.device == device]
    device_readings.sort(key=lambda r: r.timestamp_us)

    samples = []
    for i, r in enumerate(device_readings):
        samples.append({
            "sample_idx": i,
            "ax_g": r.ax,
            "ay_g": r.ay,
            "az_g": r.az,
            "gx_dps": r.gx,
            "gy_dps": r.gy,
            "gz_dps": r.gz,
        })

    return {"samples": samples}


# ---------------------------------------------------------------------------
# Stage 1 — Wrangling
# ---------------------------------------------------------------------------

def _build_imu_dataframe(imu_json: dict, sensor_location: str) -> pd.DataFrame:
    """Convert a single IMU JSON structure into a signals DataFrame."""
    if "samples" not in imu_json or len(imu_json["samples"]) == 0:
        raise ValueError(
            f"IMU JSON for '{sensor_location}' is empty or missing 'samples' key."
        )

    df = pd.DataFrame(imu_json["samples"])

    missing = set(COLUMN_MAPPING.keys()) - set(df.columns)
    if missing:
        raise ValueError(
            f"IMU JSON for '{sensor_location}' is missing columns: {missing}"
        )

    df = df.rename(columns=COLUMN_MAPPING)
    df = df.sort_values("sample_idx").reset_index(drop=True)

    df["time"] = df.index * SAMPLE_PERIOD_S
    df["sensor_location"] = sensor_location

    return df[SIGNAL_COLUMNS + ["time", "sensor_location"]]


def wrangle(imu1_json: dict, imu2_json: dict) -> pd.DataFrame:
    """Convert imu1 and imu2 JSON structures into a single signals DataFrame."""
    foot_df = _build_imu_dataframe(imu1_json, "foot")
    shank_df = _build_imu_dataframe(imu2_json, "shank")

    min_rows = min(len(foot_df), len(shank_df))
    foot_df = foot_df.iloc[:min_rows].reset_index(drop=True)
    shank_df = shank_df.iloc[:min_rows].reset_index(drop=True)

    time_values = np.arange(min_rows) * SAMPLE_PERIOD_S
    foot_df["time"] = time_values
    shank_df["time"] = time_values

    signals_df = pd.concat([foot_df, shank_df], ignore_index=True)
    return signals_df


# ---------------------------------------------------------------------------
# Stage 2 — Butterworth Lowpass Filtering
# ---------------------------------------------------------------------------

def _butter_lowpass(data: np.ndarray) -> np.ndarray:
    """Apply a 2nd-order Butterworth lowpass filter."""
    nyq = 0.5 * SAMPLE_RATE_HZ
    wn = FILTER_CUTOFF_HZ / nyq
    b, a = butter(FILTER_ORDER, wn, btype="low")
    return filtfilt(b, a, data)


def filter_signals(signals_df: pd.DataFrame) -> pd.DataFrame:
    """Apply the lowpass filter to all six signal channels for each sensor."""
    filtered_df = signals_df.copy()

    for location, group in filtered_df.groupby("sensor_location"):
        for col in SIGNAL_COLUMNS:
            filtered_df.loc[group.index, col] = _butter_lowpass(group[col].values)

    return filtered_df


# ---------------------------------------------------------------------------
# Stage 3 — Roll and Pitch Computation
# ---------------------------------------------------------------------------

def _compute_roll_pitch(
    acc_x: np.ndarray,
    acc_y: np.ndarray,
    acc_z: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute roll and pitch angles in degrees from accelerometer data."""
    roll_deg = np.degrees(np.arctan2(acc_y, acc_z))
    pitch_deg = np.degrees(np.arctan2(-acc_x, np.sqrt(acc_y ** 2 + acc_z ** 2)))
    return roll_deg, pitch_deg


def extract_features(signals_df: pd.DataFrame) -> pd.DataFrame:
    """Add roll and pitch columns to the signals DataFrame."""
    featured_df = signals_df.copy()
    featured_df["roll"] = 0.0
    featured_df["pitch"] = 0.0

    for location, group in featured_df.groupby("sensor_location"):
        roll, pitch = _compute_roll_pitch(
            group["acc_x"].values,
            group["acc_y"].values,
            group["acc_z"].values,
        )
        featured_df.loc[group.index, "roll"] = roll
        featured_df.loc[group.index, "pitch"] = pitch

    return featured_df


# ---------------------------------------------------------------------------
# Stage 4 — Rep Segmentation and Normalization
# ---------------------------------------------------------------------------

def _find_rep_boundaries(pitch_signal: np.ndarray) -> list[tuple[int, int]]:
    """Detect rep boundaries from pitch peaks."""
    peaks, _ = find_peaks(
        pitch_signal,
        distance=PEAK_MIN_DISTANCE,
        prominence=PEAK_MIN_PROMINENCE,
    )

    boundaries = []
    for i in range(len(peaks) - 1):
        boundaries.append((peaks[i], peaks[i + 1]))

    return boundaries


def _normalize_rep(rep_df: pd.DataFrame) -> pd.DataFrame:
    """Normalize each signal channel in a rep using its first N samples as baseline."""
    rep_out = rep_df.copy()

    for feature in FEATURES_TO_NORMALIZE:
        signal = rep_out[feature].values

        if len(signal) >= BASELINE_SAMPLES:
            baseline = np.mean(signal[:BASELINE_SAMPLES])
        else:
            baseline = signal[0] if len(signal) > 0 else 0.0

        if baseline != 0:
            rep_out[f"{feature}_norm"] = signal / baseline
        else:
            max_val = np.max(np.abs(signal))
            rep_out[f"{feature}_norm"] = signal / max_val if max_val != 0 else signal

    return rep_out


def segment(featured_df: pd.DataFrame) -> pd.DataFrame:
    """Segment the full session into individual reps for foot and shank sensors."""
    foot_df = featured_df[featured_df["sensor_location"] == "foot"].reset_index(drop=True)
    shank_df = featured_df[featured_df["sensor_location"] == "shank"].reset_index(drop=True)

    boundaries = _find_rep_boundaries(foot_df["pitch"].values)

    if len(boundaries) == 0:
        raise ValueError(
            "No rep boundaries detected. Check signal quality or peak detection parameters."
        )

    segmented_rows = []

    signal_fields = (
        SIGNAL_COLUMNS
        + ["roll", "pitch"]
        + [f"{f}_norm" for f in FEATURES_TO_NORMALIZE]
    )

    for rep_num, (start_idx, end_idx) in enumerate(boundaries, start=1):
        foot_rep = _normalize_rep(foot_df.iloc[start_idx:end_idx + 1].copy())

        start_time = foot_rep["time"].iloc[0]
        end_time = foot_rep["time"].iloc[-1]
        shank_rep = shank_df[
            (shank_df["time"] >= start_time) &
            (shank_df["time"] <= end_time)
        ].copy()

        if not shank_rep.empty:
            shank_rep = _normalize_rep(shank_rep)

        foot_row = {"sensor_location": "foot", "rep": rep_num}
        foot_row["time"] = foot_rep["time"].values
        for col in signal_fields:
            foot_row[col] = foot_rep[col].values
        segmented_rows.append(foot_row)

        if not shank_rep.empty:
            shank_row = {"sensor_location": "shank", "rep": rep_num}
            shank_row["time"] = shank_rep["time"].values
            for col in signal_fields:
                shank_row[col] = shank_rep[col].values
            segmented_rows.append(shank_row)

    segmented_df = pd.DataFrame(segmented_rows)
    segmented_df = segmented_df.sort_values(["rep", "sensor_location"]).reset_index(
        drop=True
    )

    return segmented_df


# ---------------------------------------------------------------------------
# Stage 5 — Statistical Feature Extraction
# ---------------------------------------------------------------------------

def _extract_rep_statistical_features(row: pd.Series) -> np.ndarray:
    """Extract 64 statistical features from a single segmented rep row."""
    features = []

    for col in STATISTICAL_FEATURE_COLS:
        signal = row[col]
        features.append(np.mean(signal))
        features.append(np.std(signal))
        features.append(np.min(signal))
        features.append(np.max(signal))
        features.append(np.max(signal) - np.min(signal))
        features.append(np.median(signal))

        if len(signal) > 1:
            features.append(np.percentile(signal, 25))
            features.append(np.percentile(signal, 75))
        else:
            features.append(0.0)
            features.append(0.0)

    return np.array(features)


def extract_statistical_features(
    segmented_df: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Extract statistical features from all reps for both foot and shank sensors.

    Returns:
        (X, rep_indices, sensor_locations) where X is (n_samples, 64)
    """
    X_list = []
    rep_list = []
    location_list = []

    for _, row in segmented_df.iterrows():
        X_list.append(_extract_rep_statistical_features(row))
        rep_list.append(row["rep"])
        location_list.append(row["sensor_location"])

    return np.array(X_list), np.array(rep_list), np.array(location_list)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def preprocess_session(
    readings: list[SensorReading],
) -> dict:
    """
    Execute the full preprocessing pipeline on a buffer of SensorReadings.

    Returns:
        {
            "imu1_json": dict,
            "imu2_json": dict,
            "segmented_df": pd.DataFrame,
            "X": np.ndarray (n_samples x 64),
            "rep_indices": np.ndarray,
            "sensor_locations": np.ndarray,
        }
    """
    # Stage 0: Convert buffer to IMU JSON format
    imu1_json = sensor_readings_to_imu_json(readings, "imu1")
    imu2_json = sensor_readings_to_imu_json(readings, "imu2")

    # Stage 1: Wrangle into aligned DataFrames
    signals_df = wrangle(imu1_json, imu2_json)

    # Stage 2: Butterworth lowpass filtering
    filtered_df = filter_signals(signals_df)

    # Stage 3: Roll and pitch computation
    featured_df = extract_features(filtered_df)

    # Stage 4: Rep segmentation with normalization
    segmented_df = segment(featured_df)

    # Stage 5: Statistical feature extraction
    X, rep_indices, sensor_locations = extract_statistical_features(segmented_df)

    return {
        "imu1_json": imu1_json,
        "imu2_json": imu2_json,
        "segmented_df": segmented_df,
        "X": X,
        "rep_indices": rep_indices,
        "sensor_locations": sensor_locations,
    }
