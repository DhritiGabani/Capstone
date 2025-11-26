#!/usr/bin/env python3
"""
Calculate Quaternions from IMU Data (Accelerometer + Gyroscope)

This script uses the Madgwick filter algorithm to calculate orientation
quaternions (Quat_q0, Quat_q1, Quat_q2, Quat_q3) from raw sensor data.

Input columns required:
    - Acc_X, Acc_Y, Acc_Z (accelerometer in m/s²)
    - Gyr_X, Gyr_Y, Gyr_Z (gyroscope in rad/s)

Output columns added:
    - Calc_Quat_q0, Calc_Quat_q1, Calc_Quat_q2, Calc_Quat_q3

Usage:
    python calculate_quaternions.py <input_csv> [output_csv] [--beta 0.1] [--sample_rate 100]
"""

import numpy as np
import pandas as pd
import argparse
from pathlib import Path


class MadgwickFilter:
    """
    Madgwick AHRS Filter for quaternion estimation.

    Fuses accelerometer and gyroscope data to estimate orientation.

    Quaternion format: [q0, q1, q2, q3] where q0 is the scalar component.

    Reference:
        S. Madgwick, "An efficient orientation filter for inertial and
        inertial/magnetic sensor arrays", 2010
    """

    def __init__(self, sample_rate=100.0, beta=0.1):
        """
        Initialize the Madgwick filter.

        Parameters
        ----------
        sample_rate : float
            Sensor sampling frequency in Hz (default: 100 Hz for Xsens)
        beta : float
            Filter gain controlling accelerometer vs gyroscope trust.
            - Higher (0.3-0.5): More accelerometer trust, better for slow motion
            - Lower (0.01-0.05): More gyroscope trust, better for fast motion
            - Default (0.1): Good balance for general movement
        """
        self.sample_rate = sample_rate
        self.beta = beta
        self.dt = 1.0 / sample_rate

        # Initial quaternion (identity - no rotation)
        self.q = np.array([1.0, 0.0, 0.0, 0.0])

    def reset(self, q=None):
        """
        Reset the filter state.

        Parameters
        ----------
        q : array-like, optional
            Initial quaternion [q0, q1, q2, q3]. If None, resets to identity.
        """
        if q is not None:
            self.q = np.array(q, dtype=float)
        else:
            self.q = np.array([1.0, 0.0, 0.0, 0.0])

    def update(self, gyro, accel):
        """
        Update quaternion estimate with new sensor readings.

        Parameters
        ----------
        gyro : array-like
            Gyroscope reading [gx, gy, gz] in rad/s
        accel : array-like
            Accelerometer reading [ax, ay, az] in m/s² or g

        Returns
        -------
        q : numpy array
            Updated quaternion [q0, q1, q2, q3]
        """
        q = self.q.copy()
        gx, gy, gz = gyro
        ax, ay, az = accel

        # Normalize accelerometer measurement
        accel_norm = np.sqrt(ax*ax + ay*ay + az*az)
        if accel_norm == 0:
            return q  # Cannot normalize, return current estimate

        ax /= accel_norm
        ay /= accel_norm
        az /= accel_norm

        # Extract quaternion components
        q0, q1, q2, q3 = q

        # Auxiliary variables to avoid repeated calculations
        _2q0 = 2.0 * q0
        _2q1 = 2.0 * q1
        _2q2 = 2.0 * q2
        _2q3 = 2.0 * q3
        _4q0 = 4.0 * q0
        _4q1 = 4.0 * q1
        _4q2 = 4.0 * q2
        _8q1 = 8.0 * q1
        _8q2 = 8.0 * q2
        q0q0 = q0 * q0
        q1q1 = q1 * q1
        q2q2 = q2 * q2
        q3q3 = q3 * q3

        # Gradient descent corrective step
        # Minimizes error between measured and estimated gravity direction
        s0 = _4q0 * q2q2 + _2q2 * ax + _4q0 * q1q1 - _2q1 * ay
        s1 = _4q1 * q3q3 - _2q3 * ax + 4.0 * q0q0 * q1 - _2q0 * \
            ay - _4q1 + _8q1 * q1q1 + _8q1 * q2q2 + _4q1 * az
        s2 = 4.0 * q0q0 * q2 + _2q0 * ax + _4q2 * q3q3 - _2q3 * \
            ay - _4q2 + _8q2 * q1q1 + _8q2 * q2q2 + _4q2 * az
        s3 = 4.0 * q1q1 * q3 - _2q1 * ax + 4.0 * q2q2 * q3 - _2q2 * ay

        # Normalize step magnitude
        s_norm = np.sqrt(s0*s0 + s1*s1 + s2*s2 + s3*s3)
        if s_norm > 0:
            s0 /= s_norm
            s1 /= s_norm
            s2 /= s_norm
            s3 /= s_norm

        # Rate of change from gyroscope
        qDot0 = 0.5 * (-q1 * gx - q2 * gy - q3 * gz)
        qDot1 = 0.5 * (q0 * gx + q2 * gz - q3 * gy)
        qDot2 = 0.5 * (q0 * gy - q1 * gz + q3 * gx)
        qDot3 = 0.5 * (q0 * gz + q1 * gy - q2 * gx)

        # Apply feedback (accelerometer correction)
        qDot0 -= self.beta * s0
        qDot1 -= self.beta * s1
        qDot2 -= self.beta * s2
        qDot3 -= self.beta * s3

        # Integrate to get new quaternion
        q0 += qDot0 * self.dt
        q1 += qDot1 * self.dt
        q2 += qDot2 * self.dt
        q3 += qDot3 * self.dt

        # Normalize quaternion
        q_norm = np.sqrt(q0*q0 + q1*q1 + q2*q2 + q3*q3)
        q0 /= q_norm
        q1 /= q_norm
        q2 /= q_norm
        q3 /= q_norm

        self.q = np.array([q0, q1, q2, q3])
        return self.q.copy()

    def get_quaternion(self):
        """Return current quaternion estimate."""
        return self.q.copy()


