import PillButton from "@/components/PillButton";
import { IconSymbol } from "@/components/ui/icon-symbol";
import { router } from "expo-router";
import React from "react";
import { SafeAreaView, ScrollView, Text, View } from "react-native";

type Day = {
  label: string;
  completedCount: number;
  isToday?: boolean;
};

export default function HomeScreen() {
  const userName = "Jane";
  const goalPerDay = 2;
  const mostRecentSessionDate = "2026-03-18";

  const days: Day[] = [
    { label: "Sun", completedCount: 2 },
    { label: "Mon", completedCount: 0 },
    { label: "Tue", completedCount: 2 },
    { label: "Wed", completedCount: 1 },
    { label: "Thu", completedCount: 0, isToday: true },
    { label: "Fri", completedCount: 0 },
    { label: "Sat", completedCount: 0 },
  ];

  const goalText = `${goalPerDay}x per day`;

  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
      <ScrollView
        contentContainerStyle={{ paddingVertical: 40 }}
        showsVerticalScrollIndicator={false}
      >
        <View className="gap-12 px-[22px]">
          <View className="items-center gap-2">
            <Text className="pb-2 text-[26px] text-[#11181C] dark:text-[#ECEDEE]">
              Welcome back, {userName}!
            </Text>

            <IconSymbol name="flame.fill" size={120} color="#FF7A28" />

            <Text className="text-xl text-[#11181C] dark:text-[#ECEDEE]">
              <Text className="font-extrabold">GOAL:</Text> {goalText}
            </Text>
          </View>

          <View className="items-center">
            <View className="max-w-[420px] flex-row gap-4 self-center">
              {days.map((d) => (
                <View
                  key={d.label}
                  className={`w-10 items-center rounded-xl py-1.5 ${
                    d.isToday ? "border-2 border-brand-purple-dark" : ""
                  }`}
                >
                  <Text className="mb-2 text-sm text-[#11181C] dark:text-[#ECEDEE]">
                    {d.label}
                  </Text>

                  <View className="items-center gap-2">
                    {Array.from({ length: goalPerDay }).map((_, i) => {
                      const filled = i < d.completedCount;
                      return (
                        <View
                          key={i}
                          className={`h-[22px] w-[22px] items-center justify-center rounded-md ${
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

          <View className="items-center">
            <View className="max-w-[420px] w-4/5 self-center gap-3.5">
              <PillButton
                title={"View most recent\nexercise session"}
                onPress={() =>
                  router.push({
                    pathname: "/exercise-summary",
                    params: { date: mostRecentSessionDate },
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
