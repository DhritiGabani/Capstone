"""
SensorReading dataclass for dorsiflexx backend.
"""

from dataclasses import dataclass


@dataclass
class SensorReading:
    device: str          # "imu1" or "imu2"
    timestamp_us: int    # device timestamp in microseconds
    ax: float            # accelerometer X in g
    ay: float            # accelerometer Y in g
    az: float            # accelerometer Z in g
    gx: float            # gyroscope X in degrees/s
    gy: float            # gyroscope Y in degrees/s
    gz: float            # gyroscope Z in degrees/s
