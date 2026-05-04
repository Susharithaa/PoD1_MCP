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

  const saved = sessions.filter(s => s.state === "SAVED").length;
  const pending = sessions.filter(s => s.state === "HITL_PENDING").length;

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-slide-up">
      <section className="grid gap-5 lg:grid-cols-[1.3fr_0.7fr] items-stretch">
        <div className="card p-6 lg:p-8 shadow-sm">
          <p className="eyebrow">{t("Overview")}</p>
          <h1 className="h-page mt-2">{t("API and tool hub for structured onboarding")}</h1>
          <p className="lead mt-3 max-w-2xl">
            {t("Review uploads, convert docs into tools, connect APIs, and monitor the system with a calmer production-style console.")}
          </p>
          <div className="flex flex-wrap gap-3 mt-6">
            <Link to="/create/chat" className="btn btn-primary">{t("Chat Builder")}</Link>
            <Link to="/create/upload" className="btn btn-secondary">{t("Doc Upload")}</Link>
            <Link to="/registry" className="btn btn-secondary">{t("API Registry")}</Link>
          </div>
        </div>
        <div className="card-flat p-6 lg:p-7 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="eyebrow">{t("System Snapshot")}</p>
              <h2 className="h-section mt-1">{t("Current activity")}</h2>
            </div>
            <span className="pill pill-ok"><span className="w-1.5 h-1.5 rounded-full bg-[var(--ok)]" />Live</span>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <MiniStat label={t("Total APIs")} value={apis.length} />
            <MiniStat label={t("Saved")} value={saved} />
            <MiniStat label={t("Pending")} value={pending} />
          </div>
          <div className="rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4">
            <p className="text-xs text-[var(--muted-2)] uppercase tracking-[0.18em] mb-2">{t("Recent state")}</p>
            <div className="space-y-2">
              {sessions.slice(0, 4).map(s => (
                <div key={s.id} className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{s.id.slice(0, 8)}…</p>
                    <p className="text-xs text-[var(--muted)]">{s.mode || "—"}</p>
                  </div>
                  <Badge label={STATE_LABEL[s.state] || s.state} variant={s.state} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section>
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="eyebrow">{t("Create")}</p>
            <h2 className="h-section mt-1">{t("Start a new API flow")}</h2>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <ActionCard
            title={t("Chat Builder")}
            desc={t("Describe your API in plain language and let the pipeline draft endpoints.")}
            to="/create/chat"
            accent="var(--info)"
          />
          <ActionCard
            title={t("Document Upload")}
            desc={t("Parse Swagger, OpenAPI, Markdown, text, or PDF documents into reviewable sessions.")}
            to="/create/upload"
            accent="var(--warn)"
          />
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <div className="card p-0 overflow-hidden">
          <div className="px-5 py-4 border-b border-[var(--line)]">
            <p className="eyebrow">{t("Recent Sessions")}</p>
          </div>
          {sessions.length === 0 ? (
            <EmptyState text={t("No sessions yet")} />
          ) : (
            <div className="divide-y divide-[var(--line)]">
              {sessions.slice(0, 6).map(s => (
                <Link key={s.id} to={s.state === "HITL_PENDING" ? `/validate/${s.id}` : "#"} className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-[var(--hover)] transition-colors">
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{s.id.slice(0, 8)}…</p>
                    <p className="text-xs text-[var(--muted)]">{s.mode || "—"}</p>
                  </div>
                  <Badge label={STATE_LABEL[s.state] || s.state} variant={s.state} />
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="card p-0 overflow-hidden">
          <div className="px-5 py-4 border-b border-[var(--line)] flex items-center justify-between">
            <div>
              <p className="eyebrow">{t("API Registry")}</p>
            </div>
            <Link to="/registry" className="text-xs text-[var(--muted)] hover:text-[var(--ink)]">{t("View all →")}</Link>
          </div>
          {apis.length === 0 ? (
            <EmptyState text={t("No APIs saved yet")} />
          ) : (
            <div className="divide-y divide-[var(--line)]">
              {apis.slice(0, 6).map(api => (
                <div key={api.id} className="flex items-center justify-between gap-4 px-5 py-4">
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{api.name}</p>
                    {api.base_url && <p className="text-xs text-[var(--muted)] font-mono truncate mt-0.5">{api.base_url}</p>}
                  </div>
                  <Badge label={api.visibility} variant={api.visibility} />
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function MiniStat({ label, value }) {
  return (
    <div className="rounded-lg border border-[var(--line)] bg-[var(--surface)] p-3">
      <p className="text-xs text-[var(--muted-2)] uppercase tracking-[0.18em]">{label}</p>
      <p className="mt-2 text-2xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}

function ActionCard({ title, desc, to, accent }) {
  return (
    <Link to={to} className="card p-5 hover:border-[var(--ink)] transition-all block">
      <div className="w-10 h-10 rounded-lg border" style={{ borderColor: `${accent}33`, background: `${accent}12` }} />
      <h3 className="mt-4 text-sm font-semibold">{title}</h3>
      <p className="lead mt-1">{desc}</p>
    </Link>
  );
}

function EmptyState({ text }) {
  return <div className="px-5 py-10 text-center text-sm text-[var(--muted)]">{text}</div>;
}
