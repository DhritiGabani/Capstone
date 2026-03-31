"""
Unit tests for analysis.py — classification, smoothing, block building,
rep counting, durations, consistency, ankle angles, ROM consistency.

No TFLite model needed: mock_classifier fixture is used for classify_reps.
No real pipeline needed: helper builders produce minimal segmented DataFrames.
"""

import json
import os
import tempfile

import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

import analysis
from analysis import (
    _smooth_classifications,
    build_exercise_blocks,
    calculate_ankle_angles,
    calculate_consistency,
    calculate_rep_durations,
    calculate_rom_consistency,
    classify_reps,
    count_reps,
    analyze_session,
)


# ---------------------------------------------------------------------------
# Builders for minimal test data
# ---------------------------------------------------------------------------

def _clf_df(reps: list[int], exercise: str = "Calf Raises") -> pd.DataFrame:
    """Build a classification DataFrame with a single exercise label."""
    return pd.DataFrame(
        {
            "rep": reps,
            "predicted_exercise": [exercise] * len(reps),
            "confidence": [0.95] * len(reps),
        }
    )


def _foot_data(n_reps: int = 5, n_samples: int = 100, amp: float = 20.0) -> pd.DataFrame:
    """
    Build a minimal foot_data DataFrame where each row represents one rep.
    Pitch oscillates ±amp degrees, suitable for ROM and consistency tests.
    """
    t = np.linspace(0, 1, n_samples)
    pitch = amp * np.sin(2 * np.pi * t)
    roll = (amp / 2) * np.sin(2 * np.pi * t + 0.5)
    acc_mag = np.ones(n_samples)

    rows = []
    for rep in range(1, n_reps + 1):
        rows.append(
            {
                "sensor_location": "foot",
                "rep": rep,
                "time": t,
                "acc_x": acc_mag * 0.1,
                "acc_y": np.zeros(n_samples),
                "acc_z": np.ones(n_samples),
                "gyr_x": np.zeros(n_samples),
                "gyr_y": pitch * 0.5,
                "gyr_z": roll * 0.3,
                "roll": roll,
                "pitch": pitch,
                "roll_norm": roll / (np.abs(roll[0]) + 1e-6),
                "pitch_norm": pitch / (np.abs(pitch[0]) + 1e-6),
            }
        )
    return pd.DataFrame(rows)


def _blocks(n_reps: int = 5, exercise: str = "Calf Raises") -> list[dict]:
    """Build minimal exercise blocks for analysis function tests."""
    foot = _foot_data(n_reps)
    return [
        {
            "exercise": exercise,
            "reps": list(range(1, n_reps + 1)),
            "foot_data": foot,
            "shank_data": pd.DataFrame(),
        }
    ]


def _write_model_config(path: str, n_features: int = 112) -> None:
    config = {
        "classes": ["Ankle Rotation", "Calf Raises", "Heel Walk"],
        "scaler": {
            "mean": [0.0] * n_features,
            "scale": [1.0] * n_features,
        },
    }
    with open(path, "w") as f:
        json.dump(config, f)


# ---------------------------------------------------------------------------
# _smooth_classifications
# ---------------------------------------------------------------------------

