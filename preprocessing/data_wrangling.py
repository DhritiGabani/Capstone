import os
import re
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "dataset")

EXPECTED_STEP = 0.01


def extract_subject_id(subject_folder):
    """Extract 3-digit subject ID from folder name: Subject_001_Name → 001."""
    match = re.search(r"Subject_(\d{3})", subject_folder)
    return match.group(1) if match else None


def extract_set(exercise, filename):
    """Extract the set number from MT_012002CC-[set]-000_...txt based on exercise rules."""
    if exercise in ["Calibration", "Knee to Wall"]:
        return "default"

    match = re.search(r"MT_012002CC[-_](\d{3})[-_]", filename)
    if not match:
        return None
    set_num = match.group(1)

    if exercise == "Ankle Rotation":
        mapping = {
            "000": "10_slow_CW",
            "001": "10_fast_CW",
            "002": "10_slow_CCW",
            "003": "10_fast_CCW"
        }
        return mapping.get(set_num, set_num)

    elif exercise == "Calf Raises":
        mapping = {
            "000": "10_slow",
            "001": "10_fast"
        }
        return mapping.get(set_num, set_num)

    elif exercise == "Heel Walk":
        mapping = {
            "000": "toe_high",
            "001": "toe_low"
        }
        return mapping.get(set_num, set_num)

    return set_num


def extract_sensor_location(filename):
    """Determine if IMU corresponds to foot or shank using last 2 characters before .txt."""

    match = re.search(r"([A-Za-z0-9]{2})\.txt$", filename)
    if not match:
        return None

    code = match.group(1).upper()

    foot_codes = {"7C", "EE", "E6"}
    shank_codes = {"EC", "EF", "7B"}

    if code in foot_codes:
        return "foot"
    if code in shank_codes:
        return "shank"

    return "unknown"


def load_signals_from_txt(filepath):
    """Load IMU signals from .txt file, ignoring comment rows beginning with //."""
    rows = []
    with open(filepath, "r") as f:
        for line in f:
            if line.startswith("//"):
                continue
            rows.append(line)

    if not rows:
        return pd.DataFrame()

    header = [h.strip() for h in rows[0].strip().split(",")]

    cols_needed = ["PacketCounter", "Acc_X",
                   "Acc_Y", "Acc_Z", "Gyr_X", "Gyr_Y", "Gyr_Z"]

    indices = {}
    for col in cols_needed:
        try:
            indices[col] = header.index(col)
        except ValueError:
            raise ValueError(
                f"Column '{col}' not found in {filepath}. Header: {header}")

    data = []
    for row in rows[1:]:
        parts = row.strip().split(",")
        data.append([parts[indices[c]] for c in cols_needed])

    df = pd.DataFrame(data, columns=[
        "packet_counter", "acc_x", "acc_y", "acc_z",
        "gyr_x", "gyr_y", "gyr_z"
    ])

    df = df.apply(pd.to_numeric, errors="coerce")

    if not df.empty:
        first_packet = df["packet_counter"].iloc[0]
        df["time"] = (df["packet_counter"] - first_packet) / 100.0

        time_diff = df["time"].diff()
        gap_rows = time_diff > (EXPECTED_STEP + 1e-9)

        cols_to_nan = ["acc_x", "acc_y", "acc_z", "gyr_x", "gyr_y", "gyr_z"]
        df.loc[gap_rows, cols_to_nan] = float("nan")

    return df


def create_metadata_and_signals(base_path=DATA_DIR):
    metadata_rows = []
    signals_rows = []

    for subject_folder in os.listdir(base_path):
        if subject_folder == "Subject_template":
            continue
        if not subject_folder.startswith("Subject_"):
            continue

        subject_id = extract_subject_id(subject_folder)
        subject_path = os.path.join(base_path, subject_folder)

        for date_folder in os.listdir(subject_path):
            date_path = os.path.join(subject_path, date_folder)
            if not os.path.isdir(date_path):
                continue

            # Check for all exercise folders, including "Heel Walking" variant
            for exercise in ["Ankle Rotation", "Calf Raises", "Calibration", "Heel Walk", "Heel Walking", "Knee to Wall"]:
                exercise_path = os.path.join(date_path, exercise)
                if not os.path.exists(exercise_path):
                    continue

                # Normalize "Heel Walking" to "Heel Walk" for consistency
                exercise_normalized = "Heel Walk" if exercise == "Heel Walking" else exercise

                for file in os.listdir(exercise_path):
                    if not file.endswith(".txt"):
                        continue
                    if file.lower() == "note.txt":
                        continue

                    filepath = os.path.join(exercise_path, file)

                    set_label = extract_set(exercise_normalized, file)
                    sensor_location = extract_sensor_location(file)

                    metadata_rows.append({
                        "subject_id": subject_id,
                        "date": date_folder,
                        "exercise": exercise_normalized,
                        "set": set_label,
                        "sensor_location": sensor_location,
                        "file_path": filepath
                    })

                    df_signals = load_signals_from_txt(filepath)
                    df_signals["subject_id"] = subject_id
                    df_signals["date"] = date_folder
                    df_signals["exercise"] = exercise_normalized
                    df_signals["set"] = set_label
                    df_signals["sensor_location"] = sensor_location
                    df_signals["file_path"] = filepath

                    signals_rows.append(df_signals)

    metadata_df = pd.DataFrame(metadata_rows)
    signals_df = pd.concat(signals_rows, ignore_index=True)

    return metadata_df, signals_df


if __name__ == "__main__":
    raw_meta_df, raw_signals_df = create_metadata_and_signals()

    raw_meta_df.to_csv("results/raw_metadata.csv", index=False)
    raw_signals_df.to_csv("results/raw_signals.csv")
