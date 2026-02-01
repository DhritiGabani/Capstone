import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import type { SQLiteDatabase } from 'expo-sqlite';
import { useEffect, useState } from 'react';
import { Text, View } from 'react-native';
import 'react-native-reanimated';

import { useColorScheme } from '@/hooks/use-color-scheme';
import { DatabaseService } from '@/src/services/database';

export const unstable_settings = {
  anchor: '(tabs)',
};

// Separate component that only renders after db is ready
function RootLayoutNav({ db }: { db: SQLiteDatabase }) {
  const colorScheme = useColorScheme();

  // Enable Drizzle Studio - press shift+m in terminal to open

  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="modal" options={{ presentation: 'modal', title: 'Modal' }} />
      </Stack>
      <StatusBar style="auto" />
    </ThemeProvider>
  );
}

export default function RootLayout() {
  const [db, setDb] = useState<SQLiteDatabase | null>(null);
  const [dbError, setDbError] = useState<string | null>(null);

  useEffect(() => {
    async function initDatabase() {
      try {
        await DatabaseService.open();

        // Debug: List all tables
        const tables = await DatabaseService.query(
          "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        );
        console.log('📋 Tables in database:', tables);

        setDb(DatabaseService.db);
      } catch (error) {
        console.error('Failed to initialize database:', error);
        setDbError(error instanceof Error ? error.message : 'Unknown error');
      }
    }

    initDatabase();
  }, []);

  if (dbError) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <Text>Database Error: {dbError}</Text>
      </View>
    );
  }

  if (!db) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <Text>Loading database...</Text>
      </View>
    );
  }

  return <RootLayoutNav db={db} />;
}
