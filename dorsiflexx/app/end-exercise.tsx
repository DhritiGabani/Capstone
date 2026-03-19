import {
  ExerciseAccordionRow,
  mapBackendToExercises,
} from "@/components/ExerciseCards";
import PillButton from "@/components/PillButton";
import { router, useLocalSearchParams } from "expo-router";
import React, { useMemo, useRef, useState } from "react";
import {
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  Text,
  TextInput,
  View,
  useColorScheme,
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
        h-24 w-24 items-center justify-center rounded-full
        ${selected ? "bg-brand-purple-dark" : ""}
      `}
    >
      <Text style={{ fontSize: 64 }}>{emoji}</Text>
    </Pressable>
  );
}

export default function EndExercise() {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";

  const params = useLocalSearchParams<{
    session_id?: string;
    duration_seconds?: string;
    total_samples?: string;
    exercises?: string;
    analysis?: string;
  }>();

  const scrollRef = useRef<ScrollView>(null);
  const [rating, setRating] = useState<Rating | null>(null);
  const [comments, setComments] = useState("");
  const [expandedById, setExpandedById] = useState<Record<string, boolean>>({});

  const toggleExercise = (id: string) => {
    setExpandedById((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const analysis: Record<string, any> = useMemo(() => {
    try {
      return params.analysis ? JSON.parse(params.analysis) : {};
    } catch {
      return {};
    }
  }, [params.analysis]);

  const exercises = useMemo(
    () =>
      Object.keys(analysis).length > 0
        ? mapBackendToExercises(analysis, params.session_id ?? "session")
        : [],
    [analysis, params.session_id],
  );

  const durationSeconds = Number(params.duration_seconds) || 0;
  const durationMin = Math.floor(durationSeconds / 60);
  const durationSec = Math.round(durationSeconds % 60);

  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        className="flex-1"
      >
        <ScrollView
          ref={scrollRef}
          contentContainerStyle={{ flexGrow: 1 }}
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode="on-drag"
        >
          <View className="flex-1 justify-center gap-12 px-6 py-8">
            {exercises.length > 0 && (
              <View className="gap-4">
                <Text className="text-center text-2xl font-bold text-[#11181C] dark:text-[#ECEDEE]">
                  Session Summary
                </Text>

                <Text className="text-center text-base text-[#687076] dark:text-[#9BA1A6]">
                  Duration: {durationMin}m {durationSec}s
                </Text>

                <View className="h-[1px] w-full bg-[#8C8C8C] dark:bg-[#6C6C6C]" />

                {exercises.map((exercise) => (
                  <ExerciseAccordionRow
                    key={exercise.id}
                    exercise={exercise}
                    expanded={!!expandedById[exercise.id]}
                    onToggle={() => toggleExercise(exercise.id)}
                    isDark={isDark}
                  />
                ))}
              </View>
            )}

            <View className="items-center">
              <Text className="text-center text-4xl font-semibold text-[#11181C] dark:text-[#ECEDEE]">
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
                  onFocus={() =>
                    setTimeout(
                      () => scrollRef.current?.scrollToEnd({ animated: true }),
                      100,
                    )
                  }
                  placeholder="Optional Comments"
                  placeholderTextColor="#6B7280"
                  multiline
                  textAlignVertical="top"
                  className="min-h-[140px] w-full rounded-2xl border border-[#9CA3AF] px-4 py-4 text-base text-[#11181C] dark:border-[#3A3A3A] dark:text-[#ECEDEE]"
                />
              </View>
            </View>

            <View className="items-center">
              <View className="w-full flex-row gap-8 px-4">
                <View className="flex-1">
                  <PillButton
                    title="Skip"
                    onPress={() => {
                      Keyboard.dismiss();
                      router.replace("/");
                    }}
                  />
                </View>

                <View className="flex-1">
                  <PillButton
                    title="Save"
                    disabled={!rating}
                    onPress={() => {
                      Keyboard.dismiss();
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
  );
}
