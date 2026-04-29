import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { monitorApi } from "../lib/api";
import { useLanguage } from "../context/LanguageContext";

const REFRESH_MS = 5000;

const STATE_COLOR = {
  SAVED:             "text-emerald-400",
  FAILED:            "text-red-400",
  HITL_PENDING:      "text-amber-400",
  CLASSIFYING:       "text-blue-400",
  PARSING:           "text-blue-400",
  SCHEMA_GENERATING: "text-blue-400",
  CONFIDENCE_SCORING:"text-blue-400",
  VALIDATING:        "text-blue-400",
  API_TESTING:       "text-blue-400",
  SAVING:            "text-blue-400",
};

const STATE_DOT = {
  SAVED:        "bg-emerald-400",
  FAILED:       "bg-red-400",
  HITL_PENDING: "bg-amber-400",
};

const ACTIVE_STATES = new Set([
  "CLASSIFYING","PARSING","SCHEMA_GENERATING","CONFIDENCE_SCORING",
  "VALIDATING","API_TESTING","SAVING",
]);

const VERDICT_STYLE = {
  PASS:          { dot: "bg-emerald-400", label: "Pass",          text: "text-emerald-400" },
  AUTH_REQUIRED: { dot: "bg-amber-400",   label: "Auth required", text: "text-amber-400"  },
  WARNING:       { dot: "bg-orange-400",  label: "Warning",       text: "text-orange-400" },
  UNREACHABLE:   { dot: "bg-red-400",     label: "Unreachable",   text: "text-red-400"    },
  SKIPPED:       { dot: "bg-zinc-600",    label: "Skipped",       text: "text-zinc-500"   },
  NONE:          { dot: "bg-zinc-700",    label: "—",             text: "text-zinc-600"   },
  UNKNOWN:       { dot: "bg-zinc-600",    label: "Unknown",       text: "text-zinc-500"   },
};

function timeAgo(iso) {
  const secs = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (secs < 60)   return `${secs}s ago`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  return `${Math.floor(secs / 3600)}h ago`;
}

function fmtDuration(ms) {
  if (ms < 1000)  return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
}

