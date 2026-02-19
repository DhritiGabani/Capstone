import PillButton from "@/components/PillButton";
import { router } from "expo-router";
import React, { useState } from "react";
import {
    KeyboardAvoidingView,
    Platform,
    Pressable,
    SafeAreaView,
    ScrollView,
    Text,
    TextInput,
    View,
} from "react-native";

type Rating = "good" | "okay" | "bad";

function EmojiFace({
  emoji,
  selected,
  onSelect,
}: {
  emoji: string;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <Pressable
      onPress={onSelect}
      hitSlop={10}
      className={`
        items-center justify-center
        h-24 w-24 rounded-full
        ${selected ? "bg-brand-purple-dark" : ""}
      `}
    >
      <Text style={{ fontSize: 64 }}>{emoji}</Text>
    </Pressable>
  );
}

export default function EndExercise() {
  const [rating, setRating] = useState<Rating | null>(null);
  const [comments, setComments] = useState("");

  return (
    <>
      <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          className="flex-1"
        >
          <ScrollView
            contentContainerStyle={{ flexGrow: 1 }}
            keyboardShouldPersistTaps="handled"
          >
            <View className="flex-1 px-6 py-8 justify-center gap-12">
              <View className="items-center">
                <Text className="text-4xl font-semibold text-[#11181C] dark:text-[#ECEDEE] text-center">
                  How was your{"\n"}exercise session?
                </Text>
              </View>

              <View className="items-center">
                <View className="flex-row gap-10">
                  <EmojiFace
                    emoji="😀"
                    selected={rating === "good"}
                    onSelect={() => setRating("good")}
                  />
                  <EmojiFace
                    emoji="😐"
                    selected={rating === "okay"}
                    onSelect={() => setRating("okay")}
                  />
                  <EmojiFace
                    emoji="☹️"
                    selected={rating === "bad"}
                    onSelect={() => setRating("bad")}
                  />
                </View>
              </View>

              <View className="items-center">
                <View className="w-full max-w-[520px]">
                  <TextInput
                    value={comments}
                    onChangeText={setComments}
                    placeholder="Optional Comments"
                    placeholderTextColor="#6B7280"
                    multiline
                    textAlignVertical="top"
                    className="w-full min-h-[140px] rounded-2xl border border-[#9CA3AF] dark:border-[#3A3A3A] px-4 py-4 text-base text-[#11181C] dark:text-[#ECEDEE]"
                  />
                </View>
              </View>

              <View className="items-center">
                <View className="w-full px-4 flex-row gap-8">
                  <View className="flex-1">
                    <PillButton
                      title="Skip"
                      onPress={() => {
                        router.replace("/");
                      }}
                    />
                  </View>

                  <View className="flex-1">
                    <PillButton
                      title="Save"
                      disabled={!rating}
                      onPress={() => {
                        // TODO: save `rating` and `comments`
                        router.replace("/");
                      }}
                    />
                  </View>
                </View>
              </View>
            </View>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </>
  );
}
