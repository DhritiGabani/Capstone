import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
import React, { useMemo, useState } from "react";
import {
    Pressable,
    SafeAreaView,
    ScrollView,
    Text,
    View,
    useColorScheme,
} from "react-native";
import { LineChart } from "react-native-chart-kit";
import Svg, { Line, Text as SvgText } from "react-native-svg";

type ExerciseType =
  | "ankle_circles_cw"
  | "ankle_circles_ccw"
  | "calf_raises_on_step"
  | "heel_walks";

type BaseExercise = {
  id: string;
  displayName: string;
  type: ExerciseType;
};

type AnkleCirclesExercise = BaseExercise & {
  type: "ankle_circles_cw" | "ankle_circles_ccw";
  repetitions: number;
  averageSpeed: number;
  percentMaxROM: number[];
};

type CalfRaisesExercise = BaseExercise & {
  type: "calf_raises_on_step";
  repetitions: number;
  averageSpeed: number;
  percentMaxROM: number[];
};

type HeelWalksExercise = BaseExercise & {
  type: "heel_walks";
  duration: number;
  numberOfSteps: number;
  percentMaxROM: number[];
};

type ExerciseEntry =
  | AnkleCirclesExercise
  | CalfRaisesExercise
  | HeelWalksExercise;

type SessionEntry = {
  id: string;
  timeLabel: string;
  exercises: ExerciseEntry[];
};

type RendererProps<T extends ExerciseEntry> = {
  exercise: T;
  isDark: boolean;
};

type MiniLineChartProps = {
  values: number[];
  isDark: boolean;
  referenceLabel?: string;
  referenceValue?: number;
};

