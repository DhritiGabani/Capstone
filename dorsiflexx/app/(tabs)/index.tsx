import { IconSymbol } from "@/components/ui/icon-symbol";
import React from "react";
import { Pressable, SafeAreaView, StyleSheet, Text, View } from "react-native";

import { Colors } from "@/constants/theme";
import { useColorScheme } from "@/hooks/use-color-scheme";

type Day = {
  label: string;
  completedCount: number;
  isToday?: boolean;
};

export default function HomeScreen() {
  const colorScheme = useColorScheme();
  const theme = Colors[colorScheme ?? "light"];

  // HARDCODED VARIABLES /////////////////////////////
  const name = "Jane";
  const goalPerDay = 3;
  const days: Day[] = [
    { label: "Sun", completedCount: 2 },
    { label: "Mon", completedCount: 0 },
    { label: "Tue", completedCount: 2 },
    { label: "Wed", completedCount: 1 },
    { label: "Thu", completedCount: 0, isToday: true },
    { label: "Fri", completedCount: 0 },
    { label: "Sat", completedCount: 0 },
  ];
  ////////////////////////////////////////////////////

  const goalText = `${goalPerDay}x per day`;

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: theme.background }]}>
      <View style={styles.container}>
        {/* Top section */}
        <View style={styles.topSection}>
          <Text style={[styles.welcome, { color: theme.text }]}>
            Welcome back, {name}!
          </Text>

          <IconSymbol name="flame.fill" size={120} color={theme.orange} />

          <Text style={[styles.goal, { color: theme.text }]}>
            <Text style={styles.goalBold}>GOAL:</Text> {goalText}
          </Text>
        </View>

        {/* Middle section */}
        <View style={styles.middleSection}>
          <View style={styles.streakGrid}>
            {days.map((d) => (
              <View
                key={d.label}
                style={[
                  styles.dayGridCol,
                  d.isToday && {
                    borderWidth: 2,
                    borderColor: theme.darkPurple,
                  },
                ]}
              >
                <Text style={[styles.dayTopLabel, { color: theme.text }]}>
                  {d.label}
                </Text>

                <View style={styles.boxStack}>
                  {Array.from({ length: goalPerDay }).map((_, i) => {
                    const filled = i < d.completedCount;
                    return (
                      <View
                        key={i}
                        style={[
                          styles.goalBox,
                          {
                            backgroundColor: filled
                              ? theme.darkPurple
                              : theme.lightGrey,
                          },
                        ]}
                      >
                        {filled && (
                          <IconSymbol
                            name="checkmark"
                            size={14}
                            color={theme.white}
                          />
                        )}
                      </View>
                    );
                  })}
                </View>
              </View>
            ))}
          </View>
        </View>

        {/* Bottom section */}
        <View style={styles.bottomSection}>
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

const styles = StyleSheet.create({
  safe: {
    flex: 1,
  },

  container: {
    flex: 1,
    paddingHorizontal: 22,
    paddingTop: 12,
  },

  topSection: {
    paddingTop: 16,
    alignItems: "center",
    gap: 8,
  },

  middleSection: {
    alignItems: "center",
    flex: 1, // takes up remaining space
    justifyContent: "center",
  },

  bottomSection: {
    paddingBottom: 48,
    alignItems: "center",
  },

  welcome: {
    fontSize: 26,
    fontWeight: "400",
    paddingBottom: 8,
  },

  goal: {
    fontSize: 20,
  },

  goalBold: {
    fontWeight: "800",
  },

  streakGrid: {
    flexDirection: "row",
    justifyContent: "space-between",
    width: "100%",
    paddingHorizontal: 4,
  },

  dayGridCol: {
    alignItems: "center",
    width: 40,
    paddingVertical: 6,
    borderRadius: 12,
  },

  dayTopLabel: {
    fontSize: 14,
    marginBottom: 8,
  },

  boxStack: {
    gap: 8,
    alignItems: "center",
  },

  goalBox: {
    width: 22,
    height: 22,
    borderRadius: 6,
    alignItems: "center",
    justifyContent: "center",
  },

  buttons: {
    width: "80%",
    gap: 14,
    alignSelf: "center",
    maxWidth: 420,
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
