import os
import pandas as pd
from scipy.signal import find_peaks
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, "..", "..")
CLEAN_SIGNALS_PATH = os.path.join(PROJECT_DIR, "results/clean_signals_with_features_mika.csv")
CLEAN_META_PATH = os.path.join(PROJECT_DIR, "results/clean_metadata_mika.csv")

def find_rep_boundaries(pitch_signal):
    """
    Find rep boundaries based on pitch peaks
    """
    peaks, _ = find_peaks(pitch_signal, distance=30, prominence=15)
    
    boundaries = []
    for i in range(len(peaks) - 1):
        start_idx = peaks[i]
        end_idx = peaks[i + 1]
        boundaries.append((start_idx, end_idx))
    
    return boundaries, peaks

def remove_bad_reps_and_renumber(segmented_df):
    """
    Remove bad reps and renumber remaining reps sequentially
    """
    bad_reps = [
        (3, "Calf Raises", "10_fast", [1]),
        (3, "Heel Walk", "toe_high", [11]),
        (3, "Heel Walk", "toe_low", [2, 5]),
        (4, "Ankle Rotation", "10_fast_CW", [10]),
        (4, "Calf Raises", "10_fast", [10]),
        (4, "Calf Raises", "10_slow", [10]),
        (5, "Ankle Rotation", "10_fast_CCW", [1, 6, 7, 13]),
        (5, "Ankle Rotation", "10_fast_CW", [3, 6]),
        (5, "Ankle Rotation", "10_slow_CCW", [1, 2, 3, 4]),
        (5, "Heel Walk", "toe_high", [1, 2, 3, 4]),
        (6, "Ankle Rotation", "10_fast_CCW", [1, 2, 3, 4]),
        (6, "Calf Raises", "10_fast", [10, 11]),
        (7, "Heel Walk", "toe_low", [5]),
        (8, "Ankle Rotation", "10_fast_CCW", [1, 2, 3]),
        (9, "Calf Raises", "10_fast", [5, 9, 11, 12, 14, 15]),
        (12, "Heel Walk", "toe_low", [17]),
        (13, "Ankle Rotation", "10_fast_CW", [8]),
        (13, "Calf Raises", "10_slow", [10, 11]),
        (14, "Calf Raises", "10_fast", [6]),
        (14, "Heel Walk", "toe_low", [1, 2, 6, 7, 8, 9, 10, 11]),
        (15, "Ankle Rotation", "10_slow_CCW", [1]),
        (15, "Heel Walk", "toe_high", [1, 2, 3, 4, 5, 8, 9, 11, 12, 13, 14]),
        (15, "Heel Walk", "toe_low", [4, 5, 7, 9])
    ]
    
    cleaned_df = segmented_df.copy()
    
    for subject_id, exercise, set_name, reps_to_remove in bad_reps:
        mask = (
            (cleaned_df['subject_id'] == subject_id) &
            (cleaned_df['exercise'] == exercise) &
            (cleaned_df['set'] == set_name) &
            (cleaned_df['rep'].isin(reps_to_remove))
        )
        cleaned_df = cleaned_df[~mask]
    
    renumbered_rows = []
    grouped = cleaned_df.groupby(['subject_id', 'exercise', 'set', 'sensor_location', 'file_path'])
    
    for (subject_id, exercise, set_name, sensor_location, file_path), group in grouped:
        group = group.sort_values('rep')
        
        for new_rep_num, (idx, row) in enumerate(group.iterrows(), start=1):
            row_dict = row.to_dict()
            row_dict['rep'] = new_rep_num
            renumbered_rows.append(row_dict)
    
    cleaned_df = pd.DataFrame(renumbered_rows)
    cleaned_df = cleaned_df.sort_values(['subject_id', 'exercise', 'set', 'sensor_location', 'rep']).reset_index(drop=True)
    
    return cleaned_df

def normalize_rep_data(rep_data, features_to_normalize, n_baseline_samples=5):
    """
    Normalize a rep using its own first N samples as baseline.
    """
    rep_data_copy = rep_data.copy()
    
    for feature in features_to_normalize:
        signal = rep_data_copy[feature].values
        
        if len(signal) >= n_baseline_samples:
            baseline = np.mean(signal[:n_baseline_samples])
        else:
            baseline = signal[0] if len(signal) > 0 else 0
        
        if baseline != 0:
            rep_data_copy[f'{feature}_norm'] = signal / baseline
        else:
            max_val = np.max(np.abs(signal))
            if max_val != 0:
                rep_data_copy[f'{feature}_norm'] = signal / max_val
            else:
                rep_data_copy[f'{feature}_norm'] = signal
    
    return rep_data_copy

