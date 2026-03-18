import React from "react";
import { Image, SafeAreaView, Text, View } from "react-native";

export default function ExercisesScreen() {
  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
      {/* Title */}
      <Text className="pb-2 text-center mt-8 mb-8 text-[26px] text-[#11181C] dark:text-[#ECEDEE]">
        EXERCISES
      </Text>

      {/* Card 1 */}
      <View className="mx-6 mb-8 h-36 flex-row overflow-hidden border border-[#11181C] dark:border-[#ECEDEE]">
        <Image
          source={require("@/assets/images/ankle-circles.jpg")}
          className="h-full w-36"
          resizeMode="cover"
        />
        <View className="flex-1 p-3">
          <Text className="font-bold text-base mb-1 text-[#11181C] dark:text-[#ECEDEE]">
            ANKLE CIRCLES
          </Text>
          <Text className="text-sm text-[#11181C] dark:text-[#ECEDEE]">
            Turn your ankle slowly in circles. Move just your foot and ankle,
            not your leg.
          </Text>
        </View>
      </View>

      {/* Card 2 */}
      <View className="mx-6 mb-8 h-36 flex-row overflow-hidden border border-[#11181C] dark:border-[#ECEDEE]">
        <Image
          source={require("@/assets/images/calf-raises.jpg")}
          className="h-full w-36"
          resizeMode="cover"
        />
        <View className="flex-1 p-3">
          <Text className="mb-1 text-base font-bold text-[#11181C] dark:text-[#ECEDEE]">
            CALF RAISES ON A STEP
          </Text>
          <Text className="text-sm text-[#11181C] dark:text-[#ECEDEE]">
            Stand on a step with your heels hanging off the step. Raise up onto
            your toes and then slowly lower your feet.
          </Text>
        </View>
      </View>

      {/* Card 3 */}
      <View className="mx-6 mb-8 h-36 flex-row overflow-hidden border border-[#11181C] dark:border-[#ECEDEE]">
        <Image
          source={require("@/assets/images/heel-walks.jpg")}
          className="h-full w-36"
          resizeMode="cover"
        />
        <View className="flex-1 p-3">
          <Text className="font-bold text-base mb-1 text-[#11181C] dark:text-[#ECEDEE]">
            HEEL WALKS
          </Text>
          <Text className="text-sm text-[#11181C] dark:text-[#ECEDEE]">
            Walk around on your heels, keeping your toes as high off the ground
            as possible.
          </Text>
        </View>
      </View>

      {/* Footer */}
      <Text className="pb-2 text-center text-xl mt-4 text-[#11181C] dark:text-[#ECEDEE]">
        More exercises coming soon!
      </Text>
    </SafeAreaView>
  );
}
