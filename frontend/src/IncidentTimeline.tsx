import {
  Clock3,
  CheckCircle2,
  ArrowUpRight,
  ArrowDownLeft,
} from "lucide-react";
import type { History } from "./api";
import { date, duration } from "./format";

export default function IncidentTimeline({ history }: { history: History }) {
  return (
    <section className="panel" id="incidents">
      <div className="panel-heading">
        <div className="section-title">
          <Clock3 size={17} />
          <h3>Incident timeline</h3>
        </div>
        <span className="count-badge">{history.incidents.length}</span>
      </div>
      {!history.incidents.length && (
        <div className="empty compact">
          <CheckCircle2 size={26} />
          <h3>No incidents in this window</h3>
          <p>Three consecutive failed checks open an incident.</p>
        </div>
      )}
      <div className="timeline">
        {history.incidents.map((incident) => (
          <div className="timeline-item" key={incident.id}>
            <span
              className={`timeline-dot ${incident.resolved_at ? "resolved" : ""}`}
            >
              {incident.resolved_at ? (
                <ArrowUpRight size={14} />
              ) : (
                <ArrowDownLeft size={14} />
              )}
            </span>
            <div>
              <div className="timeline-title">
                <strong>
                  {incident.resolved_at ? "Recovered" : "Endpoint unavailable"}
                </strong>
                <span
                  className={`badge ${incident.resolved_at ? "healthy" : "down"}`}
                >
                  {incident.resolved_at ? "Resolved" : "Open"}
                </span>
              </div>
              <p>First failure {date(incident.started_at)}</p>
              <small>
                Detected {date(incident.detected_at)} ·{" "}
                {duration(incident.started_at, incident.resolved_at)} observed
              </small>
              {incident.resolved_at && (
                <small>Recovered {date(incident.resolved_at)}</small>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