function formatDateLabel(dateString?: string | string[]) {
  if (!dateString || Array.isArray(dateString)) return "";

  const [year, month, day] = dateString.split("-").map(Number);
  if (!year || !month || !day) return "";

  const d = new Date(year, month - 1, day);

  return d.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function MiniLineChart({
  values,
  isDark,
  referenceLabel,
  referenceValue,
}: MiniLineChartProps) {
  if (!values.length) return null;

  const width = 280;
  const height = 120;

  const textColor = isDark ? "#ECEDEE" : "#11181C";
  const panelBg = isDark ? "#2B2D31" : "#eee";

  const padTop = 16;
  const padBottom = 22;

  const plotHeight = height - padTop - padBottom;

  const yForValue = (v: number) => {
    return padTop + (1 - v) * plotHeight;
  };

  const refY =
    referenceValue !== undefined ? yForValue(referenceValue) : undefined;

  return (
    <View className="mt-2 pl-4">
      <View style={{ width, height }}>
        <LineChart
          data={{
            labels: values.map(() => ""),
            datasets: [
              { data: values },
              {
                data: [0, 1],
                withDots: false,
                color: () => "transparent",
                strokeWidth: 0,
              },
            ],
          }}
          width={width}
          height={height}
          withDots
          withShadow={false}
          withInnerLines={false}
          withOuterLines={false}
          withVerticalLines={false}
          withHorizontalLines={false}
          withVerticalLabels={false}
          withHorizontalLabels={false}
          bezier={false}
          chartConfig={{
            backgroundColor: panelBg,
            backgroundGradientFrom: panelBg,
            backgroundGradientTo: panelBg,
            decimalPlaces: 0,
            color: () => textColor,
            labelColor: () => textColor,
            propsForDots: {
              r: "2.5",
              strokeWidth: "0",
              fill: textColor,
            },
            propsForBackgroundLines: {
              strokeWidth: 0,
            },
          }}
          style={{
            backgroundColor: panelBg,
          }}
        />

        {/*Manually draw the axes since chart-kit cannot render solid axes*/}
        <Svg
          width={width}
          height={height}
          style={{ position: "absolute", left: 0, top: 0 }}
        >
          <Line
            x1={48}
            y1={16}
            x2={48}
            y2={height - 14}
            stroke={textColor}
            strokeWidth={1}
          />
          <Line
            x1={48}
            y1={height - 14}
            x2={width - 12}
            y2={height - 14}
            stroke={textColor}
            strokeWidth={1}
          />

          {refY !== undefined && (
            <>
              <Line
                x1={48}
                y1={refY}
                x2={width - 12}
                y2={refY}
                stroke={textColor}
                strokeWidth={1}
                strokeDasharray="6 6"
              />
              {!!referenceLabel && (
                <SvgText
                  x={42}
                  y={height / 2}
                  fontSize={13}
                  textAnchor="end"
                  fill={textColor}
                >
                  {referenceLabel}
                </SvgText>
              )}
            </>
          )}
        </Svg>
      </View>
    </View>
  );
}

function AnkleCirclesDetails({
  exercise,
  isDark,
}: RendererProps<AnkleCirclesExercise>) {
  return (
    <View className="bg-[#eee] px-3 py-3 dark:bg-[#2B2D31]">
      <Text className="text-[16px] text-[#11181C] dark:text-[#ECEDEE]">
        <Text className="font-semibold"># Repetitions:</Text>{" "}
        {exercise.repetitions}
      </Text>

      <Text className="mt-1 text-[16px] text-[#11181C] dark:text-[#ECEDEE]">
        <Text className="font-semibold">Average speed:</Text>{" "}
        {exercise.averageSpeed.toFixed(1)} seconds/circle
      </Text>

      <MiniLineChart
        values={exercise.percentMaxROM}
        isDark={isDark}
        referenceLabel="% Max"
        referenceValue={1}
      />
    </View>
  );
}

function CalfRaisesDetails({
  exercise,
  isDark,
}: RendererProps<CalfRaisesExercise>) {
  return (
    <View className="bg-[#eee] px-3 py-3 dark:bg-[#2B2D31]">
      <Text className="text-[16px] text-[#11181C] dark:text-[#ECEDEE]">
        <Text className="font-semibold"># Repetitions:</Text>{" "}
        {exercise.repetitions}
      </Text>

      <Text className="mt-1 text-[16px] text-[#11181C] dark:text-[#ECEDEE]">
        <Text className="font-semibold">Average speed:</Text>{" "}
        {exercise.averageSpeed.toFixed(1)} seconds/rep
      </Text>

      <MiniLineChart
        values={exercise.percentMaxROM}
        isDark={isDark}
        referenceLabel="% Max"
        referenceValue={1}
      />
    </View>
  );
}

function HeelWalksDetails({
  exercise,
  isDark,
}: RendererProps<HeelWalksExercise>) {
  return (
    <View className="bg-[#eee] px-3 py-3 dark:bg-[#2B2D31]">
      <Text className="text-[16px] text-[#11181C] dark:text-[#ECEDEE]">
        <Text className="font-semibold">Duration:</Text> {exercise.duration} sec
      </Text>

      <Text className="mt-1 text-[16px] text-[#11181C] dark:text-[#ECEDEE]">
        <Text className="font-semibold">Number of steps:</Text>{" "}
        {exercise.numberOfSteps} steps
      </Text>

      <MiniLineChart
        values={exercise.percentMaxROM}
        isDark={isDark}
        referenceLabel="% Max"
        referenceValue={1}
      />
    </View>
  );
}

const exerciseDetailRenderers = {
  ankle_circles_cw: AnkleCirclesDetails,
  ankle_circles_ccw: AnkleCirclesDetails,
  calf_raises_on_step: CalfRaisesDetails,
  heel_walks: HeelWalksDetails,
} as const;

function ExerciseDetails({
  exercise,
  isDark,
}: {
  exercise: ExerciseEntry;
  isDark: boolean;
}) {
  const Renderer = exerciseDetailRenderers[
    exercise.type
  ] as React.ComponentType<RendererProps<any>>;

  return <Renderer exercise={exercise} isDark={isDark} />;
}

function ExerciseAccordionRow({
  exercise,
  expanded,
  onToggle,
  isDark,
}: {
  exercise: ExerciseEntry;
  expanded: boolean;
  onToggle: () => void;
  isDark: boolean;
}) {
  return (
    <View className="w-full">
      <Pressable
        onPress={onToggle}
        className="flex-row items-center justify-between py-2"
      >
        <Text className="text-[18px] font-semibold text-[#11181C] dark:text-[#ECEDEE]">
          {exercise.displayName}
        </Text>

        <Ionicons
          name={expanded ? "remove" : "add"}
          size={26}
          color={isDark ? "#ECEDEE" : "#11181C"}
        />
      </Pressable>

      {expanded && <ExerciseDetails exercise={exercise} isDark={isDark} />}

      <View className="h-[1px] w-full bg-[#8C8C8C] dark:bg-[#6C6C6C]" />
    </View>
  );
}

export default function HistorySingleScreen() {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";

  const { date } = useLocalSearchParams<{ date: string }>();

  const selectedDateLabel = useMemo(() => formatDateLabel(date), [date]);

  // TODO: replace this hardcoded data with real data for sessions on this date
  const sessions: SessionEntry[] = useMemo(
    () => [
      {
        id: "session-1",
        timeLabel: "10:24 AM",
        exercises: [
          {
            id: "ex-1",
            type: "ankle_circles_cw",
            displayName: "ANKLE CIRCLES (CW)",
            repetitions: 10,
            averageSpeed: 1.2,
            percentMaxROM: [
              0.925, 0.8787, 0.3598, 0.7938, 0.568, 0.6378, 0.5205, 0.7988, 1.0,
              0.8012,
            ],
          },
          {
            id: "ex-2",
            type: "ankle_circles_ccw",
            displayName: "ANKLE CIRCLES (CCW)",
            repetitions: 10,
            averageSpeed: 1.4,
            percentMaxROM: [1, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0],
          },
          {
            id: "ex-3",
            type: "calf_raises_on_step",
            displayName: "CALF RAISES ON STEP",
            repetitions: 12,
            averageSpeed: 1.1,
            percentMaxROM: [
              0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97, 0.97, 0.98, 0.99, 0.99,
              1,
            ],
          },
        ],
      },
      {
        id: "session-2",
        timeLabel: "6:33 PM",
        exercises: [
          {
            id: "ex-4",
            type: "heel_walks",
            displayName: "HEEL WALKS",
            duration: 22,
            numberOfSteps: 13,
            percentMaxROM: [
              0.8, 0.9, 0.6, 0.75, 0.78, 1, 0.2, 0.3, 0.4, 0.5, 0.3, 0.42, 0.41,
            ],
          },
          {
            id: "ex-5",
            type: "calf_raises_on_step",
            displayName: "CALF RAISES ON STEP",
            repetitions: 8,
            averageSpeed: 0.8,
            percentMaxROM: [1, 0.88, 0.9, 0.93, 0.4, 0.55, 0.69, 0.97],
          },
        ],
      },
    ],
    [],
  );

  const [expandedById, setExpandedById] = useState<Record<string, boolean>>({});

  const toggleExercise = (exerciseId: string) => {
    setExpandedById((prev) => ({
      ...prev,
      [exerciseId]: !prev[exerciseId],
    }));
  };

  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
      <ScrollView
        className="flex-1"
        contentContainerStyle={{
          paddingHorizontal: 24,
          paddingTop: 36,
          paddingBottom: 36,
        }}
        showsVerticalScrollIndicator={false}
      >
        <View className="mb-8 flex-row items-center justify-center">
          <Text className="text-[22px] font-semibold text-[#11181C] dark:text-[#ECEDEE]">
            {selectedDateLabel}
          </Text>
        </View>

        {sessions.map((session) => (
          <View key={session.id} className="mb-8">
            <View className="mb-3 min-w-[50px] self-start rounded-full bg-[#8d44bc] px-4 py-2">
              <Text className="text-[16px] font-semibold text-[#fff]">
                {session.timeLabel}
              </Text>
            </View>

            <View className="mb-1 h-[1px] w-full bg-[#8C8C8C] dark:bg-[#6C6C6C]" />

            {session.exercises.map((exercise) => (
              <ExerciseAccordionRow
                key={exercise.id}
                exercise={exercise}
                expanded={!!expandedById[exercise.id]}
                onToggle={() => toggleExercise(exercise.id)}
                isDark={isDark}
              />
            ))}
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}
