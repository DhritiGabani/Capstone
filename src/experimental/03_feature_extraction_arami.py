import os
import pandas as pd
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, "..", "..")
RAW_SIGNALS_PATH = os.path.join(PROJECT_DIR, "results/clean_signals.csv")

def roll_pitch_from_acc(acc_x, acc_y, acc_z, exercise):
    """
    Compute roll and pitch in degrees from accelerometer data
    """
    roll = np.arctan2(acc_y, acc_z)
    pitch = np.arctan2(-acc_x, np.sqrt(acc_y**2 + acc_z**2))

    roll_deg = np.degrees(roll)
    pitch_deg = np.degrees(pitch)

    if exercise == 'Heel Walk':
        roll_rad = np.radians(roll_deg)
        roll_unwrapped = np.unwrap(roll_rad)
        roll_deg = np.degrees(roll_unwrapped)

    return roll_deg, pitch_deg

def extract_features(df):
    """
    Add features to the signals dataframe
    """
    # Compute roll and pitch
    # roll, pitch = roll_pitch_from_acc(df['acc_x'].values, df['acc_y'].values, df['acc_z'].values, df['exercise'])
    # df['roll'] = roll
    # df['pitch'] = pitch

    df['roll'] = 0.0
    df['pitch'] = 0.0

    for exercise, group in df.groupby('exercise'):
        roll, pitch = roll_pitch_from_acc(
            group['acc_x'].values,
            group['acc_y'].values,
            group['acc_z'].values,
            exercise
        )
        df.loc[group.index, 'roll'] = roll
        df.loc[group.index, 'pitch'] = pitch

    return df

if __name__ == "__main__":
    signals_df = pd.read_csv(RAW_SIGNALS_PATH)

    signals_with_features = extract_features(signals_df)

    signals_with_features.to_csv("results/clean_signals_with_features.csv", index=False)
