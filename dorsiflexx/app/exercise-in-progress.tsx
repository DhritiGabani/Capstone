import { Text, View } from "react-native";

export default function ExerciseInProgress() {
  return (
    <View className="flex-1 items-center justify-center bg-white">
      <Text className="text-xl font-bold text-blue-500">
        Welcome to your exercise session! {"\n"}This page is a work in progress.
      </Text>
    </View>
  );
}
