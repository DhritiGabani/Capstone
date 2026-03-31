"""
Unit tests for pipeline.py — each stage tested in isolation and end-to-end.

Synthetic sensor data from conftest.make_sensor_readings() is used throughout.
No real BLE hardware or TFLite model is needed.
"""

import numpy as np
import pandas as pd
import pytest

from pipeline import (
    SIGNAL_COLUMNS,
    extract_features,
    extract_statistical_features,
    filter_signals,
    preprocess_session,
    segment,
    sensor_readings_to_imu_json,
    wrangle,
)
from conftest import make_sensor_readings
from sensor import SensorReading


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _flat_imu_json(n: int = 100) -> dict:
    """IMU JSON with constant acc_z=1 (zero pitch / roll) — no detectable reps."""
    return {
        "samples": [
            {
                "sample_idx": i,
                "timestamp_us": i * 6250,
                "ax_g": 0.0,
                "ay_g": 0.0,
                "az_g": 1.0,
                "gx_dps": 0.0,
                "gy_dps": 0.0,
                "gz_dps": 0.0,
            }
            for i in range(n)
        ]
    }


# ---------------------------------------------------------------------------
# Stage 0 — sensor_readings_to_imu_json
# ---------------------------------------------------------------------------

class TestSensorReadingsToImuJson:
    def test_returns_dict_with_samples_key(self, synthetic_readings):
        result = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        assert "samples" in result

    def test_filters_to_correct_device(self, synthetic_readings):
        n_imu1 = sum(1 for r in synthetic_readings if r.device == "imu1")
        result = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        assert len(result["samples"]) == n_imu1

    def test_imu2_count_matches(self, synthetic_readings):
        n_imu2 = sum(1 for r in synthetic_readings if r.device == "imu2")
        result = sensor_readings_to_imu_json(synthetic_readings, "imu2")
        assert len(result["samples"]) == n_imu2

    def test_samples_sorted_by_timestamp(self, synthetic_readings):
        import random
        shuffled = synthetic_readings[:]
        random.shuffle(shuffled)
        result = sensor_readings_to_imu_json(shuffled, "imu1")
        timestamps = [s["timestamp_us"] for s in result["samples"]]
        assert timestamps == sorted(timestamps)

    def test_sample_indices_are_sequential(self, synthetic_readings):
        result = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        indices = [s["sample_idx"] for s in result["samples"]]
        assert indices == list(range(len(indices)))

    def test_all_imu_fields_present(self, synthetic_readings):
        result = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        required = {"sample_idx", "timestamp_us", "ax_g", "ay_g", "az_g",
                    "gx_dps", "gy_dps", "gz_dps"}
        for sample in result["samples"]:
            assert required.issubset(sample.keys())

    def test_unknown_device_returns_empty(self, synthetic_readings):
        result = sensor_readings_to_imu_json(synthetic_readings, "imu99")
        assert result["samples"] == []

    def test_acc_values_match_readings(self, synthetic_readings):
        imu1_readings = sorted(
            [r for r in synthetic_readings if r.device == "imu1"],
            key=lambda r: r.timestamp_us,
        )
        result = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        for r, s in zip(imu1_readings, result["samples"]):
            assert s["ax_g"] == pytest.approx(r.ax)
            assert s["ay_g"] == pytest.approx(r.ay)
            assert s["az_g"] == pytest.approx(r.az)


# ---------------------------------------------------------------------------
# Stage 1 — wrangle
# ---------------------------------------------------------------------------

