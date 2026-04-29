import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { agentApi, chatgptApi } from "../lib/api";
import Badge from "../components/Badge";
import { PageSpinner } from "../components/Spinner";
import Spinner from "../components/Spinner";
import { useLanguage } from "../context/LanguageContext";

/* ── Constants ── */
const PROCESSING_STATES = ["CLASSIFYING", "PARSING", "SCHEMA_GENERATING", "RECONCILING", "CONFIDENCE_SCORING"];
const POST_HITL_STATES  = ["VALIDATING", "API_TESTING", "SAVING"];
const STATE_LABEL_KEYS = {
  CLASSIFYING:        "Detecting input type…",
  PARSING:            "Extracting API structure…",
  SCHEMA_GENERATING:  "Building schema…",
  RECONCILING:        "Reconciling endpoints…",
  CONFIDENCE_SCORING: "Scoring confidence…",
  VALIDATING:         "Validating schema…",
  API_TESTING:        "Testing API endpoints live…",
  SAVING:             "Saving MCP tool…",
};
const METHODS   = ["GET", "POST", "PUT", "PATCH", "DELETE"];
const TYPES     = ["string", "number", "integer", "boolean", "object", "array"];
const AUTH_OPTS = [
  { value: "none",          label: "None" },
  { value: "basic",         label: "Basic Auth" },
  { value: "bearer",        label: "Bearer Token" },
  { value: "api_key",       label: "API Key (Header)" },
  { value: "api_key_query", label: "API Key (Query Param)" },
  { value: "oauth2",        label: "OAuth 2.0 Client" },
];

const AUTH_CRED_FIELDS = {
  none:          [],
  basic:         [
    { key: "username",      label: "Username",      secret: false },
    { key: "password",      label: "Password",      secret: true  },
  ],
  bearer:        [
    { key: "token",         label: "Token",         secret: true  },
  ],
  api_key:       [
    { key: "header_name",   label: "Header Name",   secret: false, placeholder: "X-API-Key" },
    { key: "value",         label: "Key Value",      secret: true  },
  ],
  api_key_query: [
    { key: "param_name",    label: "Query Param",   secret: false },
    { key: "value",         label: "Value",         secret: true  },
  ],
  oauth2:        [
    { key: "client_id",     label: "Client ID",     secret: false },
    { key: "client_secret", label: "Client Secret", secret: true  },
    { key: "token_url",     label: "Token URL",     secret: false },
  ],
};

const EMPTY_CREDS = {
  type: "none", username: "", password: "", token: "",
  header_name: "", value: "", param_name: "",
  client_id: "", client_secret: "", token_url: "",
};

/* ── Helpers ── */
function uid() { return Math.random().toString(36).slice(2, 9); }

function schemaToParams(schema) {
  if (!schema || !schema.properties) return [];
  return Object.entries(schema.properties).map(([name, def]) => ({
    _id:         uid(),
    name,
    type:        def.type || "string",
    required:    (schema.required || []).includes(name),
    description: def.description || "",
  }));
}

function paramsToSchema(params) {
  const valid = params.filter(p => p.name.trim());
  if (!valid.length) return { type: "object", properties: {} };
  return {
    type: "object",
    properties: Object.fromEntries(
      valid.map(p => [p.name, { type: p.type, description: p.description }])
    ),
    required: valid.filter(p => p.required).map(p => p.name),
  };
}

function draftToForm(draft) {
  return {
    name:        draft?.name || "",
    description: draft?.description || "",
    base_url:    draft?.base_url || "",
    version:     draft?.version || "1.0.0",
    auth_type:   draft?.auth_type || "none",
    auth_header: draft?.auth_header || "",
    endpoints:   (draft?.endpoints || []).map(ep => ({
      _id:        uid(),
      method:     ep.method || "GET",
      path:       ep.path || "",
      name:       ep.name || "",
      description:ep.description || "",
      auth_type:  ep.auth_type || "",
      auth_creds: { ...EMPTY_CREDS, type: ep.auth_type || "none" },
      parameters: schemaToParams(ep.input_schema),
    })),
  };
}

function formToEdits(form, authMode, globalAuth) {
  return {
    name:        form.name,
    description: form.description,
    base_url:    form.base_url,
    version:     form.version,
    auth_type:   authMode === "same" ? globalAuth.type : form.auth_type,
    endpoints:   form.endpoints.map(ep => ({
      name:         ep.name || `${ep.method} ${ep.path}`,
      description:  ep.description,
      method:       ep.method,
      path:         ep.path,
      auth_type:    authMode === "per_endpoint"
                      ? (ep.auth_creds?.type || ep.auth_type || "")
                      : ep.auth_type,
      input_schema: paramsToSchema(ep.parameters),
    })),
  };
}

function buildAuthCredentials(authMode, globalAuth, endpoints) {
  if (authMode === "same") {
    if (!globalAuth.type || globalAuth.type === "none") return null;
    return { mode: "same", ...globalAuth };
  }
  const credentials = endpoints.map(ep => ep.auth_creds || { type: "none" });
  if (credentials.every(c => !c.type || c.type === "none")) return null;
  return { mode: "per_endpoint", credentials };
}

