import { Tabs } from "expo-router";
import React, { useState } from "react";
import { View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { HapticTab } from "@/components/haptic-tab";
import { TopBar } from "@/components/TopBar";
import { IconSymbol } from "@/components/ui/icon-symbol";
import { useColorScheme } from "@/hooks/use-color-scheme";

export default function TabLayout() {
  const colorScheme = useColorScheme();
  const insets = useSafeAreaInsets();
  const [bluetoothOn, setBluetoothOn] = useState(false);

  const iconColor = colorScheme === "dark" ? "#9BA1A6" : "#687076";
  const tintColor = colorScheme === "dark" ? "#fff" : "#8d44bc";
  const tabBgColor = colorScheme === "dark" ? "#151718" : "#fff";

  return (
    <View className="flex-1">
      <TopBar
        bluetoothOn={bluetoothOn}
        setBluetoothOn={setBluetoothOn}
        iconColor={iconColor}
      />

      {/* Tabs */}
      <View className="flex-1">
        <Tabs
          screenOptions={{
            tabBarActiveTintColor: tintColor,
            tabBarStyle: { backgroundColor: tabBgColor },
            headerShown: false,
            tabBarButton: HapticTab,
          }}
        >
          <Tabs.Screen
            name="index"
            options={{
              title: "Home",
              tabBarIcon: ({ color }) => (
                <IconSymbol size={28} name="house.fill" color={color} />
              ),
            }}
          />
          <Tabs.Screen
            name="history"
            options={{
              title: "History",
              tabBarIcon: ({ color }) => (
                <IconSymbol size={28} name="calendar" color={color} />
              ),
            }}
          />
          <Tabs.Screen
            name="measure"
            options={{
              title: "Measure",
              tabBarIcon: ({ color }) => (
                <IconSymbol
                  size={28}
                  name="ruler"
                  color={color}
                  style={{ transform: [{ rotate: "315deg" }] }}
                />
              ),
            }}
          />
          <Tabs.Screen
            name="booklet"
            options={{
              title: "Booklet",
              tabBarIcon: ({ color }) => (
                <IconSymbol size={28} name="book.fill" color={color} />
              ),
            }}
          />
          <Tabs.Screen
            name="settings"
            options={{
              title: "Settings",
              tabBarIcon: ({ color }) => (
                <IconSymbol size={28} name="gearshape.fill" color={color} />
              ),
            }}
          />
        </Tabs>
      </View>
    </View>
  );
}
