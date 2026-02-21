import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.interpolate import interp1d


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL_PATH         = Path(__file__).parent.parent / "model" / "mlp_model_v3.pkl"
SCALER_PATH        = Path(__file__).parent.parent / "model" / "scaler_v3.pkl"
LABEL_ENCODER_PATH = Path(__file__).parent.parent / "model" / "label_encoder_v3.pkl"

STATISTICAL_FEATURE_COLS = [
    "acc_x_norm", "acc_y_norm", "acc_z_norm",
    "gyr_x_norm", "gyr_y_norm", "gyr_z_norm",
    "roll_norm",  "pitch_norm",
]

CONSISTENCY_EXERCISES = {"Ankle Rotation", "Calf Raises"}
HEEL_WALK_EXERCISE    = "Heel Walk"
MIN_REPS_CONSISTENCY  = 3

# DTW / Matrix Profile normalization target length
NORMALIZED_SIGNAL_LENGTH = 100

# Consistency score weights
CV_WEIGHT  = 0.50
DTW_WEIGHT = 0.30
MP_WEIGHT  = 0.20

# CV feature weights
CV_FEATURE_WEIGHTS = {
    "duration":          0.25,
    "rom_primary":       0.30,
    "rom_secondary":     0.15,
    "peak_velocity":     0.20,
    "mean_acc":          0.05,
    "time_to_peak_norm": 0.05,
}

# Matrix Profile window size
MP_WINDOW_SIZE = 20


# ---------------------------------------------------------------------------
# Stage 1 — Statistical Feature Extraction
# ---------------------------------------------------------------------------

def _extract_rep_statistical_features(row: pd.Series) -> np.ndarray:
    """
    Extract statistical features from a single rep row
    """
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
    Extract statistical features from all reps for both foot and shank sensors
    """
    X_list        = []
    rep_list      = []
    location_list = []

    for _, row in segmented_df.iterrows():
        X_list.append(_extract_rep_statistical_features(row))
        rep_list.append(row["rep"])
        location_list.append(row["sensor_location"])

    return np.array(X_list), np.array(rep_list), np.array(location_list)


# ---------------------------------------------------------------------------
# Stage 2 — Classification
# ---------------------------------------------------------------------------

def _load_model_artifacts() -> tuple:
    """
    Load the trained MLP model, scaler, and label encoder
    """
    for path in [MODEL_PATH, SCALER_PATH, LABEL_ENCODER_PATH]:
        if not path.exists():
            raise FileNotFoundError(
                f"Required model artifact not found: {path}\n"
                "Ensure model.pkl, scaler.pkl, and label_encoder.pkl "
                "are present in the model directory."
            )

    with open(MODEL_PATH,         "rb") as f: model         = pickle.load(f)
    with open(SCALER_PATH,        "rb") as f: scaler        = pickle.load(f)
    with open(LABEL_ENCODER_PATH, "rb") as f: label_encoder = pickle.load(f)

    return model, scaler, label_encoder


def classify(
    X: np.ndarray,
    rep_indices: np.ndarray,
    sensor_locations: np.ndarray,
) -> pd.DataFrame:
    """
    Classify each rep using the trained MLP model
    """
    model, scaler, label_encoder = _load_model_artifacts()

    X_scaled      = scaler.transform(X)
    probabilities = model.predict_proba(X_scaled)
    predicted_idx = np.argmax(probabilities, axis=1)

    predicted_labels = label_encoder.inverse_transform(predicted_idx)
    confidence       = probabilities[np.arange(len(probabilities)), predicted_idx]

    raw_df = pd.DataFrame({
        "rep":                rep_indices,
        "sensor_location":    sensor_locations,
        "predicted_exercise": predicted_labels,
        "confidence":         np.round(confidence, 4),
    })

    results = []

    for rep in sorted(raw_df["rep"].unique()):
        rep_rows = raw_df[raw_df["rep"] == rep]

        foot_rows  = rep_rows[rep_rows["sensor_location"] == "foot"]
        shank_rows = rep_rows[rep_rows["sensor_location"] == "shank"]

        if not foot_rows.empty and not shank_rows.empty:
            foot_row  = foot_rows.iloc[0]
            shank_row = shank_rows.iloc[0]

            if foot_row["predicted_exercise"] == shank_row["predicted_exercise"]:
                results.append({
                    "rep":                int(rep),
                    "predicted_exercise": foot_row["predicted_exercise"],
                    "confidence":         max(foot_row["confidence"], shank_row["confidence"]),
                })
            else:
                winner = (
                    foot_row
                    if foot_row["confidence"] >= shank_row["confidence"]
                    else shank_row
                )
                results.append({
                    "rep":                int(rep),
                    "predicted_exercise": winner["predicted_exercise"],
                    "confidence":         winner["confidence"],
                })
        else:
            row = rep_rows.iloc[0]
            results.append({
                "rep":                int(rep),
                "predicted_exercise": row["predicted_exercise"],
                "confidence":         row["confidence"],
            })

    return pd.DataFrame(results).sort_values("rep").reset_index(drop=True)


def _smooth_classifications(classifications_df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply majority-vote smoothing to correct isolated misclassifications
    at exercise transition boundaries.
    """
    smoothed = classifications_df.copy()
    labels   = smoothed["predicted_exercise"].values

    for i in range(1, len(labels) - 1):
        if labels[i - 1] == labels[i + 1] and labels[i] != labels[i - 1]:
            smoothed.loc[smoothed.index[i], "predicted_exercise"] = labels[i - 1]

    return smoothed