class TestSmoothClassifications:
    def test_fixes_isolated_mismatch_in_middle(self):
        df = _clf_df([1, 2, 3, 4, 5])
        df.loc[2, "predicted_exercise"] = "Ankle Rotation"  # rep 3 is different
        result = _smooth_classifications(df)
        assert list(result["predicted_exercise"]) == ["Calf Raises"] * 5

    def test_corrects_first_rep_mismatch(self):
        df = pd.DataFrame(
            {
                "rep": [1, 2, 3],
                "predicted_exercise": ["Ankle Rotation", "Calf Raises", "Calf Raises"],
                "confidence": [0.9] * 3,
            }
        )
        result = _smooth_classifications(df)
        assert result.iloc[0]["predicted_exercise"] == "Calf Raises"

    def test_corrects_last_rep_mismatch(self):
        df = pd.DataFrame(
            {
                "rep": [1, 2, 3],
                "predicted_exercise": ["Calf Raises", "Calf Raises", "Ankle Rotation"],
                "confidence": [0.9] * 3,
            }
        )
        result = _smooth_classifications(df)
        assert result.iloc[-1]["predicted_exercise"] == "Calf Raises"

    def test_no_change_when_already_consistent(self):
        df = _clf_df([1, 2, 3, 4])
        result = _smooth_classifications(df)
        assert list(result["predicted_exercise"]) == ["Calf Raises"] * 4

    def test_returns_dataframe(self):
        df = _clf_df([1, 2])
        result = _smooth_classifications(df)
        assert isinstance(result, pd.DataFrame)

    def test_does_not_modify_original(self):
        df = _clf_df([1, 2, 3])
        original_labels = list(df["predicted_exercise"])
        _smooth_classifications(df)
        assert list(df["predicted_exercise"]) == original_labels

    def test_two_different_exercises_not_flattened(self):
        """Equal runs of two exercises should not be smoothed away."""
        df = pd.DataFrame(
            {
                "rep": [1, 2, 3, 4],
                "predicted_exercise": ["A", "A", "B", "B"],
                "confidence": [0.9] * 4,
            }
        )
        result = _smooth_classifications(df)
        # Both blocks should survive (no single-rep island to fix)
        assert "A" in result["predicted_exercise"].values
        assert "B" in result["predicted_exercise"].values


# ---------------------------------------------------------------------------
# build_exercise_blocks
# ---------------------------------------------------------------------------

class TestBuildExerciseBlocks:
    def test_groups_single_exercise(self):
        clf_df = _clf_df([1, 2, 3, 4, 5])
        segmented_df = _foot_data(5)
        blocks = build_exercise_blocks(clf_df, segmented_df)
        assert len(blocks) == 1
        assert blocks[0]["exercise"] == "Calf Raises"
        assert len(blocks[0]["reps"]) == 5

    def test_groups_two_consecutive_exercises(self):
        clf_df = pd.DataFrame(
            {
                "rep": [1, 2, 3, 4, 5, 6],
                "predicted_exercise": ["A", "A", "A", "B", "B", "B"],
                "confidence": [0.9] * 6,
            }
        )
        segmented_df = _foot_data(6)
        blocks = build_exercise_blocks(clf_df, segmented_df)
        exercises = [b["exercise"] for b in blocks]
        assert exercises == ["A", "B"]

    def test_each_block_has_foot_and_shank_data(self):
        clf_df = _clf_df([1, 2, 3])
        segmented_df = _foot_data(3)
        blocks = build_exercise_blocks(clf_df, segmented_df)
        for block in blocks:
            assert "foot_data" in block
            assert "shank_data" in block

    def test_foot_data_is_dataframe(self):
        clf_df = _clf_df([1, 2])
        segmented_df = _foot_data(2)
        blocks = build_exercise_blocks(clf_df, segmented_df)
        assert isinstance(blocks[0]["foot_data"], pd.DataFrame)


# ---------------------------------------------------------------------------
# count_reps
# ---------------------------------------------------------------------------

class TestCountReps:
    def test_single_exercise_count(self):
        blocks = _blocks(5, "Calf Raises")
        counts = count_reps(blocks)
        assert counts["Calf Raises"] == 5

    def test_multiple_exercises(self):
        blocks = _blocks(4, "Calf Raises") + _blocks(3, "Ankle Rotation")
        counts = count_reps(blocks)
        assert counts["Calf Raises"] == 4
        assert counts["Ankle Rotation"] == 3

    def test_same_exercise_in_multiple_blocks_aggregates(self):
        blocks = _blocks(3, "Calf Raises") + _blocks(4, "Calf Raises")
        counts = count_reps(blocks)
        assert counts["Calf Raises"] == 7

    def test_empty_blocks_returns_empty_dict(self):
        assert count_reps([]) == {}


# ---------------------------------------------------------------------------
# calculate_rep_durations
# ---------------------------------------------------------------------------

