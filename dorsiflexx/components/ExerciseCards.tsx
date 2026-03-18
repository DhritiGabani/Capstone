/**
 * Shared exercise card components used in both exercise-summary (history)
 * and end-exercise (post-session summary).
 */

import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { Pressable, Text, View } from "react-native";
import Svg, { Circle, Line, Polyline, Text as SvgText } from "react-native-svg";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ExerciseType =
  | "ankle_circles_cw"
  | "ankle_circles_ccw"
  | "calf_raises_on_step"
  | "heel_walks";

type BaseExercise = {
  id: string;
  displayName: string;
  type: ExerciseType;
};

export type AnkleCirclesExercise = BaseExercise & {
  type: "ankle_circles_cw" | "ankle_circles_ccw";
  repetitions: number;
  averageSpeed: number;
  percentMaxROM: number[];
  consistencyScore?: number | null;
};

export type CalfRaisesExercise = BaseExercise & {
  type: "calf_raises_on_step";
  repetitions: number;
  averageSpeed: number;
  percentMaxROM: number[];
  consistencyScore?: number | null;
};

export type HeelWalksExercise = BaseExercise & {
  type: "heel_walks";
  duration: number;
  numberOfSteps: number;
  repAngles: number[];
  meanAngleDeg?: number | null;
};

export type ExerciseEntry =
  | AnkleCirclesExercise
  | CalfRaisesExercise
  | HeelWalksExercise;

// ---------------------------------------------------------------------------
// Data mapping
// ---------------------------------------------------------------------------

export function mapBackendToExercises(
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

      const repAngleMap =
        ankleAngles?.rep_min_angle_deg ?? ankleAngles?.rep_max_angle_deg;
      const repAngles: number[] = repAngleMap
        ? Object.values(repAngleMap)
        : [];

      const meanAngleDeg =
        ankleAngles?.mean_min_angle_deg ??
        ankleAngles?.mean_max_angle_deg ??
        null;

      exercises.push({
        id: `${idPrefix}-ex-${idx}`,
        type: "heel_walks",
        displayName: "HEEL WALKING",
        duration: Math.round(totalDuration as number),
        numberOfSteps: repCount as number,
        repAngles,
        meanAngleDeg,
      });
    }
  }

  return exercises;
}

// ---------------------------------------------------------------------------
// MiniLineChart (pure SVG)
// ---------------------------------------------------------------------------

type MiniLineChartProps = {
  values: number[];
  isDark: boolean;
  referenceLabel?: string;
  referenceValue?: number;
  yMin?: number;
  yMax?: number;
};

