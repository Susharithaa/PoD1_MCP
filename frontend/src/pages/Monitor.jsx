import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { monitorApi } from "../lib/api";
import { useLanguage } from "../context/LanguageContext";

const METHOD_COLOR = {
  GET:    "bg-blue-100 text-blue-700",
  POST:   "bg-green-100 text-green-700",
  PUT:    "bg-amber-100 text-amber-700",
  PATCH:  "bg-purple-100 text-purple-700",
  DELETE: "bg-red-100 text-red-700",
};

const REFRESH_MS = 5000;

const STATE_COLOR = {
  SAVED:             "text-[var(--ok)]",
  HITL_PENDING:      "text-[var(--warn)]",
  FAILED:            "text-[var(--err)]",
  PARSING:           "text-[var(--info)]",
  SCHEMA_GENERATING: "text-[var(--info)]",
  CLASSIFYING:       "text-[var(--muted)]",
  VALIDATING:        "text-[var(--info)]",
  SAVING:            "text-[var(--info)]",
};

export default function Monitor() {
  const { t } = useLanguage();
  const [overview,         setOverview]         = useState(null);
  const [active,           setActive]           = useState([]);
  const [sessions,         setSessions]         = useState([]);
  const [toolCalls,        setToolCalls]        = useState([]);
  const [selectedSession,  setSelectedSession]  = useState(null);
  const [sessionToolCalls, setSessionToolCalls] = useState([]);
  const [lastRefresh,      setLastRefresh]      = useState(null);
  const [loading,          setLoading]          = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [ov, ac, se, tc] = await Promise.all([
        monitorApi.overview().catch(() => null),
        monitorApi.active().catch(() => []),
        monitorApi.sessions(30).catch(() => []),
        monitorApi.toolCalls(30).catch(() => []),
      ]);
      if (ov) setOverview(ov);
      setActive(ac);
      setSessions(se.filter(s => s.state === "SAVED"));
      setToolCalls(tc);
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

  function selectSession(s) {
    setSelectedSession(prev => prev?.id === s.id ? null : s);
    setSessionToolCalls([]);
    if (s.api_definition_id) {
      monitorApi.apiToolCalls(s.api_definition_id).then(setSessionToolCalls).catch(() => {});
    }
  }

  return (
    <div className="max-w-6xl mx-auto animate-slide-up space-y-6">

      {/* Header */}
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Monitor</p>
          <h1 className="h-page mt-2">{t("System Monitor")}</h1>
          <p className="lead mt-2">{t("Real-time view of sessions, pipelines, and tool calls")}</p>
        </div>
        <div className="text-xs text-[var(--muted)]">
          {lastRefresh && (
            <span className="pill">
              {t("Updated")} {lastRefresh.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {/* Metric cards */}
      {overview && (
        <div className="grid gap-3 md:grid-cols-5">
          <Metric label={t("Total Sessions")} value={overview.total_sessions} />
          <Metric label={t("Active Now")}     value={overview.active_sessions}  accent="info" />
          <Metric label={t("Pending Review")} value={overview.pending_sessions} accent="warn" />
          <Metric label={t("APIs Registered")}value={overview.total_apis} />
          <Metric label={t("Tool Calls")}     value={overview.total_tool_calls} accent="ok" />
        </div>
      )}

      {/* Pipeline health */}
      {overview && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="eyebrow">Pipeline Health</p>
              <p className="text-xs text-[var(--muted)] mt-0.5">
                {overview.saved_sessions} saved · {overview.pending_sessions} pending · {overview.failed_sessions} failed
              </p>
            </div>
            <span className={`text-sm font-bold ${overview.success_rate >= 80 ? "text-[var(--ok)]" : overview.success_rate >= 50 ? "text-[var(--warn)]" : "text-[var(--err)]"}`}>
              {overview.success_rate}%
            </span>
          </div>
          <div className="h-2 rounded-full bg-[var(--panel)] overflow-hidden flex gap-px">
            {(() => {
              const total = Math.max(1, overview.saved_sessions + overview.failed_sessions + overview.pending_sessions);
              return (
                <>
                  <div className="bg-[var(--ok)] rounded-l-full transition-all"    style={{ width: `${overview.saved_sessions   / total * 100}%` }} />
                  <div className="bg-[var(--warn)] transition-all"                  style={{ width: `${overview.pending_sessions / total * 100}%` }} />
                  <div className="bg-[var(--err)] rounded-r-full transition-all"    style={{ width: `${overview.failed_sessions  / total * 100}%` }} />
                </>
              );
            })()}
          </div>
          <div className="flex gap-4 mt-2">
            {[["var(--ok)","Saved"],["var(--warn)","Pending"],["var(--err)","Failed"]].map(([c,l]) => (
              <div key={l} className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full" style={{ background: c }} />
                <span className="text-[10px] text-[var(--muted-2)]">{l}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active sessions + Tool call log */}
      <div className="grid gap-5 lg:grid-cols-2">

        <Panel title={t("Active Now")} count={active.length} loading={loading}>
          {active.length === 0 ? (
            <p className="text-xs text-[var(--muted)] py-4">{t("No active sessions")}</p>
          ) : active.map(s => (
            <div key={s.id} className="flex items-center justify-between gap-3 py-2.5 border-b border-[var(--line)] last:border-0">
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{s.api_name || "—"}</p>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className={`text-[10px] font-mono ${STATE_COLOR[s.state] || "text-[var(--muted)]"}`}>{s.state}</span>
                  {s.user_name && <span className="text-[10px] text-[var(--muted-2)]">· by {s.user_name}</span>}
                </div>
              </div>
              <span className="text-xs tabular-nums text-[var(--muted)] flex-shrink-0">{s.elapsed_seconds}s</span>
            </div>
          ))}
        </Panel>

        <Panel title={t("Tool Call Log")} count={toolCalls.length} loading={loading}>
          {toolCalls.length === 0 ? (
            <p className="text-xs text-[var(--muted)] py-4">{t("No tool calls yet")}</p>
          ) : toolCalls.map(c => (
            <div key={c.id} className="py-2.5 border-b border-[var(--line)] last:border-0">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{c.api_name}</p>
                  <p className="text-xs text-[var(--muted)] font-mono truncate">{c.endpoint_name}</p>
                </div>
                <span className="text-[10px] text-[var(--muted-2)] whitespace-nowrap flex-shrink-0">
                  {new Date(c.called_at).toLocaleTimeString()}
                </span>
              </div>
              {(c.user_name || c.user_email) && (
                <p className="text-[10px] text-[var(--muted-2)] mt-0.5">
                  called by {c.user_name || c.user_email}
                  {c.user_role && (
                    <span className="ml-1.5 px-1 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wide bg-[var(--surface-2)] text-[var(--muted)]">
                      {c.user_role}
                    </span>
                  )}
                </p>
              )}
            </div>
          ))}
        </Panel>
      </div>

      {/* Session history table */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--line)] flex items-center justify-between">
          <div>
            <p className="eyebrow">Session History</p>
            <p className="text-xs text-[var(--muted)] mt-0.5">{sessions.length} recent sessions</p>
          </div>
          <Link to="/registry" className="text-xs text-[var(--muted)] hover:text-[var(--ink)]">{t("View Registry →")}</Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[var(--line)] bg-[var(--panel)]">
                {["Session ID", "Created By", "Mode", "State", "API Name", "Test Result", "Prompt", "Duration", "Created"].map(h => (
                  <th key={h} className="px-4 py-2.5 text-left font-semibold text-[10px] uppercase tracking-[0.18em] text-[var(--muted-2)] whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--line)]">
              {sessions.map(s => (
                <tr
                  key={s.id}
                  className={`hover:bg-[var(--hover)] cursor-pointer transition-colors ${selectedSession?.id === s.id ? "bg-[var(--hover)]" : ""}`}
                  onClick={() => selectSession(s)}
                >
                  <td className="px-4 py-3 font-mono text-[var(--muted)]">{s.id.slice(0, 8)}…</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-0.5">
                      <div className="flex items-center gap-1.5">
                        <span className="font-medium text-[var(--ink)] truncate max-w-[130px]">{s.user_name || "—"}</span>
                        {s.user_role && (
                          <span className="px-1 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wide bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 shrink-0">
                            {s.user_role}
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-[var(--muted)] truncate max-w-[160px]">{s.user_email}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-[var(--muted)]">{s.mode}</td>
                  <td className="px-4 py-3">
                    <span className={`font-mono ${STATE_COLOR[s.state] || "text-[var(--muted)]"}`}>{s.state}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <span className="font-medium truncate max-w-[130px]">{s.api_name || "—"}</span>
                      {s.endpoints?.length > 0 && (
                        <span className="shrink-0 px-1.5 py-0.5 rounded-full text-[9px] font-semibold bg-[var(--surface-2)] text-[var(--muted)]">
                          {s.endpoints.length} tool{s.endpoints.length !== 1 ? "s" : ""}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {s.test_verdict && s.test_verdict !== "NONE" ? (
                      <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide ${
                        s.test_verdict === "PASS"        ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" :
                        s.test_verdict === "UNREACHABLE" ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" :
                        s.test_verdict === "WARNING"     ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" :
                        "bg-[var(--surface-2)] text-[var(--muted)]"
                      }`}>{s.test_verdict}</span>
                    ) : <span className="text-[var(--muted)]">—</span>}
                  </td>
                  <td className="px-4 py-3 max-w-[220px] truncate text-[var(--muted)]">{s.prompt || "—"}</td>
                  <td className="px-4 py-3 tabular-nums text-[var(--muted)]">{fmtDuration(s.duration_ms)}</td>
                  <td className="px-4 py-3 text-[var(--muted)] whitespace-nowrap">{s.created_time || timeAgo(s.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Selected session detail — tabless, all sections visible */}
      {selectedSession && (
        <div className="card overflow-hidden space-y-0">

          {/* Header */}
          <div className="px-5 py-4 border-b border-[var(--line)] flex items-center justify-between">
            <div>
              <p className="eyebrow">Session Detail</p>
              <div className="flex flex-wrap items-center gap-2 mt-1">
                <span className="font-mono text-xs text-[var(--muted)]">{selectedSession.id.slice(0, 8)}…</span>
                <span className="text-[var(--muted)]">·</span>
                <span className="text-xs font-medium text-[var(--ink)]">{selectedSession.api_name || "—"}</span>
                <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase ${STATE_COLOR[selectedSession.state] || "text-[var(--muted)]"} bg-[var(--panel)] border border-[var(--line)]`}>{selectedSession.state}</span>
                <span className="text-[var(--muted)]">·</span>
                <span className="text-xs text-[var(--muted)]">{selectedSession.mode}</span>
                <span className="text-[var(--muted)]">·</span>
                <span className="text-xs text-[var(--muted)]">{fmtDuration(selectedSession.duration_ms)}</span>
                <span className="text-[var(--muted)]">·</span>
                <span className="text-xs text-[var(--muted)]">{timeAgo(selectedSession.created_at)}</span>
              </div>
            </div>
            <button className="btn btn-secondary btn-sm" onClick={() => setSelectedSession(null)}>Close</button>
          </div>

          <div className="p-5 space-y-6">

            {/* Who created it */}
            <div>
              <p className="eyebrow mb-3">Created By</p>
              <div className="flex items-center gap-3 rounded-xl border border-[var(--line)] bg-[var(--panel)] px-4 py-3">
                <div className="w-8 h-8 rounded-full bg-[var(--surface-2)] flex items-center justify-center text-xs font-bold text-[var(--muted)]">
                  {(selectedSession.user_name || "?")[0].toUpperCase()}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-[var(--ink)]">{selectedSession.user_name || "—"}</span>
                    {selectedSession.user_role && (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wide bg-amber-100 text-amber-700">
                        {selectedSession.user_role}
                      </span>
                    )}
                    {selectedSession.test_verdict && selectedSession.test_verdict !== "NONE" && (
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wide ${
                        selectedSession.test_verdict === "PASS"        ? "bg-green-100 text-green-700" :
                        selectedSession.test_verdict === "UNREACHABLE" ? "bg-red-100 text-red-700" :
                        "bg-amber-100 text-amber-700"
                      }`}>Test: {selectedSession.test_verdict}</span>
                    )}
                  </div>
                  <p className="text-xs text-[var(--muted)]">{selectedSession.user_email}</p>
                </div>
              </div>
            </div>

            {/* Registered MCP Tools (endpoints) */}
            <div>
              <p className="eyebrow mb-3">Registered MCP Tools ({selectedSession.endpoints?.length || 0})</p>
              {(!selectedSession.endpoints || selectedSession.endpoints.length === 0) ? (
                <p className="text-xs text-[var(--muted)]">No endpoints registered in this session.</p>
              ) : (
                <div className="divide-y divide-[var(--line)] rounded-xl border border-[var(--line)] overflow-hidden">
                  {selectedSession.endpoints.map((ep, i) => (
                    <div key={i} className="flex items-start gap-3 px-4 py-3 bg-[var(--panel)]">
                      <span className={`shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded font-mono mt-0.5 ${METHOD_COLOR[ep.method] || "bg-[var(--surface-2)] text-[var(--muted)]"}`}>
                        {ep.method}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <p className="text-xs font-semibold font-mono text-[var(--ink)]">{ep.path}</p>
                          {ep.name && ep.name !== ep.path && (
                            <span className="text-[10px] text-[var(--muted)] truncate">· {ep.name}</span>
                          )}
                        </div>
                        {ep.description && <p className="text-[11px] text-[var(--muted)] mt-0.5">{ep.description}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Live tool call history for this API */}
            <div>
              <p className="eyebrow mb-3">Tool Call History ({sessionToolCalls.length})</p>
              {sessionToolCalls.length === 0 ? (
                <p className="text-xs text-[var(--muted)]">No tool calls recorded yet for this API.</p>
              ) : (
                <div className="divide-y divide-[var(--line)] rounded-xl border border-[var(--line)] overflow-hidden">
                  {sessionToolCalls.map(tc => (
                    <div key={tc.id} className="px-4 py-3 bg-[var(--panel)]">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className={`shrink-0 text-[9px] font-bold px-1 py-0.5 rounded ${tc.success ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                              {tc.success ? "OK" : "FAIL"}
                            </span>
                            <span className="text-xs font-mono font-medium text-[var(--ink)]">{tc.endpoint_name}</span>
                            {tc.user_name && (
                              <span className="text-[10px] text-[var(--muted)]">
                                by {tc.user_name}
                                {tc.user_role && (
                                  <span className="ml-1 px-1 py-0.5 rounded text-[9px] font-semibold uppercase bg-[var(--surface-2)] text-[var(--muted)]">{tc.user_role}</span>
                                )}
                              </span>
                            )}
                          </div>
                          {tc.result_preview && (
                            <p className="text-[10px] text-[var(--muted)] mt-1 font-mono truncate max-w-[500px]">{tc.result_preview}</p>
                          )}
                        </div>
                        <span className="text-[10px] text-[var(--muted-2)] whitespace-nowrap shrink-0">
                          {new Date(tc.called_at).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Source prompt */}
            {selectedSession.prompt && (
              <div>
                <p className="eyebrow mb-3">Source</p>
                <div className="rounded-xl border border-[var(--line)] bg-[var(--panel)] px-4 py-3">
                  <p className="text-xs text-[var(--muted)] leading-relaxed">{selectedSession.raw_input || selectedSession.prompt}</p>
                </div>
              </div>
            )}

          </div>
        </div>
      )}
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
      <div className="px-5 py-3 min-h-[220px] overflow-y-auto">
        {loading && count === 0
          ? <div className="text-sm text-[var(--muted)] py-4">Loading…</div>
          : children
        }
      </div>
    </div>
  );
}

function Metric({ label, value, accent }) {
  const color = accent === "ok" ? "text-[var(--ok)]"
              : accent === "warn" ? "text-[var(--warn)]"
              : accent === "err" ? "text-[var(--err)]"
              : accent === "info" ? "text-[var(--info)]"
              : "text-[var(--ink)]";
  return (
    <div className="card p-4">
      <p className="text-[10px] uppercase tracking-[0.18em] text-[var(--muted-2)]">{label}</p>
      <p className={`mt-2 text-2xl font-semibold tabular-nums ${color}`}>{value ?? "—"}</p>
    </div>
  );
}

function timeAgo(iso) {
  if (!iso) return "—";
  const secs = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (secs < 60)   return `${secs}s ago`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  return `${Math.floor(secs / 3600)}h ago`;
}

function fmtDuration(ms) {
  if (!ms && ms !== 0) return "—";
  if (ms < 1000)   return `${ms}ms`;
  if (ms < 60000)  return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
}