def segment_data(signals_df, meta_df):
    """
    Segment the signals dataframe into individual reps with PER-REP normalization.
    """
    segmented_rows = []
    
    foot_files = meta_df[meta_df['sensor_location'] == 'foot']['file_path'].unique()
    
    for file_idx, foot_file in enumerate(foot_files):
        foot_meta = meta_df[meta_df['file_path'] == foot_file].iloc[0]
        
        if foot_meta['exercise'] not in ['Ankle Rotation', 'Calf Raises', 'Heel Walk']:
            continue
        
        foot_data = signals_df[signals_df['file_path'] == foot_file].copy()
        
        if foot_data.empty:
            continue
        
        shank_file = meta_df[
            (meta_df['subject_id'] == foot_meta['subject_id']) &
            (meta_df['date'] == foot_meta['date']) &
            (meta_df['exercise'] == foot_meta['exercise']) &
            (meta_df['set'] == foot_meta['set']) &
            (meta_df['sensor_location'] == 'shank')
        ]['file_path'].values
        
        if len(shank_file) == 0:
            continue
        
        shank_file = shank_file[0]
        shank_data = signals_df[signals_df['file_path'] == shank_file].copy()
        
        boundaries, peaks = find_rep_boundaries(foot_data['pitch'].values)
        
        if len(boundaries) == 0:
            continue
                
        features_to_normalize = ['acc_x', 'acc_y', 'acc_z', 'gyr_x', 'gyr_y', 'gyr_z', 'roll', 'pitch']
        
        for new_rep_num, (start_idx, end_idx) in enumerate(boundaries, start=1):
            foot_rep = foot_data.iloc[start_idx:end_idx+1].copy()
            
            foot_rep = normalize_rep_data(foot_rep, features_to_normalize, n_baseline_samples=5)
            
            start_time = foot_rep['time'].iloc[0]
            end_time = foot_rep['time'].iloc[-1]
            
            shank_rep = shank_data[
                (shank_data['time'] >= start_time) &
                (shank_data['time'] <= end_time)
            ].copy()
            
            if not shank_rep.empty:
                shank_rep = normalize_rep_data(shank_rep, features_to_normalize, n_baseline_samples=5)
            
            foot_row = {
                'subject_id': foot_meta['subject_id'],
                'date': foot_meta['date'],
                'exercise': foot_meta['exercise'],
                'set': foot_meta['set'],
                'sensor_location': 'foot',
                'rep': new_rep_num,
                'time': foot_rep['time'].values,
                'acc_x': foot_rep['acc_x'].values,
                'acc_y': foot_rep['acc_y'].values,
                'acc_z': foot_rep['acc_z'].values,
                'gyr_x': foot_rep['gyr_x'].values,
                'gyr_y': foot_rep['gyr_y'].values,
                'gyr_z': foot_rep['gyr_z'].values,
                'roll': foot_rep['roll'].values,
                'pitch': foot_rep['pitch'].values,
                'acc_x_norm': foot_rep['acc_x_norm'].values,
                'acc_y_norm': foot_rep['acc_y_norm'].values,
                'acc_z_norm': foot_rep['acc_z_norm'].values,
                'gyr_x_norm': foot_rep['gyr_x_norm'].values,
                'gyr_y_norm': foot_rep['gyr_y_norm'].values,
                'gyr_z_norm': foot_rep['gyr_z_norm'].values,
                'roll_norm': foot_rep['roll_norm'].values,
                'pitch_norm': foot_rep['pitch_norm'].values,
                'file_path': foot_file
            }
            segmented_rows.append(foot_row)
            
            if not shank_rep.empty:
                shank_row = {
                    'subject_id': foot_meta['subject_id'],
                    'date': foot_meta['date'],
                    'exercise': foot_meta['exercise'],
                    'set': foot_meta['set'],
                    'sensor_location': 'shank',
                    'rep': new_rep_num,
                    'time': shank_rep['time'].values,
                    'acc_x': shank_rep['acc_x'].values,
                    'acc_y': shank_rep['acc_y'].values,
                    'acc_z': shank_rep['acc_z'].values,
                    'gyr_x': shank_rep['gyr_x'].values,
                    'gyr_y': shank_rep['gyr_y'].values,
                    'gyr_z': shank_rep['gyr_z'].values,
                    'roll': shank_rep['roll'].values,
                    'pitch': shank_rep['pitch'].values,
                    'acc_x_norm': shank_rep['acc_x_norm'].values,
                    'acc_y_norm': shank_rep['acc_y_norm'].values,
                    'acc_z_norm': shank_rep['acc_z_norm'].values,
                    'gyr_x_norm': shank_rep['gyr_x_norm'].values,
                    'gyr_y_norm': shank_rep['gyr_y_norm'].values,
                    'gyr_z_norm': shank_rep['gyr_z_norm'].values,
                    'roll_norm': shank_rep['roll_norm'].values,
                    'pitch_norm': shank_rep['pitch_norm'].values,
                    'file_path': shank_file
                }
                segmented_rows.append(shank_row)
    
    
    segmented_df_initial = pd.DataFrame(segmented_rows)
    segmented_df_cleaned = remove_bad_reps_and_renumber(segmented_df_initial)
        
    return segmented_df_cleaned

if __name__ == "__main__":
    signals_df = pd.read_csv(CLEAN_SIGNALS_PATH)
    meta_df = pd.read_csv(CLEAN_META_PATH)
    
    segmented_signals = segment_data(signals_df, meta_df)
    
    output_path = os.path.join(PROJECT_DIR, "results/segmented_signals_mika.csv")
    segmented_signals.to_csv(output_path, index=False)
