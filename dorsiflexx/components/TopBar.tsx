import { IconSymbol } from "@/components/ui/icon-symbol";
import React from "react";
import { Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

export function TopBar({
  bluetoothOn,
  setBluetoothOn,
  iconColor,
}: {
  bluetoothOn: boolean;
  setBluetoothOn: React.Dispatch<React.SetStateAction<boolean>>;
  iconColor: string;
}) {
  const insets = useSafeAreaInsets();

  return (
    <View
      className="bg-white dark:bg-[#151718]"
      style={{ paddingTop: insets.top }}
    >
      <View className="h-8 justify-center items-center relative">
        <Text className="text-base font-black text-[#11181C] dark:text-[#ECEDEE]">
          DorsiFlexx™
        </Text>

        <View className="absolute right-4 top-0 bottom-0 justify-center">
          <Pressable
            onPress={() => setBluetoothOn((prev) => !prev)}
            className={`w-8 h-8 rounded-full items-center justify-center ${
              bluetoothOn ? "bg-brand-purple-dark" : ""
            }`}
          >
            <IconSymbol
              name="antenna.radiowaves.left.and.right"
              size={18}
              color={bluetoothOn ? "#fff" : iconColor}
            />
          </Pressable>
        </View>
      </View>
    </View>
  );
}
