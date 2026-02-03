import { IconSymbol } from "@/components/ui/icon-symbol";
import React from "react";
import { Pressable, SafeAreaView, StyleSheet, Text, View } from "react-native";

import { Colors } from "@/constants/theme";
import { useColorScheme } from "@/hooks/use-color-scheme";

type Day = {
  label: string;
  // "check" = completed, "miss" = attempted but failed, "empty" = not done yet
  state: "check" | "miss" | "empty";
  isToday?: boolean;
};

export default function HomeScreen() {
  const colorScheme = useColorScheme();
  const theme = Colors[colorScheme ?? "light"];

  const name = "Jane";
  const goalText = "2x per day";

  const days: Day[] = [
    { label: "Sun", state: "check" },
    { label: "Mon", state: "miss" },
    { label: "Tue", state: "check" },
    { label: "Wed", state: "check" },
    { label: "Thu", state: "empty", isToday: true },
    { label: "Fri", state: "empty" },
    { label: "Sat", state: "empty" },
  ];

  return (
    <SafeAreaView style={styles.safe}>
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Text style={[styles.welcome, { color: theme.text }]}>
          Welcome back, {name}!
        </Text>

        <View style={styles.flameWrap}>
          <IconSymbol name="flame.fill" size={120} color={theme.orange} />
        </View>

        <Text style={[styles.goal, { color: theme.text }]}>
          <Text style={styles.goalBold}>GOAL:</Text> {goalText}
        </Text>

        <View style={styles.streakRow}>
          {days.map((d) => (
            <View key={d.label} style={styles.dayCol}>
              <View
                style={[
                  styles.dayCircle,
                  d.state === "check" && styles.circleCheck,
                  d.state === "miss" && styles.circleMiss,
                  d.state === "empty" && styles.circleEmpty,
                  d.isToday && styles.circleTodayRing,
                ]}
              >
                {d.state === "check" && (
                  <IconSymbol name="checkmark" size={18} color="#FFFFFF" />
                )}
                {d.state === "miss" && (
                  <IconSymbol name="xmark" size={18} color="#FFFFFF" />
                )}
              </View>
              <Text style={[styles.dayLabel, { color: theme.text }]}>
                {d.label}
              </Text>
            </View>
          ))}
        </View>

        <View style={styles.buttons}>
          <PillButton
            title={"View most recent\nexercise session"}
            onPress={() => {}}
            backgroundColor={theme.darkPurple}
            textColor={theme.white}
          />
          <PillButton
            title={"Start new\nexercise session"}
            onPress={() => {}}
            backgroundColor={theme.darkPurple}
            textColor={theme.white}
          />
        </View>
      </View>
    </SafeAreaView>
  );
}

function PillButton({
  title,
  onPress,
  backgroundColor,
  textColor,
}: {
  title: string;
  onPress: () => void;
  backgroundColor?: string;
  textColor?: string;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        backgroundColor && { backgroundColor },
        pressed && styles.pressed,
      ]}
    >
      <Text style={[styles.buttonText, textColor && { color: textColor }]}>
        {title}
      </Text>
    </Pressable>
  );
}

const PURPLE = "#8D44BC";
const MEDPURPLE = "#DCA5FF";

const GRAY = "#BFBFBF";

const styles = StyleSheet.create({
  safe: {
    flex: 1,
  },
  container: {
    flex: 1,
    alignItems: "center",
    paddingHorizontal: 22,
    paddingTop: 12,
  },
  welcome: {
    fontSize: 26,
    fontWeight: "400",
    marginTop: 10,
    marginBottom: 40,
  },
  flameWrap: {
    marginTop: 10,
    marginBottom: 0,
  },
  goal: {
    marginTop: 10,
    marginBottom: 20,
    fontSize: 20,
  },
  goalBold: {
    fontWeight: "800",
  },
  streakRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    width: "100%",
    paddingHorizontal: 4,
    marginTop: 6,
    marginBottom: 40,
  },
  dayCol: {
    alignItems: "center",
    width: 40,
  },
  dayCircle: {
    width: 26,
    height: 26,
    borderRadius: 13,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 6,
  },
  circleCheck: {
    backgroundColor: PURPLE,
  },
  circleMiss: {
    backgroundColor: MEDPURPLE,
    opacity: 0.95,
  },
  circleEmpty: {
    backgroundColor: GRAY,
  },
  circleTodayRing: {
    borderWidth: 2,
    borderColor: PURPLE,
    backgroundColor: GRAY,
  },
  dayLabel: {
    fontSize: 12,
    color: "#11181C",
  },

  buttons: {
    width: "80%",
    gap: 14,
    marginTop: 10,
  },
  button: {
    borderRadius: 999,
    paddingVertical: 16,
    paddingHorizontal: 22,
    alignItems: "center",
    justifyContent: "center",
  },
  pressed: {
    opacity: 0.9,
    transform: [{ scale: 0.99 }],
  },
  buttonText: {
    fontSize: 20,
    fontWeight: "700",
    textAlign: "center",
    lineHeight: 22,
  },
});
