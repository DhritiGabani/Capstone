import PillButton from "@/components/PillButton";
import { Stack, router, useLocalSearchParams } from "expo-router";
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  SafeAreaView,
  Text,
  View,
} from "react-native";

function formatElapsedTime(totalSeconds: number) {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  const pad = (n: number) => String(n).padStart(2, "0");

  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
}

export default function ExerciseInProgress() {
  const { session_id } = useLocalSearchParams<{ session_id: string }>();
  const [isPaused, setIsPaused] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (isPaused || isProcessing) return;

    const interval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [isPaused, isProcessing]);

  const confirmLeave = useCallback((onConfirm: () => void) => {
    Alert.alert(
      "Cancel session?",
      "Are you sure you want to cancel your session? Your data from this session will be lost.",
      [
        { text: "Close", style: "cancel" },
        { text: "Cancel session", style: "destructive", onPress: onConfirm },
      ],
    );
  }, []);

  const confirmEndSession = useCallback((onConfirm: () => void) => {
    Alert.alert("End session?", "Are you sure you want to end this session?", [
      { text: "Keep going", style: "cancel" },
      { text: "End session", style: "destructive", onPress: onConfirm },
    ]);
  }, []);

  const onPressCancel = useCallback(() => {
    confirmLeave(() => router.back());
  }, [confirmLeave]);

  const handleEndSession = useCallback(async () => {
    setIsProcessing(true);

    const mockAnalysis = {
      rep_counts: {
        "Ankle Rotation": 6,
        "Calf Raises": 6,
      },
      rep_durations: {
        "Ankle Rotation": {
          mean_duration_s: 1.4,
        },
        "Calf Raises": {
          mean_duration_s: 1.2,
        },
      },
      rom_consistency: {
        "Ankle Rotation": {
          rep_rom_fraction: {
            1: 0.84,
            2: 0.88,
            3: 0.91,
            4: 0.87,
            5: 0.93,
            6: 0.9,
          },
        },
        "Calf Raises": {
          rep_rom_fraction: {
            1: 0.76,
            2: 0.8,
            3: 0.83,
            4: 0.81,
            5: 0.85,
            6: 0.84,
          },
        },
      },
      consistency_scores: {
        "Ankle Rotation": 90.5,
        "Calf Raises": 86.8,
      },
    };

    const mockExercises = [
      {
        exercise_type: "Ankle Rotation",
        repetitions: 6,
      },
      {
        exercise_type: "Calf Raises",
        repetitions: 6,
      },
    ];

    setTimeout(() => {
      router.replace({
        pathname: "/end-exercise",
        params: {
          session_id: session_id ?? "mock-session-123",
          duration_seconds: String(elapsedSeconds),
          total_samples: "720",
          exercises: JSON.stringify(mockExercises),
          analysis: JSON.stringify(mockAnalysis),
        },
      });
    }, 1500);
  }, [elapsedSeconds, session_id]);

  const onPressEndSession = useCallback(() => {
    confirmEndSession(() => handleEndSession());
  }, [confirmEndSession, handleEndSession]);

  return (
    <>
      <Stack.Screen
        options={{
          headerBackVisible: false,
          gestureEnabled: false,
          headerLeft: () => (
            <Pressable
              onPress={onPressCancel}
              className="px-3 active:opacity-40"
              hitSlop={10}
            >
              <Text className="text-[17px] text-[#007AFF]">Cancel</Text>
            </Pressable>
          ),
        }}
      />

      <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
        <View className="flex-1 justify-center gap-14 px-6 py-8">
          <View className="items-center">
            <Text className="text-center text-4xl font-semibold text-[#11181C] dark:text-[#ECEDEE]">
              {isProcessing
                ? "Processing\nSession..."
                : "Exercise Session\nIn Progress"}
            </Text>
          </View>

          <View className="items-center py-8">
            <View className="h-28 w-28 items-center justify-center">
              <ActivityIndicator
                size="large"
                animating={isProcessing || !isPaused}
                hidesWhenStopped={false}
                color="#8d44bc"
                className="scale-[3]"
              />
            </View>

            <Text className="mt-4 text-lg text-[#11181C] dark:text-[#ECEDEE]">
              {isProcessing
                ? "Analyzing your exercises..."
                : isPaused
                  ? "Paused"
                  : "Collecting data"}
            </Text>

            {!isProcessing && (
              <Text className="mt-4 text-2xl font-bold text-[#11181C] dark:text-[#ECEDEE]">
                Time Elapsed: {formatElapsedTime(elapsedSeconds)}
              </Text>
            )}
          </View>

          {!isProcessing && (
            <View className="items-center">
              <View className="w-full flex-row gap-8 px-4">
                <View className="flex-1">
                  <PillButton
                    title={isPaused ? "Continue" : "Pause"}
                    variant={isPaused ? "success" : "warning"}
                    onPress={() => setIsPaused((p) => !p)}
                  />
                </View>

                <View className="flex-1">
                  <PillButton
                    title="END SESSION"
                    variant="danger"
                    onPress={onPressEndSession}
                  />
                </View>
              </View>
            </View>
          )}
        </View>
      </SafeAreaView>
    </>
  );
}
