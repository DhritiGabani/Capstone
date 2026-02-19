import PillButton from "@/components/PillButton";
import { Stack, router } from "expo-router";
import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  SafeAreaView,
  Text,
  View,
} from "react-native";

export default function ExerciseInProgress() {
  const [isPaused, setIsPaused] = useState(false);

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

  const onPressCancel = useCallback(() => {
    confirmLeave(() => router.back());
  }, [confirmLeave]);

  return (
    <>
      <Stack.Screen
        options={{
          // Hide the default back button
          headerBackVisible: false,

          // Prevent iOS swipe-back (otherwise it can still trigger the “fade”)
          gestureEnabled: false,

          // Provide your own Cancel button that won't "half-navigate"
          headerLeft: () => (
            <Pressable
              onPress={onPressCancel}
              style={({ pressed }) => ({
                opacity: pressed ? 0.4 : 1,
                paddingHorizontal: 12,
              })}
              hitSlop={10}
            >
              <Text style={{ fontSize: 17, color: "#007AFF" }}>Cancel</Text>
            </Pressable>
          ),
        }}
      />

      <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
        <View className="flex-1 px-6 py-8 justify-center gap-14">
          <View className="items-center">
            <Text className="text-4xl font-semibold text-[#11181C] dark:text-[#ECEDEE] text-center">
              Exercise Session{"\n"}In Progress
            </Text>
          </View>

          <View className="items-center py-8">
            <View className="h-28 w-28 items-center justify-center">
              <ActivityIndicator
                size="large"
                animating={!isPaused}
                hidesWhenStopped={false}
                color="#8d44bc"
                style={{ transform: [{ scale: 3 }] }}
              />
            </View>

            <Text className="mt-4 text-lg text-[#11181C] dark:text-[#ECEDEE]">
              {isPaused ? "Paused" : "Collecting data"}
            </Text>
          </View>

          <View className="items-center">
            <View className="w-full px-5 flex-row gap-8">
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
                  onPress={() => router.replace("/end-exercise")}
                />
              </View>
            </View>
          </View>
        </View>
      </SafeAreaView>
    </>
  );
}
