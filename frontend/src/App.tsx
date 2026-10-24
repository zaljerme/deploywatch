import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity as ActivityIcon,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Github,
  LayoutDashboard,
  LogOut,
  Plus,
  Radio,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import {
  request,
  type Activity,
  type History,
  type Monitor,
  type MonitorInput,
} from "./api";
import { health } from "./format";
import MonitorForm from "./MonitorForm";
import MonitorList from "./MonitorList";
import MonitorDetails from "./MonitorDetails";
import Login from "./Login";
import { Summary } from "./ui";

export default function App() {
  const [token, setToken] = useState("");
  const [monitors, setMonitors] = useState<Monitor[]>([]);
  const [histories, setHistories] = useState<Record<number, History>>({});
  const [selected, setSelected] = useState<number | null>(null);
  const [activity, setActivity] = useState<Activity | null>(null);
  const [activityError, setActivityError] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [updated, setUpdated] = useState("");
  const [form, setForm] = useState<Monitor | "new" | null>(null);
  const [busy, setBusy] = useState(false);
  const [windowHours, setWindowHours] = useState(24);
  const refreshId = useRef(0);

  const refresh = useCallback(
    async (signal?: AbortSignal) => {
      if (!token) return;
      const id = ++refreshId.current;
      setLoading(true);
      try {
        const rows = await request<Monitor[]>("/monitors", token, { signal });
        const details = await Promise.all(
          rows.map(
            async (monitor) =>
              [
                monitor.id,
                await request<History>(
                  `/monitors/${monitor.id}/history?hours=${windowHours}`,
                  token,
                  { signal },
                ),
              ] as const,
          ),
        );
        if (id !== refreshId.current || signal?.aborted) return;
        setMonitors(rows);
        setHistories(Object.fromEntries(details));
        setSelected((current) =>
          rows.some((row) => row.id === current)
            ? current
            : (rows[0]?.id ?? null),
        );
        setError("");
        setUpdated(new Date().toLocaleTimeString());
      } catch (err) {
        if (id === refreshId.current && !signal?.aborted)
          setError((err as Error).message);
      } finally {
        if (id === refreshId.current) setLoading(false);
      }
    },
    [token, windowHours],
  );

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      await refresh(controller.signal);
      if (!controller.signal.aborted) timer = setTimeout(poll, 10000);
    };
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
      refreshId.current++;
    };
  }, [refresh]);

  const monitor = monitors.find((row) => row.id === selected);
  const history = selected ? histories[selected] : undefined;
  useEffect(() => {
    setActivity(null);
    setActivityError("");
    if (!selected || !token) return;
    const controller = new AbortController();
    request<Activity>(`/monitors/${selected}/activity`, token, {
      signal: controller.signal,
    })
      .then(setActivity)
      .catch((err) => {
        if (!controller.signal.aborted) setActivityError(err.message);
      });
    return () => controller.abort();
  }, [selected, token, monitor?.repository, updated]);

  async function save(input: MonitorInput) {
    await request(
      `/monitors${form && form !== "new" ? `/${form.id}` : ""}`,
      token,
      {
        method: form === "new" ? "POST" : "PUT",
        body: JSON.stringify(input),
      },
    );
    setForm(null);
    await refresh();
  }

  async function mutate(action: "pause" | "delete") {
    if (!monitor) return;
    if (
      action === "delete" &&
      !window.confirm(
        `Delete ${monitor.name} and all its check and incident history?`,
      )
    )
      return;
    setBusy(true);
    try {
      if (action === "delete")
        await request(`/monitors/${monitor.id}`, token, { method: "DELETE" });
      else
        await request(`/monitors/${monitor.id}`, token, {
          method: "PUT",
          body: JSON.stringify({
            name: monitor.name,
            url: monitor.url,
            interval_seconds: monitor.interval_seconds,
            timeout_seconds: monitor.timeout_seconds,
            expected_status: monitor.expected_status,
            paused: !monitor.paused,
            repository: monitor.repository,
          }),
        });
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const active = monitors.filter((row) => !row.paused).length;
  const openIncidents = Object.values(histories).reduce(
    (sum, value) =>
      sum + value.incidents.filter((incident) => !incident.resolved_at).length,
    0,
  );
  const healthy = monitors.filter(
    (row) => health(row, histories[row.id]) === "Healthy",
  ).length;

  if (!token) return <Login onConnect={setToken} />;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-symbol">
            <Radio size={22} />
          </span>
          DeployWatch<span className="beta">BETA</span>
        </div>
        <div className="workspace">
          <span className="workspace-avatar">DW</span>
          <div>
            Local workspace<small>Development</small>
          </div>
          <ChevronRight size={15} />
        </div>
        <p className="nav-label">WORKSPACE</p>
        <a className="nav-item active" href="#overview">
          <LayoutDashboard size={17} />
          Overview
        </a>
        <a className="nav-item" href="#monitors">
          <Radio size={17} />
          Monitors<span className="nav-count">{monitors.length}</span>
        </a>
        <a className="nav-item" href="#incidents">
          <Clock3 size={17} />
          Incidents
          {openIncidents > 0 && (
            <span className="nav-count alert-count">{openIncidents}</span>
          )}
        </a>
        <a className="nav-item" href="#activity">
          <Github size={17} />
          Repository activity
        </a>
        <div className="sidebar-bottom">
          <div className="local-note">
            <span className="status-dot" />
            Local environment
            <p>
              Checks run independently
              <br />
              of this dashboard.
            </p>
          </div>
          <button
            className="logout"
            onClick={() => {
              setToken("");
              setMonitors([]);
              setHistories({});
              setSelected(null);
              setUpdated("");
              setError("");
            }}
          >
            <LogOut size={16} />
            Disconnect
          </button>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div>
            Workspace <ChevronRight size={13} />
            <span>Overview</span>
          </div>
          <span className="topbar-note">
            <ShieldCheck size={14} />
            Authenticated session
          </span>
        </header>
        <main id="overview">
          <div className="page-heading">
            <div>
              <p className="eyebrow">API OBSERVABILITY</p>
              <h1>
                Overview
                <span className="live-label">
                  <span className="status-dot" />
                  Live
                </span>
              </h1>
              <p className="muted">
                Your endpoints, their health, and what changed.
              </p>
            </div>
            <button className="primary" onClick={() => setForm("new")}>
              <Plus size={16} />
              New monitor
            </button>
          </div>
          {error && (
            <div className="error-banner" role="alert">
              {error}
              <button onClick={() => void refresh()}>Try again</button>
            </div>
          )}
          <div className="summary-grid">
            <Summary
              label="Active monitors"
              value={String(active)}
              detail={`${monitors.filter((row) => row.paused).length} paused`}
              icon={<Radio size={18} />}
            />
            <Summary
              label="Healthy endpoints"
              value={String(healthy)}
              detail={
                active
                  ? `${active - healthy} awaiting attention or checks`
                  : "Add a monitor to begin"
              }
              icon={<CheckCircle2 size={18} />}
            />
            <Summary
              label="Open incidents"
              value={String(openIncidents)}
              detail={
                openIncidents
                  ? "Investigate affected endpoints"
                  : "No open incidents recorded"
              }
              icon={<ActivityIcon size={18} />}
            />
          </div>
          <div className="section-heading" id="monitors">
            <div className="section-title">
              <h2>Monitors</h2>
              <span className="count-badge">{monitors.length}</span>
            </div>
            <div className="toolbar">
              <span className="refresh-label">
                {loading
                  ? "Refreshing…"
                  : updated
                    ? `Updated ${updated}`
                    : "Waiting for data"}
              </span>
              <button
                className="icon-button"
                aria-label="Refresh monitors"
                disabled={loading}
                onClick={() => void refresh()}
              >
                <RefreshCw size={15} className={loading ? "spin" : ""} />
              </button>
            </div>
          </div>
          <MonitorList
            monitors={monitors}
            histories={histories}
            windowHours={windowHours}
            loading={loading}
            selected={selected}
            setSelected={setSelected}
            onCreate={() => setForm("new")}
          />
          {monitor && history && (
            <MonitorDetails
              monitor={monitor}
              history={history}
              windowHours={windowHours}
              busy={busy}
              activity={activity}
              activityError={activityError}
              onWindowChange={setWindowHours}
              onEdit={() => setForm(monitor)}
              onPause={() => void mutate("pause")}
              onDelete={() => void mutate("delete")}
            />
          )}
          <footer className="page-footer">
            <span>
              <Radio size={13} />
              DeployWatch
            </span>
            <span>Observed health. Useful context.</span>
          </footer>
        </main>
      </div>
      {form && (
        <MonitorForm
          monitor={form === "new" ? undefined : form}
          save={save}
          close={() => setForm(null)}
        />
      )}
    </div>
  );
}