class TestWrangle:
    def test_returns_dataframe(self, synthetic_readings):
        imu1 = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        imu2 = sensor_readings_to_imu_json(synthetic_readings, "imu2")
        df = wrangle(imu1, imu2)
        assert isinstance(df, pd.DataFrame)

    def test_has_foot_and_shank_locations(self, synthetic_readings):
        imu1 = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        imu2 = sensor_readings_to_imu_json(synthetic_readings, "imu2")
        df = wrangle(imu1, imu2)
        assert set(df["sensor_location"].unique()) == {"foot", "shank"}

    def test_foot_and_shank_are_equal_length(self, synthetic_readings):
        imu1 = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        imu2 = sensor_readings_to_imu_json(synthetic_readings, "imu2")
        df = wrangle(imu1, imu2)
        foot_len = (df["sensor_location"] == "foot").sum()
        shank_len = (df["sensor_location"] == "shank").sum()
        assert foot_len == shank_len

    def test_all_signal_columns_present(self, synthetic_readings):
        imu1 = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        imu2 = sensor_readings_to_imu_json(synthetic_readings, "imu2")
        df = wrangle(imu1, imu2)
        for col in SIGNAL_COLUMNS:
            assert col in df.columns

    def test_time_column_present(self, synthetic_readings):
        imu1 = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        imu2 = sensor_readings_to_imu_json(synthetic_readings, "imu2")
        df = wrangle(imu1, imu2)
        assert "time" in df.columns

    def test_time_starts_at_zero(self, synthetic_readings):
        imu1 = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        imu2 = sensor_readings_to_imu_json(synthetic_readings, "imu2")
        df = wrangle(imu1, imu2)
        assert df["time"].min() == pytest.approx(0.0, abs=1e-6)

    def test_raises_on_empty_imu2(self, synthetic_readings):
        imu1 = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        with pytest.raises(ValueError, match="empty"):
            wrangle(imu1, {"samples": []})

    def test_raises_on_empty_imu1(self, synthetic_readings):
        imu2 = sensor_readings_to_imu_json(synthetic_readings, "imu2")
        with pytest.raises(ValueError, match="empty"):
            wrangle({"samples": []}, imu2)

    def test_imu1_becomes_shank(self, synthetic_readings):
        """pipeline.wrangle maps imu1→shank and imu2→foot (hardware convention)."""
        imu1 = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        imu2 = sensor_readings_to_imu_json(synthetic_readings, "imu2")
        df = wrangle(imu1, imu2)
        assert "shank" in df["sensor_location"].values
        assert "foot" in df["sensor_location"].values

    def test_shorter_device_trims_longer(self):
        long_imu = _flat_imu_json(n=200)
        short_imu = _flat_imu_json(n=100)
        df = wrangle(long_imu, short_imu)
        foot_len = (df["sensor_location"] == "foot").sum()
        shank_len = (df["sensor_location"] == "shank").sum()
        assert foot_len == shank_len == 100


# ---------------------------------------------------------------------------
# Stage 2 — filter_signals
# ---------------------------------------------------------------------------

class TestFilterSignals:
    def test_preserves_dataframe_shape(self, synthetic_readings):
        imu1 = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        imu2 = sensor_readings_to_imu_json(synthetic_readings, "imu2")
        df = wrangle(imu1, imu2)
        filtered = filter_signals(df)
        assert filtered.shape == df.shape

    def test_preserves_sensor_locations(self, synthetic_readings):
        imu1 = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        imu2 = sensor_readings_to_imu_json(synthetic_readings, "imu2")
        df = wrangle(imu1, imu2)
        filtered = filter_signals(df)
        assert set(filtered["sensor_location"].unique()) == {"foot", "shank"}

    def test_signal_columns_preserved(self, synthetic_readings):
        imu1 = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        imu2 = sensor_readings_to_imu_json(synthetic_readings, "imu2")
        df = wrangle(imu1, imu2)
        filtered = filter_signals(df)
        for col in SIGNAL_COLUMNS:
            assert col in filtered.columns

    def test_attenuates_high_frequency_noise(self):
        """A 60 Hz noise component should be strongly reduced by the 2 Hz lowpass."""
        n = 480
        t = np.arange(n) / 160.0
        # Low-freq component (0.5 Hz) + high-freq noise (60 Hz)
        noise_amp = 0.5
        signal = np.sin(2 * np.pi * 0.5 * t) + noise_amp * np.sin(2 * np.pi * 60 * t)

        samples = [
            {
                "sample_idx": i,
                "timestamp_us": i * 6250,
                "ax_g": float(signal[i]),
                "ay_g": 0.0,
                "az_g": 1.0,
                "gx_dps": 0.0,
                "gy_dps": 0.0,
                "gz_dps": 0.0,
            }
            for i in range(n)
        ]
        imu_json = {"samples": samples}
        df = wrangle(imu_json, imu_json)

        original_std = df[df["sensor_location"] == "foot"]["acc_x"].std()
        filtered = filter_signals(df)
        filtered_std = filtered[filtered["sensor_location"] == "foot"]["acc_x"].std()

        assert filtered_std < original_std

    def test_does_not_modify_original_df(self, synthetic_readings):
        imu1 = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        imu2 = sensor_readings_to_imu_json(synthetic_readings, "imu2")
        df = wrangle(imu1, imu2)
        original_acc_x = df["acc_x"].copy()
        filter_signals(df)
        pd.testing.assert_series_equal(df["acc_x"], original_acc_x)


