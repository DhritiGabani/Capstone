export interface SensorReading {
  device: string; // "imu1" or "imu2"
  timestamp_us: number;
  ax: number; // accelerometer X in g
  ay: number; // accelerometer Y in g
  az: number; // accelerometer Z in g
  gx: number; // gyroscope X in deg/s
  gy: number; // gyroscope Y in deg/s
  gz: number; // gyroscope Z in deg/s
}

export type BleConnectionState =
  | "idle"
  | "scanning"
  | "connecting"
  | "connected"
  | "streaming"
  | "stopping"
  | "error";

export interface StreamingStats {
  imu1Count: number;
  imu2Count: number;
  elapsedSeconds: number;
}
