import { Activity as ActivityIcon } from "lucide-react";
import type { History } from "./api";
import { date } from "./format";

export default function ResponseChart({ history }: { history: History }) {
  const checks = [...history.checks].reverse();
  if (!checks.length)
    return (
      <div className="empty chart-empty">
        <ActivityIcon size={25} />
        <p>Response times will appear after the first check.</p>
      </div>
    );
  const max = Math.max(100, ...checks.map((check) => check.response_ms)) * 1.2;
  const firstTime = Date.parse(checks[0].checked_at);
  const span = Math.max(1, Date.parse(checks.at(-1)!.checked_at) - firstTime);
  const points = checks
    .map(
      (check) =>
        `${40 + (checks.length === 1 ? 0.5 : (Date.parse(check.checked_at) - firstTime) / span) * 640},${160 - (check.response_ms / max) * 140}`,
    )
    .join(" ");
  return (
    <>
      <svg
        className="response-chart"
        viewBox="0 0 710 190"
        role="img"
        aria-label={`Response time chart with ${checks.length} samples`}
      >
        <defs>
          <linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6366f1" stopOpacity="0.17" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0, 1, 2, 3].map((index) => (
          <g key={index}>
            <line
              x1="40"
              x2="680"
              y1={20 + index * 47}
              y2={20 + index * 47}
              stroke="#edf0f4"
              strokeDasharray="4 4"
            />
            <text x="0" y={24 + index * 47} fontSize="10" fill="#9299a7">
              {Math.round(max * (1 - index / 3))}
            </text>
          </g>
        ))}
        {checks.length > 1 && (
          <>
            <polygon
              points={`40,162 ${points} 680,162`}
              fill="url(#chart-fill)"
            />
            <polyline
              points={points}
              fill="none"
              stroke="#6366f1"
              strokeWidth="2.2"
              strokeLinejoin="round"
            />
          </>
        )}
        {checks.map((check) => (
          <circle
            key={check.id}
            cx={
              40 +
              (checks.length === 1
                ? 0.5
                : (Date.parse(check.checked_at) - firstTime) / span) *
                640
            }
            cy={160 - (check.response_ms / max) * 140}
            r={checks.length < 50 || !check.success ? 3 : 1.5}
            fill={check.success ? "#6366f1" : "#ef6464"}
          >
            <title>
              {date(check.checked_at)}: {check.response_ms} ms ·{" "}
              {check.error ?? "success"}
            </title>
          </circle>
        ))}
        <text x="40" y="185" fontSize="10" fill="#9299a7">
          {date(checks[0].checked_at)}
        </text>
        <text x="680" textAnchor="end" y="185" fontSize="10" fill="#9299a7">
          {date(checks.at(-1)!.checked_at)}
        </text>
      </svg>
    </>
  );
}