def build_exercise_blocks(
    classifications_df: pd.DataFrame,
    segmented_df: pd.DataFrame,
) -> list[dict]:
    """
    Group consecutive reps with the same predicted exercise into blocks
    and attach the corresponding signal data for each block.
    """
    smoothed = _smooth_classifications(classifications_df)

    blocks           = []
    current_exercise = None
    current_reps     = []

    for _, row in smoothed.iterrows():
        if row["predicted_exercise"] != current_exercise:
            if current_exercise is not None:
                blocks.append({"exercise": current_exercise, "reps": current_reps})
            current_exercise = row["predicted_exercise"]
            current_reps     = [row["rep"]]
        else:
            current_reps.append(row["rep"])

    if current_exercise is not None:
        blocks.append({"exercise": current_exercise, "reps": current_reps})

    for block in blocks:
        rep_mask = segmented_df["rep"].isin(block["reps"])
        block["foot_data"]  = segmented_df[rep_mask & (segmented_df["sensor_location"] == "foot")].copy()
        block["shank_data"] = segmented_df[rep_mask & (segmented_df["sensor_location"] == "shank")].copy()

    return blocks


# ---------------------------------------------------------------------------
# Stage 3 — Rep Counting
# ---------------------------------------------------------------------------

def count_reps(blocks: list[dict]) -> dict[str, int]:
    """
    Count the total number of reps per exercise across all blocks
    """
    counts: dict[str, int] = {}

    for block in blocks:
        exercise = block["exercise"]
        counts[exercise] = counts.get(exercise, 0) + len(block["reps"])

    return counts


# ---------------------------------------------------------------------------
# Stage 4 — Rep Duration
# ---------------------------------------------------------------------------

def calculate_rep_durations(blocks: list[dict]) -> dict[str, dict]:
    """
    Calculate duration for each rep and mean duration per exercise
    """
    exercise_durations: dict[str, list] = {}
    exercise_rep_map:   dict[str, dict] = {}

    for block in blocks:
        exercise  = block["exercise"]
        foot_data = block["foot_data"]

        if exercise not in exercise_durations:
            exercise_durations[exercise] = []
            exercise_rep_map[exercise]   = {}

        for _, row in foot_data.iterrows():
            time_array = row["time"]
            duration   = float(time_array[-1] - time_array[0])
            rep        = int(row["rep"])

            exercise_durations[exercise].append(duration)
            exercise_rep_map[exercise][rep] = round(duration, 3)

    return {
        exercise: {
            "rep_durations_s": exercise_rep_map[exercise],
            "mean_duration_s": round(float(np.mean(exercise_durations[exercise])), 3),
        }
        for exercise in exercise_rep_map
    }


# ---------------------------------------------------------------------------
# Stage 5 — Movement Consistency (Ankle Rotation and Calf Raises only)
# ---------------------------------------------------------------------------

def _extract_kinematic_features(row: pd.Series, exercise: str) -> dict:
    """
    Extract key kinematic features from a single rep for CV calculation.
    """
    if exercise == "Ankle Rotation":
        primary   = row["roll"]
        secondary = row["pitch"]
        peak_vel  = np.max(np.abs(row["gyr_z"]))
    else:  # Calf Raises
        primary   = row["pitch"]
        secondary = row["roll"]
        peak_vel  = np.max(np.abs(row["gyr_y"]))

    time_array = row["time"]
    acc_mag    = np.sqrt(row["acc_x"] ** 2 + row["acc_y"] ** 2 + row["acc_z"] ** 2)
    peak_idx   = int(np.argmax(np.abs(primary)))

    return {
        "duration":          float(time_array[-1] - time_array[0]),
        "rom_primary":       float(np.max(primary) - np.min(primary)),
        "rom_secondary":     float(np.max(secondary) - np.min(secondary)),
        "peak_velocity":     float(peak_vel),
        "mean_acc":          float(np.mean(acc_mag)),
        "time_to_peak_norm": float(peak_idx / len(primary)),
    }


