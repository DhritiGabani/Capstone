import os
import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, "..", "..")
RAW_META_PATH = os.path.join(PROJECT_DIR, "results/raw_metadata_mika.csv")
RAW_SIGNALS_PATH = os.path.join(PROJECT_DIR, "results/raw_signals_mika.csv")

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

def create_clean_datasets(apply_filter=True):
    """
    Process raw metadata and signal data:
    - Filter data
    """
    raw_meta_df = pd.read_csv(RAW_META_PATH)

    raw_signals_df = pd.read_csv(RAW_SIGNALS_PATH)

    clean_metadata_rows = []
    clean_signals_rows = []

    for idx, row in raw_meta_df.iterrows():
        file_path = row["file_path"]
        signals = raw_signals_df[raw_signals_df["file_path"] == file_path].copy()

        if signals.empty:
            continue

        # Apply filtering
        if apply_filter:
            signal_cols = ["acc_x", "acc_y", "acc_z", "gyr_x", "gyr_y", "gyr_z"]
            for col in signal_cols:
                signals[col] = butter_filter(
                    signals[col].values, 
                    fs=100, 
                    f_low=None, 
                    f_high=2, 
                    filter_type="lowpass", 
                    order=2
                )

        # Keep metadata
        clean_metadata_rows.append(row.to_dict())

        # Add metadata columns to signals
        signals["subject_id"] = row["subject_id"]
        signals["date"] = row["date"]
        signals["exercise"] = row["exercise"]
        signals["set"] = row["set"]
        signals["sensor_location"] = row["sensor_location"]
        signals["file_path"] = row["file_path"]

        clean_signals_rows.append(signals)

    clean_metadata = pd.DataFrame(clean_metadata_rows)
    clean_signals = pd.concat(clean_signals_rows, ignore_index=True)

    return clean_metadata, clean_signals

if __name__ == "__main__":
    clean_metadata, clean_signals = create_clean_datasets(apply_filter=True)

    clean_metadata.to_csv("results/clean_metadata_mika.csv", index=False)
    clean_signals.to_csv("results/clean_signals_mika.csv", index=False)
