import PillButton from "@/components/PillButton";
import BackendService, {
  KTWMeasurement,
} from "@/src/services/api/BackendService";
import { router, useFocusEffect } from "expo-router";
import React, { useCallback, useMemo, useState } from "react";
import { SafeAreaView, Text, useColorScheme, View } from "react-native";
import Svg, { Circle, Line, Polyline, Text as SvgText } from "react-native-svg";

type Measurement = {
  date: string;
  dateKey: string; // unique calendar day key
  dateLabel: string; // display label
  angleDeg: number;
};

function formatDateLabel(isoDate: string): string {
  const d = new Date(isoDate);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "America/New_York",
  });
}

function formatDateKey(isoDate: string): string {
  const d = new Date(isoDate);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);

  if (sorted.length % 2 === 0) {
    return (sorted[mid - 1] + sorted[mid]) / 2;
  }
  return sorted[mid];
}

export default function MeasurementsScreen() {
  const goalAngle = 45;

  const [ktwData, setKtwData] = useState<KTWMeasurement[]>([]);

  useFocusEffect(
    useCallback(() => {
      BackendService.getKTWHistory()
        .then(setKtwData)
        .catch(() => setKtwData([]));
    }, []),
  );

  const measurements: Measurement[] = useMemo(
    () =>
      ktwData.map((m) => ({
        date: m.measured_at,
        dateKey: formatDateKey(m.measured_at),
        dateLabel: formatDateLabel(m.measured_at),
        angleDeg: m.angle_deg,
      })),
    [ktwData],
  );

  const colorScheme = useColorScheme();
  const textColor = colorScheme === "dark" ? "#ECEDEE" : "#11181C";

  const chart = useMemo(() => {
    const W = 320;
    const H = 300;

    const padL = 62;
    const padR = 16;
    const padT = 18;
    const padB = 70;

    const innerW = W - padL - padR;
    const innerH = H - padT - padB;

    const yMin = 0;
    const yMax = 60;

    const groupedMap = new Map<
      string,
      {
        dateKey: string;
        dateLabel: string;
        timestamp: number;
        measurements: Measurement[];
        medianAngle: number;
      }
    >();

    for (const m of measurements) {
      const d = new Date(m.date);
      const dayTimestamp = new Date(
        d.getFullYear(),
        d.getMonth(),
        d.getDate(),
      ).getTime();

      if (!groupedMap.has(m.dateKey)) {
        groupedMap.set(m.dateKey, {
          dateKey: m.dateKey,
          dateLabel: m.dateLabel,
          timestamp: dayTimestamp,
          measurements: [],
          medianAngle: 0,
        });
      }

      groupedMap.get(m.dateKey)!.measurements.push(m);
    }

    const groupedDates = Array.from(groupedMap.values())
      .sort((a, b) => a.timestamp - b.timestamp)
      .map((group) => ({
        ...group,
        medianAngle: median(group.measurements.map((m) => m.angleDeg)),
      }));

    const times = groupedDates.map((g) => g.timestamp);
    const tMin = Math.min(...times);
    const tMax = Math.max(...times);

    const xForTimestamp = (timestamp: number) => {
      if (tMax === tMin) return padL + innerW / 2;

      const edgePadding = 12;
      const usableWidth = innerW - edgePadding * 2;
      const t = (timestamp - tMin) / (tMax - tMin);

      return padL + edgePadding + t * usableWidth;
    };

    const xByDateKey = new Map<string, number>();
    groupedDates.forEach((group) => {
      xByDateKey.set(group.dateKey, xForTimestamp(group.timestamp));
    });

    const xForMeasurement = (m: Measurement) =>
      xByDateKey.get(m.dateKey) ?? padL;

    const yForValue = (v: number) => {
      const t = (v - yMin) / (yMax - yMin);
      return padT + (1 - t) * innerH;
    };

    const medianPoints = groupedDates
      .map(
        (group) =>
          `${xByDateKey.get(group.dateKey)},${yForValue(group.medianAngle)}`,
      )
      .join(" ");

    const goalY = yForValue(goalAngle);

    const ticks = Array.from({ length: 13 }).map((_, i) => {
      const v = i * 5;
      return {
        v,
        y: yForValue(v),
        isMajor: v === 20 || v === 40,
      };
    });

    return {
      W,
      H,
      padL,
      padR,
      padT,
      padB,
      innerW,
      innerH,
      groupedDates,
      xForMeasurement,
      yForValue,
      medianPoints,
      goalY,
      ticks,
    };
  }, [measurements, goalAngle]);

  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
      <View className="flex-1 justify-center gap-8 px-[22px]">
        <View className="items-center">
          <Text className="pb-2 text-center text-[26px] text-[#11181C] dark:text-[#ECEDEE]">
            KNEE-TO-WALL{"\n"}MEASUREMENTS
          </Text>
        </View>

        <View className="items-center">
          <View className="w-full max-w-[420px] px-4 py-5">
            <View className="items-center">
              <Svg width={chart.W} height={chart.H}>
                {/* Axes */}
                <Line
                  x1={chart.padL}
                  y1={chart.padT}
                  x2={chart.padL}
                  y2={chart.H - chart.padB}
                  stroke={textColor}
                  strokeWidth={1.5}
                />
                <Line
                  x1={chart.padL}
                  y1={chart.H - chart.padB}
                  x2={chart.W - chart.padR}
                  y2={chart.H - chart.padB}
                  stroke={textColor}
                  strokeWidth={1.5}
                />

                {/* Y labels */}
                <SvgText
                  x={chart.padL - 20}
                  y={chart.yForValue(20)}
                  fontSize={14}
                  textAnchor="end"
                  alignmentBaseline="middle"
                  fill={textColor}
                >
                  20°
                </SvgText>

                <SvgText
                  x={chart.padL - 20}
                  y={chart.yForValue(40)}
                  fontSize={14}
                  textAnchor="end"
                  alignmentBaseline="middle"
                  fill={textColor}
                >
                  40°
                </SvgText>

                {/* One x tick per unique date */}
                {chart.groupedDates.map((group, i) => {
                  const x = chart.xForMeasurement(group.measurements[0]);
                  const yAxis = chart.H - chart.padB;

                  return (
                    <Line
                      key={`xtick-${group.dateKey}-${i}`}
                      x1={x}
                      y1={yAxis}
                      x2={x}
                      y2={yAxis + 8}
                      stroke={textColor}
                      strokeWidth={1.5}
                    />
                  );
                })}

                {/* Y ticks */}
                {chart.ticks.map((t) => (
                  <React.Fragment key={`tick-${t.v}`}>
                    <Line
                      x1={chart.padL - (t.isMajor ? 10 : 6)}
                      y1={t.y}
                      x2={chart.padL}
                      y2={t.y}
                      stroke={textColor}
                      strokeWidth={t.isMajor ? 1.6 : 1.2}
                    />
                  </React.Fragment>
                ))}

                {/* Goal line */}
                <Line
                  x1={chart.padL}
                  y1={chart.goalY}
                  x2={chart.W - chart.padR}
                  y2={chart.goalY}
                  stroke={textColor}
                  strokeWidth={1.4}
                  strokeDasharray="6 6"
                />
                <SvgText
                  x={chart.W - chart.padR - 4}
                  y={chart.goalY - 8}
                  fontSize={16}
                  textAnchor="end"
                  fill={textColor}
                >
                  GOAL
                </SvgText>

                {/* Line through medians */}
                <Polyline
                  points={chart.medianPoints}
                  fill="none"
                  stroke={textColor}
                  strokeWidth={2}
                />

                {/* All points, stacked on same x if same date */}
                {measurements.map((m, i) => {
                  const cx = chart.xForMeasurement(m);
                  const cy = chart.yForValue(m.angleDeg);
                  return (
                    <Circle
                      key={`${m.date}-${i}`}
                      cx={cx}
                      cy={cy}
                      r={3.2}
                      fill={textColor}
                    />
                  );
                })}

                {/* One x label per unique date */}
                {chart.groupedDates.map((group, i) => {
                  const x = chart.xForMeasurement(group.measurements[0]) + 5;
                  const y = chart.H - chart.padB + 18;

                  return (
                    <SvgText
                      key={`xlabel-${group.dateKey}-${i}`}
                      x={x}
                      y={y}
                      fontSize={14}
                      fill={textColor}
                      textAnchor="end"
                      transform={`rotate(-90, ${x}, ${y})`}
                    >
                      {group.dateLabel}
                    </SvgText>
                  );
                })}
              </Svg>
            </View>
          </View>
        </View>

        <View className="items-center">
          <View className="w-4/5 max-w-[420px] self-center">
            <PillButton
              title="Add measurement"
              onPress={() => router.push("/start-kneetowall")}
            />
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}
