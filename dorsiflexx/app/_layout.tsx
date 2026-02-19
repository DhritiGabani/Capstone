import {
  DarkTheme,
  DefaultTheme,
  ThemeProvider,
} from "@react-navigation/native";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import "react-native-reanimated";

import { useColorScheme } from "@/hooks/use-color-scheme";

import "./../global.css";

export const unstable_settings = {
  anchor: "(tabs)",
};

export default function RootLayout() {
  const colorScheme = useColorScheme();

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
      </Stack>
      <StatusBar style="auto" />
    </ThemeProvider>
  );
}
