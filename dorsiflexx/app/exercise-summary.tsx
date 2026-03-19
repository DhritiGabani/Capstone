import {
  ExerciseAccordionRow,
  ExerciseEntry,
} from "@/components/ExerciseCards";
import { Ionicons } from "@expo/vector-icons";
import { Stack, router, useLocalSearchParams } from "expo-router";
import React, { useMemo, useState } from "react";
import {
  Pressable,
  SafeAreaView,
  ScrollView,
  Text,
  View,
  useColorScheme,
} from "react-native";

type SessionEntry = {
  id: string;
  sortTime: string;
  timeLabel: string;
  exercises: ExerciseEntry[];
};

type KTWEntry = {
  id: string;
  measured_at: string;
  angle_deg: number;
};

type TimelineItem =
  | { type: "session"; sortTime: string; data: SessionEntry }
  | { type: "ktw"; sortTime: string; data: KTWEntry };

function formatDateLabel(dateString?: string | string[]) {
  if (!dateString || Array.isArray(dateString)) return "";

  const [year, month, day] = dateString.split("-").map(Number);
  if (!year || !month || !day) return "";

  const d = new Date(year, month - 1, day);

  return d.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

export default function HistorySingleScreen() {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";

  const { date } = useLocalSearchParams<{ date: string }>();
  const selectedDateLabel = useMemo(() => formatDateLabel(date), [date]);

  const timeline = useMemo<TimelineItem[]>(
    () => [
      {
        type: "session",
        sortTime: "2026-03-18T09:00:00",
        data: {
          id: "session-1",
          sortTime: "2026-03-18T09:00:00",
          timeLabel: "9:00 AM",
          exercises: [
            {
              id: "session-1-ankle",
              displayName: "ANKLE ROTATIONS",
              type: "ankle_circles_cw",
              repetitions: 10,
              averageSpeed: 1.3,
              percentMaxROM: [0.82, 0.91, 0.95, 0.88, 0.97, 0.93, 0.9, 0.96],
              consistencyScore: 91.4,
            },
            {
              id: "session-1-calf",
              displayName: "CALF RAISES",
              type: "calf_raises_on_step",
              repetitions: 12,
              averageSpeed: 1.1,
              percentMaxROM: [0.75, 0.8, 0.84, 0.82, 0.88, 0.86, 0.83, 0.89],
              consistencyScore: 88.2,
            },
          ],
        },
      },
      {
        type: "session",
        sortTime: "2026-03-18T14:30:00",
        data: {
          id: "session-2",
          sortTime: "2026-03-18T14:30:00",
          timeLabel: "2:30 PM",
          exercises: [
            {
              id: "session-2-calf",
              displayName: "CALF RAISES",
              type: "calf_raises_on_step",
              repetitions: 15,
              averageSpeed: 1.0,
              percentMaxROM: [0.78, 0.83, 0.85, 0.87, 0.86, 0.9, 0.88, 0.91],
              consistencyScore: 90.1,
            },
            {
              id: "session-2-heel",
              displayName: "HEEL WALKING",
              type: "heel_walks",
              duration: 24,
              numberOfSteps: 16,
              repAngles: [8.4, 9.1, 10.3, 9.8, 10.7, 11.2, 10.6, 11.0],
              meanAngleDeg: 10.1,
            },
          ],
        },
      },
      {
        type: "ktw",
        sortTime: "2026-03-18T19:15:00",
        data: {
          id: "ktw-1",
          measured_at: "2026-03-18T19:15:00",
          angle_deg: 28.7,
        },
      },
    ],
    [],
  );

  const [expandedById, setExpandedById] = useState<Record<string, boolean>>({});

  const toggleExercise = (exerciseId: string) => {
    setExpandedById((prev) => ({
      ...prev,
      [exerciseId]: !prev[exerciseId],
    }));
  };

  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
      <Stack.Screen
        options={{
          headerLeft: () => (
            <Pressable
              onPress={() => {
                if (router.canGoBack()) {
                  router.back();
                } else {
                  router.replace("/(tabs)");
                }
              }}
              style={{ paddingLeft: 4 }}
            >
              <Ionicons
                name="chevron-back"
                size={28}
                color={isDark ? "#ECEDEE" : "#11181C"}
              />
            </Pressable>
          ),
        }}
      />

      <ScrollView
        className="flex-1"
        contentContainerStyle={{
          paddingHorizontal: 24,
          paddingTop: 36,
          paddingBottom: 36,
        }}
        showsVerticalScrollIndicator={false}
      >
        <View className="mb-8 flex-row items-center justify-center">
          <Text className="text-[22px] font-semibold text-[#11181C] dark:text-[#ECEDEE]">
            {selectedDateLabel}
          </Text>
        </View>

        {timeline.map((item) => {
          if (item.type === "session") {
            const session = item.data;

            return (
              <View key={session.id} className="mb-8">
                <View className="mb-3 min-w-[50px] self-start rounded-full bg-[#8d44bc] px-4 py-2">
                  <Text className="text-[16px] font-semibold text-[#fff]">
                    {session.timeLabel}
                  </Text>
                </View>

                <View className="mb-1 h-[1px] w-full bg-[#8C8C8C] dark:bg-[#6C6C6C]" />

                {session.exercises.map((exercise) => (
                  <ExerciseAccordionRow
                    key={exercise.id}
                    exercise={exercise}
                    expanded={!!expandedById[exercise.id]}
                    onToggle={() => toggleExercise(exercise.id)}
                    isDark={isDark}
                  />
                ))}
              </View>
            );
          }

          const m = item.data;

          return (
            <View key={`ktw-${m.id}`} className="mb-8">
              <View className="mb-3 min-w-[50px] self-start rounded-full bg-[#8d44bc] px-4 py-2">
                <Text className="text-[16px] font-semibold text-[#fff]">
                  7:15 PM
                </Text>
              </View>

              <View className="mb-1 h-[1px] w-full bg-[#8C8C8C] dark:bg-[#6C6C6C]" />

              <View className="w-full">
                <Pressable
                  onPress={() => toggleExercise(`ktw-${m.id}`)}
                  className="flex-row items-center justify-between py-2"
                >
                  <Text className="text-[18px] font-semibold text-[#11181C] dark:text-[#ECEDEE]">
                    KNEE-TO-WALL TEST
                  </Text>
                  <Ionicons
                    name={expandedById[`ktw-${m.id}`] ? "remove" : "add"}
                    size={26}
                    color={isDark ? "#ECEDEE" : "#11181C"}
                  />
                </Pressable>

                {expandedById[`ktw-${m.id}`] && (
                  <View className="bg-[#eee] px-3 py-3 dark:bg-[#2B2D31]">
                    <Text className="text-[16px] text-[#11181C] dark:text-[#ECEDEE]">
                      <Text className="font-semibold">Ankle angle:</Text>{" "}
                      {m.angle_deg.toFixed(1)}°
                    </Text>
                  </View>
                )}

                <View className="h-[1px] w-full bg-[#8C8C8C] dark:bg-[#6C6C6C]" />
              </View>
            </View>
          );
        })}
      </ScrollView>
    </SafeAreaView>
  );
}