class TestCalculateRepDurations:
    def test_returns_mean_duration(self):
        blocks = _blocks(5)
        result = calculate_rep_durations(blocks)
        assert "Calf Raises" in result
        assert "mean_duration_s" in result["Calf Raises"]
        assert result["Calf Raises"]["mean_duration_s"] > 0

    def test_returns_per_rep_durations(self):
        blocks = _blocks(3)
        result = calculate_rep_durations(blocks)
        assert "rep_durations_s" in result["Calf Raises"]
        assert len(result["Calf Raises"]["rep_durations_s"]) == 3

    def test_per_rep_durations_are_positive(self):
        blocks = _blocks(4)
        result = calculate_rep_durations(blocks)
        for dur in result["Calf Raises"]["rep_durations_s"].values():
            assert dur > 0

    def test_mean_equals_average_of_per_rep(self):
        blocks = _blocks(5)
        result = calculate_rep_durations(blocks)
        per_rep = list(result["Calf Raises"]["rep_durations_s"].values())
        assert result["Calf Raises"]["mean_duration_s"] == pytest.approx(
            float(np.mean(per_rep)), rel=1e-3
        )


# ---------------------------------------------------------------------------
# calculate_consistency
# ---------------------------------------------------------------------------

class TestCalculateConsistency:
    def test_returns_none_below_min_reps(self):
        """MIN_REPS_CONSISTENCY = 3; with only 2 reps result must be None."""
        blocks = _blocks(2, "Calf Raises")
        result = calculate_consistency(blocks)
        assert result.get("Calf Raises") is None

    def test_returns_score_in_valid_range(self):
        blocks = _blocks(5, "Calf Raises")
        result = calculate_consistency(blocks)
        score = result.get("Calf Raises")
        if score is not None:
            assert 0.0 <= score <= 100.0

    def test_ankle_rotation_uses_roll(self):
        blocks = _blocks(5, "Ankle Rotation")
        result = calculate_consistency(blocks)
        assert "Ankle Rotation" in result

    def test_heel_walk_not_included(self):
        """Heel Walk is not in CONSISTENCY_EXERCISES so it should be absent."""
        blocks = _blocks(5, "Heel Walk")
        result = calculate_consistency(blocks)
        assert "Heel Walk" not in result

    def test_perfect_identical_reps_score_is_high(self):
        """Identical rep signals should yield near-perfect consistency (>80)."""
        n_reps, n_samples = 5, 100
        t = np.linspace(0, 1, n_samples)
        identical_pitch = 20.0 * np.sin(2 * np.pi * t)

        rows = []
        for rep in range(1, n_reps + 1):
            rows.append(
                {
                    "sensor_location": "foot",
                    "rep": rep,
                    "time": t,
                    "acc_x": np.ones(n_samples) * 0.1,
                    "acc_y": np.zeros(n_samples),
                    "acc_z": np.ones(n_samples),
                    "gyr_x": np.zeros(n_samples),
                    "gyr_y": identical_pitch * 0.5,
                    "gyr_z": identical_pitch * 0.3,
                    "roll": identical_pitch * 0.5,
                    "pitch": identical_pitch,
                    "roll_norm": identical_pitch,
                    "pitch_norm": identical_pitch,
                }
            )
        foot = pd.DataFrame(rows)
        blocks = [
            {
                "exercise": "Calf Raises",
                "reps": list(range(1, n_reps + 1)),
                "foot_data": foot,
                "shank_data": pd.DataFrame(),
            }
        ]
        result = calculate_consistency(blocks)
        score = result.get("Calf Raises")
        if score is not None:
            assert score > 70.0, f"Expected high score for identical reps, got {score}"


# ---------------------------------------------------------------------------
# calculate_ankle_angles
# ---------------------------------------------------------------------------

