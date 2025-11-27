import os
import pandas as pd
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, "..")
RAW_SIGNALS_PATH = os.path.join(PROJECT_DIR, "results/clean_signals.csv")

def roll_pitch_from_acc(acc_x, acc_y, acc_z):
    """
    Compute roll and pitch in degrees from accelerometer data
    """
    roll = np.arctan2(acc_y, acc_z)
    pitch = np.arctan2(-acc_x, np.sqrt(acc_y**2 + acc_z**2))
    return np.degrees(roll), np.degrees(pitch)

def extract_features(df):
    """
    Add features to the signals dataframe
    """
    # Compute roll and pitch
    roll, pitch = roll_pitch_from_acc(df['acc_x'].values, df['acc_y'].values, df['acc_z'].values)
    df['roll'] = roll
    df['pitch'] = pitch

    return df

if __name__ == "__main__":
    signals_df = pd.read_csv(RAW_SIGNALS_PATH)

    signals_with_features = extract_features(signals_df)

    signals_with_features.to_csv("results/clean_signals_with_features.csv", index=False)
