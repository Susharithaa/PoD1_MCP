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

  const saved   = sessions.filter(s => s.state === "SAVED").length;
  const pending = sessions.filter(s => s.state === "HITL_PENDING").length;
  const failed  = sessions.filter(s => s.state === "FAILED").length;

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-slide-up">

      {/* ── Hero + Snapshot ─────────────────────────────────────────────── */}
      <section className="grid gap-5 lg:grid-cols-[1.4fr_0.6fr] items-stretch">
        <div className="card p-6 lg:p-8 shadow-sm flex flex-col">
          <p className="eyebrow">{t("Overview")}</p>
          <h1 className="h-page mt-2">{t("API and tool hub for structured onboarding")}</h1>
          <p className="lead mt-3 max-w-2xl">
            {t("Review uploads, convert docs into tools, connect APIs, and monitor the system with a calmer production-style console.")}
          </p>
          <div className="grid gap-3 mt-6 sm:grid-cols-2">
            <QuickAction
              to="/create/chat"
              label={t("API Builder")}
              desc={t("Describe your API in plain language.")}
              accent="var(--info)"
            />
            <QuickAction
              to="/create/upload"
              label={t("Doc Upload")}
              desc={t("Parse Swagger, OpenAPI, PDF or Markdown.")}
              accent="var(--warn)"
            />
          </div>
          <div className="mt-3">
            <Link to="/registry" className="btn btn-secondary w-full text-center">{t("Open API Registry →")}</Link>
          </div>
        </div>

        <div className="card-flat p-6 space-y-4 flex flex-col">
          <div className="flex items-center justify-between">
            <div>
              <p className="eyebrow">{t("System Snapshot")}</p>
              <h2 className="h-section mt-1">{t("Current activity")}</h2>
            </div>
            <span className="pill pill-ok">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--ok)]" />Live
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <MiniStat label={t("Total APIs")}  value={apis.length}   />
            <MiniStat label={t("Saved")}        value={saved}         color="var(--ok)" />
            <MiniStat label={t("Pending")}      value={pending}       color="var(--warn)" />
            <MiniStat label={t("Failed")}       value={failed}        color="var(--err)" />
          </div>

          <div className="flex-1 rounded-lg border border-[var(--line)] bg-[var(--surface)] p-3 overflow-hidden">
            <p className="text-[10px] text-[var(--muted-2)] uppercase tracking-[0.18em] mb-2">{t("Recent state")}</p>
            <div className="space-y-2">
              {sessions.length === 0 ? (
                <p className="text-xs text-[var(--muted)]">{t("No sessions yet")}</p>
              ) : sessions.slice(0, 5).map(s => (
                <div key={s.id} className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-medium truncate">{s.api_name || s.id.slice(0, 8) + "…"}</p>
                    <p className="text-[10px] text-[var(--muted)] truncate">{s.user_name || s.mode || "—"}</p>
                  </div>
                  <Badge label={STATE_LABEL[s.state] || s.state} variant={s.state} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Recent Sessions + API Registry ──────────────────────────────── */}
      <section className="grid gap-5 lg:grid-cols-2">

        {/* Recent Sessions */}
        <div className="card p-0 overflow-hidden">
          <div className="px-5 py-4 border-b border-[var(--line)] flex items-center justify-between">
            <div>
              <p className="eyebrow">{t("Recent Sessions")}</p>
              <p className="text-xs text-[var(--muted)] mt-0.5">{sessions.length} total</p>
            </div>
            <Link to="/monitor" className="text-xs text-[var(--muted)] hover:text-[var(--ink)]">{t("Monitor →")}</Link>
          </div>
          {sessions.length === 0 ? (
            <EmptyRow text={t("No sessions yet")} />
          ) : (
            <div className="divide-y divide-[var(--line)]">
              {sessions.slice(0, 6).map(s => (
                <Link
                  key={s.id}
                  to={s.state === "HITL_PENDING" ? `/validate/${s.id}` : "#"}
                  className="flex items-center justify-between gap-4 px-5 py-3.5 hover:bg-[var(--hover)] transition-colors"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">
                      {s.api_name || s.id.slice(0, 8) + "…"}
                    </p>
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
              ))}
            </div>
          )}
        </div>

        {/* API Registry */}
        <div className="card p-0 overflow-hidden">
          <div className="px-5 py-4 border-b border-[var(--line)] flex items-center justify-between">
            <div>
              <p className="eyebrow">{t("API Registry")}</p>
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
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {api.endpoint_count != null && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--panel)] text-[var(--muted)] font-mono">
                        {api.endpoint_count} ep
                      </span>
                    )}
                    <Badge label={api.visibility} variant={api.visibility} />
                  </div>
                </Link>
              ))}
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

function QuickAction({ label, desc, to, accent }) {
  return (
    <Link to={to} className="flex items-start gap-3 rounded-xl border border-[var(--line)] p-4
                              hover:border-[var(--ink)] hover:bg-[var(--hover)] transition-all">
      <div className="w-8 h-8 rounded-lg flex-shrink-0 border"
        style={{ borderColor: `${accent}33`, background: `${accent}12` }} />
      <div className="min-w-0">
        <p className="text-sm font-semibold">{label}</p>
        <p className="text-xs text-[var(--muted)] mt-0.5">{desc}</p>
      </div>
    </Link>
  );
}

function EmptyRow({ text }) {
  return <div className="px-5 py-10 text-center text-sm text-[var(--muted)]">{text}</div>;
}
