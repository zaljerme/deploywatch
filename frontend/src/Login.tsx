import { useState } from "react";
import { Radio, ArrowUpRight, ShieldCheck } from "lucide-react";
export default function Login({
  onConnect,
}: {
  onConnect: (token: string) => void;
}) {
  const [draftToken, setDraftToken] = useState("");
  return (
    <div className="login">
      <div className="login-card">
        <div className="brand">
          <span className="brand-symbol">
            <Radio size={23} />
          </span>
          DeployWatch
        </div>
        <p className="eyebrow">KNOW WHEN YOUR API NEEDS YOU</p>
        <h1>
          A clearer view of
          <br />
          your API’s health.
        </h1>
        <p className="muted">
          Monitor endpoints, follow incidents, and put recent code changes in
          context.
        </p>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            onConnect(draftToken);
          }}
        >
          <label>
            API access token
            <input
              type="password"
              required
              autoComplete="off"
              value={draftToken}
              onChange={(event) => setDraftToken(event.target.value)}
              placeholder="Enter the token from your .env file"
            />
          </label>
          <button className="primary wide">
            Open dashboard <ArrowUpRight size={16} />
          </button>
        </form>
        <p className="login-note">
          <ShieldCheck size={14} /> Token stays in this tab’s memory.
        </p>
        <details>
          <summary>Local development setup</summary>
          <p>
            Use the API_TOKEN value in your .env file. The example starts with{" "}
            <code>local-development-token-change-me</code>.
          </p>
        </details>
      </div>
      <div className="login-art">
        <Radio size={100} strokeWidth={0.6} />
        <p>
          Small signals.
          <br />
          Useful context.
        </p>
      </div>
    </div>
  );
}