export function MiniLineChart({
  values,
  isDark,
  referenceLabel,
  referenceValue,
  yMin = 0,
  yMax = 1,
}: MiniLineChartProps) {
  if (!values.length) return null;

  const W = 260;
  const H = 110;
  const padL = 38;
  const padR = 12;
  const padT = 10;
  const padB = 14;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const textColor = isDark ? "#ECEDEE" : "#11181C";

  const xForIdx = (i: number) => {
    if (values.length === 1) return padL + innerW / 2;
    return padL + (i / (values.length - 1)) * innerW;
  };

  const yForVal = (v: number) => {
    const range = yMax - yMin || 1;
    const t = (v - yMin) / range;
    return padT + (1 - t) * innerH;
  };

  const points = values
    .map((v, i) => `${xForIdx(i)},${yForVal(v)}`)
    .join(" ");

  const refY =
    referenceValue !== undefined ? yForVal(referenceValue) : undefined;

  const yTopLabel = yMax % 1 === 0 ? String(yMax) : yMax.toFixed(1);
  const yBotLabel = yMin % 1 === 0 ? String(yMin) : yMin.toFixed(1);

  return (
    <View className="mt-2">
      <Svg width={W} height={H}>
        {/* Y axis */}
        <Line
          x1={padL} y1={padT}
          x2={padL} y2={H - padB}
          stroke={textColor} strokeWidth={1}
        />
        {/* X axis */}
        <Line
          x1={padL} y1={H - padB}
          x2={W - padR} y2={H - padB}
          stroke={textColor} strokeWidth={1}
        />

        {/* Y axis labels */}
        <SvgText
          x={padL - 4} y={padT + 4}
          fontSize={10} textAnchor="end"
          fill={textColor} fillOpacity={0.7}
        >
          {yTopLabel}
        </SvgText>
        <SvgText
          x={padL - 4} y={H - padB}
          fontSize={10} textAnchor="end"
          fill={textColor} fillOpacity={0.7}
        >
          {yBotLabel}
        </SvgText>

        {/* Reference line */}
        {refY !== undefined && (
          <>
            <Line
              x1={padL} y1={refY}
              x2={W - padR} y2={refY}
              stroke={textColor} strokeWidth={1}
              strokeDasharray="5 4"
              strokeOpacity={0.5}
            />
            {!!referenceLabel && (
              <SvgText
                x={padL - 4} y={refY - 2}
                fontSize={9} textAnchor="end"
                fill={textColor} fillOpacity={0.6}
              >
                {referenceLabel}
              </SvgText>
            )}
          </>
        )}

        {/* Line */}
        {values.length > 1 && (
          <Polyline
            points={points}
            fill="none"
            stroke={textColor}
            strokeWidth={1.5}
          />
        )}

        {/* Dots */}
        {values.map((v, i) => (
          <Circle
            key={i}
            cx={xForIdx(i)}
            cy={yForVal(v)}
            r={3}
            fill={textColor}
          />
        ))}

        {/* X axis rep labels */}
        {values.map((_, i) => (
          <SvgText
            key={`xl-${i}`}
            x={xForIdx(i)}
            y={H - 1}
            fontSize={9}
            textAnchor="middle"
            fill={textColor}
            fillOpacity={0.5}
          >
            {i + 1}
          </SvgText>
        ))}
      </Svg>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Detail panels
// ---------------------------------------------------------------------------

type RendererProps<T extends ExerciseEntry> = {
  exercise: T;
  isDark: boolean;
};

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
        {exercise.averageSpeed.toFixed(1)} sec/circle
      </Text>

      {exercise.consistencyScore != null && (
        <Text className="mt-1 text-[16px] text-[#11181C] dark:text-[#ECEDEE]">
          <Text className="font-semibold">Session score:</Text>{" "}
          {exercise.consistencyScore.toFixed(1)}%
        </Text>
      )}

      {exercise.percentMaxROM.length > 0 && (
        <>
          <Text className="mt-3 text-[14px] font-semibold text-[#11181C] dark:text-[#ECEDEE]">
            ROM per rep (fraction of max):
          </Text>
          <MiniLineChart
            values={exercise.percentMaxROM}
            isDark={isDark}
            referenceValue={1}
            referenceLabel="max"
            yMin={0}
            yMax={1}
          />
        </>
      )}
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
        {exercise.averageSpeed.toFixed(1)} sec/rep
      </Text>

      {exercise.consistencyScore != null && (
        <Text className="mt-1 text-[16px] text-[#11181C] dark:text-[#ECEDEE]">
          <Text className="font-semibold">Session score:</Text>{" "}
          {exercise.consistencyScore.toFixed(1)}%
        </Text>
      )}

      {exercise.percentMaxROM.length > 0 && (
        <>
          <Text className="mt-3 text-[14px] font-semibold text-[#11181C] dark:text-[#ECEDEE]">
            ROM per rep (fraction of max):
          </Text>
          <MiniLineChart
            values={exercise.percentMaxROM}
            isDark={isDark}
            referenceValue={1}
            referenceLabel="max"
            yMin={0}
            yMax={1}
          />
        </>
      )}
    </View>
  );
}

function HeelWalksDetails({
  exercise,
  isDark,
}: RendererProps<HeelWalksExercise>) {
  const angleYMax =
    exercise.repAngles.length > 0
      ? Math.ceil(Math.max(...exercise.repAngles) / 10) * 10
      : 90;

  return (
    <View className="bg-[#eee] px-3 py-3 dark:bg-[#2B2D31]">
      <Text className="text-[16px] text-[#11181C] dark:text-[#ECEDEE]">
        <Text className="font-semibold">Duration:</Text> {exercise.duration} sec
      </Text>

      <Text className="mt-3 text-[14px] font-semibold text-[#11181C] dark:text-[#ECEDEE]">
        Ankle angle per step (°):
      </Text>

      {exercise.repAngles.length > 0 ? (
        <MiniLineChart
          values={exercise.repAngles}
          isDark={isDark}
          referenceValue={exercise.meanAngleDeg ?? undefined}
          referenceLabel="mean"
          yMin={0}
          yMax={angleYMax}
        />
      ) : (
        <Text className="mt-1 text-[14px] text-[#11181C] dark:text-[#ECEDEE] opacity-50">
          No angle data available for this session.
        </Text>
      )}

      {exercise.meanAngleDeg != null && (
        <Text className="mt-3 text-[16px] text-[#11181C] dark:text-[#ECEDEE]">
          <Text className="font-semibold">Mean ankle angle:</Text>{" "}
          {exercise.meanAngleDeg.toFixed(1)}°
        </Text>
      )}
    </View>
  );
}

const detailRenderers = {
  ankle_circles_cw: AnkleCirclesDetails,
  ankle_circles_ccw: AnkleCirclesDetails,
  calf_raises_on_step: CalfRaisesDetails,
  heel_walks: HeelWalksDetails,
} as const;

// ---------------------------------------------------------------------------
// Accordion row (exported for use in both screens)
// ---------------------------------------------------------------------------

export function ExerciseAccordionRow({
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
  const Renderer = detailRenderers[
    exercise.type
  ] as React.ComponentType<RendererProps<any>>;

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

      {expanded && <Renderer exercise={exercise} isDark={isDark} />}

      <View className="h-[1px] w-full bg-[#8C8C8C] dark:bg-[#6C6C6C]" />
    </View>
  );
}
