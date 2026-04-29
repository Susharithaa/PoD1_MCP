import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { registryApi, agentApi } from "../lib/api";
import { STAGE_LABELS, PIPELINE_STAGES } from "../context/UploadContext";

/* ── constants ──────────────────────────────────────────────────────────────── */
const METHOD_COLORS = {
  GET:    { text: "#22c55e", bg: "rgba(34,197,94,0.08)",   border: "rgba(34,197,94,0.25)" },
  POST:   { text: "#3b82f6", bg: "rgba(59,130,246,0.08)",  border: "rgba(59,130,246,0.25)" },
  PUT:    { text: "#f59e0b", bg: "rgba(245,158,11,0.08)",  border: "rgba(245,158,11,0.25)" },
  PATCH:  { text: "#a78bfa", bg: "rgba(167,139,250,0.08)", border: "rgba(167,139,250,0.25)" },
  DELETE: { text: "#ef4444", bg: "rgba(239,68,68,0.08)",   border: "rgba(239,68,68,0.25)" },
};
const AUTH_TYPES   = ["NONE", "BEARER", "API_KEY", "BASIC"];
const HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"];
const PARAM_TYPES  = ["string", "integer", "number", "boolean", "array", "object"];
const ACCEPTED_EXTS = ".json,.yaml,.yml,.pdf,.txt,.md,.docx";

/* ── schema helpers ─────────────────────────────────────────────────────────── */
function schemaToParams(schema) {
  if (!schema || typeof schema !== "object") return [];
  const props = schema.properties || {};
  const req   = schema.required   || [];
  return Object.entries(props).map(([name, def]) => ({
    name,
    type:        def.type        || "string",
    required:    req.includes(name),
    description: def.description || "",
  }));
}
function paramsToSchema(params) {
  const properties = {};
  const required   = [];
  for (const p of params) {
    if (!p.name.trim()) continue;
    properties[p.name.trim()] = { type: p.type, description: p.description };
    if (p.required) required.push(p.name.trim());
  }
  return { type: "object", properties, ...(required.length ? { required } : {}) };
}
function blankEndpoint() {
  return { name: "", description: "", path: "", method: "GET", auth_type: "NONE", params: [] };
}