/* ════════════════════════════════════════════════════════════════════════════
   Main page
═══════════════════════════════════════════════════════════════════════════ */
export default function HITLValidator() {
  const { t }                             = useLanguage();
  const { sessionId }                     = useParams();
  const navigate                          = useNavigate();
  const [session,    setSession]          = useState(null);
  const [form,       setForm]             = useState(null);
  const [saving,     setSaving]           = useState(false);
  const [error,      setError]            = useState(null);
  const [loading,    setLoading]          = useState(true);
  const [authMode,      setAuthMode]      = useState("same");
  const [globalAuth,    setGlobalAuth]    = useState({ ...EMPTY_CREDS });
  const [recovering,      setRecovering]      = useState(false);
  const [confirmDiscard,  setConfirmDiscard]  = useState(false);
  const [localTestResults, setLocalTestResults] = useState([]);
  const pollRef                           = useRef(null);

  /* ── polling during LLM processing ── */
  function startPolling(id) {
    pollRef.current = setInterval(async () => {
      const s = await agentApi.getSession(id).catch(() => null);
      if (!s) return;
      setSession(s);
      if (!PROCESSING_STATES.includes(s.state)) {
        clearInterval(pollRef.current);
        if (s.state === "SAVED") {
          navigate(`/registry/${s.api_definition_id}`, { replace: true });
        } else {
          setForm(draftToForm(s.final_api || s.draft_api));
          setLocalTestResults(s.api_test_results || []);
        }
      }
    }, 1800);
  }

  useEffect(() => {
    agentApi.getSession(sessionId)
      .then(s => {
        setSession(s);
        if (s.state === "SAVED") {
          navigate(`/registry/${s.api_definition_id}`, { replace: true });
        } else if (PROCESSING_STATES.includes(s.state)) {
          startPolling(sessionId);
        } else {
          const draft = s.final_api || s.draft_api;
          setForm(draftToForm(draft));
          setLocalTestResults(s.api_test_results || []);
          if (s.auth_credentials && s.auth_credentials.type && s.auth_credentials.type !== "none") {
            setGlobalAuth({ ...EMPTY_CREDS, ...s.auth_credentials });
          } else if (draft?.auth_type && draft.auth_type !== "none") {
            setGlobalAuth(c => ({ ...c, type: draft.auth_type }));
          }
        }
      })
      .catch(() => setError(t("Session not found.")))
      .finally(() => setLoading(false));
    return () => clearInterval(pollRef.current);
  }, [sessionId]);

  /* ── form mutators ── */
  function sf(key, val) { setForm(f => ({ ...f, [key]: val })); }

  function setEp(i, key, val) {
    setForm(f => {
      const eps = [...f.endpoints];
      eps[i] = { ...eps[i], [key]: val };
      return { ...f, endpoints: eps };
    });
  }

  function setParam(ei, pi, key, val) {
    setForm(f => {
      const eps = [...f.endpoints];
      const params = [...eps[ei].parameters];
      params[pi] = { ...params[pi], [key]: val };
      eps[ei] = { ...eps[ei], parameters: params };
      return { ...f, endpoints: eps };
    });
  }

  function addParam(ei) {
    setForm(f => {
      const eps = [...f.endpoints];
      eps[ei] = { ...eps[ei], parameters: [...eps[ei].parameters, { _id: uid(), name: "", type: "string", required: false, description: "" }] };
      return { ...f, endpoints: eps };
    });
  }

  function removeParam(ei, pi) {
    setForm(f => {
      const eps = [...f.endpoints];
      eps[ei] = { ...eps[ei], parameters: eps[ei].parameters.filter((_, idx) => idx !== pi) };
      return { ...f, endpoints: eps };
    });
  }

  function _persistEndpointDeletion(updatedEndpoints) {
    const clean = updatedEndpoints.map(ep => ({
      name:         ep.name || `${ep.method} ${ep.path}`,
      description:  ep.description,
      method:       ep.method,
      path:         ep.path,
      auth_type:    ep.auth_type,
      input_schema: paramsToSchema(ep.parameters),
    }));
    agentApi.patchDraft(sessionId, { endpoints: clean }).catch(() => {});
  }

  function removeEndpoint(ei) {
    setForm(f => {
      const removed = f.endpoints[ei];
      const updated = f.endpoints.filter((_, idx) => idx !== ei);
      _persistEndpointDeletion(updated);
      if (removed) {
        setLocalTestResults(tr => tr.filter(r => !(r.method === removed.method && r.path === removed.path)));
      }
      return { ...f, endpoints: updated };
    });
  }

  function removeEndpointByMethodPath(method, path) {
    setForm(f => {
      const updated = f.endpoints.filter(ep => !(ep.method === method && ep.path === path));
      _persistEndpointDeletion(updated);
      setLocalTestResults(tr => tr.filter(r => !(r.method === method && r.path === path)));
      return { ...f, endpoints: updated };
    });
  }

  function setEpCreds(ei, key, val) {
    setForm(f => {
      const eps = [...f.endpoints];
      eps[ei] = { ...eps[ei], auth_creds: { ...(eps[ei].auth_creds || EMPTY_CREDS), [key]: val } };
      return { ...f, endpoints: eps };
    });
  }

  /* ── submit ── */
  async function handleConfirm(e, saveAnyway = false) {
    if (e && e.preventDefault) e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const edits = formToEdits(form, authMode, globalAuth);
      const authCredentials = buildAuthCredentials(authMode, globalAuth, form.endpoints);
      const updated = await agentApi.submitHITL(sessionId, edits, authCredentials, saveAnyway);
      setSession(updated);
      if (updated.state === "SAVED") {
        navigate(`/registry/${updated.api_definition_id}`, { replace: true });
      } else if (updated.state === "HITL_PENDING") {
        setForm(draftToForm(updated.final_api || updated.draft_api));
        setLocalTestResults(updated.api_test_results || []);
      }
    } catch (err) {
      setError(err.response?.data?.detail || t("Save failed."));
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveAnyway() {
    await handleConfirm(null, true);
  }

  /* ── restart pipeline with same file ── */
  async function handleRestart() {
    setRecovering(true);
    setError(null);
    try {
      const newSession = await agentApi.restart(sessionId);
      navigate(`/validate/${newSession.id}`, { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || t("Restart failed."));
      setRecovering(false);
    }
  }

  /* ── discard session ── */
  async function handleDiscard() {
    setRecovering(true);
    try {
      await agentApi.discard(sessionId);
      navigate("/create/upload", { replace: true });
    } catch {
      navigate("/create/upload", { replace: true });
    }
  }

  /* ── render ── */
  if (loading)                                           return <PageSpinner />;
  if (error && !session)                                 return <ErrorPage message={error} t={t} />;
  if (PROCESSING_STATES.includes(session?.state))        return <ProcessingPage state={session.state} t={t} />;

  const confidence  = session?.confidence_map || {};
  const valErrors   = session?.validation_errors || [];
  const isFailed    = session?.state === "FAILED";
  const isManual    = session?.mode === "MANUAL";
  const testResults = localTestResults;
  const hasTestIssues = session?.state === "HITL_PENDING" &&
    testResults.some(r => r.verdict === "UNREACHABLE" || r.verdict === "WARNING");

  // Detect when auth type is required but no credentials have been filled in
  const apiAuthType    = form?.auth_type || "none";
  const credsEmpty     = !globalAuth.token && !globalAuth.password && !globalAuth.value && !globalAuth.client_secret;
  const authWarning    = apiAuthType !== "none" && credsEmpty && authMode === "same";

  return (
    <div className="max-w-3xl animate-slide-up">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="page-title">{t("Review & Validate")}</h1>
          <p className="page-subtitle mt-1">
            {t("Confirm the API definition before registering it as an MCP tool.")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge label={session?.mode || "CHAT"} variant={session?.mode} />
          <Badge label={session?.state} variant={session?.state} />
        </div>
      </div>

      {/* Auth credentials missing warning */}
      {authWarning && (
        <div className="mb-5 flex items-start gap-3 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30">
          <span className="text-amber-400 text-base leading-none mt-0.5 flex-shrink-0">⚠</span>
          <div>
            <p className="text-sm font-semibold text-amber-300">{t("Auth credentials missing")}</p>
            <p className="text-xs text-amber-400/80 mt-0.5">
              {t("This API uses")} <span className="font-mono font-semibold">{apiAuthType}</span>{" "}
              {t("authentication but no credentials are set. Add them in the Authentication section below before confirming — otherwise the live endpoint test will return Auth Required.")}
            </p>
          </div>
        </div>
      )}

      {/* Failed */}
      {isFailed && (
        <div className="mb-5 p-4 rounded-xl bg-red-500/10 border border-red-500/20">
          <p className="text-sm font-medium text-red-400 mb-1">{t("Processing failed")}</p>
          {session.error_log?.slice(-1).map((e, i) => (
            <p key={i} className="text-xs text-red-400/70 font-mono">{e.step}: {e.error}</p>
          ))}
        </div>
      )}

      {/* Validation errors */}
      {valErrors.length > 0 && (
        <div className="mb-4 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
          <p className="text-sm font-medium text-amber-400 mb-2">{t("Fix before saving:")}</p>
          <ul className="space-y-1">
            {valErrors.map((e, i) => (
              <li key={i} className="text-xs text-amber-400/80 flex items-start gap-1.5">
                <span className="mt-0.5">·</span>{e}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* API test issues — shown when UNREACHABLE / WARNING blocked saving */}
      {hasTestIssues && (
        <div className="mb-5">
          <div className="mb-3 flex items-start gap-3 p-4 rounded-xl bg-orange-500/10 border border-orange-500/30">
            <span className="text-orange-400 text-base leading-none mt-0.5 flex-shrink-0">⚠</span>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-orange-300">{t("Some endpoints could not be reached")}</p>
              <p className="text-xs text-orange-400/80 mt-0.5 leading-relaxed">
                {t("The live test found unreachable or problematic endpoints. Review the results below, then fix the API details and try again — or save anyway if the endpoints are not yet live.")}
              </p>
            </div>
          </div>
          <TestResultsPanel
            results={testResults}
            sessionId={sessionId}
            t={t}
            onDeleteEndpoint={(method, path) => removeEndpointByMethodPath(method, path)}
          />
          <div className="mt-3 flex justify-end">
            <button
              type="button"
              onClick={handleSaveAnyway}
              disabled={saving}
              className="btn-secondary text-sm px-5 py-2"
            >
              {saving ? <><Spinner size={12} /> {t("Saving…")}</> : t("Save Anyway")}
            </button>
          </div>
        </div>
      )}

      {/* Recovery action bar — shown when validation failed, pipeline failed, or test issues */}
      {(valErrors.length > 0 || isFailed || hasTestIssues) && (
        <RecoveryActions
          isFailed={isFailed && !hasTestIssues}
          recovering={recovering}
          confirmDiscard={confirmDiscard}
          onRestart={handleRestart}
          onReupload={() => navigate("/create/upload")}
          onDiscardRequest={() => setConfirmDiscard(true)}
          onDiscardConfirm={handleDiscard}
          onDiscardCancel={() => setConfirmDiscard(false)}
          t={t}
        />
      )}

      <form onSubmit={handleConfirm} className="space-y-5">
        {/* ── Overview ── */}
        <Section title={t("API Overview")}>
          <div className="grid grid-cols-2 gap-3">
            <CField label={t("API Name")} required fkey="name" confidence={confidence} isManual={isManual}>
              <input className="input" value={form?.name || ""} onChange={e => sf("name", e.target.value)} />
            </CField>
            <CField label={t("Version")} fkey="version" confidence={confidence} isManual={isManual}>
              <input className="input" value={form?.version || ""} onChange={e => sf("version", e.target.value)} />
            </CField>
          </div>
          <CField label={t("Base URL")} required fkey="base_url" confidence={confidence} isManual={isManual}>
            <input className="input font-mono" placeholder="https://api.example.com"
              value={form?.base_url || ""} onChange={e => sf("base_url", e.target.value)} />
          </CField>
          <CField label={t("Description")} fkey="description" confidence={confidence} isManual={isManual}>
            <textarea className="input resize-none" rows={2}
              value={form?.description || ""} onChange={e => sf("description", e.target.value)} />
          </CField>
        </Section>

        {/* ── Auth ── */}
        <Section title={t("Authentication")}>
          {/* Mode toggle */}
          <div className="flex p-1 bg-zinc-950 rounded-lg border border-zinc-800 gap-1">
            {[
              { val: "same",         label: t("Same for all endpoints") },
              { val: "per_endpoint", label: t("Per endpoint") },
            ].map(opt => (
              <button key={opt.val} type="button"
                onClick={() => setAuthMode(opt.val)}
                className={`flex-1 py-1.5 text-xs rounded-md font-medium transition-colors ${
                  authMode === opt.val
                    ? "bg-blue-600/20 text-blue-300 border border-blue-500/30"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}>
                {opt.label}
              </button>
            ))}
          </div>

          {authMode === "same" ? (
            <AuthCredFields
              creds={globalAuth}
              onChange={(k, v) => setGlobalAuth(c => ({ ...c, [k]: v }))}
              t={t}
            />
          ) : (
            <p className="text-xs text-zinc-500 pt-1">
              {t("Expand each endpoint below to set its auth type and credentials individually.")}
            </p>
          )}
        </Section>

        {/* ── Endpoints ── */}
        <div>
          <p className="section-title mb-3">
            {t("Endpoints")}
            <span className="text-xs font-normal text-zinc-600 ml-2">
              {form?.endpoints?.length || 0}{t(" defined")}
            </span>
          </p>
          <div className="space-y-4">
            {(form?.endpoints || []).map((ep, ei) => (
              <EndpointReview
                key={ep._id}
                ep={ep} index={ei}
                confidence={confidence}
                isManual={isManual}
                authMode={authMode}
                totalEndpoints={form.endpoints.length}
                t={t}
                onChange={(k, v) => setEp(ei, k, v)}
                onChangeCreds={(k, v) => setEpCreds(ei, k, v)}
                onAddParam={() => addParam(ei)}
                onChangeParam={(pi, k, v) => setParam(ei, pi, k, v)}
                onRemoveParam={(pi) => removeParam(ei, pi)}
                onRemoveEndpoint={() => removeEndpoint(ei)}
              />
            ))}
          </div>
        </div>

        {/* ── Actions ── */}
        {error && <p className="text-xs text-red-400 text-center">{error}</p>}

        {saving && <SavingSteps />}

        <div className="flex gap-3">
          <button type="button" onClick={() => navigate(-1)} className="btn-secondary flex-1 py-2.5">
            {t("Back")}
          </button>
          <button type="submit" disabled={saving || isFailed} className="btn-primary flex-1 py-2.5">
            {saving ? <><Spinner size={13} /> {t("Running…")}</> : t("Confirm & Save")}
          </button>
        </div>
      </form>
    </div>
  );
}

/* ── Recovery action bar ── */
function RecoveryActions({ isFailed, recovering, confirmDiscard, onRestart, onReupload, onDiscardRequest, onDiscardConfirm, onDiscardCancel, t }) {
  return (
    <div className="mb-5 rounded-xl border border-zinc-700/60 bg-zinc-900/60 overflow-hidden">
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center gap-2">
        <span className="text-sm font-semibold text-zinc-200">{t("What would you like to do?")}</span>
      </div>

      <div className="p-4 grid grid-cols-1 gap-2 sm:grid-cols-3">
        {/* Restart pipeline */}
        <button
          type="button"
          disabled={recovering}
          onClick={onRestart}
          className="flex flex-col gap-1 px-4 py-3 rounded-lg bg-blue-600/10 border border-blue-500/25
                     hover:bg-blue-600/20 hover:border-blue-500/50 transition-all text-left disabled:opacity-50"
        >
          <span className="text-sm font-semibold text-blue-300">
            {recovering ? t("Restarting…") : t("Restart Pipeline")}
          </span>
          <span className="text-xs text-blue-400/70 leading-snug">
            {t("Re-run the full AI extraction on the same file from scratch.")}
          </span>
        </button>

        {/* Re-upload different file */}
        <button
          type="button"
          disabled={recovering}
          onClick={onReupload}
          className="flex flex-col gap-1 px-4 py-3 rounded-lg bg-zinc-800/60 border border-zinc-700
                     hover:bg-zinc-800 hover:border-zinc-600 transition-all text-left disabled:opacity-50"
        >
          <span className="text-sm font-semibold text-zinc-200">{t("Re-upload File")}</span>
          <span className="text-xs text-zinc-500 leading-snug">
            {t("Discard this session and upload a different or corrected file.")}
          </span>
        </button>

        {/* Discard */}
        {!confirmDiscard ? (
          <button
            type="button"
            disabled={recovering}
            onClick={onDiscardRequest}
            className="flex flex-col gap-1 px-4 py-3 rounded-lg bg-red-500/5 border border-red-500/20
                       hover:bg-red-500/10 hover:border-red-500/35 transition-all text-left disabled:opacity-50"
          >
            <span className="text-sm font-semibold text-red-400">{t("Discard")}</span>
            <span className="text-xs text-red-400/60 leading-snug">
              {t("Permanently remove this session.")}
            </span>
          </button>
        ) : (
          <div className="flex flex-col gap-2 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30">
            <p className="text-xs font-semibold text-red-300">{t("Confirm discard?")}</p>
            <div className="flex gap-2">
              <button type="button" onClick={onDiscardConfirm}
                className="flex-1 py-1 text-xs rounded-md bg-red-600/25 text-red-300 border border-red-500/30 hover:bg-red-600/40 transition-colors">
                {t("Yes, discard")}
              </button>
              <button type="button" onClick={onDiscardCancel}
                className="flex-1 py-1 text-xs rounded-md bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700 transition-colors">
                {t("Cancel")}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Edit again hint — only shown when validation errors (not pipeline failure) */}
      {!isFailed && (
        <div className="px-4 pb-3">
          <p className="text-xs text-zinc-600">
            {t("Or fix the errors above directly in the form and click")} <span className="text-zinc-400 font-medium">{t("Confirm & Save")}</span> {t("again.")}
          </p>
        </div>
      )}
    </div>
  );
}

/* ── Endpoint review block ── */
function EndpointReview({ ep, index, confidence, isManual, authMode, totalEndpoints, t, onChange, onChangeCreds, onAddParam, onChangeParam, onRemoveParam, onRemoveEndpoint }) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const isLast = totalEndpoints === 1;

  return (
    <div className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="section-label">{t("Endpoints")} {index + 1}</span>
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs text-zinc-600">{ep.method} {ep.path}</span>
          {!confirmDelete ? (
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              title={isLast ? t("At least one endpoint is required") : t("Delete endpoint")}
              disabled={isLast}
              className="text-zinc-600 hover:text-red-400 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <TrashIcon />
            </button>
          ) : (
            <div className="flex items-center gap-1.5 animate-fade-in">
              <span className="text-xs text-red-400">{t("Delete?")}</span>
              <button
                type="button"
                onClick={() => { setConfirmDelete(false); onRemoveEndpoint(); }}
                className="text-xs px-2 py-0.5 rounded bg-red-600/20 text-red-300 border border-red-500/30 hover:bg-red-600/35 transition-colors"
              >
                {t("Yes")}
              </button>
              <button
                type="button"
                onClick={() => setConfirmDelete(false)}
                className="text-xs px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700 transition-colors"
              >
                {t("No")}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="flex gap-2">
        <CField label={t("Method")} fkey={`endpoints.${index}.method`} confidence={confidence} isManual={isManual}>
          <select className="input w-28 font-mono text-xs" value={ep.method}
            onChange={e => onChange("method", e.target.value)}>
            {METHODS.map(m => <option key={m}>{m}</option>)}
          </select>
        </CField>
        <div className="flex-1">
          <CField label={t("Path")} fkey={`endpoints.${index}.path`} confidence={confidence} isManual={isManual}>
            <input className="input font-mono" value={ep.path}
              onChange={e => onChange("path", e.target.value)} />
          </CField>
        </div>
      </div>

      <div className={`grid gap-3 ${authMode === "per_endpoint" ? "grid-cols-1" : "grid-cols-2"}`}>
        <CField label={t("Name")} fkey={`endpoints.${index}.name`} confidence={confidence} isManual={isManual}>
          <input className="input" value={ep.name} onChange={e => onChange("name", e.target.value)} />
        </CField>
        {authMode !== "per_endpoint" && (
          <CField label={t("Auth Override")} fkey={`endpoints.${index}.auth_type`} confidence={confidence} isManual={isManual}>
            <select className="input" value={ep.auth_type} onChange={e => onChange("auth_type", e.target.value)}>
              <option value="">{t("Inherit from API")}</option>
              {AUTH_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </CField>
        )}
      </div>

      {authMode === "per_endpoint" && (
        <div className="rounded-lg border border-zinc-800 p-3 bg-zinc-950/50 space-y-3">
          <p className="text-xs font-medium text-zinc-500">{t("Endpoint Credentials")}</p>
          <AuthCredFields
            creds={ep.auth_creds || EMPTY_CREDS}
            onChange={onChangeCreds}
            t={t}
          />
        </div>
      )}

      <CField label={t("Description")} fkey={`endpoints.${index}.description`} confidence={confidence} isManual={isManual}>
        <textarea className="input resize-none" rows={2}
          value={ep.description} onChange={e => onChange("description", e.target.value)} />
      </CField>

      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-medium text-zinc-500">{t("Parameters")}</p>
          <button type="button" onClick={onAddParam}
            className="text-xs text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1">
            + {t("Add param")}
          </button>
        </div>
        {ep.parameters.length > 0 ? (
          <div className="space-y-1.5">
            <div className="grid grid-cols-[1fr_90px_60px_1fr_20px] gap-2 px-1">
              {[t("Name"), t("Type"), t("Req"), t("Description"), ""].map((h, i) => (
                <span key={i} className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider">{h}</span>
              ))}
            </div>
            {ep.parameters.map((p, pi) => (
              <div key={p._id} className="grid grid-cols-[1fr_90px_60px_1fr_20px] gap-2 items-center">
                <input className="input text-xs py-1.5" value={p.name}
                  onChange={e => onChangeParam(pi, "name", e.target.value)} />
                <select className="input text-xs py-1.5" value={p.type}
                  onChange={e => onChangeParam(pi, "type", e.target.value)}>
                  {TYPES.map(tp => <option key={tp}>{tp}</option>)}
                </select>
                <label className="flex items-center justify-center">
                  <input type="checkbox" checked={p.required}
                    onChange={e => onChangeParam(pi, "required", e.target.checked)}
                    className="accent-blue-500 w-3.5 h-3.5" />
                </label>
                <input className="input text-xs py-1.5" value={p.description}
                  onChange={e => onChangeParam(pi, "description", e.target.value)} />
                <button type="button" onClick={() => onRemoveParam(pi)}
                  className="text-zinc-600 hover:text-red-400 transition-colors">
                  <XIcon />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-zinc-700 italic">{t("No parameters")}</p>
        )}
      </div>
    </div>
  );
}

/* ── Confidence-aware field wrapper ── */
function CField({ label, fkey, required, confidence, isManual, children }) {
  const info = !isManual && confidence?.[fkey];
  const dot  = { HIGH: "bg-emerald-400", MEDIUM: "bg-amber-400", LOW: "bg-red-400", MISSING: "bg-red-500 animate-pulse-dot" };
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-1">
        {info && <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dot[info.status] || "bg-zinc-600"}`} />}
        <label className="text-xs font-medium text-zinc-400">
          {label}{required && <span className="text-red-400 ml-0.5">*</span>}
        </label>
        {info?.suggestion && <span className="text-xs text-zinc-600 truncate">— {info.suggestion}</span>}
      </div>
      {children}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="card p-4 space-y-3">
      <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-0.5">{title}</p>
      {children}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════════════
   Success Panel — shown after SAVED
═══════════════════════════════════════════════════════════════════════════ */
function SuccessPanel({ apiId, session, t }) {
  const [connecting,  setConnecting]  = useState(false);
  const [connected,   setConnected]   = useState(false);
  const [tools,       setTools]       = useState(null);
  const [copied,      setCopied]      = useState(false);
  const apiName    = session?.draft_api?.name || "Your API";
  const toolCount  = session?.draft_api?.endpoints?.length || 0;
  const testResults = session?.api_test_results || [];

  async function handleConnect() {
    setConnecting(true);
    try {
      await chatgptApi.connect(apiId);
      const t = await chatgptApi.getTools(apiId);
      setTools(t.tools);
      setConnected(true);
    } finally {
      setConnecting(false);
    }
  }

  function copySchema() {
    navigator.clipboard.writeText(JSON.stringify(tools, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const mcpChatUrl = "http://localhost:8000/api/chatgpt/chat";
  const toolsUrl   = `http://localhost:8000/api/chatgpt/tools/${apiId}`;

  return (
    <div className="max-w-2xl animate-slide-up">
      {/* Success header */}
      <div className="card p-6 mb-5 border-emerald-500/20 bg-emerald-500/5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20
                          flex items-center justify-center text-emerald-400 text-lg">
            ✓
          </div>
          <div>
            <h1 className="text-lg font-semibold text-zinc-100">{t("MCP Tool Created!")}</h1>
            <p className="text-sm text-zinc-500 mt-0.5">
              <span className="text-zinc-300 font-medium">{apiName}</span>
              {" "}· {toolCount}{toolCount === 1 ? t("1 tool registered") : t(" tools registered")}
            </p>
          </div>
        </div>

        {!connected ? (
          <button
            onClick={handleConnect}
            disabled={connecting}
            className="btn-primary w-full py-2.5"
          >
            {connecting ? <><Spinner size={13} /> {t("Connecting…")}</> : <><PlugIcon /> {t("Connect to ChatGPT")}</>}
          </button>
        ) : (
          <div className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="text-sm text-emerald-300 font-medium">{t("Connected to ChatGPT")}</span>
          </div>
        )}
      </div>

      {/* Test results — always shown */}
      {testResults.length > 0 && (
        <div className="animate-slide-up">
          <TestResultsPanel results={testResults} sessionId={apiId} t={t} />
        </div>
      )}

      {/* Access instructions — shown after connecting */}
      {connected && (
        <div className="space-y-4 animate-slide-up">
          <h2 className="text-sm font-semibold text-zinc-300">{t("How to access this tool")}</h2>

          <AccessOption number="1" title={t("Use MCP Hub Chat (built-in)")} accent="blue">
            <p className="text-xs text-zinc-500 mb-3">
              {t("The simplest way — open the ChatGPT Tools page, type your question, and MCP Hub will route it through your connected tools automatically.")}
            </p>
            <Link to="/chatgpt" className="btn-secondary text-xs px-4 py-2 inline-flex">
              {t("Open ChatGPT Tools →")}
            </Link>
          </AccessOption>

          <AccessOption number="2" title={t("Call via HTTP (any language)")} accent="zinc">
            <p className="text-xs text-zinc-500 mb-2">
              {t("POST a message to MCP Hub's chat endpoint. It handles tool selection and execution.")}
            </p>
            <CodeBlock code={`import requests

response = requests.post(
    "${mcpChatUrl}",
    json={"message": "your question here"}
)
result = response.json()
print(result["response"])
# Tool calls are in result["tool_calls"]`} />
          </AccessOption>

          <AccessOption number="3" title={t("Direct OpenAI integration")} accent="zinc">
            <p className="text-xs text-zinc-500 mb-2">
              {t("Fetch the OpenAI-format tool schema from MCP Hub and pass it to your own ChatGPT API call.")}
            </p>
            <CodeBlock code={`import openai, requests

# 1. Get tool schema from MCP Hub
tools = requests.get("${toolsUrl}").json()["tools"]

# 2. Call ChatGPT with the tools
client = openai.OpenAI(api_key="sk-...")
resp = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "your question"}],
    tools=tools,
    tool_choice="auto"
)

# 3. If tool_calls in response, forward execution to MCP Hub:
# POST ${mcpChatUrl} with {"message": "..."}
# MCP Hub handles the full execution loop.`} />
          </AccessOption>

          {/* Copy schema */}
          {tools && (
            <div className="card p-4">
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                  {t("OpenAI Tool Schema")}
                </p>
                <button onClick={copySchema}
                  className="btn-ghost text-xs px-3 py-1.5 gap-1.5">
                  {copied ? <><CheckIcon /> {t("Copied!")}</> : <><CopyIcon /> {t("Copy JSON")}</>}
                </button>
              </div>
              <pre className="text-xs font-mono text-zinc-500 overflow-x-auto max-h-48">
                {JSON.stringify(tools, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Footer links */}
      <div className="flex gap-3 mt-5">
        <Link to="/registry" className="btn-secondary flex-1 py-2 text-center">
          {t("View in Registry")}
        </Link>
        <Link to="/chatgpt" className="btn-secondary flex-1 py-2 text-center">
          {t("ChatGPT Tools")}
        </Link>
      </div>
    </div>
  );
}

/* ── Saving steps inline progress ── */
function SavingSteps() {
  const { t } = useLanguage();
  const [step, setStep] = useState(0);
  const steps = [
    { label: t("Validating schema"),     icon: "◈" },
    { label: t("Testing API endpoints"), icon: "⟳" },
    { label: t("Saving MCP tool"),       icon: "↓" },
  ];
  useEffect(() => {
    const t1 = setTimeout(() => setStep(1), 800);
    const t2 = setTimeout(() => setStep(2), 2200);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  return (
    <div className="card p-3 animate-fade-in">
      <div className="flex items-center gap-4">
        {steps.map((s, i) => (
          <div key={i} className={`flex items-center gap-1.5 text-xs transition-colors
                                   ${i < step ? "text-emerald-400" : i === step ? "text-zinc-300" : "text-zinc-700"}`}>
            <span className={i === step ? "animate-spin-slow" : ""}>{i < step ? "✓" : s.icon}</span>
            {s.label}
            {i < steps.length - 1 && <span className="text-zinc-700 ml-2">→</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Test Results panel (shown inside SuccessPanel) ── */
function TestResultsPanel({ results, sessionId, t, onDeleteEndpoint }) {
  if (!results || results.length === 0) return null;

  const verdictStyle = {
    PASS:          { dot: "bg-emerald-400", text: "text-emerald-400", label: t("Pass") },
    AUTH_REQUIRED: { dot: "bg-amber-400",   text: "text-amber-400",  label: t("Auth Required") },
    WARNING:       { dot: "bg-orange-400",  text: "text-orange-400", label: t("Warning") },
    UNREACHABLE:   { dot: "bg-red-400",     text: "text-red-400",    label: t("Unreachable") },
    SKIPPED:       { dot: "bg-zinc-600",    text: "text-zinc-500",   label: t("Skipped") },
  };

  const hasAuthRequired = results.some(r => r.verdict === "AUTH_REQUIRED");

  return (
    <div className="card p-4">
      <p className="section-label mb-3">
        {t("Live API Test Results")}
      </p>

      {hasAuthRequired && (
        <div className="mb-3 flex items-start gap-2.5 px-3 py-2.5 rounded-lg
                        bg-amber-500/10 border border-amber-500/25">
          <span className="text-amber-400 text-sm leading-none mt-0.5 flex-shrink-0">⚠</span>
          <div className="min-w-0">
            <p className="text-xs font-semibold text-amber-300">{t("Auth Required — endpoints need credentials")}</p>
            <p className="text-[11px] text-amber-400/70 mt-0.5 leading-relaxed">
              {t("The live test could not authenticate. To fix: re-upload the document and add credentials on the Review & Validate page before confirming, or update them in the API Registry.")}
            </p>
          </div>
        </div>
      )}

      <div className="space-y-2">
        {results.map((r, i) => {
          const s = verdictStyle[r.verdict] || verdictStyle.WARNING;
          return (
            <TestResultRow
              key={i}
              result={r}
              style={s}
              onDelete={onDeleteEndpoint
                ? () => onDeleteEndpoint(r.method, r.path)
                : null}
            />
          );
        })}
      </div>
    </div>
  );
}

function TestResultRow({ result, style, onDelete }) {
  const [open,          setOpen]          = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  return (
    <div className="rounded-lg bg-zinc-950 border border-zinc-800 overflow-hidden">
      <div className="flex items-center">
        <button
          onClick={() => setOpen(o => !o)}
          className="flex-1 flex items-center gap-3 px-3 py-2.5 text-left hover:bg-zinc-900 transition-colors min-w-0"
        >
          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${style.dot}`} />
          <span className="flex-1 text-xs text-zinc-300 font-medium truncate">
            {result.endpoint_name}
          </span>
          <span className="font-mono text-xs text-zinc-600">{result.method}</span>
          <span className={`text-xs font-semibold ${style.text} flex-shrink-0`}>
            {style.label}
          </span>
          {result.duration_ms && (
            <span className="text-xs text-zinc-600 flex-shrink-0">{result.duration_ms}ms</span>
          )}
          <ChevronSmIcon open={open} />
        </button>

        {onDelete && (
          <div className="flex items-center gap-1.5 px-2 flex-shrink-0">
            {!confirmDelete ? (
              <button
                type="button"
                onClick={() => setConfirmDelete(true)}
                title="Remove endpoint"
                className="text-zinc-700 hover:text-red-400 transition-colors p-1"
              >
                <TrashIcon />
              </button>
            ) : (
              <div className="flex items-center gap-1 animate-fade-in">
                <span className="text-[10px] text-red-400">Remove?</span>
                <button
                  type="button"
                  onClick={() => { setConfirmDelete(false); onDelete(); }}
                  className="text-[10px] px-1.5 py-0.5 rounded bg-red-600/20 text-red-300 border border-red-500/30 hover:bg-red-600/35 transition-colors"
                >
                  Yes
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmDelete(false)}
                  className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700 transition-colors"
                >
                  No
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {open && (
        <div className="border-t border-zinc-800 px-3 py-3 space-y-2 animate-fade-in text-xs">
          {result.assessment && (
            <p className="text-zinc-400">{result.assessment}</p>
          )}
          {result.skip_reason && (
            <p className="text-zinc-600 italic">{result.skip_reason}</p>
          )}
          {result.url_tested && (
            <p className="font-mono text-zinc-600 truncate">{result.url_tested}</p>
          )}
          {result.test_params && Object.keys(result.test_params).length > 0 && (
            <div>
              <p className="text-zinc-600 mb-1">Test params</p>
              <pre className="font-mono text-zinc-500 overflow-x-auto">
                {JSON.stringify(result.test_params, null, 2)}
              </pre>
            </div>
          )}
          {result.response_preview && (
            <div>
              <p className="text-zinc-600 mb-1">Response preview</p>
              <pre className="font-mono text-zinc-500 overflow-x-auto max-h-28">
                {result.response_preview}
              </pre>
            </div>
          )}
          {result.issues?.length > 0 && (
            <ul className="space-y-0.5">
              {result.issues.map((iss, j) => (
                <li key={j} className="text-orange-400 flex gap-1.5">
                  <span>·</span>{iss}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function ChevronSmIcon({ open }) {
  return (
    <svg width="11" height="11" viewBox="0 0 15 15" fill="none"
      className={`text-zinc-600 transition-transform flex-shrink-0 ${open ? "rotate-180" : ""}`}>
      <path d="M3 5l4.5 5L12 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

function AccessOption({ number, title, accent, children }) {
  const border = { blue: "border-blue-500/20", zinc: "border-zinc-800" };
  return (
    <div className={`card p-4 border ${border[accent] || "border-zinc-800"}`}>
      <div className="flex items-center gap-2 mb-3">
        <span className="w-5 h-5 rounded-full bg-zinc-800 border border-zinc-700
                         flex items-center justify-center text-[10px] font-bold text-zinc-400">
          {number}
        </span>
        <p className="text-sm font-medium text-zinc-200">{title}</p>
      </div>
      {children}
    </div>
  );
}

function CodeBlock({ code }) {
  const { t } = useLanguage();
  const [copied, setCopied] = useState(false);
  function copy() {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }
  return (
    <div className="relative rounded-lg bg-zinc-950 border border-zinc-800 overflow-hidden">
      <button onClick={copy}
        className="absolute top-2 right-2 text-xs text-zinc-600 hover:text-zinc-300
                   bg-zinc-900 border border-zinc-700 rounded px-2 py-1 transition-colors">
        {copied ? t("Copied!") : t("Copy")}
      </button>
      <pre className="text-xs font-mono text-zinc-400 p-4 pr-16 overflow-x-auto">{code}</pre>
    </div>
  );
}

/* ── Auth credential fields ── */
function AuthCredFields({ creds, onChange, t }) {
  const fields = AUTH_CRED_FIELDS[creds.type] || [];
  const cols   = fields.length === 1 ? "grid-cols-1" : "grid-cols-2";

  return (
    <div className="space-y-3">
      {/* Auth type selector */}
      <div>
        <label className="text-xs font-medium text-zinc-400 block mb-1">{t("Auth Type")}</label>
        <select
          className="input"
          value={creds.type}
          onChange={e => onChange("type", e.target.value)}
        >
          {AUTH_OPTS.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {/* No auth hint */}
      {creds.type === "none" && (
        <p className="text-xs text-zinc-600 italic">
          {t("Select an auth type above to configure credentials.")}
        </p>
      )}

      {/* Credential fields — only shown when type is not none */}
      {fields.length > 0 && (
        <div className={`grid ${cols} gap-3 p-3 rounded-lg bg-zinc-950 border border-zinc-800 animate-fade-in`}>
          {fields.map(f => (
            <div key={f.key}>
              <label className="text-xs font-medium text-zinc-400 block mb-1">{f.label}</label>
              <SecretInput
                value={creds[f.key] || ""}
                onChange={v => onChange(f.key, v)}
                placeholder={f.placeholder || ""}
                isSecret={f.secret}
              />
            </div>
          ))}
        </div>
      )}

      {creds.type !== "none" && (
        <p className="text-xs text-zinc-600">
          {t("Credentials are stored securely and used for live endpoint testing.")}
        </p>
      )}
    </div>
  );
}

function SecretInput({ value, onChange, placeholder, isSecret }) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <input
        type={isSecret && !show ? "password" : "text"}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete="off"
        className="input w-full pr-8"
      />
      {isSecret && (
        <button type="button" onClick={() => setShow(s => !s)}
          className="absolute right-2.5 top-1/2 -translate-y-1/2
                     text-zinc-600 hover:text-zinc-400 transition-colors">
          {show ? <EyeOffIcon /> : <EyeIcon />}
        </button>
      )}
    </div>
  );
}

/* ── Processing / Error pages ── */
function ProcessingPage({ state, t }) {
  return (
    <div className="flex flex-col items-center justify-center py-32 text-center animate-fade-in">
      <div className="w-12 h-12 rounded-xl bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-5">
        <Spinner size={20} />
      </div>
      <p className="text-zinc-200 font-medium mb-1">{t(STATE_LABEL_KEYS[state]) || state}</p>
      <p className="text-zinc-600 text-sm">{t("This usually takes a few seconds")}</p>
      <div className="flex gap-1.5 mt-5">
        {["CLASSIFYING","PARSING","SCHEMA_GENERATING","RECONCILING","CONFIDENCE_SCORING"].map(s => (
          <div key={s} className={`w-1.5 h-1.5 rounded-full transition-colors ${s === state ? "bg-blue-400 animate-pulse-dot" : "bg-zinc-700"}`} />
        ))}
      </div>
    </div>
  );
}

function ErrorPage({ message, t }) {
  return (
    <div className="flex flex-col items-center justify-center py-32 text-center">
      <div className="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-4 text-red-400 text-lg">
        ✕
      </div>
      <p className="text-red-400 font-medium mb-1">{t("Error")}</p>
      <p className="text-zinc-500 text-sm">{message}</p>
    </div>
  );
}

/* ── Icons ── */
function EyeIcon() {
  return <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" stroke="currentColor" strokeWidth="1.8"/><circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.8"/></svg>;
}
function EyeOffIcon() {
  return <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19M1 1l22 22" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>;
}
function XIcon() {
  return <svg width="12" height="12" viewBox="0 0 15 15" fill="none"><path d="M3 3l9 9M12 3l-9 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>;
}
function TrashIcon() {
  return <svg width="13" height="13" viewBox="0 0 15 15" fill="none"><path d="M5 1h5M2 3h11M4 3l.8 9.5a1 1 0 0 0 1 .5h4.4a1 1 0 0 0 1-.5L12 3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}
function PlugIcon() {
  return <svg width="14" height="14" viewBox="0 0 15 15" fill="none"><path d="M5 1v3M10 1v3M3 7h9M4 4h7v3a3.5 3.5 0 0 1-7 0V4Z" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/><path d="M7.5 10.5v3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>;
}
function CopyIcon() {
  return <svg width="12" height="12" viewBox="0 0 15 15" fill="none"><rect x="2" y="4" width="9" height="10" rx="1" stroke="currentColor" strokeWidth="1.3"/><path d="M5 4V3a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1h-1" stroke="currentColor" strokeWidth="1.3"/></svg>;
}
function CheckIcon() {
  return <svg width="12" height="12" viewBox="0 0 15 15" fill="none"><path d="M2.5 8l4 4 6-7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}
