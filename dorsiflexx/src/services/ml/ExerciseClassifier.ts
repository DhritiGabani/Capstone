/**
 * Exercise Classifier Service
 * Loads TFLite model and performs inference for exercise classification
 */

import { loadTensorflowModel, TensorflowModel } from 'react-native-fast-tflite';
import { Asset } from 'expo-asset';
import {
  ClassificationResult,
  ModelConfig,
  SensorWindow,
  SensorReading,
  TOTAL_FEATURES,
} from './types';
import { Preprocessor } from './Preprocessor';

// Import model and config assets
import modelAsset from '../../../assets/models/exercise_classifier.tflite';
import modelConfig from '../../../assets/models/model_config.json';

class ExerciseClassifierService {
  private static instance: ExerciseClassifierService | null = null;
  private model: TensorflowModel | null = null;
  private preprocessor: Preprocessor | null = null;
  private config: ModelConfig | null = null;
  private isInitialized = false;
  private initPromise: Promise<void> | null = null;

  private constructor() {}

  /**
   * Get singleton instance
   */
  static getInstance(): ExerciseClassifierService {
    if (!ExerciseClassifierService.instance) {
      ExerciseClassifierService.instance = new ExerciseClassifierService();
    }
    return ExerciseClassifierService.instance;
  }

  /**
   * Initialize the classifier - loads model and config
   * Safe to call multiple times, will only initialize once
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) {
      return;
    }

    // Prevent concurrent initialization
    if (this.initPromise) {
      return this.initPromise;
    }

    this.initPromise = this._doInitialize();
    await this.initPromise;
  }

  private async _doInitialize(): Promise<void> {
    try {
      console.log('[ExerciseClassifier] Starting initialization...');

      // Load config
      this.config = modelConfig as ModelConfig;
      console.log('[ExerciseClassifier] Config loaded:', {
        version: this.config.modelVersion,
        classes: this.config.classes,
        inputSize: this.config.architecture.inputSize,
      });

      // Initialize preprocessor with scaler params
      if (!this.config.scaler) {
        throw new Error('Model config missing scaler parameters');
      }
      this.preprocessor = new Preprocessor(this.config.scaler);
      console.log('[ExerciseClassifier] Preprocessor initialized');

      // Load TFLite model
      const asset = Asset.fromModule(modelAsset);
      await asset.downloadAsync();

      if (!asset.localUri) {
        throw new Error('Failed to download model asset');
      }

      console.log('[ExerciseClassifier] Loading TFLite model from:', asset.localUri);
      this.model = await loadTensorflowModel({ url: asset.localUri });
      console.log('[ExerciseClassifier] Model loaded successfully');

      this.isInitialized = true;
    } catch (error) {
      this.initPromise = null;
      console.error('[ExerciseClassifier] Initialization failed:', error);
      throw error;
    }
  }

  /**
   * Check if classifier is ready for inference
   */
  isReady(): boolean {
    return this.isInitialized && this.model !== null && this.preprocessor !== null;
  }

  /**
   * Get class labels
   */
  getClasses(): string[] {
    return this.config?.classes ?? [];
  }

  /**
   * Classify exercise from sensor windows (8 windows of 8 features each)
   */
  async classify(windows: SensorWindow[]): Promise<ClassificationResult> {
    if (!this.isReady()) {
      throw new Error('Classifier not initialized. Call initialize() first.');
    }

    const startTime = performance.now();

    // Preprocess: windows -> scaled features
    const features = this.preprocessor!.preprocess(windows);

    // Run inference
    const result = await this.classifyFromFeatures(features);

    result.processingTimeMs = performance.now() - startTime;
    return result;
  }

  /**
   * Classify exercise from raw sensor readings (8 readings)
   */
  async classifyFromReadings(readings: SensorReading[]): Promise<ClassificationResult> {
    if (!this.isReady()) {
      throw new Error('Classifier not initialized. Call initialize() first.');
    }

    const startTime = performance.now();

    // Preprocess: readings -> windows -> scaled features
    const features = this.preprocessor!.preprocessReadings(readings);

    // Run inference
    const result = await this.classifyFromFeatures(features);

    result.processingTimeMs = performance.now() - startTime;
    return result;
  }

  /**
   * Classify exercise from pre-computed features (64 values)
   * Features should already be scaled using the StandardScaler
   */
  async classifyFromFeatures(scaledFeatures: number[]): Promise<ClassificationResult> {
    if (!this.isReady()) {
      throw new Error('Classifier not initialized. Call initialize() first.');
    }

    if (scaledFeatures.length !== TOTAL_FEATURES) {
      throw new Error(`Expected ${TOTAL_FEATURES} features, got ${scaledFeatures.length}`);
    }

    const startTime = performance.now();

    // Create input tensor - shape: [1, 64]
    const inputArray = new Float32Array(scaledFeatures);

    // Run inference
    const outputs = await this.model!.run([inputArray]);

    // Get output probabilities - shape: [1, 3]
    const outputData = outputs[0] as Float32Array;

    // Find class with highest probability
    let maxProb = -1;
    let maxIdx = 0;
    for (let i = 0; i < outputData.length; i++) {
      if (outputData[i] > maxProb) {
        maxProb = outputData[i];
        maxIdx = i;
      }
    }

    // Build probabilities map
    const classes = this.config!.classes;
    const probabilities: Record<string, number> = {};
    for (let i = 0; i < classes.length; i++) {
      probabilities[classes[i]] = outputData[i];
    }

    return {
      predictedClass: classes[maxIdx],
      classIndex: maxIdx,
      confidence: maxProb,
      probabilities,
      processingTimeMs: performance.now() - startTime,
    };
  }

  /**
   * Dispose of model resources
   */
  dispose(): void {
    this.model = null;
    this.preprocessor = null;
    this.config = null;
    this.isInitialized = false;
    this.initPromise = null;
    ExerciseClassifierService.instance = null;
  }
}

// Export singleton accessor functions for convenience
export const ExerciseClassifier = {
  /**
   * Initialize the classifier (call once at app startup)
   */
  initialize: () => ExerciseClassifierService.getInstance().initialize(),

  /**
   * Check if classifier is ready
   */
  isReady: () => ExerciseClassifierService.getInstance().isReady(),

  /**
   * Get available exercise classes
   */
  getClasses: () => ExerciseClassifierService.getInstance().getClasses(),

  /**
   * Classify from sensor windows
   */
  classify: (windows: SensorWindow[]) =>
    ExerciseClassifierService.getInstance().classify(windows),

  /**
   * Classify from raw sensor readings
   */
  classifyFromReadings: (readings: SensorReading[]) =>
    ExerciseClassifierService.getInstance().classifyFromReadings(readings),

  /**
   * Classify from pre-scaled features
   */
  classifyFromFeatures: (features: number[]) =>
    ExerciseClassifierService.getInstance().classifyFromFeatures(features),

  /**
   * Dispose resources
   */
  dispose: () => ExerciseClassifierService.getInstance().dispose(),
};

export { ExerciseClassifierService };
