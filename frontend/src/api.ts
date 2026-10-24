export interface Monitor {
  id: number;
  name: string;
  url: string;
  interval_seconds: number;
  timeout_seconds: number;
  expected_status: number;
  paused: boolean;
  repository: string | null;
  failure_count: number;
  next_check_at: string;
}
export type MonitorInput = Omit<
  Monitor,
  "id" | "failure_count" | "next_check_at"
>;
export interface Check {
  id: number;
  checked_at: string;
  success: boolean;
  status_code: number | null;
  response_ms: number;
  error: string | null;
}
export interface Incident {
  id: number;
  started_at: string;
  detected_at: string;
  resolved_at: string | null;
}
export interface History {
  checks: Check[];
  incidents: Incident[];
  sample_count: number;
  uptime_percent: number | null;
  next_before_id: number | null;
}
export interface ActivityItem {
  kind: "commit" | "deployment";
  sha: string;
  title: string;
  timestamp: string;
  url: string;
}
export interface ActivityStream {
  status: string;
  items: ActivityItem[];
  stale?: boolean;
  truncated?: boolean;
}
export interface Activity {
  repository: string | null;
  notice: string;
  commits?: ActivityStream;
  deployments?: ActivityStream;
}

export async function request<T>(
  path: string,
  token: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    signal: init.signal
      ? AbortSignal.any([init.signal, AbortSignal.timeout(15000)])
      : AbortSignal.timeout(15000),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const details = body?.error?.details
      ?.map(
        (d: { field: string; message: string }) => `${d.field}: ${d.message}`,
      )
      .join("; ");
    throw new Error(
      details || body?.error?.message || `Request failed (${response.status})`,
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
