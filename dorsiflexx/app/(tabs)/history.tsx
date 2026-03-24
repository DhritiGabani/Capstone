import {
  ExerciseEntry,
  mapBackendToExercises,
} from "@/components/ExerciseCards";
import BackendService from "@/src/services/api/BackendService";
import { Ionicons } from "@expo/vector-icons";
import DateTimePicker, {
  DateTimePickerEvent,
} from "@react-native-community/datetimepicker";
import * as MailComposer from "expo-mail-composer";
import * as Print from "expo-print";
import { router, useFocusEffect } from "expo-router";
import React, { useCallback, useMemo, useState } from "react";
import {
  Alert,
  Modal,
  Platform,
  Pressable,
  SafeAreaView,
  Text,
  View,
  useColorScheme,
} from "react-native";
import { Calendar, DateData } from "react-native-calendars";

type MarkedDate = {
  disableTouchEvent?: boolean;
  customStyles?: {
    container?: Record<string, any>;
    text?: Record<string, any>;
  };
};

type PdfSessionEntry = {
  id: string;
  sortTime: string;
  timeLabel: string;
  exercises: ExerciseEntry[];
};

type PdfTimelineItem =
  | { type: "session"; sortTime: string; data: PdfSessionEntry }
  | {
      type: "ktw";
      sortTime: string;
      data: {
        id: string | number;
        measured_at: string;
        angle_deg: number;
      };
    };

type PdfDateSection = {
  date: string;
  title: string;
  timeline: PdfTimelineItem[];
};

type PdfRow = {
  label: string;
  value: string;
};

const HARD_CODED_RECIPIENT = "xiesophia7@gmail.com";

function toLocalDateString(date: Date) {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function isPastDate(dateString: string, todayString: string) {
  return dateString < todayString;
}

function getTwoWeeksAgo(date: Date) {
  const d = new Date(date);
  d.setDate(d.getDate() - 14);
  return d;
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function formatPdfTimeLabel(isoString: string): string {
  const d = new Date(isoString);
  return d.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "America/Toronto",
  });
}

