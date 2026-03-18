import PillButton from "@/components/PillButton";
import React, { useState } from "react";
import {
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

      <View className="flex-1 items-center justify-center bg-white">
        <Text className="text-base text-[#2B2B2B]">{value}</Text>
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

export default function ProfileSettingsScreen() {
  const [name, setName] = useState("Jane");
  const [height, setHeight] = useState("165");
  const [heightUnit, setHeightUnit] = useState("cm");

  const [shoeGender, setShoeGender] = useState("Women’s");
  const [shoeSize, setShoeSize] = useState(7);

  const [ankle, setAnkle] = useState("Right");

  const [goalFrequency, setGoalFrequency] = useState(2);
  const [goalPeriod, setGoalPeriod] = useState("Day");

  const [notification1Day, setNotification1Day] = useState("Every day");
  const [notification1Time, setNotification1Time] = useState("8:15 AM");
  const [notification2Day, setNotification2Day] = useState("Every day");
  const [notification2Time, setNotification2Time] = useState("6:30 PM");

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
          <Pressable className="ml-3">
            <Text className="text-[26px] font-medium text-[#11181C] dark:text-[#ECEDEE]">
              +
            </Text>
          </Pressable>
        </View>

        <View className="mb-2 items-center gap-2">
          <View className="flex-row items-center gap-2">
            <Pressable className="h-9 w-[110px] flex-row items-center justify-between rounded-md border border-[#565656] px-3">
              <Text className="text-[15px] text-[#11181C] dark:text-[#ECEDEE]">
                {notification1Day}
              </Text>
              <Text className="text-[13px] text-[#11181C] dark:text-[#ECEDEE]">
                ▼
              </Text>
            </Pressable>
            <Text className="text-[15px] text-[#11181C] dark:text-[#ECEDEE]">
              at
            </Text>
            <Pressable className="h-9 w-[114px] items-center justify-center rounded-md border border-[#565656] px-3">
              <Text className="text-[15px] text-[#11181C] dark:text-[#ECEDEE]">
                {notification1Time}
              </Text>
            </Pressable>
          </View>

          <View className="flex-row items-center gap-2">
            <Pressable className="h-9 w-[110px] flex-row items-center justify-between rounded-md border border-[#565656] px-3">
              <Text className="text-[15px] text-[#11181C] dark:text-[#ECEDEE]">
                {notification2Day}
              </Text>
              <Text className="text-[13px] text-[#11181C] dark:text-[#ECEDEE]">
                ▼
              </Text>
            </Pressable>
            <Text className="text-[15px] text-[#11181C] dark:text-[#ECEDEE]">
              at
            </Text>
            <Pressable className="h-9 w-[114px] items-center justify-center rounded-md border border-[#565656] px-3">
              <Text className="text-[15px] text-[#11181C] dark:text-[#ECEDEE]">
                {notification2Time}
              </Text>
            </Pressable>
          </View>
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
