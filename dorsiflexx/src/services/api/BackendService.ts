import Constants from "expo-constants";

/**
 * Resolve the backend URL at runtime.
 *
 * On a physical device running via Expo Go the debuggerHost property
 * contains the dev machine's LAN IP (e.g. "192.168.1.42:8081").
 * We extract the IP and point to the backend on port 8000.
 * On the iOS simulator, localhost works fine.
 */
function getBackendUrl(): string {
  // Allow explicit override via EXPO_PUBLIC_BACKEND_URL (e.g. when using --tunnel)
  const envUrl = process.env.EXPO_PUBLIC_BACKEND_URL;
  if (envUrl) {
    console.log("[BackendService] Using env backend URL:", envUrl);
    return envUrl;
  }

  const debuggerHost =
    Constants.expoGoConfig?.debuggerHost ??
    (Constants as any).manifest?.debuggerHost ??
    (Constants as any).manifest2?.extra?.expoGo?.debuggerHost;
  if (debuggerHost) {
    const ip = debuggerHost.split(":")[0];
    // If the host looks like a tunnel URL (contains dots beyond a plain IP), skip it
    const isIp = /^\d{1,3}(\.\d{1,3}){3}$/.test(ip);
    if (isIp) {
      const url = `http://${ip}:8000`;
      console.log("[BackendService] Resolved backend URL:", url);
      return url;
    }
    console.log("[BackendService] debuggerHost appears to be a tunnel host, ignoring:", ip);
  }
  console.log("[BackendService] No debuggerHost found, falling back to localhost");
  console.log("[BackendService] Constants keys:", JSON.stringify(Object.keys(Constants)));
  return "http://localhost:8000";
}

const BACKEND_URL = getBackendUrl();

export interface SessionStartResponse {
  session_id: string;
  status: string;
  start_time: string;
}

export interface SessionStopResponse {
  session_id: string;
  status: string;
  duration_seconds: number;
  total_samples: number;
  exercises: Array<{
    exercise_type: string;
    rep_count: number;
    rom: number;
    tempo_consistency: number;
    movement_consistency: number;
  }>;
  analysis: Record<string, any>;
}

export interface StatusResponse {
  status: string;
  is_streaming: boolean;
  is_connected: boolean;
  session_id: string | null;
  stats: Record<string, any> | null;
}

export interface KTWStopResponse {
  largest_angle_deg: number;
  angle_over_time: Record<string, number>;
}

export interface KTWMeasurement {
  id: number;
  measured_at: string;
  angle_deg: number;
  details?: Record<string, any>;
}

export interface SessionByDate {
  session_id: string;
  start_time: string;
  end_time: string | null;
  duration_s: number | null;
  analysis?: Record<string, any>;
}

class BackendService {
  async connect(): Promise<SessionStartResponse> {
    const res = await fetch(`${BACKEND_URL}/session/start`, {
      method: "POST",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Failed to start session");
    }
    return res.json();
  }

  async disconnect(): Promise<SessionStopResponse> {
    const res = await fetch(`${BACKEND_URL}/session/stop`, {
      method: "POST",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Failed to stop session");
    }
    return res.json();
  }

  async saveFeedback(
    sessionId: string,
    rating: string,
    comments: string,
  ): Promise<void> {
    const res = await fetch(
      `${BACKEND_URL}/session/${sessionId}/feedback`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rating, comments }),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Failed to save feedback");
    }
  }

  async bleDisconnect(): Promise<void> {
    await fetch(`${BACKEND_URL}/ble/disconnect`, { method: "POST" }).catch(() => {});
  }

  async getStatus(): Promise<StatusResponse> {
    const res = await fetch(`${BACKEND_URL}/status`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Failed to get status");
    }
    return res.json();
  }

  async startKTW(): Promise<{ status: string; mode: string }> {
    const res = await fetch(`${BACKEND_URL}/ktw/start`, { method: "POST" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Failed to start KTW session");
    }
    return res.json();
  }

  async stopKTW(): Promise<KTWStopResponse> {
    const res = await fetch(`${BACKEND_URL}/ktw/stop`, { method: "POST" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Failed to stop KTW session");
    }
    return res.json();
  }

  async saveKTW(
    angleDeg: number,
    details?: Record<string, any>,
    name?: string,
  ): Promise<{ status: string; id: number }> {
    const res = await fetch(`${BACKEND_URL}/ktw/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ angle_deg: angleDeg, details: details ?? null, name: name ?? "Anonymous" }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Failed to save KTW measurement");
    }
    return res.json();
  }

  async getKTWHistory(): Promise<KTWMeasurement[]> {
    const res = await fetch(`${BACKEND_URL}/ktw/history`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Failed to get KTW history");
    }
    return res.json();
  }

  async getKTWByDate(date: string): Promise<KTWMeasurement[]> {
    const res = await fetch(`${BACKEND_URL}/ktw/by-date/${date}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Failed to get KTW measurements for date");
    }
    return res.json();
  }

  async getSessionDates(): Promise<string[]> {
    const res = await fetch(`${BACKEND_URL}/sessions/dates`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Failed to get session dates");
    }
    return res.json();
  }

  async getSessionsByDate(date: string): Promise<SessionByDate[]> {
    const res = await fetch(`${BACKEND_URL}/sessions/by-date/${date}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Failed to get sessions for date");
    }
    return res.json();
  }
}

export default new BackendService();
