import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { agentApi } from "../lib/api";
import Spinner from "../components/Spinner";
import { useLanguage } from "../context/LanguageContext";

const METHODS   = ["GET", "POST", "PUT", "PATCH", "DELETE"];
const TYPES     = ["string", "number", "integer", "boolean", "object", "array"];
const AUTH_OPTS = [
  { value: "none",          label: "None" },
  { value: "api_key",       label: "API Key (header)" },
  { value: "api_key_query", label: "API Key (query param)" },
  { value: "bearer",        label: "Bearer Token" },
  { value: "basic",         label: "Basic Auth" },
  { value: "oauth2",        label: "OAuth 2.0" },
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

function uid() { return Math.random().toString(36).slice(2, 9); }
function emptyEndpoint() {
  return { _id: uid(), method: "GET", path: "", name: "", description: "", auth_type: "", parameters: [] };
}
function emptyParam() {
  return { _id: uid(), name: "", type: "string", required: false, description: "" };
}
function initForm() {
  return {
    name: "", description: "", base_url: "", version: "1.0.0",
    auth_type: "none", auth_header: "",
    auth_creds: { ...EMPTY_CREDS },
    endpoints: [emptyEndpoint()],
  };
}

export default function ChatBuilder() {
  const { t } = useLanguage();
  const [form,     setForm]     = useState(initForm);
  const [loading,  setLoading]  = useState(false);
  const [errors,   setErrors]   = useState({});
  const [apiError, setApiError] = useState(null);
  const navigate = useNavigate();

  function sf(key, val) { setForm(f => ({ ...f, [key]: val })); }
  function setEp(i, key, val) {
    setForm(f => { const eps = [...f.endpoints]; eps[i] = { ...eps[i], [key]: val }; return { ...f, endpoints: eps }; });
  }
  function addEndpoint() {
    setForm(f => ({ ...f, endpoints: [...f.endpoints, emptyEndpoint()] }));
  }
  function removeEndpoint(i) {
    setForm(f => ({ ...f, endpoints: f.endpoints.filter((_, idx) => idx !== i) }));
  }
  function setParam(ei, pi, key, val) {
    setForm(f => {
      const eps = [...f.endpoints]; const params = [...eps[ei].parameters];
      params[pi] = { ...params[pi], [key]: val };
      eps[ei] = { ...eps[ei], parameters: params };
      return { ...f, endpoints: eps };
    });
  }
  function addParam(ei) {
    setForm(f => {
      const eps = [...f.endpoints];
      eps[ei] = { ...eps[ei], parameters: [...eps[ei].parameters, emptyParam()] };
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

  function validate() {
    const e = {};
    if (!form.name.trim())     e.name     = t("API name is required");
    if (!form.base_url.trim()) e.base_url = t("Base URL is required");
    if (form.endpoints.length === 0) e.endpoints = t("Add at least one endpoint");
    form.endpoints.forEach((ep, i) => {
      if (!ep.path.trim()) e[`ep_path_${i}`] = t("Path is required");
    });
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);
    setApiError(null);
    try {
      const authCreds = form.auth_creds;
      const session = await agentApi.manual({
        name:        form.name,
        description: form.description,
        base_url:    form.base_url,
        version:     form.version || "1.0.0",
        auth_type:   authCreds.type !== "none" ? authCreds.type : form.auth_type,
        auth_header: authCreds.header_name || form.auth_header,
        auth_credentials: authCreds.type !== "none" ? authCreds : null,
        endpoints:   form.endpoints.map(ep => ({
          method: ep.method, path: ep.path, name: ep.name,
          description: ep.description, auth_type: ep.auth_type,
          parameters: ep.parameters.map(p => ({
            name: p.name, type: p.type, required: p.required, description: p.description,
          })).filter(p => p.name.trim()),
        })),
      });
      navigate(`/validate/${session.id}`);
    } catch (err) {
      setApiError(err.response?.data?.detail || t("Something went wrong."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-3xl animate-slide-up">
      <div className="mb-7">
        <h1 className="page-title">{t("API Builder")}</h1>
        <p className="page-subtitle mt-1">
          {t("Define your API endpoints. MCP Hub will register them as callable tools.")}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">

        {/* ── Overview ── */}
        <Section title={t("API Overview")}>
          <div className="grid grid-cols-2 gap-3">
            <FormField label={t("API Name")} required error={errors.name}>
              <input className={`input ${errors.name ? "border-red-500/60" : ""}`}
                placeholder={t("e.g. Weather Service")} value={form.name}
                onChange={e => sf("name", e.target.value)} />
            </FormField>
            <FormField label={t("Version")}>
              <input className="input" placeholder="1.0.0" value={form.version}
                onChange={e => sf("version", e.target.value)} />
            </FormField>
          </div>
          <FormField label={t("Base URL")} required error={errors.base_url}>
            <input className={`input font-mono ${errors.base_url ? "border-red-500/60" : ""}`}
              placeholder="https://api.example.com" value={form.base_url}
              onChange={e => sf("base_url", e.target.value)} />
          </FormField>
          <FormField label={t("Description")}>
            <textarea className="input resize-none" rows={2}
              placeholder={t("What does this API do?")}
              value={form.description} onChange={e => sf("description", e.target.value)} />
          </FormField>
        </Section>

        {/* ── Auth ── */}
        <Section title={t("Authentication")}>
          <AuthCredFields
            creds={form.auth_creds}
            onChange={(k, v) => sf("auth_creds", { ...form.auth_creds, [k]: v })}
            t={t}
          />
        </Section>

        {/* ── Endpoints ── */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <p className="section-title">{t("Endpoints")}</p>
              {errors.endpoints && (
                <span className="text-red-400 text-xs">{errors.endpoints}</span>
              )}
            </div>
            <button type="button" onClick={addEndpoint}
              className="btn-secondary text-xs px-3 py-1.5 gap-1">
              <PlusIcon /> {t("Add Endpoint")}
            </button>
          </div>
          <div className="space-y-3">
            {form.endpoints.map((ep, ei) => (
              <EndpointBlock
                key={ep._id}
                ep={ep} index={ei} errors={errors} t={t}
                onChange={(k, v) => setEp(ei, k, v)}
                onRemove={() => removeEndpoint(ei)}
                canRemove={form.endpoints.length > 1}
                onAddParam={() => addParam(ei)}
                onChangeParam={(pi, k, v) => setParam(ei, pi, k, v)}
                onRemoveParam={pi => removeParam(ei, pi)}
              />
            ))}
          </div>
        </div>

        {/* ── Submit ── */}
        {apiError && (
          <div className="flex items-start gap-2 px-4 py-3 rounded-lg
                          bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            <span className="mt-0.5 flex-shrink-0">⚠</span>{apiError}
          </div>
        )}

        <button type="submit" disabled={loading} className="btn-primary w-full py-2.5">
          {loading
            ? <><Spinner size={14} /> {t("Creating MCP Tool…")}</>
            : <><ToolIcon /> {t("Create MCP Tool")}</>
          }
        </button>
      </form>
    </div>
  );
}

function EndpointBlock({ ep, index, errors, t, onChange, onRemove, canRemove, onAddParam, onChangeParam, onRemoveParam }) {
  const methodColors = {
    GET: "text-blue-400", POST: "text-emerald-400", PUT: "text-amber-400",
    PATCH: "text-orange-400", DELETE: "text-red-400",
  };
  return (
    <div className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-zinc-600 uppercase tracking-wider">
            {t("Endpoints")} {index + 1}
          </span>
          {ep.method && (
            <span className={`text-xs font-mono font-semibold ${methodColors[ep.method] || "text-zinc-400"}`}>
              {ep.method}
            </span>
          )}
        </div>
        {canRemove && (
          <button type="button" onClick={onRemove}
            className="text-xs text-zinc-600 hover:text-red-400 transition-colors px-2 py-1 rounded hover:bg-red-500/10">
            {t("Remove")}
          </button>
        )}
      </div>

      {/* Method + Path */}
      <div className="flex gap-2">
        <select
          className="input w-28 font-mono text-xs flex-shrink-0 font-semibold"
          value={ep.method}
          onChange={e => onChange("method", e.target.value)}>
          {METHODS.map(m => <option key={m}>{m}</option>)}
        </select>
        <div className="flex-1">
          <input
            className={`input font-mono ${errors[`ep_path_${index}`] ? "border-red-500/60" : ""}`}
            placeholder={t("/path/{param}")}
            value={ep.path}
            onChange={e => onChange("path", e.target.value)} />
          {errors[`ep_path_${index}`] && (
            <p className="text-xs text-red-400 mt-1">{errors[`ep_path_${index}`]}</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <FormField label={t("Endpoint Name")}>
          <input className="input" placeholder={t("e.g. Get Forecast")}
            value={ep.name} onChange={e => onChange("name", e.target.value)} />
        </FormField>
        <FormField label={t("Auth Override")}>
          <select className="input" value={ep.auth_type}
            onChange={e => onChange("auth_type", e.target.value)}>
            <option value="">{t("Inherit from API")}</option>
            {AUTH_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </FormField>
      </div>

      <FormField label={t("Description")}>
        <textarea className="input resize-none" rows={2}
          placeholder={t("What does this endpoint do?")}
          value={ep.description} onChange={e => onChange("description", e.target.value)} />
      </FormField>

      {/* Parameters */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-medium text-zinc-500">{t("Parameters")}</p>
          <button type="button" onClick={onAddParam}
            className="text-xs text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1">
            <PlusIcon size={10} /> {t("Add param")}
          </button>
        </div>

        {ep.parameters.length > 0 && (
          <div className="space-y-1.5">
            <div className="grid grid-cols-[1fr_90px_60px_1fr_20px] gap-2 px-1">
              {[t("Name"), t("Type"), t("Req"), t("Description"), ""].map((h, i) => (
                <span key={i} className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider">{h}</span>
              ))}
            </div>
            {ep.parameters.map((p, pi) => (
              <div key={p._id} className="grid grid-cols-[1fr_90px_60px_1fr_20px] gap-2 items-center">
                <input className="input text-xs py-1.5" placeholder={t("param_name")}
                  value={p.name} onChange={e => onChangeParam(pi, "name", e.target.value)} />
                <select className="input text-xs py-1.5" value={p.type}
                  onChange={e => onChangeParam(pi, "type", e.target.value)}>
                  {TYPES.map(t => <option key={t}>{t}</option>)}
                </select>
                <label className="flex items-center justify-center gap-1.5 cursor-pointer">
                  <input type="checkbox" checked={p.required}
                    onChange={e => onChangeParam(pi, "required", e.target.checked)}
                    className="accent-blue-500 w-3.5 h-3.5" />
                </label>
                <input className="input text-xs py-1.5" placeholder={t("Brief description")}
                  value={p.description} onChange={e => onChangeParam(pi, "description", e.target.value)} />
                <button type="button" onClick={() => onRemoveParam(pi)}
                  className="text-zinc-600 hover:text-red-400 transition-colors flex items-center justify-center">
                  <XIcon />
                </button>
              </div>
            ))}
          </div>
        )}

        {ep.parameters.length === 0 && (
          <p className="text-xs text-zinc-700 italic">{t("No parameters — click \"Add param\" to add one")}</p>
        )}
      </div>
    </div>
  );
}

function AuthCredFields({ creds, onChange, t }) {
  const fields = AUTH_CRED_FIELDS[creds.type] || [];
  const cols   = fields.length === 1 ? "grid-cols-1" : "grid-cols-2";
  return (
    <div className="space-y-3">
      <FormField label={t("Auth Type")}>
        <select className="input" value={creds.type}
          onChange={e => onChange("type", e.target.value)}>
          {AUTH_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </FormField>
      {creds.type === "none" && (
        <p className="text-xs text-zinc-600 italic">
          {t("Select an auth type above to configure credentials.")}
        </p>
      )}
      {fields.length > 0 && (
        <div className={`grid ${cols} gap-3 p-3 rounded-lg bg-zinc-950/60 border border-zinc-800`}>
          {fields.map(f => (
            <FormField key={f.key} label={f.label}>
              <SecretInput
                value={creds[f.key] || ""}
                onChange={v => onChange(f.key, v)}
                placeholder={f.placeholder || ""}
                isSecret={f.secret}
              />
            </FormField>
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
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-400 transition-colors">
          {show
            ? <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19M1 1l22 22" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>
            : <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" stroke="currentColor" strokeWidth="1.8"/><circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.8"/></svg>
          }
        </button>
      )}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="card p-4 space-y-3">
      <p className="section-label mb-0.5">{title}</p>
      {children}
    </div>
  );
}

function FormField({ label, required, error, children }) {
  return (
    <div>
      <label className="block text-xs font-medium text-zinc-400 mb-1.5">
        {label}{required && <span className="text-red-400 ml-0.5">*</span>}
      </label>
      {children}
      {error && <p className="text-xs text-red-400 mt-1">{error}</p>}
    </div>
  );
}

function PlusIcon({ size = 12 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 15 15" fill="none">
      <path d="M7.5 2v11M2 7.5h11" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
    </svg>
  );
}
function XIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 15 15" fill="none">
      <path d="M3 3l9 9M12 3l-9 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}
function ToolIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 15 15" fill="none">
      <path d="M5 1a4 4 0 0 0 0 8h.5L10 13.5a1.5 1.5 0 0 0 2-2L7.5 7V6.5A4 4 0 0 0 5 1Z"
        stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
    </svg>
  );
}
