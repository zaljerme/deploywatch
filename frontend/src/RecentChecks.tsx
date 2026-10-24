import type { History } from "./api";
import { date } from "./format";
import { Badge } from "./ui";

export default function RecentChecks({ history }: { history: History }) {
  return (
    <section className="panel checks-panel">
      <div className="panel-heading">
        <h3>Recent checks</h3>
        <span className="muted small">UTC timestamps</span>
      </div>
      <div className="checks-scroll">
        <table>
          <thead>
            <tr>
              <th>Checked at</th>
              <th>Result</th>
              <th>HTTP status</th>
              <th>Response time</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {history.checks.slice(0, 10).map((check) => (
              <tr key={check.id}>
                <td>{date(check.checked_at)}</td>
                <td>
                  <Badge state={check.success ? "Healthy" : "Failed"} />
                </td>
                <td>{check.status_code ?? "—"}</td>
                <td>{check.response_ms} ms</td>
                <td className="muted">
                  {check.error?.replaceAll("_", " ") ?? "Expected response"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!history.checks.length && (
          <p className="activity-message muted">
            Waiting for the worker’s first check.
          </p>
        )}
      </div>
    </section>
  );
}
