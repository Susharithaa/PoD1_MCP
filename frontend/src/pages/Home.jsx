import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { agentApi, registryApi } from "../lib/api";
import Badge from "../components/Badge";
import { PageSpinner } from "../components/Spinner";
import { useLanguage } from "../context/LanguageContext";

const STATE_LABEL = {
  SAVED: "Saved", HITL_PENDING: "Review", FAILED: "Failed",
  PARSING: "Parsing", SCHEMA_GENERATING: "Generating",
  CONFIDENCE_SCORING: "Scoring", CLASSIFYING: "Classifying",
  VALIDATING: "Validating", SAVING: "Saving", INIT: "Starting",
};

export default function Home() {
  const { t } = useLanguage();
  const [sessions, setSessions] = useState([]);
  const [apis, setApis] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([agentApi.listSessions(), registryApi.list()])
      .then(([s, a]) => { setSessions(s); setApis(a); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageSpinner />;

  const pending = sessions.filter(s => s.state === "HITL_PENDING").length;
  const failed  = sessions.filter(s => s.state === "FAILED").length;

  return (
    <div className="space-y-8 animate-slide-up">

      {/* ── System Snapshot (full width, primary focus) ─────────────────── */}
      <section className="card p-6 space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="eyebrow">{t("System Snapshot")}</p>
            </div>
          <span className="pill pill-ok">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--ok)]" />Live
          </span>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <MiniStat label={t("Onboarded")} value={apis.length} />
          <MiniStat label={t("Pending")}   value={pending}      color="var(--warn)" />
          <MiniStat label={t("Failed")}    value={failed}       color="var(--err)" />
        </div>

      </section>

      {/* ── MCP Registry + Recent Activities ───────────────────────────── */}
      <section className="grid gap-5 lg:grid-cols-2">

        {/* MCP Registry — LEFT */}
        <div className="card p-0 overflow-hidden">
          <div className="px-5 py-4 border-b border-[var(--line)] flex items-center justify-between">
            <div>
              <p className="eyebrow">{t("MCP Registry")}</p>
              <p className="text-xs text-[var(--muted)] mt-0.5">{apis.length} registered</p>
            </div>
            <Link to="/registry" className="text-xs text-[var(--muted)] hover:text-[var(--ink)]">{t("View all →")}</Link>
          </div>
          {apis.length === 0 ? (
            <EmptyRow text={t("No APIs saved yet")} />
          ) : (
            <div className="divide-y divide-[var(--line)]">
              {apis.slice(0, 6).map(api => (
                <Link
                  key={api.id}
                  to={`/registry/${api.id}`}
                  className="flex items-center justify-between gap-4 px-5 py-3.5 hover:bg-[var(--hover)] transition-colors"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{api.name}</p>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      {api.created_by && (
                        <span className="text-[10px] text-[var(--muted)] truncate">
                          by {api.created_by}
                        </span>
                      )}
                      {api.base_url && (
                        <span className="text-[10px] text-[var(--muted-2)] font-mono truncate">
                          {api.created_by ? "· " : ""}{api.base_url}
                        </span>
                      )}
                    </div>
                  </div>
                  {api.endpoint_count != null && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--panel)] text-[var(--muted)] font-mono flex-shrink-0">
                      {api.endpoint_count} ep
                    </span>
                  )}
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Recent Activities — RIGHT */}
        <div className="card p-0 overflow-hidden">
          <div className="px-5 py-4 border-b border-[var(--line)] flex items-center justify-between">
            <div>
              <p className="eyebrow">{t("Recent Activities")}</p>
              <p className="text-xs text-[var(--muted)] mt-0.5">{sessions.filter(s => s.state !== "DISCARDED").length} total</p>
            </div>
            <Link to="/monitor" className="text-xs text-[var(--muted)] hover:text-[var(--ink)]">{t("Monitor →")}</Link>
          </div>
          {sessions.filter(s => s.state !== "DISCARDED").length === 0 ? (
            <EmptyRow text={t("No sessions yet")} />
          ) : (
            <div className="divide-y divide-[var(--line)]">
              {sessions.filter(s => s.state !== "DISCARDED").slice(0, 6).map(s => {
                const isPending = s.state === "HITL_PENDING";
                return (
                  <Link
                    key={s.id}
                    to={isPending ? `/validate/${s.id}` : (s.api_definition_id ? `/registry/${s.api_definition_id}` : "#")}
                    className={`flex items-center justify-between gap-4 px-5 py-3.5 transition-colors
                      ${isPending
                        ? "bg-amber-500/5 hover:bg-amber-500/10 border-l-2 border-amber-400/50"
                        : "hover:bg-[var(--hover)]"}`}
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium truncate">
                          {s.api_name || s.original_filename || s.id.slice(0, 8) + "…"}
                        </p>
                        {isPending && (
                          <span className="text-[10px] text-amber-500 font-medium whitespace-nowrap flex-shrink-0">
                            Review →
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        {s.user_name && (
                          <span className="text-[10px] text-[var(--muted)] truncate">
                            by {s.user_name}
                          </span>
                        )}
                        {s.user_name && s.mode && (
                          <span className="text-[10px] text-[var(--muted-2)]">·</span>
                        )}
                        {s.mode && (
                          <span className="text-[10px] text-[var(--muted-2)]">{s.mode}</span>
                        )}
                      </div>
                    </div>
                    <Badge label={STATE_LABEL[s.state] || s.state} variant={s.state} />
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function MiniStat({ label, value, color }) {
  return (
    <div className="rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2.5">
      <p className="text-[10px] text-[var(--muted-2)] uppercase tracking-[0.18em]">{label}</p>
      <p className="mt-1 text-xl font-semibold tabular-nums" style={color ? { color } : {}}>
        {value}
      </p>
    </div>
  );
}


function EmptyRow({ text }) {
  return <div className="px-5 py-10 text-center text-sm text-[var(--muted)]">{text}</div>;
}
