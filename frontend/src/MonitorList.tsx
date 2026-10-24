import {
  Loader2,
  Radio,
  Plus,
  Activity as ActivityIcon,
  ChevronRight,
} from "lucide-react";
import type { Monitor, History } from "./api";
import { health, date } from "./format";
import { Badge } from "./ui";

export default function MonitorList({
  monitors,
  histories,
  windowHours,
  loading,
  selected,
  setSelected,
  onCreate,
}: {
  monitors: Monitor[];
  histories: Record<number, History>;
  windowHours: number;
  loading: boolean;
  selected: number | null;
  setSelected: (id: number) => void;
  onCreate: () => void;
}) {
  return (
    <section className="panel monitor-list" aria-label="Monitor list">
      <div className="monitor-table-heading">
        <span>ENDPOINT</span>
        <span>STATUS</span>
        <span>UPTIME · {windowHours}H</span>
        <span>RECENT CHECKS</span>
        <span>LATENCY</span>
      </div>
      {!monitors.length && (
        <div className="empty">
          {loading ? <Loader2 className="spin" /> : <Radio size={30} />}
          <h3>
            {loading ? "Loading monitors…" : "Start with your first endpoint"}
          </h3>
          <p>
            {loading
              ? "Fetching the latest check results."
              : "Add a public health endpoint or use the controllable demo API."}
          </p>
          {!loading && (
            <button onClick={onCreate}>
              <Plus size={15} />
              Add monitor
            </button>
          )}
        </div>
      )}
      {monitors.map((row) => {
        const detail = histories[row.id];
        const state = health(row, detail);
        return (
          <button
            key={row.id}
            className={`monitor-row ${row.id === selected ? "selected" : ""}`}
            onClick={() => setSelected(row.id)}
            aria-pressed={row.id === selected}
          >
            <span className="endpoint-cell">
              <span className={`endpoint-icon ${state.toLowerCase()}`}>
                <ActivityIcon size={17} />
              </span>
              <span>
                <strong>{row.name}</strong>
                <small>{row.url}</small>
              </span>
            </span>
            <span>
              <Badge state={state} />
            </span>
            <span className="uptime-cell">
              {detail?.uptime_percent == null
                ? "—"
                : `${detail.uptime_percent.toFixed(2)}%`}
            </span>
            <span
              className="mini-bars"
              aria-label="Recent checks, oldest to newest"
            >
              {detail?.checks
                .slice(0, 28)
                .reverse()
                .map((check) => (
                  <i
                    key={check.id}
                    className={check.success ? "pass" : "fail"}
                    title={`${date(check.checked_at)}: ${check.success ? "success" : check.error}`}
                  />
                ))}
              {!detail?.checks.length && <small>No checks yet</small>}
            </span>
            <span className="latency-cell">
              {detail?.checks[0] ? `${detail.checks[0].response_ms} ms` : "—"}
              <ChevronRight size={15} />
            </span>
          </button>
        );
      })}
      <div className="panel-footer">
        <span className="status-dot" />
        Checks run on each monitor’s configured interval
        <span>Refreshes every 10 seconds</span>
      </div>
    </section>
  );
}
