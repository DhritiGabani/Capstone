import { Pressable, Text } from "react-native";

export default function PillButton({
  title,
  onPress,
  disabled = false,
}: {
  title: string;
  onPress: () => void;
  disabled?: boolean;
}) {
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
        bg-brand-purple-dark
        ${disabled ? "opacity-25" : "active:opacity-80"}
      `}
    >
      <Text className="text-xl font-bold text-center leading-[22px] text-white">
        {title}
      </Text>
    </Pressable>
  );
}
