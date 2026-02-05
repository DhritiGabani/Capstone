/**
 * ML Services - Exercise Classification
 */

export { ExerciseClassifier, ExerciseClassifierService } from './ExerciseClassifier';
export { Preprocessor } from './Preprocessor';
export type {
  SensorReading,
  SensorWindow,
  ClassificationResult,
  ModelConfig,
  ScalerParams,
  ExerciseClass,
} from './types';
export {
  NUM_WINDOWS,
  FEATURES_PER_WINDOW,
  TOTAL_FEATURES,
} from './types';
