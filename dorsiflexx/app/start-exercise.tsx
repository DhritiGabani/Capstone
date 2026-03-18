import PillButton from "@/components/PillButton";
import BackendService from "@/src/services/api/BackendService";
import { router } from "expo-router";
import React, { useEffect, useMemo, useState } from "react";
import { Alert, Image, SafeAreaView, Text, useColorScheme, View } from "react-native";

type BtState = "disconnected" | "connecting" | "connected";

export default function StartExercise() {
  const scheme = useColorScheme();

  const [btState, setBtState] = useState<BtState>("disconnected");
  const [sessionId, setSessionId] = useState<string | null>(null);

  // HARDCODED VARIABLES /////////////////////////////
  const userName = "Jane";
  const deviceName = `${userName}'s DorsiFlexx`;
  ////////////////////////////////////////////////////

  const isConnected = btState === "connected";
  const isConnecting = btState === "connecting";

  useEffect(() => {
    BackendService.getStatus()
      .then((s) => { if (s.is_connected) handleConnectBluetooth(); })
      .catch(() => {});
  }, []);

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
    if (btState !== "disconnected") return;

    try {
      setBtState("connecting");
      const response = await BackendService.connect();
      setSessionId(response.session_id);
      setBtState("connected");
    } catch (e) {
      setBtState("disconnected");
      Alert.alert(
        "Connection Failed",
        e instanceof Error ? e.message : "Could not connect to sensors.",
      );
    }
  }

  function handleStart() {
    if (!isConnected || !sessionId) return;

    router.push({
      pathname: "/exercise-in-progress",
      params: { session_id: sessionId },
    });
  }

  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
      <View className="flex-1 px-6 justify-center gap-8">
        {/* Top section */}
        <View className="items-center">
          <Text className="text-4xl font-bold text-[#11181C] dark:text-[#ECEDEE] text-center">
            Instructions for{"\n"}device placement:
          </Text>
        </View>

        {/* Middle section */}
        <View className="items-center">
          <View className="w-full pl-2 pr-2">
            {instructions.map((line, idx) => (
              <View key={idx} className="flex-row mb-1">
                <Text className="text-lg font-bold text-[#11181C] dark:text-[#ECEDEE] mr-2">
                  {idx + 1}.
                </Text>
                <Text className="text-lg leading-6 text-[#11181C] dark:text-[#ECEDEE] flex-1">
                  {line}
                </Text>
              </View>
            ))}
          </View>

          <Image
            source={require("@/assets/images/DevicePlacementImage.png")}
            style={{
              width: 160,
              height: 160,
              tintColor: scheme === "dark" ? "#ECEDEE" : "#11181C",
              alignSelf: "center",
            }}
            resizeMode="contain"
          />
        </View>

        {/* Bottom section */}
        <View className="items-center">
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
