import * as Notifications from "expo-notifications";
import { Platform } from "react-native";
import type { NotificationSchedule } from "./api/BackendService";

// Show alerts when the app is in the foreground
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

const DAY_ABBREVS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"] as const;
// expo-notifications weekday: 1=Sunday, 2=Monday, ..., 7=Saturday
function dayAbbrevToWeekday(day: string): number {
  return DAY_ABBREVS.indexOf(day as (typeof DAY_ABBREVS)[number]) + 1;
}

export async function requestNotificationPermissions(): Promise<boolean> {
  if (Platform.OS === "web") return false;
  const { status: existing } = await Notifications.getPermissionsAsync();
  if (existing === "granted") return true;
  const { status } = await Notifications.requestPermissionsAsync();
  return status === "granted";
}

/**
 * Cancel all previously scheduled goal notifications and reschedule
 * based on the current notification list from settings.
 */
export async function scheduleGoalNotifications(
  notifications: NotificationSchedule[],
): Promise<void> {
  // Cancel all existing scheduled notifications first
  await Notifications.cancelAllScheduledNotificationsAsync();

  const granted = await requestNotificationPermissions();
  if (!granted) return;

  for (const notification of notifications) {
    for (const day of notification.days) {
      const weekday = dayAbbrevToWeekday(day);
      if (weekday === 0) continue; // unknown day, skip

      await Notifications.scheduleNotificationAsync({
        content: {
          title: "Time to exercise! 💪",
          body: "Don't forget your dorsiflexx session today.",
        },
        trigger: {
          type: Notifications.SchedulableTriggerInputTypes.WEEKLY,
          weekday,
          hour: notification.time_hour,
          minute: notification.time_minute,
        },
      });
    }
  }
}
