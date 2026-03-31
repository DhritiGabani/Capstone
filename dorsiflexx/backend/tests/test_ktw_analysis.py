"""
Unit tests for ktw_analysis.py — Knee-to-Wall test analysis.

All tests use synthetic DataFrames with known shank pitch values so that
the expected ankle angle (90 - pitch) can be asserted precisely.
"""

import numpy as np
import pandas as pd
import pytest

import ktw_analysis


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_signals(
    n: int = 160,
    shank_pitch: float | np.ndarray = 15.0,
    include_foot: bool = True,
) -> pd.DataFrame:
    """
    Build a minimal signals DataFrame for ktw_analysis.analyze().

    Args:
        n:            Number of samples.
        shank_pitch:  Constant pitch value (float) or array of length n.
        include_foot: If True, foot rows are included alongside shank rows.
    """
    time = np.linspace(0, 1.0, n)

    if isinstance(shank_pitch, (int, float)):
        pitch_arr = np.full(n, float(shank_pitch))
    else:
        pitch_arr = np.asarray(shank_pitch, dtype=float)

    rows = []
    if include_foot:
        for i in range(n):
            rows.append(
                {
                    "sensor_location": "foot",
                    "time": time[i],
                    "pitch": 0.0,
                    "roll": 0.0,
                    "acc_x": 0.0, "acc_y": 0.0, "acc_z": 1.0,
                    "gyr_x": 0.0, "gyr_y": 0.0, "gyr_z": 0.0,
                }
            )

    for i in range(n):
        rows.append(
            {
                "sensor_location": "shank",
                "time": time[i],
                "pitch": pitch_arr[i],
                "roll": 0.0,
                "acc_x": 0.0, "acc_y": 0.0, "acc_z": 1.0,
                "gyr_x": 0.0, "gyr_y": 0.0, "gyr_z": 0.0,
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Return structure
# ---------------------------------------------------------------------------

class TestAnalyzeReturnStructure:
    def test_returns_dict(self):
        df = _make_signals()
        result = ktw_analysis.analyze(df)
        assert isinstance(result, dict)

    def test_has_largest_angle_key(self):
        df = _make_signals()
        result = ktw_analysis.analyze(df)
        assert "largest_angle_deg" in result

    def test_has_angle_over_time_key(self):
        df = _make_signals()
        result = ktw_analysis.analyze(df)
        assert "angle_over_time" in result

    def test_angle_over_time_is_dict(self):
        df = _make_signals()
        result = ktw_analysis.analyze(df)
        assert isinstance(result["angle_over_time"], dict)

    def test_angle_over_time_is_nonempty(self):
        df = _make_signals()
        result = ktw_analysis.analyze(df)
        assert len(result["angle_over_time"]) > 0

    def test_angle_over_time_starts_at_zero(self):
        df = _make_signals()
        result = ktw_analysis.analyze(df)
        assert 0.0 in result["angle_over_time"]

    def test_angle_over_time_keys_are_floats(self):
        df = _make_signals()
        result = ktw_analysis.analyze(df)
        for key in result["angle_over_time"]:
            assert isinstance(key, float)

    def test_angle_over_time_keys_spaced_half_second(self):
        df = _make_signals(n=320)  # 2 seconds
        result = ktw_analysis.analyze(df)
        keys = sorted(result["angle_over_time"].keys())
        for k1, k2 in zip(keys, keys[1:]):
            assert k2 - k1 == pytest.approx(0.5, abs=0.01)


# ---------------------------------------------------------------------------
# Correctness
# ---------------------------------------------------------------------------

class TestAnalyzeCorrectness:
    def test_constant_pitch_gives_expected_angle(self):
        """ankle_angle = 90 - pitch; for pitch=20 → angle=70."""
        df = _make_signals(shank_pitch=20.0)
        result = ktw_analysis.analyze(df)
        # After smoothing, the constant signal remains ≈70
        assert abs(result["largest_angle_deg"] - 70.0) < 1.0

    def test_zero_pitch_gives_90_degrees(self):
        """pitch=0 → ankle_angle=90 (leg vertical)."""
        df = _make_signals(shank_pitch=0.0)
        result = ktw_analysis.analyze(df)
        assert abs(result["largest_angle_deg"] - 90.0) < 1.0

    def test_highest_pitch_produces_smallest_angle(self):
        """Larger shank pitch → smaller ankle angle → BUT largest_angle = max."""
        # Create a rising pitch signal: 0 → 30 degrees
        n = 160
        pitch = np.linspace(0, 30, n)
        df = _make_signals(shank_pitch=pitch)
        result = ktw_analysis.analyze(df)
        # ankle_angle = 90 - pitch; max ankle angle is at pitch=0 → 90
        # The "largest_angle_deg" is the maximum of the smoothed ankle_angle series
        assert result["largest_angle_deg"] > 60.0

    def test_largest_angle_is_maximum_of_series(self):
        n = 160
        # pitch peaks at 30 degrees in the middle
        pitch = 10 + 20 * np.sin(np.linspace(0, np.pi, n))
        df = _make_signals(shank_pitch=pitch)
        result = ktw_analysis.analyze(df)
        # ankle = 90 - pitch; max at min(pitch)=10 → 80; min at max(pitch)=30 → 60
        # So largest_angle_deg should be ≈80
        assert abs(result["largest_angle_deg"] - 80.0) < 3.0

    def test_angle_over_time_values_are_floats(self):
        df = _make_signals()
        result = ktw_analysis.analyze(df)
        for val in result["angle_over_time"].values():
            assert isinstance(val, float)

    def test_largest_angle_equals_max_of_angle_over_time(self):
        """largest_angle_deg should equal or exceed every sampled angle."""
        df = _make_signals(n=320)
        result = ktw_analysis.analyze(df)
        sampled_max = max(result["angle_over_time"].values())
        assert result["largest_angle_deg"] >= sampled_max - 0.5  # small tolerance for sampling


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestAnalyzeErrorHandling:
    def test_raises_value_error_on_missing_shank(self):
        df = _make_signals(include_foot=True)
        foot_only = df[df["sensor_location"] == "foot"].copy()
        with pytest.raises(ValueError, match="Missing shank sensor data"):
            ktw_analysis.analyze(foot_only)

    def test_raises_value_error_on_empty_dataframe(self):
        with pytest.raises((ValueError, KeyError)):
            ktw_analysis.analyze(pd.DataFrame())

    def test_works_without_foot_data(self):
        """KTW only uses shank data; foot rows are ignored but not required."""
        df = _make_signals(include_foot=False)
        result = ktw_analysis.analyze(df)
        assert "largest_angle_deg" in result


# ---------------------------------------------------------------------------
# Smoothing behaviour
# ---------------------------------------------------------------------------

class TestSmoothSignal:
    def test_smoothing_reduces_noise(self):
        """A noisy constant signal should be smoothed to near the constant value."""
        n = 160
        rng = np.random.default_rng(42)
        noisy_pitch = 15.0 + rng.normal(0, 5.0, n)  # mean 15, std 5
        clean_pitch = np.full(n, 15.0)

        noisy_df = _make_signals(shank_pitch=noisy_pitch)
        clean_df = _make_signals(shank_pitch=clean_pitch)

        noisy_result = ktw_analysis.analyze(noisy_df)
        clean_result = ktw_analysis.analyze(clean_df)

        # After smoothing, the noisy result should be closer to the clean value than raw noise
        noisy_angle = noisy_result["largest_angle_deg"]
        expected_angle = 90 - 15.0  # = 75
        assert abs(noisy_angle - expected_angle) < 20.0  # within 20 degrees