def quaternion_to_euler(q):
    """
    Convert quaternion to Euler angles (roll, pitch, yaw).

    Parameters
    ----------
    q : array-like
        Quaternion [q0, q1, q2, q3] where q0 is scalar

    Returns
    -------
    roll, pitch, yaw : float
        Euler angles in degrees
    """
    q0, q1, q2, q3 = q

    # Roll (x-axis rotation)
    sinr_cosp = 2.0 * (q0*q1 + q2*q3)
    cosr_cosp = 1.0 - 2.0 * (q1*q1 + q2*q2)
    roll = np.arctan2(sinr_cosp, cosr_cosp)

    # Pitch (y-axis rotation)
    sinp = 2.0 * (q0*q2 - q3*q1)
    sinp = np.clip(sinp, -1.0, 1.0)
    pitch = np.arcsin(sinp)

    # Yaw (z-axis rotation)
    siny_cosp = 2.0 * (q0*q3 + q1*q2)
    cosy_cosp = 1.0 - 2.0 * (q2*q2 + q3*q3)
    yaw = np.arctan2(siny_cosp, cosy_cosp)

    return np.degrees(roll), np.degrees(pitch), np.degrees(yaw)


def calculate_quaternions(df, sample_rate=100.0, beta=0.1, initial_quaternion=None):
    """
    Calculate quaternions for a DataFrame containing IMU data.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with columns: Acc_X, Acc_Y, Acc_Z, Gyr_X, Gyr_Y, Gyr_Z
    sample_rate : float
        Sensor sample rate in Hz
    beta : float
        Madgwick filter gain
    initial_quaternion : array-like, optional
        Starting quaternion [q0, q1, q2, q3]. If None, uses identity or
        first row's quaternion if available.

    Returns
    -------
    df : pandas.DataFrame
        DataFrame with added columns: Calc_Quat_q0, Calc_Quat_q1, Calc_Quat_q2, Calc_Quat_q3
    """
    # Validate required columns
    required = ['Acc_X', 'Acc_Y', 'Acc_Z', 'Gyr_X', 'Gyr_Y', 'Gyr_Z']
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Initialize filter
    madgwick = MadgwickFilter(sample_rate=sample_rate, beta=beta)

    # Set initial quaternion
    if initial_quaternion is not None:
        madgwick.reset(initial_quaternion)
    elif all(col in df.columns for col in ['Quat_q0', 'Quat_q1', 'Quat_q2', 'Quat_q3']):
        # Use first quaternion from existing data
        initial_q = [
            df['Quat_q0'].iloc[0],
            df['Quat_q1'].iloc[0],
            df['Quat_q2'].iloc[0],
            df['Quat_q3'].iloc[0]
        ]
        madgwick.reset(initial_q)

    # Calculate quaternions for each sample
    calc_q0, calc_q1, calc_q2, calc_q3 = [], [], [], []

    for idx in range(len(df)):
        accel = [df['Acc_X'].iloc[idx],
                 df['Acc_Y'].iloc[idx], df['Acc_Z'].iloc[idx]]
        gyro = [df['Gyr_X'].iloc[idx],
                df['Gyr_Y'].iloc[idx], df['Gyr_Z'].iloc[idx]]

        q = madgwick.update(gyro, accel)

        calc_q0.append(q[0])
        calc_q1.append(q[1])
        calc_q2.append(q[2])
        calc_q3.append(q[3])

    # Add calculated quaternions to DataFrame
    df = df.copy()
    df['Calc_Quat_q0'] = calc_q0
    df['Calc_Quat_q1'] = calc_q1
    df['Calc_Quat_q2'] = calc_q2
    df['Calc_Quat_q3'] = calc_q3

    return df