# ---------------------------------------------------------------------------
# Stage 3 — extract_features
# ---------------------------------------------------------------------------

class TestExtractFeatures:
    def test_adds_roll_column(self, synthetic_readings):
        imu1 = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        imu2 = sensor_readings_to_imu_json(synthetic_readings, "imu2")
        df = wrangle(imu1, imu2)
        featured = extract_features(filter_signals(df))
        assert "roll" in featured.columns

    def test_adds_pitch_column(self, synthetic_readings):
        imu1 = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        imu2 = sensor_readings_to_imu_json(synthetic_readings, "imu2")
        df = wrangle(imu1, imu2)
        featured = extract_features(filter_signals(df))
        assert "pitch" in featured.columns

    def test_preserves_row_count(self, synthetic_readings):
        imu1 = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        imu2 = sensor_readings_to_imu_json(synthetic_readings, "imu2")
        df = wrangle(imu1, imu2)
        filtered = filter_signals(df)
        featured = extract_features(filtered)
        assert len(featured) == len(filtered)

    def test_pitch_oscillates_with_motion(self, synthetic_readings):
        """Synthetic data has ±25° pitch; after lowpass, amplitude should still exceed 15°."""
        imu1 = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        imu2 = sensor_readings_to_imu_json(synthetic_readings, "imu2")
        df = wrangle(imu1, imu2)
        featured = extract_features(filter_signals(df))
        foot_pitch = featured[featured["sensor_location"] == "foot"]["pitch"]
        assert foot_pitch.max() > 15.0
        assert foot_pitch.min() < -15.0

    def test_flat_signal_gives_near_zero_pitch(self):
        """Constant az=1, ax=ay=0 → pitch ≈ 0°."""
        imu_json = _flat_imu_json(n=200)
        df = wrangle(imu_json, imu_json)
        filtered = filter_signals(df)
        featured = extract_features(filtered)
        pitch = featured["pitch"]
        assert pitch.abs().max() < 1.0  # nearly zero

    def test_does_not_modify_input(self, synthetic_readings):
        imu1 = sensor_readings_to_imu_json(synthetic_readings, "imu1")
        imu2 = sensor_readings_to_imu_json(synthetic_readings, "imu2")
        df = wrangle(imu1, imu2)
        filtered = filter_signals(df)
        original_acc_x = filtered["acc_x"].copy()
        extract_features(filtered)
        pd.testing.assert_series_equal(filtered["acc_x"], original_acc_x)


# ---------------------------------------------------------------------------
# Stage 4 — segment
# ---------------------------------------------------------------------------

