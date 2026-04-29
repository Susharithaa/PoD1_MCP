import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { registryApi } from "../lib/api";
import Badge from "../components/Badge";
import EmptyState from "../components/EmptyState";
import { PageSpinner } from "../components/Spinner";
import { useLanguage } from "../context/LanguageContext";

export default function Registry() {
  const { t } = useLanguage();
  const [apis,    setApis]    = useState([]);
  const [search,  setSearch]  = useState("");
  const [loading, setLoading] = useState(true);
  const [searchParams]        = useSearchParams();
  const highlight             = searchParams.get("highlight");

  useEffect(() => {
    registryApi.list().then(setApis).finally(() => setLoading(false));
  }, []);

  const filtered = apis.filter(a =>
    !search ||
    a.name.toLowerCase().includes(search.toLowerCase()) ||
    a.description?.toLowerCase().includes(search.toLowerCase()) ||
    a.base_url?.toLowerCase().includes(search.toLowerCase())
  );

  const countLabel = apis.length === 1
    ? `1${t("1 API registered")}`
    : `${apis.length}${t(" APIs registered")}`;

  return (
    <div className="max-w-5xl mx-auto animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between mb-7">
        <div>
          <h1 className="page-title">{t("API Registry")}</h1>
          <p className="page-subtitle">{countLabel}</p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/create/chat"   className="btn-secondary text-xs px-3 py-1.5">{t("Chat Builder")}</Link>
          <Link to="/create/upload" className="btn-primary  text-xs px-3 py-1.5">+ {t("Doc Upload")}</Link>
        </div>
      </div>

      {/* Search */}
      {apis.length > 0 && (
        <div className="relative mb-5">
          <SearchIcon />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder={t("Search by name, URL, or description…")}
            className="input pl-9"
          />
        </div>
      )}

      {loading ? <PageSpinner /> : filtered.length === 0 ? (
        apis.length === 0 ? (
          <EmptyState
            icon="◻"
            title={t("No APIs yet")}
            description={t("Create your first API using the Chat Builder or Document Upload.")}
            action={
              <div className="flex gap-2">
                <Link to="/create/chat"   className="btn-secondary text-xs">{t("Chat Builder")}</Link>
                <Link to="/create/upload" className="btn-primary  text-xs">{t("Doc Upload")}</Link>
              </div>
            }
          />
        ) : (
          <EmptyState icon="⊘" title={t("No results")} description={`"${search}"`} />
        )
      ) : (
        <div className="space-y-2">
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
    <div className={`card transition-all
                     ${highlighted
                       ? "border-emerald-500/30 bg-emerald-500/5"
                       : "hover:border-zinc-700"}`}>
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full px-5 py-4 flex items-start justify-between gap-4 text-left"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-sm font-semibold text-zinc-100">{api.name}</span>
            {highlighted && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10
                               text-emerald-400 border border-emerald-500/20 font-medium">
                {t("Just saved")}
              </span>
            )}
          </div>
          {api.description && (
            <p className="text-xs text-zinc-500 line-clamp-1">{api.description}</p>
          )}
          {api.base_url && (
            <p className="text-xs text-zinc-600 font-mono mt-1 truncate">{api.base_url}</p>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <Badge label={api.visibility} variant={api.visibility} />
          <ChevronIcon expanded={expanded} />
        </div>
      </button>

      {expanded && (
        <div className="border-t border-zinc-800 px-5 py-4 space-y-4 animate-fade-in">
          <div className="grid grid-cols-3 gap-3 text-xs">
            <Meta label={t("Version")}    value={api.version}    />
            <Meta label={t("Visibility")} value={api.visibility} />
            <Meta label={t("Created")}    value={new Date(api.created_at).toLocaleDateString()} />
          </div>

          {api.source_session_id && (
            <div>
              <p className="section-label mb-1.5">{t("Source Session")}</p>
              <p className="text-xs font-mono text-zinc-500">{api.source_session_id}</p>
            </div>
          )}

          <div className="flex gap-2 pt-1">
            <Link
              to={`/registry/${api.id}`}
              className="btn-primary text-xs px-3 py-1.5"
              onClick={e => e.stopPropagation()}
            >
              Manage
            </Link>
            <button
              onClick={() => navigator.clipboard.writeText(api.id)}
              className="btn-ghost text-xs px-3 py-1.5"
            >
              {t("Copy ID")}
            </button>
            <button
              onClick={async () => {
                if (confirm(`Delete "${api.name}"?`)) {
                  await registryApi.delete(api.id);
                  window.location.reload();
                }
              }}
              className="btn-danger text-xs px-3 py-1.5"
            >
              {t("Delete")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Meta({ label, value }) {
  return (
    <div>
      <p className="text-zinc-600 text-xs mb-0.5">{label}</p>
      <p className="text-zinc-300 text-xs font-mono">{value}</p>
    </div>
  );
}

function SearchIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 15 15" fill="none"
      className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600 pointer-events-none">
      <circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" strokeWidth="1.4"/>
      <path d="M10 10l3 3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
    </svg>
  );
}

function ChevronIcon({ expanded }) {
  return (
    <svg width="14" height="14" viewBox="0 0 15 15" fill="none"
      className={`text-zinc-600 transition-transform ${expanded ? "rotate-180" : ""}`}>
      <path d="M3 5l4.5 5L12 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}
