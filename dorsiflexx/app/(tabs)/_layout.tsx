import { Tabs } from "expo-router";
import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { HapticTab } from "@/components/haptic-tab";
import { IconSymbol } from "@/components/ui/icon-symbol";
import { Colors } from "@/constants/theme";
import { useColorScheme } from "@/hooks/use-color-scheme";

export default function TabLayout() {
  const colorScheme = useColorScheme();
  const theme = Colors[colorScheme ?? "light"];
  const insets = useSafeAreaInsets();
  const [bluetoothOn, setBluetoothOn] = useState(false);

  return (
    <View style={styles.container}>
      {/* Static Top Bar */}
      <View
        style={[
          styles.topBar,
          { backgroundColor: theme.background, paddingTop: insets.top },
        ]}
      >
        <View style={styles.topBarInner}>
          <Text style={[styles.title, { color: theme.text }]}>DorsiFlexx™</Text>

          <View style={styles.rightIcon}>
            <Pressable
              onPress={() => setBluetoothOn((prev) => !prev)}
              style={[
                styles.bluetoothButton,
                bluetoothOn && { backgroundColor: theme.darkPurple },
              ]}
            >
              <IconSymbol
                name="antenna.radiowaves.left.and.right"
                size={18}
                color={bluetoothOn ? theme.white : theme.icon}
              />
            </Pressable>
          </View>
        </View>
      </View>

      {/* Tabs */}
      <View style={styles.tabsContainer}>
        <Tabs
          screenOptions={{
            tabBarActiveTintColor: theme.tint,
            tabBarStyle: {
              backgroundColor: theme.background,
            },
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

const styles = StyleSheet.create({
  container: { flex: 1 },

  topBar: {},
  topBarInner: {
    height: 32,
    justifyContent: "center",
    alignItems: "center",
    position: "relative",
  },
  title: {
    fontSize: 16,
    fontWeight: "900",
  },
  rightIcon: {
    position: "absolute",
    right: 16,
    top: 0,
    bottom: 0,
    justifyContent: "center",
  },
  bluetoothButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
  },

  tabsContainer: { flex: 1 },
});
