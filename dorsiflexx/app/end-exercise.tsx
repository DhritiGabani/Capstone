import PillButton from "@/components/PillButton";
import BackendService from "@/src/services/api/BackendService";
import { router, useLocalSearchParams } from "expo-router";
import React, { useMemo, useState } from "react";
import {
    Alert,
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

interface ExerciseResult {
  exercise_type: string;
  rep_count: number;
  rom: number;
  tempo_consistency: number;
  movement_consistency: number;
}

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
  const params = useLocalSearchParams<{
    session_id?: string;
    duration_seconds?: string;
    total_samples?: string;
    exercises?: string;
  }>();

  const [rating, setRating] = useState<Rating | null>(null);
  const [comments, setComments] = useState("");

  const exercises: ExerciseResult[] = useMemo(() => {
    try {
      return params.exercises ? JSON.parse(params.exercises) : [];
    } catch {
      return [];
    }
  }, [params.exercises]);

  const durationSeconds = Number(params.duration_seconds) || 0;
  const durationMin = Math.floor(durationSeconds / 60);
  const durationSec = Math.round(durationSeconds % 60);

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
              {/* Session summary */}
              {exercises.length > 0 && (
                <View className="items-center gap-4">
                  <Text className="text-2xl font-bold text-[#11181C] dark:text-[#ECEDEE] text-center">
                    Session Summary
                  </Text>

                  <Text className="text-base text-[#687076] dark:text-[#9BA1A6] text-center">
                    Duration: {durationMin}m {durationSec}s
                  </Text>

                  {exercises.map((ex, idx) => (
                    <View
                      key={idx}
                      className="w-full rounded-2xl bg-[#F1F3F5] dark:bg-[#1E2022] px-5 py-4"
                    >
                      <Text className="text-lg font-semibold text-[#11181C] dark:text-[#ECEDEE]">
                        {ex.exercise_type}
                      </Text>
                      <Text className="text-base text-[#687076] dark:text-[#9BA1A6] mt-1">
                        Reps: {ex.rep_count}
                        {ex.movement_consistency > 0 &&
                          `  |  Consistency: ${ex.movement_consistency.toFixed(0)}%`}
                        {ex.rom > 0 && `  |  ROM: ${ex.rom.toFixed(1)}`}
                      </Text>
                    </View>
                  ))}
                </View>
              )}

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
                      onPress={async () => {
                        try {
                          if (params.session_id && rating) {
                            await BackendService.saveFeedback(
                              params.session_id,
                              rating,
                              comments,
                            );
                          }
                          router.replace("/");
                        } catch (e) {
                          Alert.alert(
                            "Save Failed",
                            e instanceof Error ? e.message : "Could not save feedback.",
                          );
                        }
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
