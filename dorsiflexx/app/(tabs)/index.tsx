import NotificationBanner from "@/components/NotificationBanner";
import PillButton from "@/components/PillButton";
import { IconSymbol } from "@/components/ui/icon-symbol";
import BackendService from "@/src/services/api/BackendService";
import {
  consumeCompletedSession,
  subscribeToSessionComplete,
} from "@/src/services/SessionProcessing";
import { router, useFocusEffect } from "expo-router";
import React, { useCallback, useState } from "react";
import { SafeAreaView, ScrollView, Text, View } from "react-native";

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export default function HomeScreen() {
  const [userName, setUserName] = useState("Jane");
  const [goalFrequency, setGoalFrequency] = useState(2);
  const [sessionDates, setSessionDates] = useState<string[]>([]);
  const [mostRecentSessionDate, setMostRecentSessionDate] = useState<string | null>(null);

  const [bannerVisible, setBannerVisible] = useState(false);
  const [completedSessionDate, setCompletedSessionDate] = useState<string | null>(null);

  const showCompletionBanner = useCallback((date: string) => {
    setCompletedSessionDate(date);
    setBannerVisible(true);
  }, []);

  useFocusEffect(
    useCallback(() => {
      BackendService.getSettings()
        .then((s) => {
          setUserName(s.name);
          setGoalFrequency(s.goal_frequency);
        })
        .catch(() => {});

      BackendService.getSessionDates()
        .then((dates) => {
          setSessionDates(dates);
          setMostRecentSessionDate(dates.length > 0 ? dates[dates.length - 1] : null);
        })
        .catch(() => {});

      // If ML finished while we were on another screen, show banner now
      const already = consumeCompletedSession();
      if (already) {
        showCompletionBanner(already.date);
      }

      // Subscribe for ML completing while we're on this screen
      const unsub = subscribeToSessionComplete((session) => {
        showCompletionBanner(session.date);
      });

      return unsub;
    }, [showCompletionBanner]),
  );

  // Build a 7-day week view centered on today
  const today = new Date();
  const todayDow = today.getDay();

  const weekStart = new Date(today);
  weekStart.setDate(today.getDate() - todayDow);

  const days = DAY_LABELS.map((label, i) => {
    const d = new Date(weekStart);
    d.setDate(weekStart.getDate() + i);
    const dateStr = d.toISOString().slice(0, 10);
    const completedCount = sessionDates.filter((s) => s === dateStr).length;
    return { label, completedCount, isToday: i === todayDow };
  });

  const goalText = `${goalFrequency}x per day`;

  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
      <NotificationBanner
        message="Your exercise results are ready! Tap to view."
        variant="info"
        visible={bannerVisible}
        onHide={() => setBannerVisible(false)}
        durationMs={6000}
        onPress={
          completedSessionDate
            ? () => {
                setBannerVisible(false);
                router.push({
                  pathname: "/exercise-summary",
                  params: { date: completedSessionDate },
                });
              }
            : undefined
        }
      />

      <ScrollView
        contentContainerStyle={{ paddingVertical: 40 }}
        showsVerticalScrollIndicator={false}
      >
        <View className="px-[22px] gap-12">
          {/* Top section */}
          <View className="items-center gap-2">
            <Text className="text-[26px] pb-2 text-[#11181C] dark:text-[#ECEDEE]">
              Welcome back, {userName}!
            </Text>

            <IconSymbol name="flame.fill" size={120} color="#FF7A28" />

            <Text className="text-xl text-[#11181C] dark:text-[#ECEDEE]">
              <Text className="font-extrabold">GOAL:</Text> {goalText}
            </Text>
          </View>

          {/* Middle section */}
          <View className="items-center">
            <View className="flex-row gap-4 self-center max-w-[420px]">
              {days.map((d) => (
                <View
                  key={d.label}
                  className={`items-center w-10 py-1.5 rounded-xl ${
                    d.isToday ? "border-2 border-brand-purple-dark" : ""
                  }`}
                >
                  <Text className="text-sm mb-2 text-[#11181C] dark:text-[#ECEDEE]">
                    {d.label}
                  </Text>

                  <View className="gap-2 items-center">
                    {Array.from({ length: goalFrequency }).map((_, i) => {
                      const filled = i < d.completedCount;
                      return (
                        <View
                          key={i}
                          className={`w-[22px] h-[22px] rounded-md items-center justify-center ${
                            filled ? "bg-brand-purple-dark" : "bg-brand-grey"
                          }`}
                        >
                          {filled && (
                            <IconSymbol
                              name="checkmark"
                              size={14}
                              color="#fff"
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
          <View className="items-center">
            <View className="w-4/5 gap-3.5 self-center max-w-[420px]">
              <PillButton
                title={"View most recent\nexercise session"}
                disabled={!mostRecentSessionDate}
                onPress={() =>
                  router.push({
                    pathname: "/exercise-summary",
                    params: { date: mostRecentSessionDate! },
                  })
                }
              />
              <PillButton
                title={"Start new\nexercise session"}
                onPress={() => router.push("/start-exercise")}
              />
            </View>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
