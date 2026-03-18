import PillButton from "@/components/PillButton";
import { IconSymbol } from "@/components/ui/icon-symbol";
import BackendService from "@/src/services/api/BackendService";
import { router, useFocusEffect } from "expo-router";
import React, { useCallback, useState } from "react";
import { SafeAreaView, ScrollView, Text, View } from "react-native";

type Day = {
  label: string;
  completedCount: number;
  isToday?: boolean;
};

export default function HomeScreen() {
  const userName = "Jane";
  const goalPerDay = 2;

  const days: Day[] = [
    { label: "Sun", completedCount: 2 },
    { label: "Mon", completedCount: 0 },
    { label: "Tue", completedCount: 2 },
    { label: "Wed", completedCount: 1 },
    { label: "Thu", completedCount: 0, isToday: true },
    { label: "Fri", completedCount: 0 },
    { label: "Sat", completedCount: 0 },
  ];

  const [mostRecentSessionDate, setMostRecentSessionDate] = useState<string | null>(null);

  useFocusEffect(
    useCallback(() => {
      BackendService.getSessionDates()
        .then((dates) => {
          setMostRecentSessionDate(dates.length > 0 ? dates[dates.length - 1] : null);
        })
        .catch(() => {});
    }, []),
  );

  const goalText = `${goalPerDay}x per day`;

  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
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
                    {Array.from({ length: goalPerDay }).map((_, i) => {
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
