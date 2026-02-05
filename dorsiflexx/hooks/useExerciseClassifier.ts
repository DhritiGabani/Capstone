/**
 * React hook for exercise classification
 * Handles initialization lifecycle and provides classification methods
 */

import { useState, useEffect, useCallback } from 'react';
import {
  ExerciseClassifier,
  ClassificationResult,
  SensorWindow,
  SensorReading,
} from '../src/services/ml';

interface UseExerciseClassifierState {
  isReady: boolean;
  isLoading: boolean;
  error: Error | null;
  classes: string[];
}

interface UseExerciseClassifierReturn extends UseExerciseClassifierState {
  /**
   * Classify exercise from 8 sensor windows
   */
  classify: (windows: SensorWindow[]) => Promise<ClassificationResult>;

  /**
   * Classify exercise from 8 raw sensor readings
   */
  classifyFromReadings: (readings: SensorReading[]) => Promise<ClassificationResult>;

  /**
   * Classify exercise from 64 pre-scaled features
   */
  classifyFromFeatures: (features: number[]) => Promise<ClassificationResult>;

  /**
   * Retry initialization if it failed
   */
  retry: () => void;
}

/**
 * Hook for using the exercise classifier in React components
 *
 * @example
 * ```tsx
 * function ExerciseScreen() {
 *   const { isReady, isLoading, error, classify } = useExerciseClassifier();
 *
 *   if (isLoading) return <Text>Loading model...</Text>;
 *   if (error) return <Text>Error: {error.message}</Text>;
 *   if (!isReady) return <Text>Model not ready</Text>;
 *
 *   const handleClassify = async () => {
 *     const result = await classify(sensorWindows);
 *     console.log('Predicted:', result.predictedClass);
 *   };
 *
 *   return <Button onPress={handleClassify} title="Classify" />;
 * }
 * ```
 */
export function useExerciseClassifier(): UseExerciseClassifierReturn {
  const [state, setState] = useState<UseExerciseClassifierState>({
    isReady: false,
    isLoading: true,
    error: null,
    classes: [],
  });

  const [initAttempt, setInitAttempt] = useState(0);

  useEffect(() => {
    let isMounted = true;

    const initialize = async () => {
      try {
        setState(prev => ({ ...prev, isLoading: true, error: null }));

        await ExerciseClassifier.initialize();

        if (isMounted) {
          setState({
            isReady: ExerciseClassifier.isReady(),
            isLoading: false,
            error: null,
            classes: ExerciseClassifier.getClasses(),
          });
        }
      } catch (err) {
        if (isMounted) {
          setState({
            isReady: false,
            isLoading: false,
            error: err instanceof Error ? err : new Error(String(err)),
            classes: [],
          });
        }
      }
    };

    initialize();

    return () => {
      isMounted = false;
    };
  }, [initAttempt]);

  const classify = useCallback(
    async (windows: SensorWindow[]): Promise<ClassificationResult> => {
      if (!state.isReady) {
        throw new Error('Classifier not ready');
      }
      return ExerciseClassifier.classify(windows);
    },
    [state.isReady]
  );

  const classifyFromReadings = useCallback(
    async (readings: SensorReading[]): Promise<ClassificationResult> => {
      if (!state.isReady) {
        throw new Error('Classifier not ready');
      }
      return ExerciseClassifier.classifyFromReadings(readings);
    },
    [state.isReady]
  );

  const classifyFromFeatures = useCallback(
    async (features: number[]): Promise<ClassificationResult> => {
      if (!state.isReady) {
        throw new Error('Classifier not ready');
      }
      return ExerciseClassifier.classifyFromFeatures(features);
    },
    [state.isReady]
  );

  const retry = useCallback(() => {
    setInitAttempt(prev => prev + 1);
  }, []);

  return {
    ...state,
    classify,
    classifyFromReadings,
    classifyFromFeatures,
    retry,
  };
}