function formatPdfDateLabel(dateString: string): string {
  const [year, month, day] = dateString.split("-").map(Number);
  const d = new Date(year, month - 1, day);

  return d.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function formatSubjectDate(date: Date) {
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function escapeHtml(text: string) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(text: string) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getExerciseRows(exercise: ExerciseEntry): PdfRow[] {
  switch (exercise.type) {
    case "ankle_circles_cw":
    case "ankle_circles_ccw":
      return [
        {
          label: "# Repetitions",
          value: String(exercise.repetitions),
        },
        {
          label: "Average speed",
          value: `${exercise.averageSpeed.toFixed(1)} sec/circle`,
        },
        ...(exercise.consistencyScore != null
          ? [
              {
                label: "Session score",
                value: `${exercise.consistencyScore.toFixed(1)}%`,
              },
            ]
          : []),
      ];

    case "calf_raises_on_step":
      return [
        {
          label: "# Repetitions",
          value: String(exercise.repetitions),
        },
        {
          label: "Average speed",
          value: `${exercise.averageSpeed.toFixed(1)} sec/rep`,
        },
        ...(exercise.consistencyScore != null
          ? [
              {
                label: "Session score",
                value: `${exercise.consistencyScore.toFixed(1)}%`,
              },
            ]
          : []),
      ];

    case "heel_walks":
      return [
        {
          label: "Duration",
          value: `${exercise.duration} sec`,
        },
        {
          label: "Number of steps",
          value: String(exercise.numberOfSteps),
        },
        ...(exercise.meanAngleDeg != null
          ? [
              {
                label: "Mean ankle angle",
                value: `${exercise.meanAngleDeg.toFixed(1)}°`,
              },
            ]
          : []),
      ];
  }
}

function buildMiniLineChartSvg(
  values: number[],
  options?: {
    width?: number;
    height?: number;
    stroke?: string;
    axis?: string;
    pointFill?: string;
    yLabel?: string;
    valueSuffix?: string;
    decimals?: number;
  },
) {
  if (values.length === 0) return "";

  const width = options?.width ?? 260;
  const height = options?.height ?? 120;
  const stroke = options?.stroke ?? "#8d44bc";
  const axis = options?.axis ?? "#999999";
  const pointFill = options?.pointFill ?? "#8d44bc";
  const yLabel = options?.yLabel ?? "";
  const valueSuffix = options?.valueSuffix ?? "";
  const decimals = options?.decimals ?? 2;

  const padL = 42;
  const padR = 10;
  const padT = 12;
  const padB = 24;

  const plotW = width - padL - padR;
  const plotH = height - padT - padB;

  const minValue = 0;
  const maxValue = Math.max(...values);

  const yMin = minValue === maxValue ? minValue - 0.1 : minValue;
  const yMax = minValue === maxValue ? maxValue + 0.1 : maxValue;

  const xForIndex = (i: number) =>
    padL +
    (values.length === 1 ? plotW / 2 : (i / (values.length - 1)) * plotW);

  const yForValue = (v: number) =>
    padT + (1 - (v - yMin) / (yMax - yMin || 1)) * plotH;

  const points = values
    .map((v, i) => `${xForIndex(i)},${yForValue(v)}`)
    .join(" ");

  const circles = values
    .map(
      (v, i) => `
        <circle cx="${xForIndex(i)}" cy="${yForValue(v)}" r="3" fill="${pointFill}" />
      `,
    )
    .join("");

  const xLabels = values
    .map(
      (_, i) => `
        <text
          x="${xForIndex(i)}"
          y="${height - 6}"
          font-size="10"
          text-anchor="middle"
          fill="#555"
        >
          ${i + 1}
        </text>
      `,
    )
    .join("");

  const yTicks = [yMin, (yMin + yMax) / 2, yMax];
  const yTickLines = yTicks
    .map((tick) => {
      const y = yForValue(tick);
      return `
        <line x1="${padL}" y1="${y}" x2="${width - padR}" y2="${y}" stroke="#e2e2e2" stroke-width="1" />
        <text x="${padL - 6}" y="${y + 3}" font-size="10" text-anchor="end" fill="#555">
          ${tick.toFixed(decimals)}${escapeAttr(valueSuffix)}
        </text>
      `;
    })
    .join("");

  return `
    <svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
      <line x1="${padL}" y1="${padT}" x2="${padL}" y2="${height - padB}" stroke="${axis}" stroke-width="1.5" />
      <line x1="${padL}" y1="${height - padB}" x2="${width - padR}" y2="${height - padB}" stroke="${axis}" stroke-width="1.5" />

      ${yTickLines}

      <polyline
        fill="none"
        stroke="${stroke}"
        stroke-width="2.5"
        points="${escapeAttr(points)}"
      />

      ${circles}
      ${xLabels}

      ${
        yLabel
          ? `
        <text
          x="4"
          y="${height / 2}"
          font-size="10"
          text-anchor="middle"
          fill="#555"
          transform="rotate(-90 12 ${height / 2})"
        >
          ${escapeHtml(yLabel)}
        </text>
      `
          : ""
      }

      <text
        x="${padL + plotW / 2}"
        y="${height - 2}"
        font-size="10"
        text-anchor="middle"
        fill="#555"
      >
        Rep
      </text>
    </svg>
  `;
}

function renderChartBlock(title: string, values: number[], yLabel: string) {
  if (values.length === 0) return "";

  return `
    <div class="chart-block">
      <div class="chart-title">${escapeHtml(title)}</div>
      ${buildMiniLineChartSvg(values, {
        yLabel,
        decimals: 2,
      })}
    </div>
  `;
}

function renderExerciseDetails(exercise: ExerciseEntry) {
  const rows = getExerciseRows(exercise);

  const romChart =
    exercise.type === "ankle_circles_cw" ||
    exercise.type === "ankle_circles_ccw" ||
    exercise.type === "calf_raises_on_step"
      ? renderChartBlock("ROM per rep", exercise.percentMaxROM, "% Max ROM")
      : "";

  const heelWalkChart =
    exercise.type === "heel_walks"
      ? renderChartBlock(
          "Ankle angle per step",
          exercise.repAngles,
          "Angle (°)",
        )
      : "";

  return `
    <div class="exercise-block">
      <div class="exercise-header">
        <div class="exercise-title">${escapeHtml(exercise.displayName)}</div>
      </div>

      <div class="exercise-expanded">
        ${
          rows.length > 0
            ? rows
                .map(
                  (row) => `
                    <div class="metric-row">
                      <div class="metric-label">${escapeHtml(row.label)}</div>
                      <div class="metric-value">${escapeHtml(row.value)}</div>
                    </div>
                  `,
                )
                .join("")
            : `
              <div class="metric-row">
                <div class="metric-label">No data</div>
                <div class="metric-value">—</div>
              </div>
            `
        }

        ${romChart}
        ${heelWalkChart}
      </div>
    </div>
  `;
}

function renderTimelineItem(item: PdfTimelineItem) {
  if (item.type === "session") {
    const session = item.data;

    return `
      <div class="session-block">
        <div class="time-pill">${escapeHtml(session.timeLabel)}</div>
        <div class="divider"></div>
        ${session.exercises.map(renderExerciseDetails).join("")}
      </div>
    `;
  }

  const m = item.data;

  return `
    <div class="session-block">
      <div class="time-pill">${escapeHtml(formatPdfTimeLabel(m.measured_at))}</div>
      <div class="divider"></div>
      <div class="exercise-block">
        <div class="exercise-header">
          <div class="exercise-title">KNEE-TO-WALL TEST</div>
        </div>
        <div class="exercise-expanded">
          <div class="metric-row">
            <div class="metric-label">Ankle angle</div>
            <div class="metric-value">${escapeHtml(m.angle_deg.toFixed(1))}°</div>
          </div>
        </div>
      </div>
    </div>
  `;
}

function buildExerciseHistoryPdfHtml(sections: PdfDateSection[]) {
  return `
    <html>
      <head>
        <meta charset="utf-8" />
        <style>
          @page {
            margin-top: 60px;
            margin-bottom: 60px;
            margin-left: 28px;
            margin-right: 28px;
          }

          body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            color: #11181C;
            background: #ffffff;
            padding: 0;
          }

          .page-title {
            text-align: center;
            font-size: 26px;
            font-weight: 700;
            margin-bottom: 20px;
          }

          .date-section {
            margin-bottom: 20px;
            page-break-inside: avoid;
          }

          .date-title {
            text-align: center;
            font-size: 22px;
            font-weight: 600;
            margin-bottom: 14px;
          }

          .session-block {
            margin-bottom: 14px;
          }

          .time-pill {
            display: inline-block;
            background: #8d44bc;
            color: white;
            border-radius: 999px;
            padding: 8px 16px;
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 6px;
          }

          .divider {
            height: 1px;
            background: #8C8C8C;
            width: 100%;
            margin-bottom: 6px;
          }

          .exercise-block {
            margin-bottom: 10px;
          }

          .exercise-header {
            padding: 8px 0;
          }

          .exercise-title {
            font-size: 18px;
            font-weight: 700;
          }

          .exercise-expanded {
            background: #eeeeee;
            padding: 10px;
            margin-bottom: 6px;
          }

          .metric-row {
            display: flex;
            justify-content: space-between;
            gap: 16px;
            padding: 4px 0;
            border-bottom: 1px solid #d7d7d7;
          }

          .metric-row:last-child {
            border-bottom: none;
          }

          .metric-label {
            font-size: 15px;
            font-weight: 600;
          }

          .metric-value {
            font-size: 15px;
            text-align: right;
          }

          .chart-block {
            margin-top: 8px;
            padding-top: 4px;
          }

          .chart-title {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 4px;
          }

          .empty-text {
            text-align: center;
            color: #666;
            font-size: 15px;
            margin-top: 8px;
          }
        </style>
      </head>
      <body>
        <div class="page-title">Exercise History Summary</div>

        ${sections
          .map(
            (section, index) => `
              <div class="date-section" ${
                index > 0 ? `style="page-break-before: always;"` : ""
              }>
                <div class="date-title">${escapeHtml(section.title)}</div>
                ${
                  section.timeline.length === 0
                    ? `<div class="empty-text">No exercise sessions found for this date.</div>`
                    : section.timeline.map(renderTimelineItem).join("")
                }
              </div>
            `,
          )
          .join("")}
      </body>
    </html>
  `;
}

export default function HistoryCalendarScreen() {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";

  const today = new Date();
  const todayString = toLocalDateString(today);

  const [completedExerciseDates, setCompletedExerciseDates] = useState<
    string[]
  >([]);
  const [showShareModal, setShowShareModal] = useState(false);
  const [startDate, setStartDate] = useState<Date>(getTwoWeeksAgo(today));
  const [endDate, setEndDate] = useState<Date>(today);
  const [isExporting, setIsExporting] = useState(false);

  useFocusEffect(
    useCallback(() => {
      BackendService.getSessionDates()
        .then((dates) => {
          setCompletedExerciseDates(dates);
        })
        .catch((err) => {
          console.error("Failed to fetch session dates:", err);
          setCompletedExerciseDates([]);
        });
    }, []),
  );

  const colors = {
    bg: isDark ? "#151718" : "#F5F1F8",
    text: isDark ? "#ECEDEE" : "#11181C",
    purple: "#8d44bc",
    card: isDark ? "#1E2224" : "#FFFFFF",
    border: isDark ? "#3A3F42" : "#D9D2E3",
    overlay: "rgba(0,0,0,0.4)",
  };

  const markedDates = useMemo<Record<string, MarkedDate>>(() => {
    const marks: Record<string, MarkedDate> = {};

    for (const date of completedExerciseDates) {
      if (isPastDate(date, todayString) || date === todayString) {
        marks[date] = {
          customStyles: {
            container: {
              backgroundColor: colors.purple,
              borderRadius: 999,
              width: 38,
              height: 38,
              alignItems: "center",
              justifyContent: "center",
            },
            text: {
              color: "#fff",
              fontSize: 18,
              fontWeight: "500",
            },
          },
        };
      }
    }

    const didExerciseToday = completedExerciseDates.includes(todayString);

    marks[todayString] = {
      customStyles: {
        container: {
          backgroundColor: didExerciseToday ? colors.purple : "transparent",
          borderWidth: 3,
          borderColor: colors.text,
          borderRadius: 999,
          width: 38,
          height: 38,
          alignItems: "center",
          justifyContent: "center",
        },
        text: {
          color: didExerciseToday ? "#fff" : colors.text,
          fontSize: 18,
          fontWeight: "500",
        },
      },
    };

    return marks;
  }, [completedExerciseDates, todayString, colors.purple, colors.text]);

  const handleDayPress = (day: DateData) => {
    if (
      day.dateString !== todayString &&
      !completedExerciseDates.includes(day.dateString)
    ) {
      return;
    }

    router.push({
      pathname: "/exercise-summary",
      params: { date: day.dateString },
    });
  };

  const handleOpenShareModal = () => {
    setStartDate(getTwoWeeksAgo(today));
    setEndDate(today);
    setShowShareModal(true);
  };

  const handleStartDateChange = (
    _event: DateTimePickerEvent,
    selectedDate?: Date,
  ) => {
    if (!selectedDate) return;

    setStartDate(selectedDate);

    if (selectedDate > endDate) {
      setEndDate(selectedDate);
    }
  };

  const handleEndDateChange = (
    _event: DateTimePickerEvent,
    selectedDate?: Date,
  ) => {
    if (!selectedDate) return;

    if (selectedDate < startDate) {
      setEndDate(startDate);
      return;
    }

    setEndDate(selectedDate);
  };

  const handleShare = async () => {
    if (isExporting) return;

    try {
      setIsExporting(true);

      const start = toLocalDateString(startDate);
      const end = toLocalDateString(endDate);

      const selectedDates = completedExerciseDates.filter(
        (date) => date >= start && date <= end,
      );

      if (selectedDates.length === 0) {
        Alert.alert("No data", "No exercise dates were found in that range.");
        return;
      }

      const allDateSections = await Promise.all(
        selectedDates.map(async (date) => {
          const [backendSessions, ktw] = await Promise.all([
            BackendService.getSessionsByDate(date).catch(() => []),
            BackendService.getKTWByDate(date).catch(() => []),
          ]);

          const sessionItems = backendSessions.map((s) => ({
            type: "session" as const,
            sortTime: s.start_time,
            data: {
              id: s.session_id,
              sortTime: s.start_time,
              timeLabel: formatPdfTimeLabel(s.start_time),
              exercises: s.analysis
                ? mapBackendToExercises(s.analysis, s.session_id)
                : [],
            },
          }));

          const ktwItems = ktw.map((m) => ({
            type: "ktw" as const,
            sortTime: m.measured_at,
            data: m,
          }));

          const timeline: PdfTimelineItem[] = [
            ...sessionItems,
            ...ktwItems,
          ].sort((a, b) => a.sortTime.localeCompare(b.sortTime));

          return {
            date,
            title: formatPdfDateLabel(date),
            timeline,
          };
        }),
      );

      const html = buildExerciseHistoryPdfHtml(allDateSections);

      const { uri } = await Print.printToFileAsync({
        html,
        base64: false,
      });

      console.log("PDF created:", uri);

      const mailAvailable = await MailComposer.isAvailableAsync();
      console.log("Mail available:", mailAvailable);

      if (!mailAvailable) {
        Alert.alert(
          "Email unavailable",
          "Mail is not configured on this device.",
        );
        return;
      }

      const startLabel = formatSubjectDate(startDate);
      const endLabel = formatSubjectDate(endDate);

      const subject =
        startLabel === endLabel
          ? `Exercise Summary – ${startLabel}`
          : `Exercise Summary – ${startLabel} to ${endLabel}`;

      setShowShareModal(false);
      await sleep(800);

      const result = await MailComposer.composeAsync({
        recipients: [HARD_CODED_RECIPIENT],
        subject,
        body: "Hi,\n\nPlease find attached my exercise history summary.\n\nThank you.",
        attachments: [uri],
      });

      console.log("Mail composer result:", result);
    } catch (err) {
      console.error("Failed to export/email PDF:", err);
      Alert.alert(
        "Email failed",
        err instanceof Error ? err.message : "Unknown error",
      );
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-[#151718]">
      <Pressable
        onPress={handleOpenShareModal}
        className="absolute right-6 top-16 z-10 p-2"
      >
        <Ionicons name="share-outline" size={36} color={colors.text} />
      </Pressable>

      <View className="flex-1 px-6 pt-36">
        <View>
          <Calendar
            initialDate={todayString}
            onDayPress={handleDayPress}
            enableSwipeMonths
            hideExtraDays
            markingType="custom"
            markedDates={markedDates}
            renderArrow={(direction) => (
              <Ionicons
                name={direction === "left" ? "chevron-back" : "chevron-forward"}
                size={26}
                color={colors.text}
              />
            )}
            style={{
              backgroundColor: "transparent",
            }}
            theme={{
              calendarBackground: "transparent",
              backgroundColor: "transparent",
              monthTextColor: colors.text,
              textMonthFontSize: 22,
              textMonthFontWeight: "700",
              textSectionTitleColor: colors.text,
              textDayHeaderFontSize: 15,
              textDayFontSize: 18,
              dayTextColor: colors.text,
              textDisabledColor: "transparent",
              todayTextColor: colors.text,
              arrowColor: colors.text,
            }}
          />
        </View>
      </View>

      <Modal
        visible={showShareModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowShareModal(false)}
      >
        <Pressable
          className="flex-1 items-center justify-center px-6"
          style={{ backgroundColor: colors.overlay }}
          onPress={() => setShowShareModal(false)}
        >
          <Pressable
            className="w-full max-w-[420px] rounded-3xl px-5 py-6"
            style={{ backgroundColor: colors.card }}
            onPress={() => {}}
          >
            <Text
              className="mb-5 text-center text-2xl font-bold"
              style={{ color: colors.text }}
            >
              Export History
            </Text>

            <View className="mb-5">
              <Text
                className="mb-2 text-xl font-bold"
                style={{ color: colors.text }}
              >
                Start
              </Text>

              <View
                className="h-36 justify-center overflow-hidden rounded-2xl"
                style={{ borderWidth: 1, borderColor: colors.border }}
              >
                <DateTimePicker
                  value={startDate}
                  mode="date"
                  display={Platform.OS === "ios" ? "spinner" : "default"}
                  onChange={handleStartDateChange}
                  maximumDate={today}
                  textColor={colors.text}
                  themeVariant={isDark ? "dark" : "light"}
                  style={
                    Platform.OS === "ios"
                      ? { transform: [{ scaleY: 0.9 }] }
                      : undefined
                  }
                />
              </View>
            </View>

            <View className="mb-6">
              <Text
                className="mb-2 text-xl font-bold"
                style={{ color: colors.text }}
              >
                End
              </Text>

              <View
                className="h-36 justify-center overflow-hidden rounded-2xl"
                style={{ borderWidth: 1, borderColor: colors.border }}
              >
                <DateTimePicker
                  value={endDate}
                  mode="date"
                  display={Platform.OS === "ios" ? "spinner" : "default"}
                  onChange={handleEndDateChange}
                  minimumDate={startDate}
                  maximumDate={today}
                  textColor={colors.text}
                  themeVariant={isDark ? "dark" : "light"}
                  style={
                    Platform.OS === "ios"
                      ? { transform: [{ scaleY: 0.9 }] }
                      : undefined
                  }
                />
              </View>
            </View>

            <View className="flex-row justify-between gap-3">
              <Pressable
                onPress={() => setShowShareModal(false)}
                className="flex-1 items-center rounded-full border py-3"
                style={{ borderColor: colors.purple }}
              >
                <Text
                  className="text-base font-semibold"
                  style={{ color: colors.purple }}
                >
                  Cancel
                </Text>
              </Pressable>

              <Pressable
                onPress={handleShare}
                disabled={isExporting}
                className="flex-1 items-center rounded-full py-3"
                style={{
                  backgroundColor: colors.purple,
                  opacity: isExporting ? 0.6 : 1,
                }}
              >
                <Text className="text-base font-semibold text-white">
                  {isExporting ? "Preparing..." : "Email"}
                </Text>
              </Pressable>
            </View>
          </Pressable>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}
