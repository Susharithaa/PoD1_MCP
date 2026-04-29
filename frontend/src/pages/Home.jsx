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
  const [apis,     setApis]     = useState([]);
  const [loading,  setLoading]  = useState(true);

  useEffect(() => {
    Promise.all([agentApi.listSessions(), registryApi.list()])
      .then(([s, a]) => { setSessions(s); setApis(a); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageSpinner />;

  const saved   = sessions.filter(s => s.state === "SAVED").length;
  const pending = sessions.filter(s => s.state === "HITL_PENDING").length;

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-slide-up">
      {/* Header */}
      <div>
        <h1 className="page-title">{t("Overview")}</h1>
        <p className="page-subtitle">{t("Monitor sessions and API registry activity.")}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard label={t("Total APIs")}     value={apis.length} color="blue"    icon={<ApiIcon />} />
        <StatCard label={t("Saved")}          value={saved}       color="emerald" icon={<CheckIcon />} />
        <StatCard label={t("Pending Review")} value={pending}     color="amber"   icon={<ClockIcon />} />
      </div>

      {/* Quick Actions */}
      <div>
        <p className="section-label mb-3">{t("Create New API")}</p>
        <div className="grid grid-cols-2 gap-3">
          <Link to="/create/chat"
            className="card p-5 hover:border-zinc-600 hover:bg-zinc-800/50 transition-all group cursor-pointer">
            <div className="w-9 h-9 rounded-lg bg-blue-600/10 border border-blue-500/20
                            flex items-center justify-center mb-3.5 group-hover:bg-blue-600/20 transition-colors">
              <svg width="17" height="17" viewBox="0 0 15 15" fill="none">
                <path d="M2 2h11a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H5l-3 3V3a1 1 0 0 1 1-1Z"
                  stroke="#60A5FA" strokeWidth="1.4" strokeLinejoin="round"/>
              </svg>
            </div>
            <p className="text-sm font-semibold text-zinc-100 mb-0.5">{t("Chat Builder")}</p>
            <p className="text-xs text-zinc-500">{t("Describe your API in plain language")}</p>
          </Link>

          <Link to="/create/upload"
            className="card p-5 hover:border-zinc-600 hover:bg-zinc-800/50 transition-all group cursor-pointer">
            <div className="w-9 h-9 rounded-lg bg-violet-500/10 border border-violet-500/20
                            flex items-center justify-center mb-3.5 group-hover:bg-violet-500/20 transition-colors">
              <svg width="17" height="17" viewBox="0 0 15 15" fill="none">
                <path d="M7.5 10V2M4 5l3.5-3.5L11 5" stroke="#A78BFA" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M2 11v1a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1v-1" stroke="#A78BFA" strokeWidth="1.4" strokeLinecap="round"/>
              </svg>
            </div>
            <p className="text-sm font-semibold text-zinc-100 mb-0.5">{t("Document Upload")}</p>
            <p className="text-xs text-zinc-500">{t("Parse from Swagger, PDF, or text")}</p>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-5">
        {/* Recent Sessions */}
        <div>
          <p className="section-label mb-3">{t("Recent Sessions")}</p>
          <div className="card divide-y divide-zinc-800">
            {sessions.length === 0 ? (
              <p className="text-zinc-600 text-sm text-center py-10">{t("No sessions yet")}</p>
            ) : sessions.slice(0, 6).map(s => (
              <Link key={s.id} to={s.state === "HITL_PENDING" ? `/validate/${s.id}` : "#"}
                className="flex items-center justify-between px-4 py-3
                           hover:bg-zinc-800/40 transition-colors first:rounded-t-xl last:rounded-b-xl">
                <div>
                  <p className="text-sm text-zinc-300 font-mono">{s.id.slice(0, 8)}…</p>
                  <p className="text-xs text-zinc-600 mt-0.5">{s.mode || "—"}</p>
                </div>
                <Badge label={STATE_LABEL[s.state] || s.state} variant={s.state} />
              </Link>
            ))}
          </div>
        </div>

        {/* Recent APIs */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <p className="section-label">{t("API Registry")}</p>
            <Link to="/registry" className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors">
              {t("View all →")}
            </Link>
          </div>
          <div className="card divide-y divide-zinc-800">
            {apis.length === 0 ? (
              <p className="text-zinc-600 text-sm text-center py-10">{t("No APIs saved yet")}</p>
            ) : apis.slice(0, 6).map(api => (
              <div key={api.id}
                className="flex items-center justify-between px-4 py-3
                           first:rounded-t-xl last:rounded-b-xl">
                <div className="min-w-0 mr-3">
                  <p className="text-sm text-zinc-200 font-medium truncate">{api.name}</p>
                  {api.base_url && (
                    <p className="text-xs text-zinc-600 font-mono mt-0.5 truncate">{api.base_url}</p>
                  )}
                </div>
                <Badge label={api.visibility} variant={api.visibility} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, color, icon }) {
  const colors = {
    blue:    { num: "text-blue-400",    bg: "bg-blue-500/10",    border: "border-blue-500/20" },
    emerald: { num: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
    amber:   { num: "text-amber-400",   bg: "bg-amber-500/10",   border: "border-amber-500/20" },
  };
  const c = colors[color] || colors.blue;
  return (
    <div className={`card p-5 border ${c.border}`}>
      <div className="flex items-center justify-between mb-3">
        <div className={`w-8 h-8 rounded-lg ${c.bg} ${c.border} border flex items-center justify-center ${c.num}`}>
          {icon}
        </div>
        <span className={`text-3xl font-bold tabular-nums tracking-tight ${c.num}`}>{value}</span>
      </div>
      <p className="text-xs text-zinc-500 font-medium">{label}</p>
    </div>
  );
}

/* ── Inline icons ── */
function ApiIcon() {
  return <svg width="14" height="14" viewBox="0 0 15 15" fill="none"><path d="M7.5 1.5L13 4.5L7.5 7.5L2 4.5L7.5 1.5Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/><path d="M2 7.5L7.5 10.5L13 7.5" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/></svg>;
}
function CheckIcon() {
  return <svg width="14" height="14" viewBox="0 0 15 15" fill="none"><path d="M2.5 8l4 4 6-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}
function ClockIcon() {
  return <svg width="14" height="14" viewBox="0 0 15 15" fill="none"><circle cx="7.5" cy="7.5" r="6" stroke="currentColor" strokeWidth="1.4"/><path d="M7.5 4.5v3.5l2 2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>;
}
