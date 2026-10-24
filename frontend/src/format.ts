import type { History, Monitor } from "./api";

export function health(monitor: Monitor, history?: History): string {
  if (monitor.paused) return "Paused";
  const latest = history?.checks[0];
  if (!latest) return "Pending";
  const age = Date.now() - Date.parse(latest.checked_at);
  if (age > (monitor.interval_seconds + monitor.timeout_seconds + 15) * 2000)
    return "Stale";
  if (history?.incidents.some((incident) => !incident.resolved_at))
    return "Down";
  return latest.success ? "Healthy" : "Degraded";
}

export function date(value: string) {
  return (
    new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      timeZone: "UTC",
    }).format(new Date(value)) + " UTC"
  );
}

export function duration(start: string, end: string | null) {
  const seconds = Math.max(
    0,
    Math.round(
      ((end ? Date.parse(end) : Date.now()) - Date.parse(start)) / 1000,
    ),
  );
  return seconds < 60
    ? `${seconds}s`
    : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}
