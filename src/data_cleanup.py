import os
import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, "..")
RAW_META_PATH = os.path.join(PROJECT_DIR, "results/raw_metadata.csv")
RAW_SIGNALS_PATH = os.path.join(PROJECT_DIR, "results/raw_signals.csv")

def butter_filter(data, fs=100, f_low=None, f_high=None, filter_type="lowpass", order=2):
    """
    Apply Butterworth filter to data
    """
    
    nyq = 0.5 * fs

    if filter_type == "lowpass":
        assert f_high is not None, "Provide f_high for lowpass"
        wn = f_high / nyq
        b, a = butter(order, wn, btype="low")

    elif filter_type == "highpass":
        assert f_low is not None, "Provide f_low for highpass"
        wn = f_low / nyq
        b, a = butter(order, wn, btype="high")

    elif filter_type == "bandpass":
        assert f_low is not None and f_high is not None, "Provide f_low and f_high for bandpass"
        wn = [f_low / nyq, f_high / nyq]
        b, a = butter(order, wn, btype="band")

    else:
        raise ValueError("filter_type must be 'lowpass', 'highpass', or 'bandpass'")

    return filtfilt(b, a, data)

def cleanup_signals(df):
    """
    Clean IMU signal dataframe:
    - Remove rows with negative time
    - Mark synthetic rows where any signal value is NaN
    """
    df = df.sort_values("time").reset_index(drop=True)

    # Remove negative time rows
    df = df[df["time"] >= 0].copy()

    # Determine synthetic rows: 1 if any signal value is NaN, else 0
    signal_cols = ["acc_x", "acc_y", "acc_z", "gyr_x", "gyr_y", "gyr_z"]
    df["synthetic"] = df[signal_cols].isna().any(axis=1).astype(int)

    return df

def filter_metadata(meta_df):
    """
    Filter metadata dataframe to remove bad data
    """
    rows_to_remove = [
        {"subject_id": 1, "date": "10_28_25", "exercise": "Ankle Rotation", "set": "10_slow_CW", "sensor_location": "shank"},
        {"subject_id": 2, "date": "10_30_25", "exercise": "Ankle Rotation", "set": "10_slow_CW", "sensor_location": "shank"},
        {"subject_id": 2, "date": "10_30_25", "exercise": "Ankle Rotation", "set": "10_slow_CCW", "sensor_location": "shank"},
        {"subject_id": 2, "date": "10_30_25", "exercise": "Heel Walk", "set": "toe_low", "sensor_location": "shank"},
        {"subject_id": 2, "date": "10_30_25", "exercise": "Heel Walk", "set": "toe_low", "sensor_location": "foot"},
        {"subject_id": 3, "date": "10_30_25", "exercise": "Knee to Wall", "set": "default", "sensor_location": "foot"},
        {"subject_id": 6, "date": "10_31_25", "exercise": "Ankle Rotation", "set": "10_fast_CW", "sensor_location": "shank"},
        {"subject_id": 6, "date": "10_31_25", "exercise": "Ankle Rotation", "set": "10_fast_CW", "sensor_location": "foot"},
        {"subject_id": 6, "date": "10_31_25", "exercise": "Ankle Rotation", "set": "10_fast_CCW", "sensor_location": "shank"},
        {"subject_id": 6, "date": "10_31_25", "exercise": "Ankle Rotation", "set": "10_fast_CCW", "sensor_location": "foot"},
        {"subject_id": 8, "date": "10_31_25", "exercise": "Calf Raises", "set": "10_slow", "sensor_location": "shank"},
        {"subject_id": 8, "date": "10_31_25", "exercise": "Calf Raises", "set": "10_slow", "sensor_location": "foot"},
        {"subject_id": 11, "date": "11_04_25", "exercise": "Ankle Rotation", "set": "10_slow_CCW", "sensor_location": "shank"},
        {"subject_id": 11, "date": "11_04_25", "exercise": "Ankle Rotation", "set": "10_slow_CCW", "sensor_location": "foot"},
        {"subject_id": 14, "date": "11_04_25", "exercise": "Ankle Rotation", "set": "10_slow_CW", "sensor_location": "shank"},
        {"subject_id": 14, "date": "11_04_25", "exercise": "Ankle Rotation", "set": "10_slow_CW", "sensor_location": "foot"},
        {"subject_id": 14, "date": "11_04_25", "exercise": "Ankle Rotation", "set": "10_fast_CW", "sensor_location": "shank"},
        {"subject_id": 14, "date": "11_04_25", "exercise": "Ankle Rotation", "set": "10_fast_CW", "sensor_location": "foot"},
        {"subject_id": 14, "date": "11_04_25", "exercise": "Ankle Rotation", "set": "10_slow_CCW", "sensor_location": "shank"},
        {"subject_id": 14, "date": "11_04_25", "exercise": "Ankle Rotation", "set": "10_slow_CCW", "sensor_location": "foot"},
        {"subject_id": 14, "date": "11_04_25", "exercise": "Ankle Rotation", "set": "10_fast_CCW", "sensor_location": "shank"},
        {"subject_id": 14, "date": "11_04_25", "exercise": "Ankle Rotation", "set": "10_fast_CCW", "sensor_location": "foot"},
        {"subject_id": 14, "date": "11_04_25", "exercise": "Knee to Wall", "set": "default", "sensor_location": "shank"},
        {"subject_id": 14, "date": "11_04_25", "exercise": "Knee to Wall", "set": "default", "sensor_location": "foot"},
        {"subject_id": 19, "date": "11_07_25", "exercise": "Heel Walk", "set": "toe_high", "sensor_location": "shank"},
        {"subject_id": 19, "date": "11_07_25", "exercise": "Heel Walk", "set": "toe_high", "sensor_location": "foot"},
        {"subject_id": 20, "date": "11_07_25", "exercise": "Calf Raises", "set": "10_slow", "sensor_location": "shank"},
        {"subject_id": 20, "date": "11_07_25", "exercise": "Calf Raises", "set": "10_slow", "sensor_location": "foot"},
        {"subject_id": 23, "date": "11_11_25", "exercise": "Calibration", "set": "default", "sensor_location": "shank"},
        {"subject_id": 23, "date": "11_11_25", "exercise": "Calibration", "set": "default", "sensor_location": "foot"},
    ]
    
    filtered_df = meta_df.copy()
    for row in rows_to_remove:
        mask = ~(
            (filtered_df["subject_id"] == row["subject_id"]) &
            (filtered_df["date"] == row["date"]) &
            (filtered_df["exercise"] == row["exercise"]) &
            (filtered_df["set"] == row["set"]) &
            (filtered_df["sensor_location"] == row["sensor_location"])
        )
        filtered_df = filtered_df[mask]

    return filtered_df.reset_index(drop=True)

