import {
  Github,
  ShieldCheck,
  GitCommitHorizontal,
  Rocket,
  ExternalLink,
} from "lucide-react";
import type { Activity } from "./api";
import { date } from "./format";

export default function ActivityPanel({
  activity,
  activityError,
  onEdit,
}: {
  activity: Activity | null;
  activityError: string;
  onEdit: () => void;
}) {
  return (
    <section className="panel" id="activity">
      <div className="panel-heading">
        <div className="section-title">
          <Github size={17} />
          <h3>Recent changes</h3>
        </div>
        {activity?.repository && (
          <a
            className="repository-link"
            href={`https://github.com/${activity.repository}`}
            target="_blank"
            rel="noreferrer"
          >
            {activity.repository}
            <ExternalLink size={12} />
          </a>
        )}
      </div>
      <div className="context-note">
        <ShieldCheck size={15} />
        <span>Investigation clues, not proof of cause.</span>
      </div>
      {activityError ? (
        <p className="error activity-message">
          GitHub data unavailable: {activityError}
        </p>
      ) : !activity ? (
        <p className="activity-message muted">Loading repository activity…</p>
      ) : !activity.repository ? (
        <div className="empty compact">
          <GitCommitHorizontal size={26} />
          <h3>Add repository context</h3>
          <p>Connect owner/repository in monitor settings.</p>
          <button onClick={onEdit}>Edit monitor</button>
        </div>
      ) : (
        <>
          {(["deployments", "commits"] as const).map((kind) => {
            const stream = activity[kind];
            return (
              <div className="activity-group" key={kind}>
                <p className="activity-label">
                  {kind === "commits" ? "COMMITS" : "DEPLOYMENT RECORDS"}
                  {stream?.stale && " · CACHED"}
                </p>
                {stream?.status !== "available" && (
                  <p className="activity-message muted">
                    {stream?.status === "rate_limited"
                      ? "GitHub rate limit reached. Retry after the cache cooldown."
                      : "GitHub data is temporarily unavailable."}
                  </p>
                )}
                {stream?.items.slice(0, 5).map((item, index) => (
                  <a
                    className="activity-item"
                    href={item.url}
                    key={`${item.sha}-${index}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {kind === "commits" ? (
                      <GitCommitHorizontal size={18} />
                    ) : (
                      <Rocket size={18} />
                    )}
                    <span>
                      <strong>{item.title}</strong>
                      <small>
                        {date(item.timestamp)} · {item.sha.slice(0, 7)}
                      </small>
                    </span>
                    <ExternalLink size={12} />
                  </a>
                ))}
                {stream?.status === "available" && !stream.items.length && (
                  <p className="activity-message muted">
                    No {kind === "commits" ? "commits" : "deployment records"}{" "}
                    found.
                  </p>
                )}
                {stream?.truncated && (
                  <small>Showing a bounded recent history.</small>
                )}
              </div>
            );
          })}
          <p className="activity-footnote">
            A commit is a code change. A deployment record is a request to
            deploy; completion is unverified.
          </p>
        </>
      )}
    </section>
  );
}
