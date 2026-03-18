import BackendService, {
  KTWMeasurement
} from "@/src/services/api/BackendService";
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
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
  consistencyScore?: number | null;
};

type CalfRaisesExercise = BaseExercise & {
  type: "calf_raises_on_step";
  repetitions: number;
  averageSpeed: number;
  percentMaxROM: number[];
  consistencyScore?: number | null;
};

type HeelWalksExercise = BaseExercise & {
  type: "heel_walks";
  duration: number;
  numberOfSteps: number;
  percentMaxROM: number[];
  meanAngleDeg?: number | null;
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

function heelWalkRomFractions(analysis: Record<string, any>): number[] {
  const ankleAngles = analysis.ankle_angles;
  if (!ankleAngles?.rep_max_angle_deg) return [];

  const angles: number[] = Object.values(ankleAngles.rep_max_angle_deg);
  if (angles.length === 0) return [];

  const maxAngle = Math.max(...angles);
  if (maxAngle === 0) return angles.map(() => 0);

  return angles.map((a) => Math.round((a / maxAngle) * 10000) / 10000);
}

function mapBackendToExercises(
  analysis: Record<string, any>,
  idPrefix: string,
): ExerciseEntry[] {
  const repCounts = analysis.rep_counts ?? {};
  const repDurations = analysis.rep_durations ?? {};
  const romConsistency = analysis.rom_consistency ?? {};
  const consistencyScores = analysis.consistency_scores ?? {};
  const ankleAngles = analysis.ankle_angles;

  const exercises: ExerciseEntry[] = [];
  let idx = 0;

  for (const [exerciseType, repCount] of Object.entries(repCounts)) {
    idx += 1;
    const durations = repDurations[exerciseType] ?? {};
    const romData = romConsistency[exerciseType] ?? {};
    const romFractions: number[] = romData.rep_rom_fraction
      ? Object.values(romData.rep_rom_fraction)
      : [];

    if (exerciseType === "Ankle Rotation") {
      exercises.push({
        id: `${idPrefix}-ex-${idx}`,
        type: "ankle_circles_cw",
        displayName: "ANKLE ROTATIONS",
        repetitions: repCount as number,
        averageSpeed: durations.mean_duration_s ?? 0,
        percentMaxROM: romFractions,
        consistencyScore: consistencyScores[exerciseType] ?? null,
      });
    } else if (exerciseType === "Calf Raises") {
      exercises.push({
        id: `${idPrefix}-ex-${idx}`,
        type: "calf_raises_on_step",
        displayName: "CALF RAISES",
        repetitions: repCount as number,
        averageSpeed: durations.mean_duration_s ?? 0,
        percentMaxROM: romFractions,
        consistencyScore: consistencyScores[exerciseType] ?? null,
      });
    } else if (exerciseType === "Heel Walk") {
      const repDurMap = durations.rep_durations_s ?? {};
      const totalDuration = Object.values(repDurMap).reduce(
        (sum: number, d: any) => sum + (d as number),
        0,
      );

      exercises.push({
        id: `${idPrefix}-ex-${idx}`,
        type: "heel_walks",
        displayName: "HEEL WALKING",
        duration: Math.round(totalDuration as number),
        numberOfSteps: repCount as number,
        percentMaxROM: heelWalkRomFractions(analysis),
        meanAngleDeg: ankleAngles?.mean_max_angle_deg ?? null,
      });
    }
  }

  return exercises;
}

function formatTimeLabel(isoString: string): string {
  const d = new Date(isoString);
  return d.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

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

      {exercise.consistencyScore != null && (
        <Text className="mt-1 text-[16px] text-[#11181C] dark:text-[#ECEDEE]">
          <Text className="font-semibold">Consistency:</Text>{" "}
          {exercise.consistencyScore.toFixed(1)}%
        </Text>
      )}

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

      {exercise.consistencyScore != null && (
        <Text className="mt-1 text-[16px] text-[#11181C] dark:text-[#ECEDEE]">
          <Text className="font-semibold">Consistency:</Text>{" "}
          {exercise.consistencyScore.toFixed(1)}%
        </Text>
      )}

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

      {exercise.meanAngleDeg != null && (
        <Text className="mt-1 text-[16px] text-[#11181C] dark:text-[#ECEDEE]">
          <Text className="font-semibold">Mean ankle angle:</Text>{" "}
          {exercise.meanAngleDeg.toFixed(1)}°
        </Text>
      )}

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

  const [sessions, setSessions] = useState<SessionEntry[]>([]);
  const [ktwMeasurements, setKtwMeasurements] = useState<KTWMeasurement[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!date) return;
    setLoading(true);
    Promise.all([
      BackendService.getSessionsByDate(date)
        .then((backendSessions) =>
          backendSessions.map((s) => ({
            id: s.session_id,
            timeLabel: formatTimeLabel(s.start_time),
            exercises: s.analysis
              ? mapBackendToExercises(s.analysis, s.session_id)
              : [],
          })),
        )
        .catch(() => [] as SessionEntry[]),
      BackendService.getKTWByDate(date).catch(() => [] as KTWMeasurement[]),
    ])
      .then(([mapped, ktw]) => {
        setSessions(mapped);
        setKtwMeasurements(ktw);
      })
      .finally(() => setLoading(false));
  }, [date]);

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

        {loading && (
          <View className="items-center mt-8">
            <ActivityIndicator size="large" />
          </View>
        )}

        {!loading && sessions.length === 0 && ktwMeasurements.length === 0 && (
          <View className="items-center mt-8">
            <Text className="text-[16px] text-[#11181C] dark:text-[#ECEDEE] opacity-60">
              No exercise sessions found for this date.
            </Text>
          </View>
        )}

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

        {ktwMeasurements.map((m) => (
          <View key={`ktw-${m.id}`} className="mb-8">
            <View className="mb-3 min-w-[50px] self-start rounded-full bg-[#8d44bc] px-4 py-2">
              <Text className="text-[16px] font-semibold text-[#fff]">
                {formatTimeLabel(m.measured_at)}
              </Text>
            </View>

            <View className="mb-1 h-[1px] w-full bg-[#8C8C8C] dark:bg-[#6C6C6C]" />

            <View className="w-full">
              <Pressable
                onPress={() => toggleExercise(`ktw-${m.id}`)}
                className="flex-row items-center justify-between py-2"
              >
                <Text className="text-[18px] font-semibold text-[#11181C] dark:text-[#ECEDEE]">
                  KNEE-TO-WALL TEST
                </Text>
                <Ionicons
                  name={expandedById[`ktw-${m.id}`] ? "remove" : "add"}
                  size={26}
                  color={isDark ? "#ECEDEE" : "#11181C"}
                />
              </Pressable>

              {expandedById[`ktw-${m.id}`] && (
                <View className="bg-[#eee] px-3 py-3 dark:bg-[#2B2D31]">
                  <Text className="text-[16px] text-[#11181C] dark:text-[#ECEDEE]">
                    <Text className="font-semibold">Ankle angle:</Text>{" "}
                    {m.angle_deg.toFixed(1)}°
                  </Text>
                </View>
              )}

              <View className="h-[1px] w-full bg-[#8C8C8C] dark:bg-[#6C6C6C]" />
            </View>
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}