def _calculate_cv_score(foot_data: pd.DataFrame, exercise: str) -> float:
    """
    Calculate Coefficient of Variation consistency score (0-100).
    """
    features_df = pd.DataFrame([
        _extract_kinematic_features(row, exercise)
        for _, row in foot_data.iterrows()
    ])

    cv_values = {}
    for feature in features_df.columns:
        mean_val = features_df[feature].mean()
        std_val  = features_df[feature].std()
        cv_values[feature] = (std_val / abs(mean_val) * 100) if mean_val != 0 else 0.0

    weighted_cv = sum(cv_values[f] * CV_FEATURE_WEIGHTS[f] for f in cv_values)
    return float(100 * np.exp(-weighted_cv / 30))


def _dtw_distance(series1: np.ndarray, series2: np.ndarray) -> float:
    """
    Calculate Dynamic Time Warping distance between two time series.
    """
    n, m       = len(series1), len(series2)
    dtw_matrix = np.full((n + 1, m + 1), np.inf)
    dtw_matrix[0, 0] = 0.0

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = abs(series1[i - 1] - series2[j - 1])
            dtw_matrix[i, j] = cost + min(
                dtw_matrix[i - 1, j],
                dtw_matrix[i, j - 1],
                dtw_matrix[i - 1, j - 1],
            )

    return float(dtw_matrix[n, m])


def _normalize_signal_length(signals: list[np.ndarray]) -> list[np.ndarray]:
    """
    Interpolate all signals to NORMALIZED_SIGNAL_LENGTH for comparison.
    """
    normalized = []
    for signal in signals:
        x_old = np.linspace(0, 1, len(signal))
        x_new = np.linspace(0, 1, NORMALIZED_SIGNAL_LENGTH)
        f     = interp1d(x_old, signal, kind="cubic", fill_value="extrapolate")
        normalized.append(f(x_new))
    return normalized


def _calculate_dtw_score(foot_data: pd.DataFrame, exercise: str) -> float:
    """
    Calculate DTW-based consistency score (0-100).
    """
    signal_col = "roll_norm" if exercise == "Ankle Rotation" else "pitch_norm"
    signals    = _normalize_signal_length([row[signal_col] for _, row in foot_data.iterrows()])

    distances = [
        _dtw_distance(signals[i], signals[j])
        for i in range(len(signals))
        for j in range(i + 1, len(signals))
    ]

    return float(100 * np.exp(-np.mean(distances) / 30))


def _mp_distance(series1: np.ndarray, series2: np.ndarray) -> float:
    """
    Calculate Matrix Profile distance between two normalized time series.
    """
    n1 = len(series1) - MP_WINDOW_SIZE + 1
    n2 = len(series2) - MP_WINDOW_SIZE + 1

    if n1 <= 0 or n2 <= 0:
        return np.inf

    min_distances = []

    for i in range(n1):
        subseq1 = series1[i:i + MP_WINDOW_SIZE]
        subseq1 = (subseq1 - np.mean(subseq1)) / (np.std(subseq1) + 1e-8)

        min_dist = np.inf
        for j in range(n2):
            subseq2 = series2[j:j + MP_WINDOW_SIZE]
            subseq2 = (subseq2 - np.mean(subseq2)) / (np.std(subseq2) + 1e-8)
            dist    = np.sqrt(np.sum((subseq1 - subseq2) ** 2))
            min_dist = min(min_dist, dist)

        min_distances.append(min_dist)

    return float(np.mean(min_distances))


def _calculate_mp_score(foot_data: pd.DataFrame, exercise: str) -> float:
    """
    Calculate Matrix Profile consistency score (0-100).
    """
    signal_col = "roll_norm" if exercise == "Ankle Rotation" else "pitch_norm"
    signals    = _normalize_signal_length([row[signal_col] for _, row in foot_data.iterrows()])
    n_reps     = len(signals)

    mp_distances = np.zeros((n_reps, n_reps))
    for i in range(n_reps):
        for j in range(i + 1, n_reps):
            dist = _mp_distance(signals[i], signals[j])
            mp_distances[i, j] = dist
            mp_distances[j, i] = dist

    mean_dist = float(np.mean(np.mean(mp_distances, axis=1)))
    return float(100 * np.exp(-mean_dist / 15))


