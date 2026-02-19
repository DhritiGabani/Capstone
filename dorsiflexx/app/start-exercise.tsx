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
  ////////////////////////////////////////////////////

  const isConnected = btState === "connected";
  const isConnecting = btState === "connecting";

  const instructions = useMemo(
    () => [
      //TODO: update with real instructions and add images
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
      "Ut enim ad minim veniam, quis nostrud exercitation.",
      "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
    ],
    [],
  );

  async function handleConnectBluetooth() {
    setBtState("connected");

    if (btState !== "disconnected") return;

    try {
      setBtState("connecting");

      // TODO: Replace with real Bluetooth connect flow.
      // This simulates a 1-second connection.
      await new Promise((res) => setTimeout(res, 1000));

      setBtState("connected");
    } catch (e) {
      // If connection fails, return to disconnected
      setBtState("disconnected");
    }
  }

  function handleStart() {
    // Only allow if connected
    if (!isConnected) return;

    router.push("/exercise-in-progress");
  }

  return (
    <SafeAreaView className="flex-1 bg-brand-purple-light">
      <View className="flex-1 px-6 pt-12">
        <Text className="text-4xl font-black text-[#11181C] mb-8 text-center">
          Instructions for{"\n"}device placement:
        </Text>

        <View className="flex-row">
          <View className="flex-1 pr-4 pl-2">
            {instructions.map((line, idx) => (
              <View key={idx} className="flex-row mb-3">
                <Text className="text-lg font-bold text-[#11181C] mr-2">
                  {idx + 1}.
                </Text>
                <Text className="text-lg leading-6 text-[#11181C] flex-1">
                  {line}
                </Text>
              </View>
            ))}
          </View>
        </View>

        <Image
          source={require("@/assets/images/InstructionsForDevicePlacement.png")} // adjust path if needed
          className="w-48 h-48 self-center"
          resizeMode="contain"
        />

        <View className="flex-1"></View>

        {/* Bottom section */}
        <View className="pb-12 items-center">
          <View className="w-4/5 gap-3.5 self-center max-w-[420px]">
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
              title="START"
              onPress={handleStart}
              disabled={!isConnected}
            />
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}