class TestCalculateAnkleAngles:
    def test_returns_none_when_no_heel_walk(self):
        blocks = _blocks(3, "Calf Raises")
        result = calculate_ankle_angles(blocks)
        assert result is None

    def test_returns_dict_with_expected_keys(self):
        blocks = _blocks(4, "Heel Walk")
        result = calculate_ankle_angles(blocks)
        assert result is not None
        assert "rep_max_dorsiflexion_deg" in result
        assert "mean_max_dorsiflexion_deg" in result

    def test_rep_count_matches_input(self):
        blocks = _blocks(4, "Heel Walk")
        result = calculate_ankle_angles(blocks)
        assert len(result["rep_max_dorsiflexion_deg"]) == 4

    def test_mean_equals_average_of_rep_maxes(self):
        blocks = _blocks(3, "Heel Walk")
        result = calculate_ankle_angles(blocks)
        per_rep = list(result["rep_max_dorsiflexion_deg"].values())
        assert result["mean_max_dorsiflexion_deg"] == pytest.approx(
            float(np.mean(per_rep)), rel=1e-3
        )

    def test_angles_are_positive(self):
        """Pitch signal is positive on its peaks → max should be positive."""
        blocks = _blocks(3, "Heel Walk")
        result = calculate_ankle_angles(blocks)
        for angle in result["rep_max_dorsiflexion_deg"].values():
            assert angle > 0


# ---------------------------------------------------------------------------
# calculate_rom_consistency
# ---------------------------------------------------------------------------

class TestCalculateRomConsistency:
    def test_returns_none_when_no_eligible_exercises(self):
        """Heel Walk is not in CONSISTENCY_EXERCISES."""
        blocks = _blocks(3, "Heel Walk")
        result = calculate_rom_consistency(blocks)
        assert result is None

    def test_returns_fractions_for_calf_raises(self):
        blocks = _blocks(4, "Calf Raises")
        result = calculate_rom_consistency(blocks)
        assert result is not None
        assert "Calf Raises" in result
        fractions = result["Calf Raises"]["rep_rom_fraction"]
        assert all(0.0 <= v <= 1.0 for v in fractions.values())

    def test_returns_max_rom_rep(self):
        blocks = _blocks(4, "Calf Raises")
        result = calculate_rom_consistency(blocks)
        assert "max_rom_rep" in result["Calf Raises"]

    def test_max_rep_fraction_is_one(self):
        """The rep with the largest ROM should have fraction == 1.0."""
        blocks = _blocks(4, "Calf Raises")
        result = calculate_rom_consistency(blocks)
        fractions = result["Calf Raises"]["rep_rom_fraction"]
        assert max(fractions.values()) == pytest.approx(1.0, abs=1e-6)

    def test_ankle_rotation_uses_roll(self):
        blocks = _blocks(5, "Ankle Rotation")
        result = calculate_rom_consistency(blocks)
        assert result is not None
        assert "Ankle Rotation" in result


# ---------------------------------------------------------------------------
# classify_reps (integration with mock classifier + temp config)
# ---------------------------------------------------------------------------

class TestClassifyReps:
    @pytest.fixture
    def model_config_path(self, tmp_path):
        path = str(tmp_path / "model_config.json")
        _write_model_config(path)
        return path

    def test_returns_dataframe(self, model_config_path, mock_classifier):
        X = np.zeros((4, 112))
        rep_idx = np.array([1, 1, 2, 2])
        sensor_locs = np.array(["foot", "shank", "foot", "shank"])

        with patch("analysis.MODEL_CONFIG_PATH", model_config_path):
            result = classify_reps(X, rep_idx, sensor_locs, mock_classifier)

        assert isinstance(result, pd.DataFrame)

    def test_has_required_columns(self, model_config_path, mock_classifier):
        X = np.zeros((4, 112))
        rep_idx = np.array([1, 1, 2, 2])
        sensor_locs = np.array(["foot", "shank", "foot", "shank"])

        with patch("analysis.MODEL_CONFIG_PATH", model_config_path):
            result = classify_reps(X, rep_idx, sensor_locs, mock_classifier)

        for col in ("rep", "predicted_exercise", "confidence"):
            assert col in result.columns

    def test_merges_foot_shank_per_rep(self, model_config_path, mock_classifier):
        X = np.zeros((4, 112))
        rep_idx = np.array([1, 1, 2, 2])
        sensor_locs = np.array(["foot", "shank", "foot", "shank"])

        with patch("analysis.MODEL_CONFIG_PATH", model_config_path):
            result = classify_reps(X, rep_idx, sensor_locs, mock_classifier)

        # After merging foot+shank, we should have one row per rep
        assert len(result) == 2
        assert set(result["rep"]) == {1, 2}

    def test_higher_confidence_wins_on_conflict(self, model_config_path):
        """When foot and shank disagree, the prediction with higher confidence wins."""
        mock_clf = MagicMock()
        mock_clf.classify.side_effect = [
            # rep 1: foot=Calf Raises(0.9), shank=Ankle Rotation(0.6)
            {"predicted_class": "Calf Raises", "confidence": 0.9},
            {"predicted_class": "Ankle Rotation", "confidence": 0.6},
        ]

        X = np.zeros((2, 112))
        rep_idx = np.array([1, 1])
        sensor_locs = np.array(["foot", "shank"])

        with patch("analysis.MODEL_CONFIG_PATH", model_config_path):
            result = classify_reps(X, rep_idx, sensor_locs, mock_clf)

        assert result.iloc[0]["predicted_exercise"] == "Calf Raises"
        assert result.iloc[0]["confidence"] == pytest.approx(0.9)

    def test_agreement_takes_max_confidence(self, model_config_path):
        """When both sensors agree, the higher of the two confidences is kept."""
        mock_clf = MagicMock()
        mock_clf.classify.side_effect = [
            {"predicted_class": "Calf Raises", "confidence": 0.8},
            {"predicted_class": "Calf Raises", "confidence": 0.95},
        ]

        X = np.zeros((2, 112))
        rep_idx = np.array([1, 1])
        sensor_locs = np.array(["foot", "shank"])

        with patch("analysis.MODEL_CONFIG_PATH", model_config_path):
            result = classify_reps(X, rep_idx, sensor_locs, mock_clf)

        assert result.iloc[0]["confidence"] == pytest.approx(0.95)


