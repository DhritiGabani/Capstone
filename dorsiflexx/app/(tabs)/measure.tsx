import PillButton from "@/components/PillButton";
import BackendService, { KTWMeasurement } from "@/src/services/api/BackendService";
import { router, useFocusEffect } from "expo-router";
import React, { useCallback, useMemo, useState } from "react";
import { SafeAreaView, Text, useColorScheme, View } from "react-native";
import Svg, { Circle, Line, Polyline, Text as SvgText } from "react-native-svg";

type Measurement = {
  date: string;
  dateLabel: string;
  angleDeg: number;
};

function formatDateLabel(isoDate: string): string {
  const d = new Date(isoDate);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
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

    const parseTime = (isoDate: string) => new Date(isoDate).getTime();

    const times = measurements.map((m) => parseTime(m.date));
    const tMin = Math.min(...times);
    const tMax = Math.max(...times);

    const xForMeasurement = (m: Measurement) => {
      // If all dates are same, center
      if (tMax === tMin) return padL + innerW / 2;

      const edgePadding = 12; // keeps first point off the y-axis and last off right edge
      const usableWidth = innerW - edgePadding * 2;

      const t = (parseTime(m.date) - tMin) / (tMax - tMin); // 0..1
      return padL + edgePadding + t * usableWidth;
    };

    const yForValue = (v: number) => {
      const t = (v - yMin) / (yMax - yMin);
      return padT + (1 - t) * innerH;
    };

    const points = measurements
      .map((m) => `${xForMeasurement(m)},${yForValue(m.angleDeg)}`)
      .join(" ");

    const goalY = yForValue(goalAngle);

    // y-axis ticks (every 5 degrees)
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
      points,
      xForMeasurement,
      yForValue,
      goalY,
      ticks,
    };
  }, [measurements, goalAngle]);

  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
      <View className="flex-1 px-[22px] justify-center gap-8">
        {/* Title */}
        <View className="items-center">
          <Text className="text-[26px] pb-2 text-[#11181C] text-center dark:text-[#ECEDEE]">
            KNEE-TO-WALL{"\n"}MEASUREMENTS
          </Text>
        </View>

        {/* Chart card */}
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

                {/* 20° label */}
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

                {/* 40° label */}
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

                {measurements.map((m, i) => {
                  const x = chart.xForMeasurement(m);
                  const yAxis = chart.H - chart.padB;

                  return (
                    <Line
                      key={`xtick-${m.dateLabel}-${i}`}
                      x1={x}
                      y1={yAxis}
                      x2={x}
                      y2={yAxis + 8}
                      stroke={textColor}
                      strokeWidth={1.5}
                    />
                  );
                })}

                {/* Y ticks + labels */}
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

                {/* Goal dashed line + label */}
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

                {/* Line path */}
                <Polyline
                  points={chart.points}
                  fill="none"
                  stroke={textColor}
                  strokeWidth={2}
                />

                {/* Points */}
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

                {/* X labels */}
                {measurements.map((m, i) => {
                  const x = chart.xForMeasurement(m) + 5;
                  const y = chart.H - chart.padB + 18;
                  return (
                    <SvgText
                      key={`xlabel-${m.date}-${i}`}
                      x={x}
                      y={y}
                      fontSize={14}
                      fill={textColor}
                      textAnchor="end"
                      transform={`rotate(-90, ${x}, ${y})`}
                    >
                      {m.dateLabel}
                    </SvgText>
                  );
                })}
              </Svg>
            </View>
          </View>
        </View>

        {/* Button */}
        <View className="items-center">
          <View className="w-4/5 self-center max-w-[420px]">
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
