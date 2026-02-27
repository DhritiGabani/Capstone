import type { SensorReading } from "../ble/types";

const BACKEND_URL = "https://dorsiflexx-api.onrender.com";

export interface SessionStartResponse {
  session_id: string;
  start_time: string;
}

export interface AnalyzeResponse {
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
}

class BackendService {
  async createSession(): Promise<SessionStartResponse> {
    const res = await fetch(`${BACKEND_URL}/session/start`, {
      method: "POST",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Failed to create session");
    }
    return res.json();
  }

  async analyzeSession(
    sessionId: string,
    readings: SensorReading[],
    durationSeconds: number,
  ): Promise<AnalyzeResponse> {
    // Convert readings to compact array-of-arrays format
    // [device_idx, timestamp_us, ax, ay, az, gx, gy, gz]
    const deviceIdx: Record<string, number> = { imu1: 1, imu2: 2 };
    const compactReadings = readings.map((r) => [
      deviceIdx[r.device] ?? 0,
      r.timestamp_us,
      r.ax,
      r.ay,
      r.az,
      r.gx,
      r.gy,
      r.gz,
    ]);

    const res = await fetch(`${BACKEND_URL}/session/${sessionId}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        readings: compactReadings,
        duration_seconds: durationSeconds,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Failed to analyze session");
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

  async getStatus(): Promise<StatusResponse> {
    const res = await fetch(`${BACKEND_URL}/status`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Failed to get status");
    }
    return res.json();
  }
}

export default new BackendService();