def calculate_consistency(blocks: list[dict]) -> dict[str, float | None]:
    """
    Calculate overall three-tier movement consistency score per exercise.
    """
    exercise_foot_data: dict[str, pd.DataFrame] = {}

    for block in blocks:
        exercise = block["exercise"]
        if exercise not in CONSISTENCY_EXERCISES:
            continue
        if exercise not in exercise_foot_data:
            exercise_foot_data[exercise] = block["foot_data"]
        else:
            exercise_foot_data[exercise] = pd.concat(
                [exercise_foot_data[exercise], block["foot_data"]], ignore_index=True
            )

    results = {}

    for exercise, foot_data in exercise_foot_data.items():
        if len(foot_data) < MIN_REPS_CONSISTENCY:
            results[exercise] = None
            continue

        cv_score  = _calculate_cv_score(foot_data, exercise)
        dtw_score = _calculate_dtw_score(foot_data, exercise)
        mp_score  = _calculate_mp_score(foot_data, exercise)

        overall = (
            CV_WEIGHT  * cv_score  +
            DTW_WEIGHT * dtw_score +
            MP_WEIGHT  * mp_score
        )

        results[exercise] = round(float(overall), 2)

    return results


# ---------------------------------------------------------------------------
# Stage 6 — Ankle Angle (Heel Walk only)
# ---------------------------------------------------------------------------

def calculate_ankle_angles(blocks: list[dict]) -> dict | None:
    """
    Calculate max dorsiflexion ankle angle per rep and session mean for Heel Walk.
    """
    heel_walk_foot  = []
    heel_walk_shank = []

    for block in blocks:
        if block["exercise"] == HEEL_WALK_EXERCISE:
            heel_walk_foot.append(block["foot_data"])
            heel_walk_shank.append(block["shank_data"])

    if not heel_walk_foot:
        return None

    foot_df  = pd.concat(heel_walk_foot,  ignore_index=True)
    shank_df = pd.concat(heel_walk_shank, ignore_index=True)

    rep_max_angles = {}

    for _, foot_row in foot_df.iterrows():
        rep = int(foot_row["rep"])

        shank_rows = shank_df[shank_df["rep"] == rep]
        if shank_rows.empty:
            continue
        shank_row = shank_rows.iloc[0]

        foot_pitch         = foot_row["pitch"]
        shank_pitch_interp = np.interp(foot_row["time"], shank_row["time"], shank_row["pitch"])
        ankle_angle        = foot_pitch - shank_pitch_interp

        rep_max_angles[rep] = round(float(np.max(ankle_angle)), 3)

    if not rep_max_angles:
        return None

    return {
        "rep_max_angle_deg":  rep_max_angles,
        "mean_max_angle_deg": round(float(np.mean(list(rep_max_angles.values()))), 3),
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(segmented_df: pd.DataFrame) -> dict:
    """
    Execute the full analysis pipeline.
    """
    X, rep_indices, sensor_locations = extract_statistical_features(segmented_df)
    classifications_df               = classify(X, rep_indices, sensor_locations)
    blocks                           = build_exercise_blocks(classifications_df, segmented_df)

    return {
        "rep_classifications": classifications_df.to_dict(orient="records"),
        "rep_counts":          count_reps(blocks),
        "rep_durations":       calculate_rep_durations(blocks),
        "consistency_scores":  calculate_consistency(blocks),
        "ankle_angles":        calculate_ankle_angles(blocks),
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def save_results_json(results: dict, output_path: str) -> None:
    """
    Serialize the results dictionary to a JSON file for database insertion.

    Parameters
    ----------
    results : dict
        Results dictionary from run().
    output_path : str
        Destination file path for the JSON output.
    """
    import json
    from pathlib import Path

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(out, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to {out}")


if __name__ == "__main__":
    import json
    import pprint
    import importlib
    preprocessing = importlib.import_module("02_preprocessing")

    imu1_path = r"C:\Users\mistr\OneDrive\Documents\Rohan\University\4A\BME 461\model\Capstone\output\imu1_data.json"
    imu2_path = r"C:\Users\mistr\OneDrive\Documents\Rohan\University\4A\BME 461\model\Capstone\output\imu2_data.json"
    output_path = r"C:\Users\mistr\OneDrive\Documents\Rohan\University\4A\BME 461\model\Capstone\output\results.json"

    with open(imu1_path) as f:
        imu1_json = json.load(f)
    with open(imu2_path) as f:
        imu2_json = json.load(f)

    segmented_df = preprocessing.run(imu1_json, imu2_json)
    results      = run(segmented_df)

    pprint.pprint(results)
    save_results_json(results, output_path)
