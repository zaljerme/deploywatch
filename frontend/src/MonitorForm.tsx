import { useEffect, useRef, useState } from "react";
import type { Monitor, MonitorInput } from "./api";
import { X } from "lucide-react";

export default function MonitorForm({
  monitor,
  save,
  close,
}: {
  monitor?: Monitor;
  save: (input: MonitorInput) => Promise<void>;
  close: () => void;
}) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const dialogRef = useRef<HTMLElement>(null);
  const previousFocus = useRef(document.activeElement as HTMLElement | null);
  useEffect(() => {
    return () => previousFocus.current?.focus();
  }, []);
  return (
    <div className="modal-backdrop">
      <section
        ref={dialogRef}
        onKeyDown={(event) => {
          if (event.key === "Escape" && !busy) close();
          if (event.key !== "Tab") return;
          const controls = dialogRef.current?.querySelectorAll<HTMLElement>(
            "button:not([disabled]), input:not([disabled]), select:not([disabled])",
          );
          if (!controls?.length) return;
          const first = controls[0];
          const last = controls[controls.length - 1];
          if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
          } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
          }
        }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="form-title"
        className="modal"
      >
        <div className="section-heading">
          <h2 id="form-title">{monitor ? "Edit monitor" : "New monitor"}</h2>
          <button aria-label="Close" className="icon-button" onClick={close}>
            <X size={20} />
          </button>
        </div>
        <p className="muted">
          Check a public HTTP endpoint, or the local demo service.
        </p>
        <form
          onSubmit={async (event) => {
            event.preventDefault();
            setBusy(true);
            setError("");
            const data = new FormData(event.currentTarget);
            try {
              await save({
                name: String(data.get("name")),
                url: String(data.get("url")),
                interval_seconds: Number(data.get("interval")),
                timeout_seconds: Number(data.get("timeout")),
                expected_status: Number(data.get("expected")),
                paused: monitor?.paused ?? false,
                repository: String(data.get("repository")).trim() || null,
              });
            } catch (err) {
              setError((err as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <label>
            Name
            <input
              autoFocus
              name="name"
              required
              maxLength={100}
              placeholder="Payments API"
              defaultValue={monitor?.name}
            />
          </label>
          <label>
            Endpoint URL
            <input
              name="url"
              required
              type="url"
              maxLength={2048}
              placeholder="https://api.example.com/health"
              defaultValue={monitor?.url}
            />
          </label>
          <div className="form-grid">
            <label>
              Interval (seconds)
              <input
                name="interval"
                type="number"
                min="5"
                max="86400"
                required
                defaultValue={monitor?.interval_seconds ?? 30}
              />
            </label>
            <label>
              Timeout (seconds)
              <input
                name="timeout"
                type="number"
                min="1"
                max="30"
                required
                defaultValue={monitor?.timeout_seconds ?? 5}
              />
            </label>
            <label>
              Expected status
              <input
                name="expected"
                type="number"
                min="100"
                max="599"
                required
                defaultValue={monitor?.expected_status ?? 200}
              />
            </label>
          </div>
          <label>
            GitHub repository <span className="muted">(optional)</span>
            <input
              name="repository"
              placeholder="owner/repository"
              defaultValue={monitor?.repository ?? ""}
            />
          </label>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <div className="modal-actions">
            <button type="button" onClick={close}>
              Cancel
            </button>
            <button className="primary" disabled={busy}>
              {busy ? "Saving…" : "Save monitor"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
