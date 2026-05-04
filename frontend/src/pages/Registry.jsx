import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { registryApi } from "../lib/api";
import Badge from "../components/Badge";
import EmptyState from "../components/EmptyState";
import { PageSpinner } from "../components/Spinner";
import { useLanguage } from "../context/LanguageContext";

export default function Registry() {
  const { t } = useLanguage();
  const [apis, setApis] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [searchParams] = useSearchParams();
  const highlight = searchParams.get("highlight");

  useEffect(() => {
    registryApi.list().then(setApis).finally(() => setLoading(false));
  }, []);

  const filtered = apis.filter(a =>
    !search ||
    a.name.toLowerCase().includes(search.toLowerCase()) ||
    a.description?.toLowerCase().includes(search.toLowerCase()) ||
    a.base_url?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="max-w-6xl mx-auto animate-slide-up space-y-5">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="eyebrow">{t("Registry")}</p>
          <h1 className="h-page mt-2">{t("API Registry")}</h1>
          <p className="lead mt-2">{apis.length} {t("APIs registered")}</p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/create/chat" className="btn btn-secondary btn-sm">{t("Chat Builder")}</Link>
          <Link to="/create/upload" className="btn btn-primary btn-sm">{t("Doc Upload")}</Link>
        </div>
      </div>

      {apis.length > 0 && (
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder={t("Search by name, URL, or description…")}
          className="input"
        />
      )}

      {loading ? <PageSpinner /> : filtered.length === 0 ? (
        apis.length === 0 ? (
          <EmptyState
            icon="◫"
            title={t("No APIs yet")}
            description={t("Create your first API using Chat Builder or Document Upload.")}
            action={<div className="flex gap-2"><Link to="/create/chat" className="btn btn-secondary btn-sm">{t("Chat Builder")}</Link><Link to="/create/upload" className="btn btn-primary btn-sm">{t("Doc Upload")}</Link></div>}
          />
        ) : (
          <EmptyState icon="⊘" title={t("No results")} description={`"${search}"`} />
        )
      ) : (
        <div className="grid gap-3">
          {filtered.map(api => (
            <ApiCard key={api.id} api={api} highlighted={highlight === api.id} t={t} />
          ))}
        </div>
      )}
    </div>
  );
}

function ApiCard({ api, highlighted, t }) {
  const [expanded, setExpanded] = useState(highlighted);

  return (
    <div className={`card overflow-hidden ${highlighted ? "ring-1 ring-[var(--ink)]" : ""}`}>
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full px-5 py-4 flex items-start justify-between gap-4 text-left hover:bg-[var(--hover)] transition-colors"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-sm font-semibold">{api.name}</span>
            {highlighted && <span className="pill pill-ok">{t("Just saved")}</span>}
          </div>
          {api.description && <p className="text-xs text-[var(--muted)] line-clamp-1">{api.description}</p>}
          {api.base_url && <p className="text-xs text-[var(--muted)] font-mono mt-1 truncate">{api.base_url}</p>}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <Badge label={api.visibility} variant={api.visibility} />
          <ChevronIcon expanded={expanded} />
        </div>
      </button>
      {expanded && (
        <div className="border-t border-[var(--line)] px-5 py-4 space-y-4">
          <div className="grid grid-cols-3 gap-3 text-xs">
            <Meta label={t("Version")} value={api.version} />
            <Meta label={t("Visibility")} value={api.visibility} />
            <Meta label={t("Created")} value={new Date(api.created_at).toLocaleDateString()} />
          </div>
          {api.source_session_id && (
            <div>
              <p className="section-label mb-1.5">{t("Source Session")}</p>
              <p className="text-xs font-mono text-[var(--muted)]">{api.source_session_id}</p>
            </div>
          )}
          <div className="flex gap-2 pt-1">
            <Link to={`/registry/${api.id}`} className="btn btn-primary btn-sm" onClick={e => e.stopPropagation()}>{t("Manage")}</Link>
            <button onClick={() => navigator.clipboard.writeText(api.id)} className="btn btn-secondary btn-sm">{t("Copy ID")}</button>
            <button onClick={async () => { if (confirm(`Delete "${api.name}"?`)) { await registryApi.delete(api.id); window.location.reload(); } }} className="btn btn-danger btn-sm">{t("Delete")}</button>
          </div>
        </div>
      )}
    </div>
  );
}

function Meta({ label, value }) {
  return (
    <div className="rounded-lg border border-[var(--line)] bg-[var(--surface)] p-3">
      <p className="text-[10px] uppercase tracking-[0.18em] text-[var(--muted-2)]">{label}</p>
      <p className="text-xs font-mono text-[var(--muted)] mt-1">{value}</p>
    </div>
  );
}

function ChevronIcon({ expanded }) {
  return (
    <svg width="14" height="14" viewBox="0 0 15 15" fill="none" className={`text-[var(--muted)] transition-transform ${expanded ? "rotate-180" : ""}`}>
      <path d="M3 5l4.5 5L12 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}