def create_clean_datasets(apply_filter=True):
    """
    Process raw metadata and signal data:
    - Remove negative times
    - Mark synthetic rows
    - Filter data
    Returns cleaned metadata and signals dataframes
    """
    raw_meta_df = pd.read_csv(RAW_META_PATH)
    raw_meta_df = filter_metadata(raw_meta_df)

    raw_signals_df = pd.read_csv(RAW_SIGNALS_PATH)

    clean_metadata_rows = []
    clean_signals_rows = []

    for idx, row in raw_meta_df.iterrows():
        file_path = row["file_path"]
        signals = raw_signals_df[raw_signals_df["file_path"] == file_path].copy()

        if signals.empty:
            continue

        # Step 1: Remove negative time and mark synthetic rows
        cleaned = cleanup_signals(signals)

        # Step 2: Apply filtering
        if apply_filter:
            signal_cols = ["acc_x", "acc_y", "acc_z", "gyr_x", "gyr_y", "gyr_z"]
            for col in signal_cols:
                cleaned[col] = butter_filter(
                    cleaned[col].values, 
                    fs=100, 
                    f_low=None, 
                    f_high=1, 
                    filter_type="lowpass", 
                    order=2
                )

        # Keep metadata
        clean_metadata_rows.append(row.to_dict())

        # Add metadata columns to signals
        cleaned["subject_id"] = row["subject_id"]
        cleaned["date"] = row["date"]
        cleaned["exercise"] = row["exercise"]
        cleaned["set"] = row["set"]
        cleaned["sensor_location"] = row["sensor_location"]
        cleaned["file_path"] = row["file_path"]

        clean_signals_rows.append(cleaned)

    clean_metadata = pd.DataFrame(clean_metadata_rows)
    clean_signals = pd.concat(clean_signals_rows, ignore_index=True)

    return clean_metadata, clean_signals


if __name__ == "__main__":
    clean_metadata, clean_signals = create_clean_datasets(apply_filter=True)

    clean_metadata.to_csv("results/clean_metadata.csv", index=False)
    clean_signals.to_csv("results/clean_signals.csv", index=False)
