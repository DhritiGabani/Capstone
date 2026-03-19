import PillButton from "@/components/PillButton";
import { router, Stack } from "expo-router";
import {
  default as React,
  useCallback,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Alert,
  Image,
  Pressable,
  SafeAreaView,
  Text,
  useColorScheme,
  View,
} from "react-native";

type MeasureState = "idle" | "measuring" | "done";

export default function MeasureKneeToWall() {
  const scheme = useColorScheme();

  const [measureState, setMeasureState] = useState<MeasureState>("idle");
  const [countdown, setCountdown] = useState<number>(5);
  const [resultAngle, setResultAngle] = useState<number | null>(null);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const instructions = useMemo(
    () => [
      "Lunge forward with your toe and knee against the wall.",
      "Keeping your heel on the ground, slide your foot back until your knee just touches the wall.",
      "Be sure your knee stays over your toes. Do not cave inwards or outwards.",
    ],
    [],
  );

  const isMeasuring = measureState === "measuring";
  const hasResult = measureState === "done" && resultAngle !== null;

  const confirmLeave = useCallback((onConfirm: () => void) => {
    Alert.alert(
      "Cancel measurement?",
      "Are you sure you want to cancel this measurement? Any data will be lost.",
      [
        { text: "Close", style: "cancel" },
        {
          text: "Cancel measurement",
          style: "destructive",
          onPress: onConfirm,
        },
      ],
    );
  }, []);

  const onPressCancel = useCallback(() => {
    confirmLeave(() => router.back());
  }, [confirmLeave]);

  function clearTimer() {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }

  function generateRandomAngle() {
    return Number((25 + Math.random() * 20).toFixed(1));
  }

  function handleMeasure() {
    if (isMeasuring) return;

    clearTimer();
    setResultAngle(null);
    setMeasureState("measuring");
    setCountdown(5);

    intervalRef.current = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) {
          clearTimer();
          setResultAngle(generateRandomAngle());
          setMeasureState("done");
          return 1;
        }
        return c - 1;
      });
    }, 1000);
  }

  function handleSave() {
    router.replace("/measure");
  }

  function handleRedo() {
    clearTimer();
    setMeasureState("idle");
    setCountdown(5);
    setResultAngle(null);
  }

  const buttonTitle =
    measureState === "idle"
      ? "MEASURE"
      : measureState === "measuring"
        ? "Measuring,\nhold still..."
        : "Redo measurement";

  return (
    <>
      <Stack.Screen
        options={{
          headerBackVisible: false,
          gestureEnabled: false,
          headerLeft: () => (
            <Pressable
              onPress={onPressCancel}
              className="px-3 active:opacity-40"
              hitSlop={10}
            >
              <Text className="text-[17px] text-[#007AFF]">Cancel</Text>
            </Pressable>
          ),
        }}
      />

      <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
        <View className="flex-1 gap-8 px-6 pt-10">
          <View className="items-center">
            <Text className="text-center text-4xl font-bold text-[#11181C] dark:text-[#ECEDEE]">
              Instructions for{"\n"}knee-to-wall test:
            </Text>
          </View>

          <View className="relative w-full">
            <Image
              source={require("@/assets/images/KneeToWallImage.png")}
              style={{
                position: "absolute",
                right: 0,
                top: 0,
                width: 140,
                height: 140,
                tintColor: scheme === "dark" ? "#ECEDEE" : "#11181C",
              }}
              resizeMode="contain"
            />
            {instructions.map((line, idx) => {
              const isTopSection = idx === 0 || idx === 1;
              return (
                <View
                  key={idx}
                  className={`mb-2 flex-row ${isTopSection ? "pr-[130px]" : ""}`}
                >
                  <Text className="mr-2 text-lg font-bold text-[#11181C] dark:text-[#ECEDEE]">
                    {idx + 1}.
                  </Text>
                  <Text className="flex-1 text-lg leading-6 text-[#11181C] dark:text-[#ECEDEE]">
                    {line}
                  </Text>
                </View>
              );
            })}
          </View>

          <View className="items-center">
            <View className="max-w-[420px] w-4/5 self-center">
              <PillButton
                title={buttonTitle}
                onPress={measureState === "done" ? handleRedo : handleMeasure}
                disabled={isMeasuring}
              />

              {isMeasuring && (
                <Text className="mt-8 text-center text-5xl font-extrabold text-[#11181C] dark:text-[#ECEDEE]">
                  {countdown}
                </Text>
              )}

              {resultAngle !== null && (
                <View className="mt-6 items-center">
                  <Text className="text-lg text-[#11181C] dark:text-[#ECEDEE]">
                    Your measurement:
                  </Text>
                  <Text className="mt-2 text-5xl font-extrabold text-[#11181C] dark:text-[#ECEDEE]">
                    {resultAngle.toFixed(1)}°
                  </Text>
                </View>
              )}

              {hasResult && (
                <View className="mt-8">
                  <PillButton title="Save" onPress={handleSave} />
                </View>
              )}
            </View>

            {measureState === "idle" && (
              <Text className="mt-4 text-center text-[#11181C] opacity-70 dark:text-[#ECEDEE]">
                Press MEASURE when you're ready.
              </Text>
            )}
          </View>
        </View>
      </SafeAreaView>
    </>
  );
}
