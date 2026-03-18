import PillButton from "@/components/PillButton";
import DateTimePicker, {
  DateTimePickerEvent,
} from "@react-native-community/datetimepicker";
import React, { useState } from "react";
import {
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";

type ToggleOptionProps = {
  options: string[];
  selected: string;
  onSelect: (value: string) => void;
  className?: string;
};

function ToggleOption({
  options,
  selected,
  onSelect,
  className = "",
}: ToggleOptionProps) {
  return (
    <View
      className={`self-start flex-row overflow-hidden rounded-md border border-[#8D44BC] ${className}`}
    >
      {options.map((option, index) => {
        const isSelected = selected === option;
        return (
          <Pressable
            key={option}
            onPress={() => onSelect(option)}
            className={`px-4 py-1.5 ${
              isSelected ? "bg-[#8D44BC]" : "bg-transparent"
            } ${index !== options.length - 1 ? "border-r border-[#8D44BC]" : ""}`}
          >
            <Text
              className={`text-base ${
                isSelected
                  ? "font-semibold text-white"
                  : "text-[#333333] dark:text-[#AAAAAA]"
              }`}
            >
              {option}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

type StepperProps = {
  value: number;
  onDecrease: () => void;
  onIncrease: () => void;
  widthClassName?: string;
};

function Stepper({
  value,
  onDecrease,
  onIncrease,
  widthClassName = "w-[128px]",
}: StepperProps) {
  return (
    <View
      className={`h-9 flex-row overflow-hidden rounded-md border border-[#8D44BC] ${widthClassName}`}
    >
      <Pressable
        onPress={onDecrease}
        className="w-9 items-center justify-center bg-[#8D44BC]"
      >
        <Text className="text-lg font-semibold text-white">−</Text>
      </Pressable>

      <View className="flex-1 items-center justify-center bg-white dark:bg-[#151718]">
        <Text className="text-base text-[#2B2B2B] dark:text-[#ECEDEE]">
          {value}
        </Text>
      </View>

      <Pressable
        onPress={onIncrease}
        className="w-9 items-center justify-center bg-[#8D44BC]"
      >
        <Text className="text-lg font-semibold text-white">+</Text>
      </Pressable>
    </View>
  );
}

type SectionTitleProps = {
  children: React.ReactNode;
};

function SectionTitle({ children }: SectionTitleProps) {
  return (
    <Text className="mb-3 text-center text-[20px] font-medium tracking-wide text-[#11181C] dark:text-[#ECEDEE]">
      {children}
    </Text>
  );
}

const DAY_ORDER = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"] as const;
type DayAbbrev = (typeof DAY_ORDER)[number];

type NotificationItem = {
  id: number;
  days: DayAbbrev[];
  time: Date;
  isDayPickerOpen: boolean;
  isTimePickerOpen: boolean;
};

function arraysEqual(a: string[], b: string[]) {
  return a.length === b.length && a.every((value, index) => value === b[index]);
}

function getNotificationDayLabel(days: DayAbbrev[]) {
  const sortedDays = DAY_ORDER.filter((day) => days.includes(day));
  const weekdays: DayAbbrev[] = ["Mon", "Tue", "Wed", "Thu", "Fri"];

  if (sortedDays.length === 7) {
    return "Every day";
  }

  if (arraysEqual(sortedDays, weekdays)) {
    return "Weekdays";
  }

  if (sortedDays.length === 0) {
    return "Select days";
  }

  return `Every ${sortedDays.join(", ")}`;
}

function formatTime(date: Date) {
  return date.toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function ProfileSettingsScreen() {
  const [name, setName] = useState("Jane");
  const [height, setHeight] = useState("165");
  const [heightUnit, setHeightUnit] = useState("cm");

  const [shoeGender, setShoeGender] = useState("Women’s");
  const [shoeSize, setShoeSize] = useState(7);

  const [ankle, setAnkle] = useState("Right");

  const [goalFrequency, setGoalFrequency] = useState(2);
  const [goalPeriod, setGoalPeriod] = useState("Day");

  const [notifications, setNotifications] = useState<NotificationItem[]>([
    {
      id: 1,
      days: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
      time: new Date(2026, 2, 18, 8, 15),
      isDayPickerOpen: false,
      isTimePickerOpen: false,
    },
    {
      id: 2,
      days: ["Mon", "Tue", "Wed", "Thu", "Fri"],
      time: new Date(2026, 2, 18, 18, 30),
      isDayPickerOpen: false,
      isTimePickerOpen: false,
    },
  ]);

  const [nextNotificationId, setNextNotificationId] = useState(3);

  const addNotification = () => {
    setNotifications((prev) => [
      ...prev,
      {
        id: nextNotificationId,
        days: ["Mon", "Tue", "Wed", "Thu", "Fri"],
        time: new Date(2026, 2, 18, 12, 0),
        isDayPickerOpen: false,
        isTimePickerOpen: false,
      },
    ]);
    setNextNotificationId((prev) => prev + 1);
  };

  const removeNotification = (id: number) => {
    setNotifications((prev) =>
      prev.filter((notification) => notification.id !== id),
    );
  };

  const toggleDayPicker = (id: number) => {
    setNotifications((prev) =>
      prev.map((notification) =>
        notification.id === id
          ? {
              ...notification,
              isDayPickerOpen: !notification.isDayPickerOpen,
              isTimePickerOpen: false,
            }
          : { ...notification, isDayPickerOpen: false },
      ),
    );
  };

  const toggleNotificationDay = (id: number, day: DayAbbrev) => {
    setNotifications((prev) =>
      prev.map((notification) => {
        if (notification.id !== id) {
          return notification;
        }

        const alreadySelected = notification.days.includes(day);

        const nextDays = alreadySelected
          ? notification.days.filter((d) => d !== day)
          : [...notification.days, day];

        const sortedNextDays = DAY_ORDER.filter((d) => nextDays.includes(d));

        return {
          ...notification,
          days: sortedNextDays,
        };
      }),
    );
  };

  const toggleTimePicker = (id: number) => {
    setNotifications((prev) =>
      prev.map((notification) =>
        notification.id === id
          ? {
              ...notification,
              isTimePickerOpen: !notification.isTimePickerOpen,
              isDayPickerOpen: false,
            }
          : { ...notification, isTimePickerOpen: false },
      ),
    );
  };

  const closeTimePicker = (id: number) => {
    setNotifications((prev) =>
      prev.map((notification) =>
        notification.id === id
          ? {
              ...notification,
              isTimePickerOpen: false,
            }
          : notification,
      ),
    );
  };

  const setNotificationTime = (
    id: number,
    event: DateTimePickerEvent,
    selectedDate?: Date,
  ) => {
    if (Platform.OS === "android") {
      setNotifications((prev) =>
        prev.map((notification) => {
          if (notification.id !== id) {
            return notification;
          }

          if (event.type === "dismissed") {
            return {
              ...notification,
              isTimePickerOpen: false,
            };
          }

          return {
            ...notification,
            isTimePickerOpen: false,
            time: selectedDate ?? notification.time,
          };
        }),
      );
      return;
    }

    if (selectedDate) {
      setNotifications((prev) =>
        prev.map((notification) =>
          notification.id === id
            ? {
                ...notification,
                time: selectedDate,
              }
            : notification,
        ),
      );
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
      <ScrollView
        className="flex-1"
        contentContainerStyle={{
          paddingHorizontal: 14,
          paddingTop: 10,
          paddingBottom: 20,
        }}
        showsVerticalScrollIndicator={false}
      >
        <SectionTitle>PROFILE</SectionTitle>

        <View className="mb-2">
          <Text className="mb-1 text-[16px] font-semibold text-[#11181C] dark:text-[#ECEDEE]">
            Name
          </Text>
          <TextInput
            value={name}
            onChangeText={setName}
            placeholder="Enter name"
            placeholderTextColor="#7A7A7A"
            className="h-9 rounded-md border border-[#565656] bg-transparent px-3 text-[16px] text-[#11181C] dark:text-[#ECEDEE]"
          />
        </View>

        <View className="mb-2">
          <Text className="mb-1 text-[16px] font-semibold text-[#11181C] dark:text-[#ECEDEE]">
            Height
          </Text>
          <View className="flex-row items-center gap-3">
            <TextInput
              value={height}
              onChangeText={setHeight}
              keyboardType="numeric"
              className="h-9 flex-1 rounded-md border border-[#565656] bg-transparent px-3 text-[16px] text-[#11181C] dark:text-[#ECEDEE]"
            />
            <ToggleOption
              options={["cm", "in"]}
              selected={heightUnit}
              onSelect={setHeightUnit}
            />
          </View>
        </View>

        <View className="mb-2">
          <Text className="mb-1 text-[16px] font-semibold text-[#11181C] dark:text-[#ECEDEE]">
            Shoe Size
          </Text>
          <View className="flex-row items-center gap-3">
            <ToggleOption
              options={["Men’s", "Women’s"]}
              selected={shoeGender}
              onSelect={setShoeGender}
            />
            <Stepper
              value={shoeSize}
              onDecrease={() => setShoeSize((prev) => Math.max(1, prev - 1))}
              onIncrease={() => setShoeSize((prev) => prev + 1)}
              widthClassName="w-[100px]"
            />
          </View>
        </View>

        <View className="mb-8">
          <Text className="mb-1 text-[16px] font-semibold text-[#11181C] dark:text-[#ECEDEE]">
            Ankle
          </Text>
          <View className="items-start">
            <ToggleOption
              options={["Left", "Right"]}
              selected={ankle}
              onSelect={setAnkle}
            />
          </View>
        </View>

        <SectionTitle>GOAL SETTING</SectionTitle>

        <View className="mb-8 flex-row items-center justify-center gap-2">
          <Stepper
            value={goalFrequency}
            onDecrease={() => setGoalFrequency((prev) => Math.max(1, prev - 1))}
            onIncrease={() => setGoalFrequency((prev) => prev + 1)}
            widthClassName="w-[98px]"
          />
          <Text className="text-[16px] text-[#11181C] dark:text-[#ECEDEE]">
            times per
          </Text>
          <ToggleOption
            options={["Day", "Week"]}
            selected={goalPeriod}
            onSelect={setGoalPeriod}
          />
        </View>

        <View className="mb-3 flex-row items-center justify-center">
          <Text className="text-center text-[20px] font-medium tracking-wide text-[#11181C] dark:text-[#ECEDEE]">
            NOTIFICATIONS
          </Text>
          <Pressable className="ml-3" onPress={addNotification}>
            <Text className="text-[26px] font-medium text-[#11181C] dark:text-[#ECEDEE]">
              +
            </Text>
          </Pressable>
        </View>

        <View className="mb-2 items-center gap-2">
          {notifications.map((notification) => (
            <View key={notification.id} className="w-full items-center">
              <View className="flex-row items-center gap-2">
                <Pressable
                  onPress={() => toggleDayPicker(notification.id)}
                  className="h-9 w-[190px] flex-row items-center justify-between rounded-md border border-[#565656] px-3"
                >
                  <Text
                    numberOfLines={1}
                    className="flex-1 pr-2 text-[15px] text-[#11181C] dark:text-[#ECEDEE]"
                  >
                    {getNotificationDayLabel(notification.days)}
                  </Text>
                  <Text className="text-[13px] text-[#11181C] dark:text-[#ECEDEE]">
                    ▼
                  </Text>
                </Pressable>

                <Text className="text-[15px] text-[#11181C] dark:text-[#ECEDEE]">
                  at
                </Text>

                <Pressable
                  onPress={() => toggleTimePicker(notification.id)}
                  className="h-9 w-[90px] items-center justify-center rounded-md border border-[#565656] px-3"
                >
                  <Text className="text-[15px] text-[#11181C] dark:text-[#ECEDEE]">
                    {formatTime(notification.time)}
                  </Text>
                </Pressable>

                <Pressable
                  onPress={() => removeNotification(notification.id)}
                  className="h-9 w-9 items-center justify-center rounded-md border border-[#8D44BC]"
                >
                  <Text className="text-[22px] font-medium text-[#8D44BC]">
                    −
                  </Text>
                </Pressable>
              </View>

              {notification.isDayPickerOpen && (
                <View className="mt-2 w-[335px] rounded-md border border-[#565656] px-3 py-3">
                  <View className="flex-row flex-wrap gap-2">
                    {DAY_ORDER.map((day) => {
                      const isSelected = notification.days.includes(day);

                      return (
                        <Pressable
                          key={day}
                          onPress={() =>
                            toggleNotificationDay(notification.id, day)
                          }
                          className={`rounded-md border px-3 py-1.5 ${
                            isSelected
                              ? "border-[#8D44BC] bg-[#8D44BC]"
                              : "border-[#8D44BC] bg-transparent"
                          }`}
                        >
                          <Text
                            className={`text-[14px] ${
                              isSelected
                                ? "font-semibold text-white"
                                : "text-[#333333] dark:text-[#AAAAAA]"
                            }`}
                          >
                            {day}
                          </Text>
                        </Pressable>
                      );
                    })}
                  </View>
                </View>
              )}

              {notification.isTimePickerOpen && (
                <View className="mt-2 w-[335px] rounded-md border border-[#565656] px-3 py-3">
                  <DateTimePicker
                    value={notification.time}
                    mode="time"
                    display={Platform.OS === "ios" ? "spinner" : "default"}
                    onChange={(event, selectedDate) =>
                      setNotificationTime(notification.id, event, selectedDate)
                    }
                  />

                  {Platform.OS === "ios" && (
                    <View className="mt-3 items-end">
                      <Pressable
                        onPress={() => closeTimePicker(notification.id)}
                        className="rounded-md border border-[#8D44BC] px-4 py-1.5"
                      >
                        <Text className="font-semibold text-[#8D44BC]">
                          Done
                        </Text>
                      </Pressable>
                    </View>
                  )}
                </View>
              )}
            </View>
          ))}
        </View>

        <View className="mt-6 flex-row justify-between px-4">
          <View className="w-[48%]">
            <PillButton title="Cancel" onPress={() => {}} />
          </View>

          <View className="w-[48%]">
            <PillButton title="Save" onPress={() => {}} />
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