/* ══════════════════════════════════════════════════════════════════════════════
   ToolDetail page
══════════════════════════════════════════════════════════════════════════════ */
export default function ToolDetail() {
  const { id }   = useParams();
  const navigate = useNavigate();

  const [api,         setApi]         = useState(null);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState(null);
  const [meta,        setMeta]        = useState({ name: "", description: "", base_url: "", version: "" });
  const [metaDirty,   setMetaDirty]   = useState(false);
  const [metaSaving,  setMetaSaving]  = useState(false);
  const [globalAuth,  setGlobalAuth]  = useState("NONE");
  const [authApplying,setAuthApplying]= useState(false);
  const [endpoints,   setEndpoints]   = useState([]);

  // add-mode: null | "picker" | "manual" | "doc"
  const [addMode,     setAddMode]     = useState(null);
  const [newEp,       setNewEp]       = useState(blankEndpoint);
  const [epSaving,    setEpSaving]    = useState(null);
  const [expandedEp,  setExpandedEp]  = useState(null);
  const [editingEp,   setEditingEp]   = useState(null);
  const [epDeleting,  setEpDeleting]  = useState(null);
  const [deleteTarget,setDeleteTarget]= useState(null);

  useEffect(() => { loadApi(); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function loadApi() {
    try {
      setLoading(true); setError(null);
      const data = await registryApi.get(id);
      applyApiState(data);
    } catch { setError("Failed to load API."); }
    finally  { setLoading(false); }
  }

  function applyApiState(data) {
    setApi(data);
    setMeta({ name: data.name || "", description: data.description || "", base_url: data.base_url || "", version: data.version || "1.0.0" });
    const eps = data.endpoints || [];
    setEndpoints(eps);
    if (eps.length) {
      const types  = eps.map(e => e.auth_type).filter(Boolean);
      const counts = types.reduce((m, t) => { m[t] = (m[t] || 0) + 1; return m; }, {});
      setGlobalAuth(Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || "NONE");
    }
    setMetaDirty(false);
  }

  async function saveMeta() {
    try { setMetaSaving(true); const u = await registryApi.update(id, meta); applyApiState(u); }
    catch { alert("Failed to save changes."); }
    finally { setMetaSaving(false); }
  }

  async function applyGlobalAuth() {
    try { setAuthApplying(true); const u = await registryApi.updateAuth(id, globalAuth); applyApiState(u); }
    catch { alert("Failed to update auth."); }
    finally { setAuthApplying(false); }
  }

  async function confirmDelete() {
    if (deleteTarget === "__api__") {
      try { await registryApi.delete(id); navigate("/registry"); }
      catch { alert("Failed to delete tool."); }
    } else {
      try {
        setEpDeleting(deleteTarget);
        await registryApi.deleteEndpoint(id, deleteTarget);
        setEndpoints(prev => prev.filter(e => e.id !== deleteTarget));
      } catch { alert("Failed to delete endpoint."); }
      finally  { setEpDeleting(null); }
    }
    setDeleteTarget(null);
  }

  async function saveManualEndpoint(draft) {
    const payload = { name: draft.name, description: draft.description, path: draft.path,
      method: draft.method, auth_type: draft.auth_type,
      input_schema: paramsToSchema(draft.params),
      output_schema: { type: "object", properties: {} }, headers: [] };
    try {
      setEpSaving("__new__");
      const created = await registryApi.createEndpoint(id, payload);
      setEndpoints(prev => [...prev, created]);
      setAddMode(null);
      setNewEp(blankEndpoint());
    } catch { alert("Failed to save endpoint."); }
    finally  { setEpSaving(null); }
  }

  async function saveEditedEndpoint(epId, draft) {
    const payload = { name: draft.name, description: draft.description, path: draft.path,
      method: draft.method, auth_type: draft.auth_type,
      input_schema: paramsToSchema(draft.params),
      output_schema: { type: "object", properties: {} }, headers: [] };
    try {
      setEpSaving(epId);
      const updated = await registryApi.updateEndpoint(id, epId, payload);
      setEndpoints(prev => prev.map(e => e.id === epId ? updated : e));
      setEditingEp(null);
      setExpandedEp(epId);
    } catch { alert("Failed to save endpoint."); }
    finally  { setEpSaving(null); }
  }

  function handleDocImported(newEndpoints) {
    setEndpoints(prev => [...prev, ...newEndpoints]);
    setAddMode(null);
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full" />
    </div>
  );
  if (error) return (
    <div className="text-center py-16">
      <p className="text-red-400 mb-4">{error}</p>
      <button onClick={() => navigate("/registry")} className="text-blue-400 hover:underline text-sm">← Back to Registry</button>
    </div>
  );

  return (
    <div className="max-w-5xl mx-auto animate-slide-up">
      {/* Breadcrumb */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2 text-sm text-zinc-500">
          <Link to="/registry" className="hover:text-zinc-300 transition-colors flex items-center gap-1">
            <BackIcon /> API Registry
          </Link>
          <ChevronRightSmIcon />
          <span className="text-zinc-300 font-medium truncate max-w-xs">{meta.name || api?.name}</span>
        </div>
        <button onClick={() => setDeleteTarget("__api__")}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-red-400 border border-red-500/20 hover:bg-red-500/10 transition-colors">
          <TrashIcon /> Delete Tool
        </button>
      </div>

      {/* Tool Info */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 mb-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Tool Info</h2>
          {metaDirty && (
            <button onClick={saveMeta} disabled={metaSaving}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50">
              {metaSaving ? "Saving…" : "Save Changes"}
            </button>
          )}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Name">
            <input value={meta.name} onChange={e => { setMeta(m => ({...m, name: e.target.value})); setMetaDirty(true); }} className="field-input" />
          </Field>
          <Field label="Base URL">
            <input value={meta.base_url} onChange={e => { setMeta(m => ({...m, base_url: e.target.value})); setMetaDirty(true); }} className="field-input font-mono" placeholder="https://api.example.com" />
          </Field>
          <Field label="Description">
            <textarea value={meta.description} onChange={e => { setMeta(m => ({...m, description: e.target.value})); setMetaDirty(true); }} rows={2} className="field-input resize-none" />
          </Field>
          <Field label="Version">
            <input value={meta.version} onChange={e => { setMeta(m => ({...m, version: e.target.value})); setMetaDirty(true); }} className="field-input" placeholder="1.0.0" />
          </Field>
        </div>
      </div>

      {/* Auth */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 mb-4">
        <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-4">Authentication</h2>
        <div className="flex items-end gap-3">
          <div className="flex-1 max-w-xs">
            <label className="block text-[10px] text-zinc-500 mb-1.5 uppercase tracking-wider">Auth Type</label>
            <select value={globalAuth} onChange={e => setGlobalAuth(e.target.value)} className="field-input">
              {AUTH_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <button onClick={applyGlobalAuth} disabled={authApplying}
            className="px-4 py-2 rounded-lg text-xs font-medium bg-blue-600/15 border border-blue-500/25 text-blue-300 hover:bg-blue-600/25 transition-colors disabled:opacity-50">
            {authApplying ? "Applying…" : "Apply to All Endpoints"}
          </button>
        </div>
        <p className="text-[11px] text-zinc-600 mt-2">You can also change auth per endpoint individually below.</p>
      </div>

      {/* Endpoints */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Endpoints</h2>
            <span className="text-[11px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-500 border border-zinc-700/60">{endpoints.length}</span>
          </div>
          {addMode === null && (
            <button onClick={() => setAddMode("picker")}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-600/15 border border-blue-500/25 text-blue-300 hover:bg-blue-600/25 transition-colors">
              <PlusIcon /> Add Endpoint
            </button>
          )}
        </div>

        {/* ── Add-mode picker ── */}
        {addMode === "picker" && (
          <div className="mb-4 p-4 rounded-xl border border-zinc-700/60 bg-zinc-800/30">
            <p className="text-xs text-zinc-400 mb-3 font-medium">How would you like to add the endpoint?</p>
            <div className="flex gap-3">
              <button onClick={() => setAddMode("manual")}
                className="flex-1 flex flex-col items-center gap-2 p-4 rounded-xl border border-zinc-700 bg-zinc-900/60
                           hover:border-blue-500/40 hover:bg-blue-600/8 transition-colors group">
                <div className="w-9 h-9 rounded-lg bg-blue-600/15 border border-blue-500/25 flex items-center justify-center group-hover:bg-blue-600/25 transition-colors">
                  <FormIcon />
                </div>
                <div className="text-center">
                  <p className="text-xs font-semibold text-zinc-200">Manual Form</p>
                  <p className="text-[11px] text-zinc-600 mt-0.5">Fill in fields directly</p>
                </div>
              </button>
              <button onClick={() => setAddMode("doc")}
                className="flex-1 flex flex-col items-center gap-2 p-4 rounded-xl border border-zinc-700 bg-zinc-900/60
                           hover:border-purple-500/40 hover:bg-purple-600/8 transition-colors group">
                <div className="w-9 h-9 rounded-lg bg-purple-600/15 border border-purple-500/25 flex items-center justify-center group-hover:bg-purple-600/25 transition-colors">
                  <DocIcon />
                </div>
                <div className="text-center">
                  <p className="text-xs font-semibold text-zinc-200">From Document</p>
                  <p className="text-[11px] text-zinc-600 mt-0.5">Upload API spec / doc</p>
                </div>
              </button>
            </div>
            <button onClick={() => setAddMode(null)} className="mt-3 w-full text-center text-[11px] text-zinc-600 hover:text-zinc-400 transition-colors">Cancel</button>
          </div>
        )}

        {/* ── Manual form ── */}
        {addMode === "manual" && (
          <div className="mb-4 p-4 rounded-xl border border-blue-500/20 bg-zinc-900/60">
            <p className="text-[11px] font-semibold text-blue-300 uppercase tracking-wider mb-3">New Endpoint</p>
            <EndpointForm
              draft={newEp}
              onChange={setNewEp}
              onSave={() => saveManualEndpoint(newEp)}
              onCancel={() => { setAddMode(null); setNewEp(blankEndpoint()); }}
              saving={epSaving === "__new__"}
            />
          </div>
        )}

        {/* ── Doc import panel ── */}
        {addMode === "doc" && (
          <DocImportPanel
            toolId={id}
            onImported={handleDocImported}
            onCancel={() => setAddMode(null)}
          />
        )}

        {/* ── Endpoint list ── */}
        <div className="space-y-2">
          {endpoints.map(ep => (
            <EndpointCard
              key={ep.id}
              ep={ep}
              isExpanded={expandedEp === ep.id}
              isEditing={editingEp?.id === ep.id}
              editDraft={editingEp?.id === ep.id ? editingEp.draft : null}
              saving={epSaving === ep.id}
              deleting={epDeleting === ep.id}
              confirmingDelete={deleteTarget === ep.id}
              onToggle={() => { if (editingEp?.id === ep.id) return; setExpandedEp(p => p === ep.id ? null : ep.id); }}
              onEdit={() => {
                setEditingEp({ id: ep.id, draft: { name: ep.name || "", description: ep.description || "",
                  path: ep.path || "", method: ep.method || "GET", auth_type: ep.auth_type || "NONE",
                  params: schemaToParams(ep.input_schema) } });
                setExpandedEp(ep.id);
              }}
              onCancelEdit={() => setEditingEp(null)}
              onDraftChange={draft => setEditingEp(prev => prev ? { ...prev, draft } : prev)}
              onSave={() => saveEditedEndpoint(ep.id, editingEp.draft)}
              onDeleteRequest={() => setDeleteTarget(ep.id)}
              onDeleteConfirm={confirmDelete}
              onDeleteCancel={() => setDeleteTarget(null)}
            />
          ))}
          {endpoints.length === 0 && addMode === null && (
            <div className="text-center py-10 text-zinc-600 text-sm">
              No endpoints yet. Click "Add Endpoint" to create one.
            </div>
          )}
        </div>
      </div>

      {deleteTarget && (
        <ConfirmModal
          message={deleteTarget === "__api__"
            ? `Permanently delete tool "${meta.name}"? All endpoints will be removed.`
            : "Permanently delete this endpoint? This cannot be undone."}
          onConfirm={confirmDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   DocImportPanel — full pipeline orchestration with HITL review
══════════════════════════════════════════════════════════════════════════════ */
function DocImportPanel({ toolId, onImported, onCancel }) {
  // stage: "select" | "uploading" | "processing" | "hitl" | "review" | "importing"
  const [stage,       setStage]       = useState("select");
  const [sessionId,   setSessionId]   = useState(null);
  const [sessionData, setSessionData] = useState(null);
  const [pipeStatus,  setPipeStatus]  = useState(null);
  const [discovered,  setDiscovered]  = useState([]);   // editable in HITL, used in review
  const [expandedHitl,setExpandedHitl]= useState(null); // index of expanded HITL row
  const [selected,    setSelected]    = useState(new Set());
  const [importErr,   setImportErr]   = useState([]);
  const [error,       setError]       = useState(null);
  const [isDragging,  setIsDragging]  = useState(false);
  const pollRef  = useRef(null);
  const fileRef  = useRef(null);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  async function handleFile(file) {
    if (!file) return;
    setStage("uploading");
    setError(null);
    try {
      const session = await agentApi.startUpload(file);
      setSessionId(session.id);
      setPipeStatus(session.state);
      setStage("processing");
      pollRef.current = setInterval(async () => {
        try {
          const s = await agentApi.getSession(session.id);
          setPipeStatus(s.state);
          if (s.state === "HITL_PENDING") {
            clearInterval(pollRef.current);
            const eps = s.draft_api?.endpoints || [];
            setSessionData(s);
            setDiscovered(eps.map(ep => ({ ...ep, _params: schemaToParams(ep.input_schema) })));
            setStage("hitl");
          } else if (s.state === "FAILED" || s.state === "ERROR") {
            clearInterval(pollRef.current);
            const last = s.error_log?.at?.(-1);
            setError(last ? `${last.step}: ${last.error}` : "Document processing failed.");
            setStage("select");
          }
        } catch {
          clearInterval(pollRef.current);
          setError("Lost connection to server. Please try again.");
          setStage("select");
        }
      }, 2000);
    } catch {
      setError("Upload failed. Check the file format and try again.");
      setStage("select");
    }
  }

  function onDrop(e) {
    e.preventDefault(); setIsDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }

  /* ── HITL helpers ── */
  function updateHitlEp(i, field, value) {
    setDiscovered(prev => { const c = [...prev]; c[i] = { ...c[i], [field]: value }; return c; });
  }
  function deleteHitlEp(i) {
    setDiscovered(prev => prev.filter((_, idx) => idx !== i));
  }
  function addHitlEp() {
    setDiscovered(prev => [...prev, { method: "GET", path: "/", name: "new_endpoint", description: "", auth_type: "NONE", input_schema: null, _params: [] }]);
  }
  function confirmHitl() {
    setSelected(new Set(discovered.map((_, i) => i)));
    setStage("review");
  }

  /* ── Review helpers ── */
  function toggleSelect(i) {
    setSelected(prev => { const n = new Set(prev); n.has(i) ? n.delete(i) : n.add(i); return n; });
  }
  function toggleAll() {
    setSelected(selected.size === discovered.length ? new Set() : new Set(discovered.map((_, i) => i)));
  }

  async function handleImport() {
    const toImport = discovered.filter((_, i) => selected.has(i));
    if (!toImport.length) return;
    setStage("importing");
    setImportErr([]);
    const created = [];
    const errs    = [];
    for (const ep of toImport) {
      try {
        const c = await registryApi.createEndpoint(toolId, {
          name:          ep.name || `${ep.method} ${ep.path}`,
          description:   ep.description || "",
          path:          ep.path,
          method:        ep.method,
          auth_type:     ep.auth_type || "NONE",
          input_schema:  ep._params?.length ? paramsToSchema(ep._params) : (ep.input_schema || null),
          output_schema: ep.output_schema,
          headers:       ep.headers || [],
        });
        created.push(c);
      } catch {
        errs.push(`${ep.method} ${ep.path}`);
      }
    }
    try { await agentApi.discard(sessionId); } catch {}
    if (errs.length) setImportErr(errs);
    onImported(created);
  }

  /* ── Stage label for header ── */
  const STAGE_HEADER = {
    select:     "Import Endpoints from Document",
    uploading:  "Uploading Document…",
    processing: "Analyzing Document…",
    hitl:       "Review Extracted Endpoints",
    review:     "Select Endpoints to Import",
    importing:  "Importing Endpoints…",
  };

  /* ── Render ── */
  return (
    <div className="mb-4 p-4 rounded-xl border border-purple-500/20 bg-zinc-900/60">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <DocIcon size={11} />
          <p className="text-[11px] font-semibold text-purple-300 uppercase tracking-wider">
            {STAGE_HEADER[stage]}
          </p>
        </div>
        {/* Step indicators */}
        <div className="flex items-center gap-1.5 mr-2">
          {["processing", "hitl", "review"].map((s, i) => {
            const stepIdx  = ["processing", "hitl", "review"].indexOf(stage);
            const done     = stepIdx > i;
            const active   = stepIdx === i;
            return (
              <span key={s} className={`w-5 h-5 rounded-full text-[9px] font-bold flex items-center justify-center transition-colors ${
                done   ? "bg-blue-600/30 text-blue-400 border border-blue-500/30" :
                active ? "bg-purple-600/30 text-purple-300 border border-purple-500/40" :
                         "bg-zinc-800 text-zinc-600 border border-zinc-700/60"
              }`}>
                {done ? "✓" : i + 1}
              </span>
            );
          })}
        </div>
        {stage !== "importing" && (
          <button onClick={onCancel} className="text-zinc-600 hover:text-zinc-400 transition-colors"><XIcon /></button>
        )}
      </div>

      {/* ── Select file ── */}
      {stage === "select" && (
        <>
          {error && (
            <div className="mb-3 px-3 py-2 rounded-lg bg-red-950/40 border border-red-500/20 text-xs text-red-300">
              {error}
            </div>
          )}
          <div
            onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={onDrop}
            onClick={() => fileRef.current?.click()}
            className={`flex flex-col items-center justify-center gap-3 p-8 rounded-xl border-2 border-dashed cursor-pointer transition-colors
              ${isDragging ? "border-purple-400/60 bg-purple-600/10" : "border-zinc-700 hover:border-zinc-600 hover:bg-zinc-800/40"}`}
          >
            <div className="w-10 h-10 rounded-xl bg-zinc-800 border border-zinc-700 flex items-center justify-center">
              <UploadCloudIcon />
            </div>
            <div className="text-center">
              <p className="text-sm text-zinc-300 font-medium">Drop your API document here</p>
              <p className="text-xs text-zinc-600 mt-1">or click to browse · JSON, YAML, PDF, TXT, DOCX</p>
            </div>
          </div>
          <input ref={fileRef} type="file" accept={ACCEPTED_EXTS} className="hidden"
            onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])} />
        </>
      )}

      {/* ── Uploading ── */}
      {stage === "uploading" && (
        <div className="flex items-center gap-3 px-4 py-5 rounded-xl bg-zinc-800/40">
          <div className="animate-spin w-5 h-5 border-2 border-purple-500 border-t-transparent rounded-full flex-shrink-0" />
          <div>
            <p className="text-sm text-zinc-300 font-medium">Uploading document…</p>
            <p className="text-xs text-zinc-600 mt-0.5">Sending file to the pipeline</p>
          </div>
        </div>
      )}

      {/* ── Processing (pipeline stages) ── */}
      {stage === "processing" && (
        <div className="space-y-2 px-1">
          {PIPELINE_STAGES.map((s, i) => {
            const idx    = PIPELINE_STAGES.indexOf(pipeStatus);
            const done   = idx > i;
            const active = idx === i;
            return (
              <div key={s} className="flex items-center gap-2.5">
                <span className="text-xs w-4 text-center flex-shrink-0"
                      style={{ color: done ? "#60a5fa" : active ? "#c084fc" : "#52525b" }}>
                  {done ? "✓" : active ? "●" : "○"}
                </span>
                <span className="text-xs flex-1"
                      style={{ color: done ? "#71717a" : active ? "#e9d5ff" : "#52525b", fontWeight: active ? 600 : 400 }}>
                  {STAGE_LABELS[s] || s}
                </span>
                {active && (
                  <span className="flex gap-0.5">
                    {[0,1,2].map(j => (
                      <span key={j} className="w-1 h-1 rounded-full bg-purple-400"
                            style={{ animation: `pulse 1.2s ease-in-out ${j * 0.2}s infinite` }} />
                    ))}
                  </span>
                )}
              </div>
            );
          })}
          <p className="text-[11px] text-zinc-600 pt-1">Processing your document through the AI pipeline…</p>
        </div>
      )}

      {/* ── HITL: Review & edit extracted endpoints ── */}
      {stage === "hitl" && (
        <>
          {/* Extracted API context banner */}
          {sessionData?.draft_api && (
            <div className="mb-3 px-3 py-2 rounded-lg bg-zinc-800/60 border border-zinc-700/40 flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-zinc-300 truncate">{sessionData.draft_api.name || "Extracted API"}</p>
                <p className="text-[11px] text-zinc-500 font-mono truncate">{sessionData.draft_api.base_url}</p>
              </div>
              <span className="text-[11px] px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20 flex-shrink-0">
                {discovered.length} endpoint{discovered.length !== 1 ? "s" : ""} found
              </span>
            </div>
          )}

          <p className="text-[11px] text-zinc-500 mb-3">
            Review and correct the extracted endpoints before selecting which ones to import.
            Edit any field inline, remove unwanted rows, or add missing ones.
          </p>

          {/* Editable endpoint rows */}
          <div className="space-y-1.5 max-h-[420px] overflow-y-auto mb-3 pr-0.5">
            {discovered.map((ep, i) => (
              <HitlEndpointRow
                key={i} ep={ep} index={i}
                isExpanded={expandedHitl === i}
                onToggle={() => setExpandedHitl(p => p === i ? null : i)}
                onChange={updateHitlEp}
                onDelete={deleteHitlEp}
              />
            ))}
            {discovered.length === 0 && (
              <p className="text-xs text-zinc-600 text-center py-6">
                No endpoints extracted. Add one manually or cancel and try a different document.
              </p>
            )}
          </div>

          {/* Footer actions */}
          <div className="flex items-center justify-between pt-2.5 border-t border-zinc-800">
            <button onClick={addHitlEp}
              className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition-colors">
              <PlusIcon size={11} /> Add endpoint
            </button>
            <div className="flex items-center gap-2">
              <button onClick={onCancel}
                className="px-3 py-1.5 rounded-lg text-xs text-zinc-400 border border-zinc-700 hover:bg-zinc-800 transition-colors">
                Cancel
              </button>
              <button
                onClick={confirmHitl}
                disabled={discovered.length === 0}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Confirm & Select Endpoints
                <svg width="11" height="11" viewBox="0 0 15 15" fill="none"><path d="M3 7.5h9M8 3l4.5 4.5L8 12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>
              </button>
            </div>
          </div>
        </>
      )}

      {/* ── Review: select which confirmed endpoints to import ── */}
      {stage === "review" && (
        <>
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-zinc-400">
              <span className="text-purple-300 font-semibold">{discovered.length}</span> endpoint{discovered.length !== 1 ? "s" : ""} confirmed — choose which to import
            </p>
            <div className="flex items-center gap-3">
              <button onClick={() => setStage("hitl")} className="text-[11px] text-zinc-500 hover:text-zinc-300 transition-colors flex items-center gap-1">
                <svg width="10" height="10" viewBox="0 0 15 15" fill="none"><path d="M12 7.5H3M7 3L2.5 7.5 7 12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>
                Back to edit
              </button>
              <button onClick={toggleAll} className="text-[11px] text-blue-400 hover:text-blue-300 transition-colors">
                {selected.size === discovered.length ? "Deselect all" : "Select all"}
              </button>
            </div>
          </div>

          {discovered.length === 0 ? (
            <div className="text-center py-6 text-zinc-600 text-sm">No endpoints to import.</div>
          ) : (
            <div className="space-y-1.5 max-h-72 overflow-y-auto mb-4 pr-1">
              {discovered.map((ep, i) => {
                const c = METHOD_COLORS[ep.method] || METHOD_COLORS.GET;
                return (
                  <label key={i}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-colors
                      ${selected.has(i) ? "bg-zinc-800/70 border border-zinc-700/60" : "border border-transparent hover:bg-zinc-800/40"}`}>
                    <input type="checkbox" checked={selected.has(i)} onChange={() => toggleSelect(i)}
                      className="w-3.5 h-3.5 accent-purple-500 cursor-pointer flex-shrink-0" />
                    <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded flex-shrink-0"
                          style={{ color: c.text, background: c.bg, border: `1px solid ${c.border}` }}>
                      {ep.method}
                    </span>
                    <span className="text-xs font-mono text-zinc-300 flex-1 truncate">{ep.path}</span>
                    <span className="text-[11px] text-zinc-500 truncate max-w-[140px] hidden sm:block">{ep.name}</span>
                  </label>
                );
              })}
            </div>
          )}

          <div className="flex items-center gap-2">
            <button
              onClick={handleImport}
              disabled={selected.size === 0}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold
                         bg-purple-600 hover:bg-purple-500 text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <PlusIcon size={13} />
              Import {selected.size > 0 ? `${selected.size} ` : ""}Endpoint{selected.size !== 1 ? "s" : ""}
            </button>
            <button onClick={onCancel}
              className="px-4 py-2.5 rounded-xl text-sm text-zinc-400 border border-zinc-700 hover:bg-zinc-800 transition-colors">
              Cancel
            </button>
          </div>
        </>
      )}

      {/* ── Importing progress ── */}
      {stage === "importing" && (
        <div className="flex items-center gap-3 px-4 py-5 rounded-xl bg-zinc-800/40">
          <div className="animate-spin w-5 h-5 border-2 border-purple-500 border-t-transparent rounded-full flex-shrink-0" />
          <div>
            <p className="text-sm text-zinc-300 font-medium">Importing endpoints…</p>
            <p className="text-xs text-zinc-600 mt-0.5">Adding {selected.size} endpoint{selected.size !== 1 ? "s" : ""} to this tool</p>
          </div>
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   HitlEndpointRow — expandable editable row in HITL review stage
══════════════════════════════════════════════════════════════════════════════ */
function HitlEndpointRow({ ep, index, isExpanded, onToggle, onChange, onDelete }) {
  const c      = METHOD_COLORS[ep.method] || METHOD_COLORS.GET;
  const params = ep._params || [];
  const isAuth = ep.auth_type && ep.auth_type !== "NONE";

  function updateParam(pi, field, val) {
    const next = [...params]; next[pi] = { ...next[pi], [field]: val };
    onChange(index, "_params", next);
  }
  function addParam()    { onChange(index, "_params", [...params, { name: "", type: "string", required: false, description: "" }]); }
  function removeParam(pi) { onChange(index, "_params", params.filter((_, j) => j !== pi)); }

  return (
    <div className={`rounded-lg border transition-colors ${isExpanded ? "border-purple-500/30 bg-zinc-800/50" : "border-zinc-700/40 bg-zinc-800/30"}`}>
      {/* ── Collapsed header (always visible) ── */}
      <div
        onClick={onToggle}
        className="flex items-center gap-2 px-3 py-2 cursor-pointer select-none group"
      >
        <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded flex-shrink-0"
              style={{ color: c.text, background: c.bg, border: `1px solid ${c.border}` }}>
          {ep.method}
        </span>
        <span className="text-xs font-mono text-zinc-300 flex-1 truncate min-w-0">{ep.path || <span className="text-zinc-600">/path</span>}</span>
        <span className="text-[11px] text-zinc-500 truncate max-w-[120px] hidden sm:block">{ep.name}</span>
        {/* Auth badge */}
        <span className="text-[10px] px-1.5 py-0.5 rounded border flex-shrink-0"
              style={{ color: isAuth ? "#60a5fa" : "#52525b", background: isAuth ? "rgba(59,130,246,0.08)" : "transparent", borderColor: isAuth ? "rgba(59,130,246,0.2)" : "#3f3f46" }}>
          {ep.auth_type || "NONE"}
        </span>
        {/* Param count pill */}
        {params.length > 0 && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-700/60 text-zinc-400 border border-zinc-700 flex-shrink-0">
            {params.length} param{params.length !== 1 ? "s" : ""}
          </span>
        )}
        <button
          onClick={e => { e.stopPropagation(); onDelete(index); }}
          className="text-zinc-700 hover:text-red-400 transition-colors flex-shrink-0 p-0.5 opacity-0 group-hover:opacity-100"
          title="Remove"
        >
          <XIcon />
        </button>
        <ChevronDownIcon open={isExpanded} />
      </div>

      {/* ── Expanded edit form ── */}
      {isExpanded && (
        <div className="px-3 pb-3 border-t border-zinc-700/40 pt-3 space-y-3">
          {/* Row 1: method + path + auth */}
          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="block text-[10px] text-zinc-600 mb-1 uppercase tracking-wider">Method</label>
              <select value={ep.method} onChange={e => onChange(index, "method", e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-700/60 rounded-lg px-2 py-1.5 text-xs font-bold font-mono focus:outline-none focus:border-purple-500/50"
                style={{ color: c.text }}>
                {HTTP_METHODS.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-[10px] text-zinc-600 mb-1 uppercase tracking-wider">Path</label>
              <input value={ep.path} onChange={e => onChange(index, "path", e.target.value)}
                placeholder="/path/{id}"
                className="w-full bg-zinc-900 border border-zinc-700/60 rounded-lg px-2.5 py-1.5 text-xs font-mono text-zinc-200 focus:outline-none focus:border-purple-500/50" />
            </div>
          </div>

          {/* Row 2: name + auth type */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-[10px] text-zinc-600 mb-1 uppercase tracking-wider">Function Name</label>
              <input value={ep.name || ""} onChange={e => onChange(index, "name", e.target.value)}
                placeholder="function_name"
                className="w-full bg-zinc-900 border border-zinc-700/60 rounded-lg px-2.5 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-purple-500/50" />
            </div>
            <div>
              <label className="block text-[10px] text-zinc-600 mb-1 uppercase tracking-wider">Auth Type</label>
              <select value={ep.auth_type || "NONE"} onChange={e => onChange(index, "auth_type", e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-700/60 rounded-lg px-2 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-purple-500/50">
                {AUTH_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-[10px] text-zinc-600 mb-1 uppercase tracking-wider">Description</label>
            <input value={ep.description || ""} onChange={e => onChange(index, "description", e.target.value)}
              placeholder="What this endpoint does"
              className="w-full bg-zinc-900 border border-zinc-700/60 rounded-lg px-2.5 py-1.5 text-xs text-zinc-400 focus:outline-none focus:border-purple-500/50" />
          </div>

          {/* Parameters */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-[10px] text-zinc-600 uppercase tracking-wider">Parameters</label>
              <button onClick={addParam} className="flex items-center gap-1 text-[11px] text-blue-400 hover:text-blue-300 transition-colors">
                <PlusIcon size={9} /> Add param
              </button>
            </div>
            {params.length === 0 ? (
              <p className="text-[11px] text-zinc-700 py-1">No parameters extracted.</p>
            ) : (
              <div className="space-y-1.5">
                {params.map((p, pi) => (
                  <div key={pi} className="flex items-center gap-1.5">
                    <input value={p.name} onChange={e => updateParam(pi, "name", e.target.value)} placeholder="name"
                      className="w-24 bg-zinc-900 border border-zinc-700/60 rounded px-2 py-1 text-[11px] text-zinc-200 font-mono focus:outline-none focus:border-purple-500/50" />
                    <select value={p.type} onChange={e => updateParam(pi, "type", e.target.value)}
                      className="w-20 bg-zinc-900 border border-zinc-700/60 rounded px-1.5 py-1 text-[11px] text-zinc-400 focus:outline-none focus:border-purple-500/50">
                      {PARAM_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                    <input value={p.description || ""} onChange={e => updateParam(pi, "description", e.target.value)} placeholder="description"
                      className="flex-1 bg-zinc-900 border border-zinc-700/60 rounded px-2 py-1 text-[11px] text-zinc-500 focus:outline-none focus:border-purple-500/50" />
                    <label className="flex items-center gap-1 text-[11px] text-zinc-600 cursor-pointer select-none flex-shrink-0">
                      <input type="checkbox" checked={!!p.required} onChange={e => updateParam(pi, "required", e.target.checked)}
                        className="w-3 h-3 accent-purple-500 cursor-pointer" />
                      req
                    </label>
                    <button onClick={() => removeParam(pi)} className="text-zinc-700 hover:text-red-400 transition-colors p-0.5 flex-shrink-0"><XIcon /></button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   EndpointCard
══════════════════════════════════════════════════════════════════════════════ */
function EndpointCard({ ep, isExpanded, isEditing, editDraft, saving, deleting, confirmingDelete,
  onToggle, onEdit, onCancelEdit, onDraftChange, onSave, onDeleteRequest, onDeleteConfirm, onDeleteCancel }) {
  const c = METHOD_COLORS[ep.method] || METHOD_COLORS.GET;
  return (
    <div className="border border-zinc-800 rounded-xl overflow-hidden">
      <div onClick={onToggle}
        className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-zinc-800/40 transition-colors select-none">
        <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded flex-shrink-0"
              style={{ color: c.text, background: c.bg, border: `1px solid ${c.border}` }}>
          {ep.method}
        </span>
        <span className="text-sm font-mono text-zinc-300 flex-1 truncate">{ep.path}</span>
        <span className="text-xs text-zinc-500 hidden sm:block flex-shrink-0 mr-1 truncate max-w-[160px]">{ep.name}</span>
        <AuthBadge type={ep.auth_type} />
        <button onClick={e => { e.stopPropagation(); onEdit(); }}
          className="p-1.5 rounded-lg text-zinc-600 hover:text-blue-400 hover:bg-blue-500/10 transition-colors flex-shrink-0" title="Edit">
          <EditIcon />
        </button>
        <button onClick={e => { e.stopPropagation(); onDeleteRequest(); }}
          className="p-1.5 rounded-lg text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition-colors flex-shrink-0" title="Delete">
          <TrashIcon size={12} />
        </button>
        <ChevronDownIcon open={isExpanded} />
      </div>
      {confirmingDelete && (
        <div className="px-4 py-3 bg-red-950/30 border-t border-red-500/20 flex items-center justify-between">
          <span className="text-xs text-red-300">Delete this endpoint?</span>
          <div className="flex gap-2">
            <button onClick={onDeleteCancel} className="px-3 py-1 rounded text-xs text-zinc-400 border border-zinc-700 hover:bg-zinc-800 transition-colors">Cancel</button>
            <button onClick={onDeleteConfirm} disabled={deleting} className="px-3 py-1 rounded text-xs font-medium bg-red-600 hover:bg-red-500 text-white disabled:opacity-50 transition-colors">
              {deleting ? "Deleting…" : "Delete"}
            </button>
          </div>
        </div>
      )}
      {isExpanded && (
        <div className="border-t border-zinc-800 px-4 py-4">
          {isEditing
            ? <EndpointForm draft={editDraft} onChange={onDraftChange} onSave={onSave} onCancel={onCancelEdit} saving={saving} />
            : <EndpointReadView ep={ep} />}
        </div>
      )}
    </div>
  );
}

function EndpointReadView({ ep }) {
  const params = schemaToParams(ep.input_schema);
  return (
    <div className="space-y-3">
      {ep.description && <p className="text-sm text-zinc-400 leading-relaxed">{ep.description}</p>}
      {params.length > 0 ? (
        <div>
          <p className="text-[10px] text-zinc-600 uppercase tracking-wider mb-2">Parameters</p>
          <div className="space-y-1.5">
            {params.map(p => (
              <div key={p.name} className="flex items-center gap-2 text-xs">
                <span className="font-mono text-zinc-200 w-32 truncate">{p.name}</span>
                <span className="text-zinc-600 w-16 flex-shrink-0">{p.type}</span>
                {p.required && <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 flex-shrink-0">required</span>}
                {p.description && <span className="text-zinc-600 truncate">{p.description}</span>}
              </div>
            ))}
          </div>
        </div>
      ) : <p className="text-xs text-zinc-600">No parameters defined.</p>}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   EndpointForm
══════════════════════════════════════════════════════════════════════════════ */
function EndpointForm({ draft, onChange, onSave, onCancel, saving }) {
  const update = (f, v) => onChange({ ...draft, [f]: v });
  function addParam()            { onChange({ ...draft, params: [...(draft.params || []), { name: "", type: "string", required: false, description: "" }] }); }
  function updateParam(i, f, v)  { const p = [...(draft.params || [])]; p[i] = { ...p[i], [f]: v }; onChange({ ...draft, params: p }); }
  function removeParam(i)        { const p = [...(draft.params || [])]; p.splice(i, 1); onChange({ ...draft, params: p }); }
  const canSave = draft.path?.trim() && draft.name?.trim();
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <Field label="Method">
          <select value={draft.method} onChange={e => update("method", e.target.value)} className="field-input">
            {HTTP_METHODS.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </Field>
        <Field label="Path">
          <input value={draft.path} onChange={e => update("path", e.target.value)} className="field-input font-mono" placeholder="/users/{id}" />
        </Field>
        <Field label="Function Name">
          <input value={draft.name} onChange={e => update("name", e.target.value)} className="field-input" placeholder="get_user_by_id" />
        </Field>
        <Field label="Auth Type">
          <select value={draft.auth_type} onChange={e => update("auth_type", e.target.value)} className="field-input">
            {AUTH_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </Field>
      </div>
      <Field label="Description">
        <input value={draft.description} onChange={e => update("description", e.target.value)} className="field-input" placeholder="What this endpoint does" />
      </Field>
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-[10px] text-zinc-500 uppercase tracking-wider">Parameters</label>
          <button onClick={addParam} className="flex items-center gap-1 text-[11px] text-blue-400 hover:text-blue-300 transition-colors">
            <PlusIcon size={10} /> Add param
          </button>
        </div>
        <div className="space-y-2">
          {(draft.params || []).map((p, i) => (
            <div key={i} className="flex items-center gap-2">
              <input value={p.name} onChange={e => updateParam(i, "name", e.target.value)} placeholder="name"
                className="w-28 bg-zinc-800/60 border border-zinc-700/60 rounded-lg px-2.5 py-1.5 text-xs text-zinc-100 font-mono focus:outline-none focus:border-blue-500/50" />
              <select value={p.type} onChange={e => updateParam(i, "type", e.target.value)}
                className="w-24 bg-zinc-800/60 border border-zinc-700/60 rounded-lg px-2 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-blue-500/50">
                {PARAM_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <input value={p.description} onChange={e => updateParam(i, "description", e.target.value)} placeholder="description (optional)"
                className="flex-1 bg-zinc-800/60 border border-zinc-700/60 rounded-lg px-2.5 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-blue-500/50" />
              <label className="flex items-center gap-1 text-[11px] text-zinc-500 cursor-pointer flex-shrink-0 select-none">
                <input type="checkbox" checked={p.required} onChange={e => updateParam(i, "required", e.target.checked)} className="w-3 h-3 accent-blue-500 cursor-pointer" />
                req
              </label>
              <button onClick={() => removeParam(i)} className="text-zinc-600 hover:text-red-400 transition-colors flex-shrink-0 p-0.5"><XIcon /></button>
            </div>
          ))}
          {!draft.params?.length && <p className="text-xs text-zinc-600 py-1">No parameters. Click "Add param" to add one.</p>}
        </div>
      </div>
      <div className="flex justify-end gap-2 pt-1 border-t border-zinc-800">
        <button onClick={onCancel} className="px-4 py-2 rounded-lg text-xs text-zinc-400 border border-zinc-700/60 hover:bg-zinc-800 transition-colors">Cancel</button>
        <button onClick={onSave} disabled={saving || !canSave}
          className="px-4 py-2 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50">
          {saving ? "Saving…" : "Save Endpoint"}
        </button>
      </div>
    </div>
  );
}

/* ── Shared atoms ───────────────────────────────────────────────────────────── */
function Field({ label, children }) {
  return (
    <div>
      <label className="block text-[10px] text-zinc-500 mb-1.5 uppercase tracking-wider">{label}</label>
      {children}
    </div>
  );
}
function AuthBadge({ type }) {
  const isAuth = type && type !== "NONE";
  return (
    <span className="text-[10px] px-1.5 py-0.5 rounded border flex-shrink-0"
          style={{ color: isAuth ? "#60a5fa" : "#52525b", background: isAuth ? "rgba(59,130,246,0.08)" : "transparent",
                   borderColor: isAuth ? "rgba(59,130,246,0.2)" : "#3f3f46" }}>
      {type || "NONE"}
    </span>
  );
}
function ConfirmModal({ message, onConfirm, onCancel }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/80 backdrop-blur-sm">
      <div className="bg-zinc-900 border border-zinc-700 rounded-2xl p-6 max-w-sm w-full mx-4 shadow-2xl">
        <p className="text-sm text-zinc-300 mb-5 leading-relaxed">{message}</p>
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} className="px-4 py-2 rounded-lg text-xs text-zinc-400 border border-zinc-700 hover:bg-zinc-800 transition-colors">Cancel</button>
          <button onClick={onConfirm} className="px-4 py-2 rounded-lg text-xs font-semibold text-white bg-red-600 hover:bg-red-500 transition-colors">Delete</button>
        </div>
      </div>
    </div>
  );
}

/* ── Icons ──────────────────────────────────────────────────────────────────── */
function BackIcon() {
  return <svg width="13" height="13" viewBox="0 0 15 15" fill="none"><path d="M8 3L3 7.5L8 12M3 7.5h9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}
function ChevronRightSmIcon() {
  return <svg width="12" height="12" viewBox="0 0 15 15" fill="none" className="text-zinc-700"><path d="M5 3l5 4.5L5 12" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}
function ChevronDownIcon({ open }) {
  return <svg width="12" height="12" viewBox="0 0 15 15" fill="none" className={`flex-shrink-0 text-zinc-600 transition-transform duration-200 ${open ? "rotate-180" : ""}`}><path d="M3 5l4.5 5L12 5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}
function TrashIcon({ size = 13 }) {
  return <svg width={size} height={size} viewBox="0 0 15 15" fill="none"><path d="M3 3.5h9M5.5 3.5V2.5h4v1M6 6v5M9 6v5M4 3.5l.5 9h6l.5-9" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}
function EditIcon() {
  return <svg width="13" height="13" viewBox="0 0 15 15" fill="none"><path d="M10.5 1.5l3 3L5 13H2v-3L10.5 1.5Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/></svg>;
}
function PlusIcon({ size = 13 }) {
  return <svg width={size} height={size} viewBox="0 0 15 15" fill="none"><path d="M7.5 2v11M2 7.5h11" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>;
}
function XIcon() {
  return <svg width="12" height="12" viewBox="0 0 15 15" fill="none"><path d="M3 3l9 9M12 3l-9 9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>;
}
function FormIcon() {
  return <svg width="15" height="15" viewBox="0 0 15 15" fill="none" className="text-blue-400"><path d="M2 3h11M2 7h7M2 11h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>;
}
function DocIcon({ size = 15 }) {
  return <svg width={size} height={size} viewBox="0 0 15 15" fill="none" className="text-purple-400"><path d="M3 1.5h6l3 3v9H3v-12Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/><path d="M9 1.5V4.5H12M5 7h5M5 9.5h3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>;
}
function UploadCloudIcon() {
  return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="text-zinc-500"><path d="M12 16V8M9 11l3-3 3 3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/><path d="M6.5 18A4.5 4.5 0 0 1 7 9h.5A6 6 0 0 1 19 11.5a3.5 3.5 0 0 1-.5 7H6.5Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/></svg>;
}
