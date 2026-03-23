import BackendService, { KTWMeasurement } from "@/src/services/api/BackendService";
import {
  ExerciseAccordionRow,
  ExerciseEntry,
  mapBackendToExercises,
} from "@/components/ExerciseCards";
import { Ionicons } from "@expo/vector-icons";
import { Stack, router, useLocalSearchParams } from "expo-router";
import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
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
  durationS: number | null;
  exercises: ExerciseEntry[];
};

type TimelineItem =
  | { type: "session"; sortTime: string; data: SessionEntry }
  | { type: "ktw"; sortTime: string; data: KTWMeasurement };

function formatDuration(seconds: number | null): string {
  if (seconds == null || seconds <= 0) return "";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  if (m === 0) return `${s}s`;
  return s === 0 ? `${m}m` : `${m}m ${s}s`;
}

function formatTimeLabel(isoString: string): string {
  const d = new Date(isoString);
  return d.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "America/New_York",
  });
}

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

  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!date) return;
    setLoading(true);
    Promise.all([
      BackendService.getSessionsByDate(date)
        .then((backendSessions) =>
          backendSessions.map((s) => ({
            type: "session" as const,
            sortTime: s.start_time,
            data: {
              id: s.session_id,
              sortTime: s.start_time,
              timeLabel: formatTimeLabel(s.start_time),
              durationS: s.duration_s,
              exercises: s.analysis
                ? mapBackendToExercises(s.analysis, s.session_id)
                : [],
            },
          })),
        )
        .catch(() => [] as TimelineItem[]),
      BackendService.getKTWByDate(date)
        .then((ktw) =>
          ktw.map((m) => ({
            type: "ktw" as const,
            sortTime: m.measured_at,
            data: m,
          })),
        )
        .catch(() => [] as TimelineItem[]),
    ])
      .then(([sessionItems, ktwItems]) => {
        const merged = [...sessionItems, ...ktwItems].sort((a, b) =>
          a.sortTime.localeCompare(b.sortTime),
        );
        setTimeline(merged);
      })
      .finally(() => setLoading(false));
  }, [date]);

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

        {loading && (
          <View className="items-center mt-8">
            <ActivityIndicator size="large" />
          </View>
        )}

        {!loading && timeline.length === 0 && (
          <View className="items-center mt-8">
            <Text className="text-[16px] text-[#11181C] dark:text-[#ECEDEE] opacity-60">
              No exercise sessions found for this date.
            </Text>
          </View>
        )}

        {timeline.map((item) => {
          if (item.type === "session") {
            const session = item.data;
            return (
              <View key={session.id} className="mb-8">
                <View className="mb-3 flex-row items-center gap-3">
                  <View className="min-w-[50px] self-start rounded-full bg-[#8d44bc] px-4 py-2">
                    <Text className="text-[16px] font-semibold text-[#fff]">
                      {session.timeLabel}
                    </Text>
                  </View>
                  {!!formatDuration(session.durationS) && (
                    <Text className="text-[15px] text-[#11181C] opacity-60 dark:text-[#ECEDEE]">
                      {formatDuration(session.durationS)}
                    </Text>
                  )}
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
                  {formatTimeLabel(m.measured_at)}
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
