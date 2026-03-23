import React, { useEffect, useRef } from "react";
import { Animated, Pressable, Text } from "react-native";

type BannerVariant = "success" | "error" | "info";

type NotificationBannerProps = {
  message: string;
  variant?: BannerVariant;
  visible: boolean;
  onHide: () => void;
  durationMs?: number;
  onPress?: () => void;
};

const VARIANT_COLORS: Record<BannerVariant, string> = {
  success: "#2E7D32",
  error: "#C62828",
  info: "#8D44BC",
};

export default function NotificationBanner({
  message,
  variant = "success",
  visible,
  onHide,
  durationMs = 2500,
  onPress,
}: NotificationBannerProps) {
  const opacity = useRef(new Animated.Value(0)).current;
  const translateY = useRef(new Animated.Value(-60)).current;

  useEffect(() => {
    if (!visible) return;

    Animated.parallel([
      Animated.timing(opacity, {
        toValue: 1,
        duration: 250,
        useNativeDriver: true,
      }),
      Animated.timing(translateY, {
        toValue: 0,
        duration: 250,
        useNativeDriver: true,
      }),
    ]).start();

    const timer = setTimeout(() => {
      Animated.parallel([
        Animated.timing(opacity, {
          toValue: 0,
          duration: 250,
          useNativeDriver: true,
        }),
        Animated.timing(translateY, {
          toValue: -60,
          duration: 250,
          useNativeDriver: true,
        }),
      ]).start(() => onHide());
    }, durationMs);

    return () => clearTimeout(timer);
  }, [visible]);

  if (!visible) return null;

  return (
    <Animated.View
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 999,
        backgroundColor: VARIANT_COLORS[variant],
        opacity,
        transform: [{ translateY }],
      }}
    >
      <Pressable
        onPress={onPress}
        style={{ paddingVertical: 14, paddingHorizontal: 20 }}
      >
        <Text
          style={{
            color: "#fff",
            fontSize: 15,
            fontWeight: "600",
            textAlign: "center",
          }}
        >
          {message}
        </Text>
      </Pressable>
    </Animated.View>
  );
}
