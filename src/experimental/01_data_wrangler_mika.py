import os
import re
import pandas as pd
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "..", "data_mika")

EXPECTED_STEP = 0.01

def extract_subject_id(subject_folder):
    """Extract 3-digit subject ID from folder name: Subject_001_Name → 001."""
    match = re.search(r"Subject_(\d{3})", subject_folder)
    return int(match.group(1)) if match else None

def load_signals_from_csv(filepath):
    """
    Load IMU signals from .csv file.
    """
    df = pd.read_csv(filepath)
    
    required_cols = ['t_host_s', 'device', 't_dev_us', 'ax_g', 'ay_g', 'az_g', 'gx_dps', 'gy_dps', 'gz_dps']
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns {missing_cols} in {filepath}")
    
    imu1_df = df[df['device'] == 'imu1'].copy() # foot
    imu2_df = df[df['device'] == 'imu2'].copy() # shank
    
    min_rows = min(len(imu1_df), len(imu2_df))
    
    if min_rows == 0:
        return pd.DataFrame(), pd.DataFrame()
    
    imu1_df = imu1_df.iloc[:min_rows].reset_index(drop=True)
    imu2_df = imu2_df.iloc[:min_rows].reset_index(drop=True)
    
    column_mapping = {
        'ax_g': 'acc_x',
        'ay_g': 'acc_y',
        'az_g': 'acc_z',
        'gx_dps': 'gyr_x',
        'gy_dps': 'gyr_y',
        'gz_dps': 'gyr_z'
    }
    
    imu1_df = imu1_df.rename(columns=column_mapping)
    imu2_df = imu2_df.rename(columns=column_mapping)
    
    time_values = np.arange(min_rows) * EXPECTED_STEP
    
    imu1_df['time'] = time_values
    imu2_df['time'] = time_values
    
    imu1_df['packet_counter'] = (time_values * 100).astype(int)
    imu2_df['packet_counter'] = (time_values * 100).astype(int)
    
    output_cols = ['packet_counter', 'acc_x', 'acc_y', 'acc_z', 'gyr_x', 'gyr_y', 'gyr_z', 'time']
    
    imu1_df = imu1_df[output_cols]
    imu2_df = imu2_df[output_cols]
    
    return imu1_df, imu2_df

def create_metadata_and_signals(base_path=DATA_DIR):
    """
    Create metadata and signals dataframes from MIKA sensor data
    """
    metadata_rows = []
    signals_rows = []
    
    total_files = 0
    processed_files = 0
    
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
            
            for exercise in ["Ankle Rotation", "Calf Raises", "Calibration", "Heel Walk", "Knee to Wall"]:
                exercise_path = os.path.join(date_path, exercise)
                if not os.path.exists(exercise_path):
                    continue
                
                for file in os.listdir(exercise_path):
                    if not file.endswith(".csv"):
                        continue
                    
                    total_files += 1
                    filepath = os.path.join(exercise_path, file)
                    
                    set_label = file.replace('.csv', '')
                    
                    try:
                        imu1_df, imu2_df = load_signals_from_csv(filepath)
                        
                        if imu1_df.empty or imu2_df.empty:
                            print(f"Warning: Empty data for {filepath}")
                            continue
                        
                        foot_filepath = f"{filepath}_imu1"
                        metadata_rows.append({
                            "subject_id": subject_id,
                            "date": date_folder,
                            "exercise": exercise,
                            "set": set_label,
                            "sensor_location": "foot",
                            "file_path": foot_filepath
                        })
                        
                        imu1_df["subject_id"] = subject_id
                        imu1_df["date"] = date_folder
                        imu1_df["exercise"] = exercise
                        imu1_df["set"] = set_label
                        imu1_df["sensor_location"] = "foot"
                        imu1_df["file_path"] = foot_filepath
                        signals_rows.append(imu1_df)
                        
                        shank_filepath = f"{filepath}_imu2"
                        metadata_rows.append({
                            "subject_id": subject_id,
                            "date": date_folder,
                            "exercise": exercise,
                            "set": set_label,
                            "sensor_location": "shank",
                            "file_path": shank_filepath
                        })
                        
                        imu2_df["subject_id"] = subject_id
                        imu2_df["date"] = date_folder
                        imu2_df["exercise"] = exercise
                        imu2_df["set"] = set_label
                        imu2_df["sensor_location"] = "shank"
                        imu2_df["file_path"] = shank_filepath
                        signals_rows.append(imu2_df)
                        
                        processed_files += 1
                    
                    except Exception as e:
                        print(f"Error processing {filepath}: {e}")
                        continue
    
    
    metadata_df = pd.DataFrame(metadata_rows)
    signals_df = pd.concat(signals_rows, ignore_index=True) if signals_rows else pd.DataFrame()
    
    return metadata_df, signals_df

if __name__ == "__main__":
    raw_meta_df, raw_signals_df = create_metadata_and_signals()

    raw_meta_df.to_csv("results/raw_metadata_mika.csv", index=False)
    raw_signals_df.to_csv("results/raw_signals_mika.csv", index=False)