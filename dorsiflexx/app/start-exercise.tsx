import PillButton from "@/components/PillButton";
import { router } from "expo-router";
import React, { useMemo, useState } from "react";
import { Image, SafeAreaView, Text, View } from "react-native";

type BtState = "disconnected" | "connecting" | "connected";

export default function StartExercise() {
  const [btState, setBtState] = useState<BtState>("disconnected");

  // HARDCODED VARIABLES /////////////////////////////
  const userName = "Jane";
  const deviceName = `${userName}'s DorsiFlexx`;
  const mockSessionId = "mock-session-123";
  ////////////////////////////////////////////////////

  const isConnected = btState === "connected";
  const isConnecting = btState === "connecting";

  const instructions = useMemo(
    () => [
      {
        text: "Wrap the foot sensor around the middle of your foot, facing upwards. Ensure the arrow is pointed towards you.",
        image: require("@/assets/images/FootPlacementImage.png"),
      },
      {
        text: "Wrap the shank sensor around the middle of your calf, facing outwards. Ensure the arrow is pointed towards you.",
        image: require("@/assets/images/ShankPlacementImage.png"),
      },
    ],
    [],
  );

  function handleConnectBluetooth() {
    if (btState !== "disconnected") return;

    setBtState("connecting");

    setTimeout(() => {
      setBtState("connected");
    }, 500);
  }

  function handleStart() {
    if (!isConnected) return;

    router.push({
      pathname: "/exercise-in-progress",
      params: { session_id: mockSessionId },
    });
  }

  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
      <View className="flex-1 justify-center gap-8 px-6">
        <View className="items-center">
          <Text className="text-center text-4xl font-bold text-[#11181C] dark:text-[#ECEDEE]">
            Instructions for{"\n"}device placement:
          </Text>
        </View>

        <View className="items-center">
          <View className="w-full pl-2 pr-2">
            {instructions.map((item, idx) => (
              <View key={idx} className="mb-4 flex-row items-center">
                <View className="flex-1 flex-row pr-3">
                  <Text className="mr-2 text-lg font-bold text-[#11181C] dark:text-[#ECEDEE]">
                    {idx + 1}.
                  </Text>
                  <Text className="flex-1 text-lg leading-6 text-[#11181C] dark:text-[#ECEDEE]">
                    {item.text}
                  </Text>
                </View>

                <Image
                  source={item.image}
                  className="h-24 w-24"
                  resizeMode="contain"
                />
              </View>
            ))}
          </View>
        </View>

        <View className="items-center">
          <View className="max-w-[420px] w-4/5 self-center gap-3.5">
            <PillButton
              title={
                isConnected
                  ? `Connected to\n${deviceName}`
                  : isConnecting
                    ? "Connecting..."
                    : "Connect to Bluetooth"
              }
              onPress={handleConnectBluetooth}
              disabled={isConnected || isConnecting}
            />

            <PillButton
              title={isConnected ? "START" : "Waiting for device connection..."}
              onPress={handleStart}
              disabled={!isConnected}
            />
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}
