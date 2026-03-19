import BackendService from "@/src/services/api/BackendService";
import { Ionicons } from "@expo/vector-icons";
import DateTimePicker, {
  DateTimePickerEvent,
} from "@react-native-community/datetimepicker";
import { router, useFocusEffect } from "expo-router";
import React, { useCallback, useMemo, useState } from "react";
import {
  Modal,
  Platform,
  Pressable,
  SafeAreaView,
  Text,
  View,
  useColorScheme,
} from "react-native";
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

function fromDateString(dateString: string) {
  const [year, month, day] = dateString.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function getTwoWeeksAgo(date: Date) {
  const d = new Date(date);
  d.setDate(d.getDate() - 14);
  return d;
}

export default function HistoryCalendarScreen() {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";

  const today = new Date();
  const todayString = toLocalDateString(today);

  const [completedExerciseDates, setCompletedExerciseDates] = useState<
    string[]
  >([]);

  const [showShareModal, setShowShareModal] = useState(false);
  const [startDate, setStartDate] = useState<Date>(getTwoWeeksAgo(today));
  const [endDate, setEndDate] = useState<Date>(today);

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
    card: isDark ? "#1E2224" : "#FFFFFF",
    border: isDark ? "#3A3F42" : "#D9D2E3",
    overlay: "rgba(0,0,0,0.4)",
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
    if (
      day.dateString !== todayString &&
      !completedExerciseDates.includes(day.dateString)
    )
      return;

    router.push({
      pathname: "/exercise-summary",
      params: { date: day.dateString },
    });
  };

  const handleOpenShareModal = () => {
    setStartDate(getTwoWeeksAgo(today));
    setEndDate(today);
    setShowShareModal(true);
  };

  const handleStartDateChange = (
    _event: DateTimePickerEvent,
    selectedDate?: Date,
  ) => {
    if (!selectedDate) return;

    setStartDate(selectedDate);

    if (selectedDate > endDate) {
      setEndDate(selectedDate);
    }
  };

  const handleEndDateChange = (
    _event: DateTimePickerEvent,
    selectedDate?: Date,
  ) => {
    if (!selectedDate) return;

    if (selectedDate < startDate) {
      setEndDate(startDate);
      return;
    }

    setEndDate(selectedDate);
  };

  const handleShare = () => {
    const start = toLocalDateString(startDate);
    const end = toLocalDateString(endDate);

    console.log("Share history from", start, "to", end);

    setShowShareModal(false);

    // replace this later with actual export/share logic
    // for example:
    // router.push({
    //   pathname: "/export-history",
    //   params: { start_date: start, end_date: end },
    // });
  };

  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
      <Pressable
        onPress={handleOpenShareModal}
        className="absolute right-6 top-16 z-10 p-2"
      >
        <Ionicons name="share-outline" size={36} color={colors.text} />
      </Pressable>

      <View className="flex-1 px-6 pt-36">
        <View>
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

      <Modal
        visible={showShareModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowShareModal(false)}
      >
        <Pressable
          className="flex-1 items-center justify-center px-6"
          style={{ backgroundColor: colors.overlay }}
          onPress={() => setShowShareModal(false)}
        >
          <Pressable
            className="w-full max-w-[420px] rounded-3xl px-5 py-6"
            style={{ backgroundColor: colors.card }}
            onPress={() => {}}
          >
            <Text
              className="mb-5 text-center text-2xl font-bold"
              style={{ color: colors.text }}
            >
              Export History
            </Text>

            <View className="mb-5">
              <Text
                className="mb-2 text-xl font-bold"
                style={{ color: colors.text }}
              >
                Start
              </Text>

              <View
                className="h-36 justify-center overflow-hidden rounded-2xl"
                style={{ borderWidth: 1, borderColor: colors.border }}
              >
                <DateTimePicker
                  value={startDate}
                  mode="date"
                  display={Platform.OS === "ios" ? "spinner" : "default"}
                  onChange={handleStartDateChange}
                  maximumDate={today}
                  textColor={colors.text}
                  themeVariant={isDark ? "dark" : "light"}
                  style={
                    Platform.OS === "ios"
                      ? { transform: [{ scaleY: 0.9 }] }
                      : undefined
                  }
                />
              </View>
            </View>

            <View className="mb-6">
              <Text
                className="mb-2 text-xl font-bold"
                style={{ color: colors.text }}
              >
                End
              </Text>

              <View
                className="h-36 justify-center overflow-hidden rounded-2xl"
                style={{ borderWidth: 1, borderColor: colors.border }}
              >
                <DateTimePicker
                  value={endDate}
                  mode="date"
                  display={Platform.OS === "ios" ? "spinner" : "default"}
                  onChange={handleEndDateChange}
                  minimumDate={startDate}
                  maximumDate={today}
                  textColor={colors.text}
                  themeVariant={isDark ? "dark" : "light"}
                  style={
                    Platform.OS === "ios"
                      ? { transform: [{ scaleY: 0.9 }] }
                      : undefined
                  }
                />
              </View>
            </View>

            <View className="flex-row justify-between gap-3">
              <Pressable
                onPress={() => setShowShareModal(false)}
                className="flex-1 items-center rounded-full border py-3"
                style={{ borderColor: colors.purple }}
              >
                <Text
                  className="text-base font-semibold"
                  style={{ color: colors.purple }}
                >
                  Cancel
                </Text>
              </Pressable>

              <Pressable
                onPress={handleShare}
                className="flex-1 items-center rounded-full py-3"
                style={{ backgroundColor: colors.purple }}
              >
                <Text className="text-base font-semibold text-white">
                  Share
                </Text>
              </Pressable>
            </View>
          </Pressable>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}
