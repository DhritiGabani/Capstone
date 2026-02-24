const BACKEND_URL = "http://localhost:8000";

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
  raw_data: {
    imu1_data: Record<string, any>;
    imu2_data: Record<string, any>;
  };
}

export interface StatusResponse {
  status: string;
  is_streaming: boolean;
  session_id: string | null;
  stats: Record<string, any> | null;
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