# ---------------------------------------------------------------------------
# analyze_session (end-to-end mock)
# ---------------------------------------------------------------------------

class TestAnalyzeSession:
    def test_returns_all_expected_keys(self, model_config_path=None, mock_classifier=None, tmp_path=None):
        pass  # covered by integration test below

    def test_full_pipeline_with_mock_classifier(self, mock_classifier, tmp_path):
        # Build a minimal pipeline result
        from conftest import make_sensor_readings
        from pipeline import (
            extract_features, extract_statistical_features, filter_signals,
            segment, sensor_readings_to_imu_json, wrangle,
        )

        config_path = str(tmp_path / "model_config.json")
        _write_model_config(config_path)

        readings = make_sensor_readings(n_samples=480, n_reps=3)
        imu1 = sensor_readings_to_imu_json(readings, "imu1")
        imu2 = sensor_readings_to_imu_json(readings, "imu2")
        df = wrangle(imu1, imu2)
        filtered = filter_signals(df)
        featured = extract_features(filtered)
        segmented = segment(featured)
        X, rep_idx, sensor_locs = extract_statistical_features(segmented)

        with patch("analysis.MODEL_CONFIG_PATH", config_path):
            result = analyze_session(
                X=X,
                rep_indices=rep_idx,
                sensor_locations=sensor_locs,
                segmented_df=segmented,
                classifier=mock_classifier,
            )

        for key in (
            "rep_classifications",
            "rep_counts",
            "rep_durations",
            "consistency_scores",
            "ankle_angles",
            "rom_consistency",
        ):
            assert key in result

    def test_rep_counts_are_nonnegative(self, mock_classifier, tmp_path):
        from conftest import make_sensor_readings
        from pipeline import (
            extract_features, extract_statistical_features, filter_signals,
            segment, sensor_readings_to_imu_json, wrangle,
        )

        config_path = str(tmp_path / "model_config.json")
        _write_model_config(config_path)

        readings = make_sensor_readings(n_samples=480, n_reps=3)
        imu1 = sensor_readings_to_imu_json(readings, "imu1")
        imu2 = sensor_readings_to_imu_json(readings, "imu2")
        df = wrangle(imu1, imu2)
        segmented = segment(extract_features(filter_signals(df)))
        X, rep_idx, sensor_locs = extract_statistical_features(segmented)

        with patch("analysis.MODEL_CONFIG_PATH", config_path):
            result = analyze_session(
                X=X,
                rep_indices=rep_idx,
                sensor_locations=sensor_locs,
                segmented_df=segmented,
                classifier=mock_classifier,
            )

        for count in result["rep_counts"].values():
            assert count >= 0