class TestSegment:
    def _get_featured(self, readings):
        imu1 = sensor_readings_to_imu_json(readings, "imu1")
        imu2 = sensor_readings_to_imu_json(readings, "imu2")
        df = wrangle(imu1, imu2)
        return extract_features(filter_signals(df))

    def test_returns_dataframe(self, synthetic_readings):
        featured = self._get_featured(synthetic_readings)
        result = segment(featured)
        assert isinstance(result, pd.DataFrame)

    def test_rep_column_present(self, synthetic_readings):
        featured = self._get_featured(synthetic_readings)
        result = segment(featured)
        assert "rep" in result.columns

    def test_detects_at_least_two_reps(self, synthetic_readings):
        featured = self._get_featured(synthetic_readings)
        result = segment(featured)
        assert result["rep"].nunique() >= 2

    def test_detects_expected_rep_count(self):
        """5 full reps over 800 samples should yield 4–5 detectable rep boundaries."""
        readings = make_sensor_readings(n_samples=800, n_reps=5, amp_deg=30.0)
        imu1 = sensor_readings_to_imu_json(readings, "imu1")
        imu2 = sensor_readings_to_imu_json(readings, "imu2")
        df = wrangle(imu1, imu2)
        featured = extract_features(filter_signals(df))
        result = segment(featured)
        assert result["rep"].nunique() >= 4

    def test_raises_on_flat_signal(self):
        """A flat signal has no detectable peaks → ValueError."""
        imu_json = _flat_imu_json(n=200)
        df = wrangle(imu_json, imu_json)
        featured = extract_features(filter_signals(df))
        with pytest.raises(ValueError, match="No rep boundaries detected"):
            segment(featured)

    def test_normalized_columns_present(self, synthetic_readings):
        featured = self._get_featured(synthetic_readings)
        result = segment(featured)
        for col in ("pitch_norm", "roll_norm", "acc_x_norm"):
            assert col in result.columns

    def test_foot_and_shank_rows_present(self, synthetic_readings):
        featured = self._get_featured(synthetic_readings)
        result = segment(featured)
        assert "foot" in result["sensor_location"].values
        assert "shank" in result["sensor_location"].values

    def test_sensor_location_column_present(self, synthetic_readings):
        featured = self._get_featured(synthetic_readings)
        result = segment(featured)
        assert "sensor_location" in result.columns


# ---------------------------------------------------------------------------
# Stage 5 — extract_statistical_features
# ---------------------------------------------------------------------------

class TestExtractStatisticalFeatures:
    def _get_segmented(self, readings):
        imu1 = sensor_readings_to_imu_json(readings, "imu1")
        imu2 = sensor_readings_to_imu_json(readings, "imu2")
        df = wrangle(imu1, imu2)
        featured = extract_features(filter_signals(df))
        return segment(featured)

    def test_feature_vector_width_is_112(self, synthetic_readings):
        segmented = self._get_segmented(synthetic_readings)
        X, _, _ = extract_statistical_features(segmented)
        assert X.shape[1] == 112

    def test_row_counts_match(self, synthetic_readings):
        segmented = self._get_segmented(synthetic_readings)
        X, rep_idx, sensor_locs = extract_statistical_features(segmented)
        assert len(X) == len(rep_idx) == len(sensor_locs)

    def test_rep_indices_cover_all_reps(self, synthetic_readings):
        segmented = self._get_segmented(synthetic_readings)
        X, rep_idx, _ = extract_statistical_features(segmented)
        assert set(rep_idx) == set(segmented["rep"].unique())

    def test_sensor_locations_are_valid(self, synthetic_readings):
        segmented = self._get_segmented(synthetic_readings)
        _, _, sensor_locs = extract_statistical_features(segmented)
        assert set(sensor_locs).issubset({"foot", "shank"})

    def test_features_are_finite(self, synthetic_readings):
        segmented = self._get_segmented(synthetic_readings)
        X, _, _ = extract_statistical_features(segmented)
        assert np.all(np.isfinite(X))


# ---------------------------------------------------------------------------
# End-to-end — preprocess_session
# ---------------------------------------------------------------------------

class TestPreprocessSession:
    def test_returns_all_expected_keys(self, synthetic_readings):
        result = preprocess_session(synthetic_readings)
        for key in ("X", "rep_indices", "sensor_locations", "segmented_df",
                    "imu1_json", "imu2_json"):
            assert key in result

    def test_feature_matrix_has_112_columns(self, synthetic_readings):
        result = preprocess_session(synthetic_readings)
        assert result["X"].shape[1] == 112

    def test_imu_json_has_samples(self, synthetic_readings):
        result = preprocess_session(synthetic_readings)
        assert len(result["imu1_json"]["samples"]) > 0
        assert len(result["imu2_json"]["samples"]) > 0

    def test_rep_indices_not_empty(self, synthetic_readings):
        result = preprocess_session(synthetic_readings)
        assert len(result["rep_indices"]) > 0

    def test_segmented_df_is_dataframe(self, synthetic_readings):
        result = preprocess_session(synthetic_readings)
        assert isinstance(result["segmented_df"], pd.DataFrame)

    def test_consistent_row_counts(self, synthetic_readings):
        result = preprocess_session(synthetic_readings)
        assert len(result["X"]) == len(result["rep_indices"]) == len(result["sensor_locations"])
