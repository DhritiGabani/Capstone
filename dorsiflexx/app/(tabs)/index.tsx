import { IconSymbol } from "@/components/ui/icon-symbol";
import React from "react";
import { Pressable, SafeAreaView, Text, View } from "react-native";

type Day = {
  label: string;
  completedCount: number;
  isToday?: boolean;
};

export default function HomeScreen() {
  // HARDCODED VARIABLES /////////////////////////////
  const name = "Jane";
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
  ////////////////////////////////////////////////////

  const goalText = `${goalPerDay}x per day`;

  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
      <View className="flex-1 px-[22px] pt-3">
        {/* Top section */}
        <View className="pt-4 items-center gap-2">
          <Text className="text-[26px] pb-2 text-[#11181C] dark:text-[#ECEDEE]">
            Welcome back, {name}!
          </Text>

          <IconSymbol name="flame.fill" size={120} color="#FF7A28" />

          <Text className="text-xl text-[#11181C] dark:text-[#ECEDEE]">
            <Text className="font-extrabold">GOAL:</Text> {goalText}
          </Text>
        </View>

        {/* Middle section */}
        <View className="items-center flex-1 justify-center">
          <View className="flex-row justify-between w-full px-1">
            {days.map((d) => (
              <View
                key={d.label}
                className={`items-center w-10 py-1.5 rounded-xl ${
                  d.isToday ? "border-2 border-brand-purple" : ""
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
                          filled ? "bg-brand-purple" : "bg-brand-grey"
                        }`}
                      >
                        {filled && (
                          <IconSymbol name="checkmark" size={14} color="#fff" />
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
        <View className="pb-12 items-center">
          <View className="w-4/5 gap-3.5 self-center max-w-[420px]">
            <PillButton
              title={"View most recent\nexercise session"}
              onPress={() => {}}
            />
            <PillButton
              title={"Start new\nexercise session"}
              onPress={() => {}}
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
}: {
  title: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      className="
        rounded-full 
        py-4 px-[22px] 
        items-center justify-center 
        bg-brand-purple
        active:opacity-80
        active:scale-95
      "
    >
      <Text className="text-xl font-bold text-center leading-[22px] text-white">
        {title}
      </Text>
    </Pressable>
  );
}
