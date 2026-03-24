import {
  DarkTheme,
  DefaultTheme,
  ThemeProvider,
} from "@react-navigation/native";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import "react-native-reanimated";
import { useEffect } from "react";

import { useColorScheme } from "@/hooks/use-color-scheme";
import BackendService from "@/src/services/api/BackendService";
import { scheduleGoalNotifications } from "@/src/services/NotificationService";

import "./../global.css";

export const unstable_settings = {
  anchor: "(tabs)",
};

export default function RootLayout() {
  const colorScheme = useColorScheme();

  // On startup, re-schedule notifications from saved settings
  useEffect(() => {
    BackendService.getSettings()
      .then((s) => scheduleGoalNotifications(s.notifications))
      .catch(() => {});
  }, []);

  return (
    <ThemeProvider value={colorScheme === "dark" ? DarkTheme : DefaultTheme}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen
          name="modal"
          options={{ presentation: "modal", title: "Modal" }}
        />
        <Stack.Screen
          name="start-exercise"
          options={{ title: "Start Exercise Session", headerBackTitle: "Home" }}
        />
        <Stack.Screen
          name="exercise-in-progress"
          options={{
            title: "Exercise in Progress",
            headerBackTitle: "Cancel",
            headerBackButtonMenuEnabled: false,
          }}
        />
        <Stack.Screen
          name="end-exercise"
          options={{
            title: "End Exercise",
            headerBackVisible: false,
            gestureEnabled: false,
          }}
        />
        <Stack.Screen
          name="exercise-summary"
          options={{
            title: "Exercise Summary",
            headerBackTitle: "Back",
          }}
        />
        <Stack.Screen
          name="start-kneetowall"
          options={{
            title: "Start Knee-to-Wall",
            headerBackTitle: "Measure",
          }}
        />
        <Stack.Screen
          name="measure-kneetowall"
          options={{
            title: "Measure Knee-to-Wall",
            headerBackTitle: "Cancel",
            headerBackButtonMenuEnabled: false,
          }}
        />
      </Stack>
      <StatusBar style="auto" />
    </ThemeProvider>
  );
}
