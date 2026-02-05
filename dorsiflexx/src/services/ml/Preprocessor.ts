/**
 * Preprocessor for sensor data - matches sklearn StandardScaler behavior exactly
 */

import {
  SensorReading,
  SensorWindow,
  ScalerParams,
  NUM_WINDOWS,
  FEATURES_PER_WINDOW,
  TOTAL_FEATURES,
} from './types';

export class Preprocessor {
  private mean: number[];
  private stdDev: number[];

  constructor(scalerParams: ScalerParams) {
    this.mean = scalerParams.mean;
    this.stdDev = scalerParams.scale;

    if (this.mean.length !== TOTAL_FEATURES || this.stdDev.length !== TOTAL_FEATURES) {
      throw new Error(
        `Scaler params must have ${TOTAL_FEATURES} values. ` +
        `Got mean: ${this.mean.length}, scale: ${this.stdDev.length}`
      );
    }
  }

  /**
   * Compute magnitude of 3D vector
   */
  private computeMagnitude(x: number, y: number, z: number): number {
    return Math.sqrt(x * x + y * y + z * z);
  }

  /**
   * Convert raw sensor reading to window with computed features
   */
  sensorReadingToWindow(reading: SensorReading): SensorWindow {
    return {
      accelX: reading.accelX,
      accelY: reading.accelY,
      accelZ: reading.accelZ,
      gyroX: reading.gyroX,
      gyroY: reading.gyroY,
      gyroZ: reading.gyroZ,
      accelMagnitude: this.computeMagnitude(reading.accelX, reading.accelY, reading.accelZ),
      gyroMagnitude: this.computeMagnitude(reading.gyroX, reading.gyroY, reading.gyroZ),
    };
  }

  /**
   * Convert sensor windows to flat feature array in correct order
   * Order: [window0_features..., window1_features..., ..., window7_features...]
   * Per window: [accelX, accelY, accelZ, gyroX, gyroY, gyroZ, accelMag, gyroMag]
   */
  windowsToFeatures(windows: SensorWindow[]): number[] {
    if (windows.length !== NUM_WINDOWS) {
      throw new Error(`Expected ${NUM_WINDOWS} windows, got ${windows.length}`);
    }

    const features: number[] = [];
    for (const window of windows) {
      features.push(
        window.accelX,
        window.accelY,
        window.accelZ,
        window.gyroX,
        window.gyroY,
        window.gyroZ,
        window.accelMagnitude,
        window.gyroMagnitude
      );
    }

    return features;
  }

  /**
   * Apply StandardScaler transformation: (x - mean) / scale
   * This must match sklearn's StandardScaler.transform() exactly
   */
  scaleFeatures(features: number[]): number[] {
    if (features.length !== TOTAL_FEATURES) {
      throw new Error(`Expected ${TOTAL_FEATURES} features, got ${features.length}`);
    }

    const scaled: number[] = new Array(TOTAL_FEATURES);
    for (let i = 0; i < TOTAL_FEATURES; i++) {
      scaled[i] = (features[i] - this.mean[i]) / this.stdDev[i];
    }

    return scaled;
  }

  /**
   * Full preprocessing pipeline: sensor windows -> scaled features ready for model
   */
  preprocess(windows: SensorWindow[]): number[] {
    const features = this.windowsToFeatures(windows);
    return this.scaleFeatures(features);
  }

  /**
   * Convert raw sensor readings to windows and preprocess
   */
  preprocessReadings(readings: SensorReading[]): number[] {
    const windows = readings.map(r => this.sensorReadingToWindow(r));
    return this.preprocess(windows);
  }
}
