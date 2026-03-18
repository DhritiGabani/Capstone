import BackendService from "@/src/services/api/BackendService";
import { Ionicons } from "@expo/vector-icons";
import { router, useFocusEffect } from "expo-router";
import React, { useCallback, useMemo, useState } from "react";
import { Pressable, SafeAreaView, View, useColorScheme } from "react-native";
import { Calendar, DateData } from "react-native-calendars";

type MarkedDate = {
  disableTouchEvent?: boolean;
  customStyles?: {
    container?: Record<string, any>;
    text?: Record<string, any>;
  };
};

function toLocalDateString(date: Date) {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function isPastDate(dateString: string, todayString: string) {
  return dateString < todayString;
}

export default function HistoryCalendarScreen() {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";

  const today = new Date();
  const todayString = toLocalDateString(today);

  const [completedExerciseDates, setCompletedExerciseDates] = useState<string[]>([]);

  useFocusEffect(
    useCallback(() => {
      BackendService.getSessionDates()
        .then((dates) => {
          setCompletedExerciseDates(dates);
        })
        .catch((err) => {
          console.error("Failed to fetch session dates:", err);
          setCompletedExerciseDates([]);
        });
    }, []),
  );

  const colors = {
    bg: isDark ? "#151718" : "#F5F1F8",
    text: isDark ? "#ECEDEE" : "#11181C",
    purple: "#8d44bc",
  };

  const markedDates = useMemo<Record<string, MarkedDate>>(() => {
    const marks: Record<string, MarkedDate> = {};

    for (const date of completedExerciseDates) {
      if (isPastDate(date, todayString) || date === todayString) {
        marks[date] = {
          customStyles: {
            container: {
              backgroundColor: colors.purple,
              borderRadius: 999,
              width: 38,
              height: 38,
              alignItems: "center",
              justifyContent: "center",
            },
            text: {
              color: "#fff",
              fontSize: 18,
              fontWeight: "500",
            },
          },
        };
      }
    }

    const didExerciseToday = completedExerciseDates.includes(todayString);

    marks[todayString] = {
      customStyles: {
        container: {
          backgroundColor: didExerciseToday ? colors.purple : "transparent",
          borderWidth: 3,
          borderColor: colors.text,
          borderRadius: 999,
          width: 38,
          height: 38,
          alignItems: "center",
          justifyContent: "center",
        },
        text: {
          color: didExerciseToday ? "#fff" : colors.text,
          fontSize: 18,
          fontWeight: "500",
        },
      },
    };

    return marks;
  }, [completedExerciseDates, todayString, colors.purple, colors.text]);

  const handleDayPress = (day: DateData) => {
    if (day.dateString !== todayString && !completedExerciseDates.includes(day.dateString)) return;

    router.push({
      pathname: "/exercise-summary",
      params: { date: day.dateString },
    });
  };

  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
      <Pressable
        onPress={() => console.log("Export history")}
        className="absolute right-6 top-16 p-2"
      >
        <Ionicons name="share-outline" size={36} color={colors.text} />
      </Pressable>
      <View className="flex-1 px-6 pt-36">
        <View className="rounded-none">
          <Calendar
            initialDate={todayString}
            onDayPress={handleDayPress}
            enableSwipeMonths
            hideExtraDays
            markingType="custom"
            markedDates={markedDates}
            renderArrow={(direction) => (
              <Ionicons
                name={direction === "left" ? "chevron-back" : "chevron-forward"}
                size={26}
                color={colors.text}
              />
            )}
            style={{
              backgroundColor: "transparent",
            }}
            theme={{
              calendarBackground: "transparent",
              backgroundColor: "transparent",

              monthTextColor: colors.text,
              textMonthFontSize: 22,
              textMonthFontWeight: "700",

              textSectionTitleColor: colors.text,
              textDayHeaderFontSize: 15,
              textDayFontSize: 18,
              dayTextColor: colors.text,
              textDisabledColor: "transparent",

              todayTextColor: colors.text,
              arrowColor: colors.text,
            }}
          />
        </View>
      </View>
    </SafeAreaView>
  );
}
