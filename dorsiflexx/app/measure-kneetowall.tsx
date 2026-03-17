import PillButton from "@/components/PillButton";
import BackendService from "@/src/services/api/BackendService";
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
  const [angleOverTime, setAngleOverTime] = useState<Record<string, number> | null>(null);

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
        { text: "Cancel measurement", style: "destructive", onPress: onConfirm },
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

  async function handleMeasure() {
    if (isMeasuring) return;

    clearTimer();
    setResultAngle(null);
    setAngleOverTime(null);
    setMeasureState("measuring");
    setCountdown(5);

    try {
      await BackendService.startKTW();
    } catch (e: any) {
      Alert.alert("Connection Failed", e.message || "Could not start KTW session.");
      setMeasureState("idle");
      return;
    }

    intervalRef.current = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) {
          clearTimer();
          BackendService.stopKTW()
            .then((result) => {
              setResultAngle(result.smallest_angle_deg);
              setAngleOverTime(result.angle_over_time);
              setMeasureState("done");
            })
            .catch((e) => {
              Alert.alert("Measurement Failed", e.message || "Could not get measurement.");
              setMeasureState("idle");
            });
          return 1;
        }
        return c - 1;
      });
    }, 1000);
  }

  function handleSave(angle: number, aot: Record<string, number> | null) {
    Alert.prompt(
      "Enter Your Name",
      "Your name will appear on the leaderboard!",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "OK",
          onPress: (name?: string) => {
            // Fire-and-forget — navigate away immediately, never surface errors
            BackendService.saveKTW(
              angle,
              aot ?? undefined,
              name?.trim() || "Anonymous",
            ).catch(() => {});
            router.replace("/measure");
          },
        },
      ],
      "plain-text",
    );
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
        <View className="flex-1 px-6 pt-10 gap-8">
          {/* Top section */}
          <View className="items-center">
            <Text className="text-4xl font-bold text-[#11181C] dark:text-[#ECEDEE] text-center">
              Instructions for{"\n"}knee-to-wall test:
            </Text>
          </View>

          {/* Middle section */}
          <View className="w-full relative">
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
                  className={`flex-row mb-2 ${isTopSection ? "pr-[130px]" : ""}`}
                >
                  <Text className="text-lg font-bold text-[#11181C] dark:text-[#ECEDEE] mr-2">
                    {idx + 1}.
                  </Text>
                  <Text className="text-lg leading-6 text-[#11181C] dark:text-[#ECEDEE] flex-1">
                    {line}
                  </Text>
                </View>
              );
            })}
          </View>

          {/* Bottom section */}
          <View className="items-center">
            <View className="w-4/5 self-center max-w-[420px]">
              <PillButton
                title={buttonTitle}
                onPress={handleMeasure}
                disabled={isMeasuring}
              />

              {/* Countdown */}
              {isMeasuring && (
                <Text className="text-center mt-8 text-5xl font-extrabold text-[#11181C] dark:text-[#ECEDEE]">
                  {countdown}
                </Text>
              )}

              {/* Result */}
              {resultAngle !== null && (
                <View className="items-center mt-6">
                  <Text className="text-[#11181C] dark:text-[#ECEDEE] text-lg">
                    Your measurement:
                  </Text>
                  <Text className="text-[#11181C] dark:text-[#ECEDEE] text-5xl font-extrabold mt-2">
                    {resultAngle.toFixed(1)}°
                  </Text>
                </View>
              )}

              {/* Save button */}
              {hasResult && (
                <View className="mt-8">
                  <PillButton
                    title="Save"
                    onPress={() => handleSave(resultAngle!, angleOverTime)}
                  />
                </View>
              )}
            </View>

            {measureState === "idle" && (
              <Text className="text-center mt-4 text-[#11181C] dark:text-[#ECEDEE] opacity-70">
                Press MEASURE when you're ready.
              </Text>
            )}
          </View>
        </View>
      </SafeAreaView>
    </>
  );
}