export default function Monitor() {
  const { t } = useLanguage();
  const [overview,    setOverview]    = useState(null);
  const [active,      setActive]      = useState([]);
  const [sessions,    setSessions]    = useState([]);
  const [toolCalls,   setToolCalls]   = useState([]);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [loading,     setLoading]     = useState(true);

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
    <div className="max-w-5xl mx-auto animate-slide-up space-y-6">
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">{t("System Monitor")}</h1>
          <p className="page-subtitle">{t("Real-time view of sessions, pipelines, and tool calls")}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-xs text-zinc-500">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse-dot" />
            {t("Live · refreshes every 5s")}
          </span>
          {lastRefresh && (
            <span className="text-xs text-zinc-700 border border-zinc-800 rounded px-2 py-1">
              {t("Updated")} {lastRefresh.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {/* ── Stat cards ── */}
      {overview && (
        <div className="grid grid-cols-5 gap-3">
          <StatCard label={t("Total Sessions")}  value={overview.total_sessions}  color="zinc"    icon={<SessionIcon />} />
          <StatCard label={t("Active Now")}       value={overview.active_sessions} color="blue"    icon={<PulseIcon />}   pulse={overview.active_sessions > 0} />
          <StatCard label={t("Pending Review")}   value={overview.pending_sessions}color="amber"   icon={<ClockIcon />} />
          <StatCard label={t("APIs Registered")}  value={overview.total_apis}      color="emerald" icon={<LayersIcon />} />
          <StatCard label={t("Tool Calls")}        value={overview.total_tool_calls}color="violet"  icon={<BoltIcon />} />
        </div>
      )}

      {/* ── Pipeline health ── */}
      {overview && <PipelineBar overview={overview} t={t} />}

      {/* ── Active + Tool call log ── */}
      <div className="grid grid-cols-2 gap-4">
        <ActivePanel sessions={active} loading={loading} t={t} />
        <ToolCallPanel calls={toolCalls} loading={loading} t={t} />
      </div>

      {/* ── Session history ── */}
      <SessionTable sessions={sessions} loading={loading} t={t} />
    </div>
  );
}

function PipelineBar({ overview, t }) {
  const { saved_sessions, failed_sessions, pending_sessions, success_rate } = overview;
  const total = saved_sessions + failed_sessions + pending_sessions;
  if (total === 0) return null;

  const pctSaved   = Math.round((saved_sessions   / total) * 100);
  const pctFailed  = Math.round((failed_sessions  / total) * 100);
  const pctPending = 100 - pctSaved - pctFailed;

  return (
    <div className="card px-5 py-4">
      <div className="flex items-center justify-between mb-3">
        <p className="section-label">{t("Pipeline Health")}</p>
        <span className={`text-sm font-bold ${success_rate >= 80 ? "text-emerald-400" : success_rate >= 50 ? "text-amber-400" : "text-red-400"}`}>
          {success_rate}{t("% success")}
        </span>
      </div>
      <div className="h-2.5 rounded-full bg-zinc-800 flex overflow-hidden gap-px">
        {pctSaved   > 0 && <div className="bg-emerald-500 h-full transition-all rounded-l-full" style={{ width: `${pctSaved}%` }} />}
        {pctPending > 0 && <div className="bg-amber-500/70 h-full transition-all" style={{ width: `${pctPending}%` }} />}
        {pctFailed  > 0 && <div className="bg-red-500 h-full transition-all rounded-r-full"   style={{ width: `${pctFailed}%` }} />}
      </div>
      <div className="flex items-center gap-5 mt-2.5">
        {[
          { color: "bg-emerald-500", label: `${saved_sessions}${t(" saved")}` },
          { color: "bg-amber-500/70",label: `${pending_sessions}${t(" pending")}` },
          { color: "bg-red-500",     label: `${failed_sessions}${t(" failed")}` },
        ].map(({ color, label }) => (
          <span key={label} className="flex items-center gap-1.5 text-xs text-zinc-500">
            <span className={`w-2 h-2 rounded-full ${color}`} />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}

function ActivePanel({ sessions, loading, t }) {
  return (
    <div className="card flex flex-col" style={{ minHeight: 220 }}>
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
        <p className="section-title">{t("Active Now")}</p>
        {sessions.length > 0 && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 font-medium">
            {sessions.length}{t(" running")}
          </span>
        )}
      </div>
      <div className="flex-1 px-4 py-3 space-y-2 overflow-y-auto">
        {loading && sessions.length === 0 ? (
          <Skeleton rows={3} />
        ) : sessions.length === 0 ? (
          <EmptyMsg text={t("No sessions running right now")} />
        ) : (
          sessions.map(s => (
            <div key={s.id} className="flex items-center gap-3 py-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse-dot flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-zinc-200 truncate">{s.api_name}</span>
                  <span className="text-[10px] font-mono text-zinc-600 flex-shrink-0">{s.mode}</span>
                </div>
                <p className={`text-xs font-mono ${STATE_COLOR[s.state] || "text-zinc-400"}`}>{s.state}</p>
              </div>
              <span className="text-xs text-zinc-600 flex-shrink-0">{s.elapsed_seconds}s</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function ToolCallPanel({ calls, loading, t }) {
  return (
    <div className="card flex flex-col" style={{ minHeight: 220 }}>
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
        <p className="section-title">{t("Tool Call Log")}</p>
        {calls.length > 0 && (
          <span className="text-xs text-zinc-600">{calls.length}{t(" recent")}</span>
        )}
      </div>
      <div className="flex-1 px-4 py-3 space-y-2 overflow-y-auto">
        {loading && calls.length === 0 ? (
          <Skeleton rows={4} />
        ) : calls.length === 0 ? (
          <EmptyMsg text={t("No tool calls yet — connect an API and chat")} />
        ) : (
          calls.map(c => (
            <div key={c.id} className="flex items-start gap-2.5 py-1">
              <span className={`mt-1 w-1.5 h-1.5 rounded-full flex-shrink-0 ${c.success ? "bg-emerald-400" : "bg-red-400"}`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-medium text-zinc-200 truncate">{c.api_name}</span>
                  <span className="text-zinc-700 text-xs">›</span>
                  <span className="text-xs font-mono text-zinc-500 truncate">{c.endpoint_name}</span>
                </div>
                <p className="text-[10px] text-zinc-700 font-mono truncate">{c.result_preview}</p>
              </div>
              <span className="text-[10px] text-zinc-700 flex-shrink-0 whitespace-nowrap">
                {timeAgo(c.called_at)}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function SessionTable({ sessions, loading, t }) {
  return (
    <div className="card">
      <div className="px-5 py-3.5 border-b border-zinc-800 flex items-center justify-between">
        <p className="section-title">{t("Session History")}</p>
        <Link to="/registry" className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors">
          {t("View Registry →")}
        </Link>
      </div>

      {loading && sessions.length === 0 ? (
        <div className="px-5 py-4"><Skeleton rows={5} /></div>
      ) : sessions.length === 0 ? (
        <div className="px-5 py-12 text-center">
          <EmptyMsg text={t("No sessions yet — create your first API")} />
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-900/50">
                {[t("Session ID"), t("Mode"), t("State"), t("API Name"), t("API Test"), t("Duration"), t("Created"), ""].map(h => (
                  <th key={h} className="px-4 py-2.5 text-left font-semibold text-zinc-600 uppercase tracking-wider whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {sessions.map(s => {
                const isActive = ACTIVE_STATES.has(s.state);
                const verdict  = VERDICT_STYLE[s.test_verdict] || VERDICT_STYLE.NONE;
                return (
                  <tr key={s.id} className="hover:bg-zinc-800/30 transition-colors group">
                    <td className="px-4 py-3 font-mono text-zinc-600">{s.id.slice(0, 8)}…</td>
                    <td className="px-4 py-3">
                      <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 font-mono text-[11px]">{s.mode}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-1.5">
                        {isActive
                          ? <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse-dot" />
                          : <span className={`w-1.5 h-1.5 rounded-full ${STATE_DOT[s.state] || "bg-zinc-700"}`} />
                        }
                        <span className={`font-mono ${STATE_COLOR[s.state] || "text-zinc-400"}`}>{s.state}</span>
                      </span>
                    </td>
                    <td className="px-4 py-3 text-zinc-200 font-medium max-w-[180px] truncate">{s.api_name}</td>
                    <td className="px-4 py-3">
                      <span className={`flex items-center gap-1.5 ${verdict.text}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${verdict.dot}`} />
                        {verdict.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-zinc-500">{fmtDuration(s.duration_ms)}</td>
                    <td className="px-4 py-3 text-zinc-600 whitespace-nowrap">{timeAgo(s.created_at)}</td>
                    <td className="px-4 py-3">
                      {s.state === "SAVED" && (
                        <Link to="/registry"
                          className="opacity-0 group-hover:opacity-100 text-zinc-500 hover:text-zinc-300 transition-all text-xs">
                          {t("View →")}
                        </Link>
                      )}
                      {s.state === "HITL_PENDING" && (
                        <Link to={`/validate/${s.id}`}
                          className="opacity-0 group-hover:opacity-100 text-amber-400 hover:text-amber-300 transition-all text-xs font-medium">
                          {t("Review →")}
                        </Link>
                      )}
                      {s.state === "FAILED" && s.error && (
                        <span className="text-red-400/70 text-[10px] font-mono truncate max-w-[120px] block" title={s.error}>
                          {s.error.slice(0, 40)}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color, icon, pulse }) {
  const colors = {
    blue:    "text-blue-400",
    emerald: "text-emerald-400",
    amber:   "text-amber-400",
    violet:  "text-violet-400",
    zinc:    "text-zinc-300",
  };
  return (
    <div className="card px-4 py-4">
      <div className="flex items-center justify-between mb-2.5">
        <span className="text-zinc-600">{icon}</span>
        <span className={`text-2xl font-bold tabular-nums ${colors[color] || "text-zinc-200"}`}>
          {value ?? "—"}
        </span>
      </div>
      <div className="flex items-center gap-1.5">
        {pulse && <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse-dot" />}
        <p className="text-xs text-zinc-500">{label}</p>
      </div>
    </div>
  );
}

function EmptyMsg({ text }) {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <p className="text-xs text-zinc-600">{text}</p>
    </div>
  );
}

function Skeleton({ rows = 3 }) {
  return (
    <div className="space-y-2.5 animate-pulse">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-3.5 rounded bg-zinc-800" style={{ width: `${55 + (i % 3) * 15}%` }} />
      ))}
    </div>
  );
}

function SessionIcon() {
  return <svg width="14" height="14" viewBox="0 0 15 15" fill="none"><rect x="1" y="1" width="13" height="13" rx="2" stroke="currentColor" strokeWidth="1.4"/><path d="M4 5h7M4 8h5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>;
}
function PulseIcon() {
  return <svg width="14" height="14" viewBox="0 0 15 15" fill="none"><path d="M1 7.5h2.5l2-4 2.5 8 2-4H14" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}
function ClockIcon() {
  return <svg width="14" height="14" viewBox="0 0 15 15" fill="none"><circle cx="7.5" cy="7.5" r="6" stroke="currentColor" strokeWidth="1.4"/><path d="M7.5 4.5v3.5l2 2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>;
}
function LayersIcon() {
  return <svg width="14" height="14" viewBox="0 0 15 15" fill="none"><path d="M7.5 1.5L13 4.5L7.5 7.5L2 4.5L7.5 1.5Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/><path d="M2 7.5L7.5 10.5L13 7.5" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/></svg>;
}
function BoltIcon() {
  return <svg width="14" height="14" viewBox="0 0 15 15" fill="none"><path d="M8.5 1.5l-5 7h5l-2 5 6-8H8l.5-4Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/></svg>;
}
