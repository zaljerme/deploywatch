import { Pencil, Play, Pause, Trash2, Clock3 } from "lucide-react";
import type { Monitor, History, Activity } from "./api";
import { health } from "./format";
import { Badge } from "./ui";
import ResponseChart from "./ResponseChart";
import ActivityPanel from "./ActivityPanel";
import IncidentTimeline from "./IncidentTimeline";
import RecentChecks from "./RecentChecks";
export default function MonitorDetails({
  monitor,
  history,
  windowHours,
  busy,
  activity,
  activityError,
  onWindowChange,
  onEdit,
  onPause,
  onDelete,
}: {
  monitor: Monitor;
  history: History;
  windowHours: number;
  busy: boolean;
  activity: Activity | null;
  activityError: string;
  onWindowChange: (hours: number) => void;
  onEdit: () => void;
  onPause: () => void;
  onDelete: () => void;
}) {
  return (
    <>
      <div className="section-heading detail-heading">
        <div>
          <div className="section-title">
            <h2>{monitor.name}</h2>
            <Badge state={health(monitor, history)} />
          </div>
          <p className="muted small">
            Every {monitor.interval_seconds}s · {monitor.timeout_seconds}s
            timeout · expects HTTP {monitor.expected_status}
          </p>
        </div>
        <div className="toolbar">
          <select
            aria-label="History window"
            value={windowHours}
            onChange={(event) => onWindowChange(Number(event.target.value))}
          >
            <option value={24}>Last 24 hours</option>
            <option value={168}>Last 7 days</option>
            <option value={720}>Last 30 days</option>
          </select>
          <button
            className="icon-button"
            aria-label="Edit monitor"
            onClick={onEdit}
          >
            <Pencil size={15} />
          </button>
          <button disabled={busy} onClick={() => onPause()}>
            {monitor.paused ? <Play size={14} /> : <Pause size={14} />}
            {monitor.paused ? "Resume" : "Pause"}
          </button>
          <button
            className="icon-button danger"
            aria-label="Delete monitor"
            disabled={busy}
            onClick={() => onDelete()}
          >
            <Trash2 size={15} />
          </button>
        </div>
      </div>
      <div className="detail-grid">
        <section className="panel chart-panel">
          <div className="section-heading">
            <h3>Response time</h3>
            <span className="chart-legend">
              <i />
              Latency in ms
            </span>
          </div>
          <ResponseChart history={history} />
          <div className="chart-footer">
            <span>Most recent {history.checks.length} samples in window</span>
            <strong>{history.sample_count} total checks</strong>
          </div>
        </section>
        <section className="panel uptime-panel">
          <p className="eyebrow">SAMPLE-BASED UPTIME</p>
          <h2>
            {history.uptime_percent == null
              ? "—"
              : `${history.uptime_percent.toFixed(2)}%`}
          </h2>
          <div className="uptime-track">
            <i style={{ width: `${history.uptime_percent ?? 0}%` }} />
          </div>
          <p>Successful checks ÷ all checks.</p>
          <small>
            Paused periods add no samples.
            <br />
            No checks means unknown.
          </small>
          <div className="uptime-bottom">
            <Clock3 size={15} />
            Last {windowHours === 24 ? "24 hours" : `${windowHours / 24} days`}
          </div>
        </section>
      </div>
      <div className="bottom-grid">
        <IncidentTimeline history={history} />
        <ActivityPanel
          activity={activity}
          activityError={activityError}
          onEdit={onEdit}
        />
      </div>
      <RecentChecks history={history} />
    </>
  );
}
