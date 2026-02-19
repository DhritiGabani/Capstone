import { Pressable, Text } from "react-native";

export default function PillButton({
  title,
  onPress,
  disabled = false,
  variant = "primary",
}: {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  variant?: "primary" | "success" | "warning" | "danger";
}) {
  const backgroundMap = {
    primary: "bg-brand-purple-dark", // ✅ your original default
    success: "bg-green-500",
    warning: "bg-yellow-500",
    danger: "bg-red-700",
  };

  return (
    <Pressable
      onPress={disabled ? undefined : onPress}
      disabled={disabled}
      className={`
        w-full
        min-h-[72px]
        rounded-full
        py-4 px-[22px]
        items-center justify-center
        ${backgroundMap[variant]}
        ${disabled ? "opacity-25" : "active:opacity-80"}
      `}
    >
      <Text className="text-xl font-bold text-center leading-[22px] text-white">
        {title}
      </Text>
    </Pressable>
  );
}
