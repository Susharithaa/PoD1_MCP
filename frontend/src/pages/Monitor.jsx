import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { monitorApi } from "../lib/api";
import { useLanguage } from "../context/LanguageContext";

const REFRESH_MS = 5000;

export default function Monitor() {
  const { t } = useLanguage();
  const [overview, setOverview] = useState(null);
  const [active, setActive] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [toolCalls, setToolCalls] = useState([]);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [ov, ac, se, tc] = await Promise.all([
        monitorApi.overview(),
        monitorApi.active(),
        monitorApi.sessions(30),
        monitorApi.toolCalls(30),
      ]);
      setOverview(ov); setActive(ac); setSessions(se); setToolCalls(tc);
      setLastRefresh(new Date());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(interval);
  }, [refresh]);

  return (
    <div className="max-w-6xl mx-auto animate-slide-up space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Monitor</p>
          <h1 className="h-page mt-2">{t("System Monitor")}</h1>
          <p className="lead mt-2">{t("Real-time view of sessions, pipelines, and tool calls")}</p>
        </div>
        <div className="text-xs text-[var(--muted)]">
          {lastRefresh && <span className="pill">{t("Updated")} {lastRefresh.toLocaleTimeString()}</span>}
        </div>
      </div>

      {overview && (
        <div className="grid gap-3 md:grid-cols-5">
          <Metric label={t("Total Sessions")} value={overview.total_sessions} />
          <Metric label={t("Active Now")} value={overview.active_sessions} />
          <Metric label={t("Pending Review")} value={overview.pending_sessions} />
          <Metric label={t("APIs Registered")} value={overview.total_apis} />
          <Metric label={t("Tool Calls")} value={overview.total_tool_calls} />
        </div>
      )}

      {overview && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="eyebrow">Pipeline Health</p>
            <span className="text-sm font-semibold">{overview.success_rate}%</span>
          </div>
          <div className="h-2 rounded-full bg-[var(--panel)] overflow-hidden flex">
            <div className="bg-[var(--ok)]" style={{ width: `${overview.saved_sessions / Math.max(1, overview.saved_sessions + overview.failed_sessions + overview.pending_sessions) * 100}%` }} />
            <div className="bg-[var(--warn)]" style={{ width: `${overview.pending_sessions / Math.max(1, overview.saved_sessions + overview.failed_sessions + overview.pending_sessions) * 100}%` }} />
            <div className="bg-[var(--err)]" style={{ width: `${overview.failed_sessions / Math.max(1, overview.saved_sessions + overview.failed_sessions + overview.pending_sessions) * 100}%` }} />
          </div>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title={t("Active Now")} count={active.length} loading={loading}>
          {active.map(s => (
            <div key={s.id} className="flex items-center justify-between gap-3 py-2">
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{s.api_name}</p>
                <p className="text-xs text-[var(--muted)] font-mono">{s.state}</p>
              </div>
              <span className="text-xs text-[var(--muted)]">{s.elapsed_seconds}s</span>
            </div>
          ))}
        </Panel>

        <Panel title={t("Tool Call Log")} count={toolCalls.length} loading={loading}>
          {toolCalls.map(c => (
            <div key={c.id} className="flex items-start justify-between gap-3 py-2">
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{c.api_name}</p>
                <p className="text-xs text-[var(--muted)] font-mono truncate">{c.endpoint_name}</p>
              </div>
              <span className="text-[10px] text-[var(--muted-2)] whitespace-nowrap">{new Date(c.called_at).toLocaleTimeString()}</span>
            </div>
          ))}
        </Panel>
      </div>

      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--line)] flex items-center justify-between">
          <p className="eyebrow">Session History</p>
          <Link to="/registry" className="text-xs text-[var(--muted)] hover:text-[var(--ink)]">{t("View Registry →")}</Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[var(--line)] bg-[var(--panel)]">
                {["Session ID", "Mode", "State", "API Name", "Duration", "Created"].map(h => (
                  <th key={h} className="px-4 py-2.5 text-left font-semibold text-[10px] uppercase tracking-[0.18em] text-[var(--muted-2)] whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--line)]">
              {sessions.map(s => (
                <tr key={s.id} className="hover:bg-[var(--hover)]">
                  <td className="px-4 py-3 font-mono text-[var(--muted)]">{s.id.slice(0, 8)}…</td>
                  <td className="px-4 py-3">{s.mode}</td>
                  <td className="px-4 py-3">{s.state}</td>
                  <td className="px-4 py-3 font-medium max-w-[180px] truncate">{s.api_name}</td>
                  <td className="px-4 py-3">{fmtDuration(s.duration_ms)}</td>
                  <td className="px-4 py-3 text-[var(--muted)] whitespace-nowrap">{timeAgo(s.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Panel({ title, count, loading, children }) {
  return (
    <div className="card flex flex-col">
      <div className="px-5 py-4 border-b border-[var(--line)] flex items-center justify-between">
        <p className="eyebrow">{title}</p>
        <span className="pill">{count}</span>
      </div>
      <div className="px-5 py-3 min-h-[220px]">
        {loading && count === 0 ? <div className="text-sm text-[var(--muted)]">Loading…</div> : children}
      </div>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="card p-4">
      <p className="text-[10px] uppercase tracking-[0.18em] text-[var(--muted-2)]">{label}</p>
      <p className="mt-2 text-2xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}

function timeAgo(iso) {
  const secs = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (secs < 60) return `${secs}s ago`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  return `${Math.floor(secs / 3600)}h ago`;
}

function fmtDuration(ms) {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
}