def process_csv_file(input_path, output_path=None, sample_rate=100.0, beta=0.1):
    """
    Process a CSV file and add calculated quaternions.

    Parameters
    ----------
    input_path : str or Path
        Path to input CSV file
    output_path : str or Path, optional
        Path to output CSV file. If None, appends '_with_quats' to input name.
    sample_rate : float
        Sensor sample rate in Hz
    beta : float
        Madgwick filter gain

    Returns
    -------
    df : pandas.DataFrame
        Processed DataFrame
    """
    input_path = Path(input_path)

    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_with_quats.csv"

    # Read CSV
    df = pd.read_csv(input_path)

    # Calculate quaternions
    df = calculate_quaternions(df, sample_rate=sample_rate, beta=beta)

    # Save result
    df.to_csv(output_path, index=False)

    return df


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calculate quaternions from IMU data using Madgwick filter"
    )
    parser.add_argument("input_csv", nargs="?", help="Input CSV file path")
    parser.add_argument("output_csv", nargs="?",
                        help="Output CSV file path (optional)")
    parser.add_argument("--beta", type=float, default=0.1,
                        help="Filter gain (default: 0.1)")
    parser.add_argument("--sample_rate", type=float, default=100.0,
                        help="Sample rate in Hz (default: 100)")
    parser.add_argument("--demo", action="store_true",
                        help="Run demo with sample data")

    args = parser.parse_args()

    if args.demo or args.input_csv is None:
        # Demo mode - show how the algorithm works
        print("=" * 60)
        print("QUATERNION CALCULATION DEMO")
        print("=" * 60)
        print()
        print("The Madgwick filter calculates quaternions by fusing:")
        print("  - Accelerometer: Measures gravity direction (slow but stable)")
        print("  - Gyroscope: Measures angular velocity (fast but drifts)")
        print()
        print("Quaternion format: [q0, q1, q2, q3]")
        print("  q0 = scalar (w)")
        print("  q1, q2, q3 = vector (x, y, z)")
        print()

        # Create sample data
        print("Creating sample data...")
        np.random.seed(42)
        n_samples = 100

        # Simulate stationary sensor (gravity pointing down in z)
        sample_data = pd.DataFrame({
            'Acc_X': np.random.normal(0, 0.1, n_samples),
            'Acc_Y': np.random.normal(0, 0.1, n_samples),
            'Acc_Z': np.random.normal(-9.81, 0.1, n_samples),  # Gravity
            'Gyr_X': np.random.normal(0, 0.01, n_samples),
            'Gyr_Y': np.random.normal(0, 0.01, n_samples),
            'Gyr_Z': np.random.normal(0, 0.01, n_samples),
        })

        # Calculate quaternions
        result = calculate_quaternions(
            sample_data, sample_rate=100.0, beta=0.1)

        print()
        print("Sample results (first 5 rows):")
        print("-" * 60)
        for i in range(5):
            q = [result['Calc_Quat_q0'].iloc[i], result['Calc_Quat_q1'].iloc[i],
                 result['Calc_Quat_q2'].iloc[i], result['Calc_Quat_q3'].iloc[i]]
            roll, pitch, yaw = quaternion_to_euler(q)
            print(
                f"Sample {i+1}: q=[{q[0]:.4f}, {q[1]:.4f}, {q[2]:.4f}, {q[3]:.4f}]")
            print(
                f"           Euler: roll={roll:.1f}, pitch={pitch:.1f}, yaw={yaw:.1f}")

        print()
        print("=" * 60)
        print("To process your own CSV file:")
        print("  python calculate_quaternions.py <input.csv> [output.csv]")
        print()
        print("Required columns: Acc_X, Acc_Y, Acc_Z, Gyr_X, Gyr_Y, Gyr_Z")
        print("=" * 60)

    else:
        # Process actual file
        input_path = Path(args.input_csv)

        if not input_path.exists():
            print(f"Error: File not found: {input_path}")
            exit(1)

        print(f"Processing: {input_path}")
        print(f"  Sample rate: {args.sample_rate} Hz")
        print(f"  Beta: {args.beta}")

        df = process_csv_file(
            input_path,
            args.output_csv,
            sample_rate=args.sample_rate,
            beta=args.beta
        )

        output_path = args.output_csv or f"{input_path.stem}_with_quats.csv"
        print(f"  Samples processed: {len(df)}")
        print(f"  Output saved to: {output_path}")
