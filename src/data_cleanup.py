import os
import pandas as pd
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, "..")
RAW_META_PATH = os.path.join(PROJECT_DIR, "raw_metadata.csv")
RAW_SIGNALS_PATH = os.path.join(PROJECT_DIR, "raw_signals.csv")


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

def create_clean_datasets():
    """
    Process raw metadata and signal data:
    - Remove negative times
    - Mark synthetic rows
    Returns cleaned metadata and signals dataframes
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

        # Step 1: Remove negative time and mark synthetic rows
        cleaned = cleanup_signals(signals)

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
    clean_metadata, clean_signals = create_clean_datasets()

    clean_metadata.to_csv("clean_metadata.csv", index=False)
    clean_signals.to_csv("clean_signals.csv", index=False)
