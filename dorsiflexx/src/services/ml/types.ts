/**
 * Types for the ML exercise classification service
 */

/**
 * Raw sensor reading from a single time point
 */
export interface SensorReading {
  accelX: number;
  accelY: number;
  accelZ: number;
  gyroX: number;
  gyroY: number;
  gyroZ: number;
  timestamp?: number;
}

/**
 * Processed sensor window with computed features
 */
export interface SensorWindow {
  accelX: number;
  accelY: number;
  accelZ: number;
  gyroX: number;
  gyroY: number;
  gyroZ: number;
  accelMagnitude: number;
  gyroMagnitude: number;
}

/**
 * Result of exercise classification
 */
export interface ClassificationResult {
  predictedClass: string;
  classIndex: number;
  confidence: number;
  probabilities: Record<string, number>;
  processingTimeMs: number;
}

/**
 * Model configuration loaded from model_config.json
 */
export interface ModelConfig {
  modelVersion: string;
  architecture: {
    inputSize: number;
    hiddenLayers: number[];
    outputSize: number;
    activation: string;
  };
  classes: string[];
  scaler: {
    mean: number[];
    scale: number[];
  } | null;
  featureNames: string[];
}

/**
 * Scaler parameters for StandardScaler
 */
export interface ScalerParams {
  mean: number[];
  scale: number[];
}

/**
 * Exercise class labels
 */
export type ExerciseClass = 'Ankle Rotation' | 'Calf Raises' | 'Heel Walk';

/**
 * Number of windows expected by the model
 */
export const NUM_WINDOWS = 8;

/**
 * Number of features per window
 */
export const FEATURES_PER_WINDOW = 8;

/**
 * Total number of input features (NUM_WINDOWS * FEATURES_PER_WINDOW)
 */
export const TOTAL_FEATURES = NUM_WINDOWS * FEATURES_PER_WINDOW;
