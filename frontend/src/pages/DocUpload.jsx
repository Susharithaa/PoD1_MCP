import { useState, useRef } from "react";
import { agentApi } from "../lib/api";
import Spinner from "../components/Spinner";
import { useLanguage } from "../context/LanguageContext";
import { useUpload } from "../context/UploadContext";

const SUPPORTED = [".yaml", ".yml", ".json", ".txt", ".md", ".pdf"];

const OPENAPI_TEMPLATE = `openapi: 3.0.0
info:
  title: Your API Title
  version: "1.0.0"
  description: Brief description of your API

servers:
  - url: https://api.example.com

# ── Step 1: Define your auth schemes ──────────────
components:
  securitySchemes:

    # Option A — API Key in header (e.g. X-API-Key)
    ApiKeyHeader:
      type: apiKey
      in: header
      name: X-API-Key

    # Option B — API Key in query param (?api_key=)
    ApiKeyQuery:
      type: apiKey
      in: query
      name: api_key

    # Option C — Bearer token
    BearerAuth:
      type: http
      scheme: bearer

    # Option D — Basic auth (username + password)
    BasicAuth:
      type: http
      scheme: basic

# ── Step 2: Apply auth globally (optional) ────────
# Remove this block to set auth per-endpoint instead
security:
  - ApiKeyHeader: []

# ── Step 3: Define your endpoints ─────────────────
paths:

  # No auth — open endpoint
  /health:
    get:
      summary: Health check (no auth)
      operationId: healthCheck
      security: []
      responses:
        "200":
          description: Service is healthy

  # Uses global auth (ApiKeyHeader defined above)
  /users/{id}:
    get:
      summary: Get user by ID
      operationId: getUser
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
          description: User identifier
      responses:
        "200":
          description: User details
          content:
            application/json:
              schema:
                type: object
                properties:
                  id:
                    type: string
                  name:
                    type: string
                  email:
                    type: string

  # Override auth per endpoint — uses Bearer instead
  /admin/reports:
    get:
      summary: List reports (Bearer auth override)
      operationId: listReports
      security:
        - BearerAuth: []
      parameters:
        - name: status
          in: query
          required: false
          schema:
            type: string
            enum: [pending, ready, failed]
          description: Filter reports by status
      responses:
        "200":
          description: List of reports
          content:
            application/json:
              schema:
                type: object
                properties:
                  reports:
                    type: array
                    items:
                      type: object
                      properties:
                        id:
                          type: string
                        status:
                          type: string

  # POST with request body — uses global auth
  /items:
    post:
      summary: Create a new item
      operationId: createItem
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [name]
              properties:
                name:
                  type: string
                  description: Item name
                tags:
                  type: array
                  items:
                    type: string
      responses:
        "201":
          description: Item created
          content:
            application/json:
              schema:
                type: object
                properties:
                  id:
                    type: string
                  name:
                    type: string`;

// Validate uploaded file content against OpenAPI structure
async function validateFile(file) {
  const ext = "." + file.name.split(".").pop().toLowerCase();

  // Plain text / pdf / md — no structural validation needed
  if ([".txt", ".md", ".pdf"].includes(ext)) return null;

  const text = await file.text();

  if ([".yaml", ".yml"].includes(ext)) {
    if (!text.includes("openapi:") && !text.includes("swagger:")) {
      return 'Template mismatch: YAML file must contain "openapi:" or "swagger:" at the root. See the OpenAPI template on the right.';
    }
    if (!text.includes("paths:") && !text.includes("info:")) {
      return 'Template mismatch: Missing required OpenAPI fields "info" and "paths". See the template on the right for the correct structure.';
    }
    return null;
  }

  if (ext === ".json") {
    try {
      const parsed = JSON.parse(text);
      // Accept JSON Schema too (has $schema or type:object at root)
      const isOpenApi = parsed.openapi || parsed.swagger;
      const isJsonSchema = parsed.$schema || parsed.type || parsed.properties;
      if (!isOpenApi && !isJsonSchema) {
        return 'Template mismatch: JSON file must be an OpenAPI spec (with "openapi" key) or a JSON Schema (with "$schema", "type", or "properties" key). See the template on the right.';
      }
      return null;
    } catch {
      return "Invalid JSON: The file could not be parsed. Please check for syntax errors.";
    }
  }

  return null;
}

export default function DocUpload({ embedded = false }) {
  const { t } = useLanguage();
  const { beginUpload, sessionReady, uploadFailed } = useUpload();
  const [file,       setFile]       = useState(null);
  const [dragging,   setDragging]   = useState(false);
  const [error,      setError]      = useState(null);
  const [validating, setValidating] = useState(false);
  const [copied,     setCopied]     = useState(false);
  const inputRef = useRef(null);

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) pickFile(f);
  }

  async function pickFile(f) {
    setError(null);
    setValidating(true);
    const validationError = await validateFile(f);
    setValidating(false);
    if (validationError) {
      setError(validationError);
      setFile(null);
    } else {
      setFile(f);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;
    setError(null);
    const fileToUpload = file;
    beginUpload(fileToUpload.name);
    setFile(null);
    try {
      const session = await agentApi.startUpload(fileToUpload);
      sessionReady(session.id, fileToUpload.name);
    } catch (err) {
      uploadFailed();
      setError(err.response?.data?.detail || t("Upload failed. Please try again."));
    }
  }

  function removeFile() { setFile(null); setError(null); }

  function copyTemplate() {
    navigator.clipboard.writeText(OPENAPI_TEMPLATE).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="animate-slide-up">
      {!embedded && (
        <div className="mb-6">
          <h1 className="page-title">{t("Automatic MCP Onboarding")}</h1>
          <p className="page-subtitle mt-1.5">
            {t("Upload an API specification or document. The system parses endpoints, parameters, and schema automatically and registers them as MCP tools.")}
          </p>
        </div>
      )}

      {/* Two-column layout */}
      <div className="flex gap-6 items-start">

        {/* LEFT — Upload panel */}
        <div className="flex-1 min-w-0 space-y-4">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Drop zone */}
            {!file ? (
              <div
                onDragOver={e => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                onClick={() => !validating && inputRef.current?.click()}
                className={`card p-12 text-center transition-all
                            ${validating ? "cursor-wait opacity-60" : "cursor-pointer"}
                            ${dragging
                              ? "border-blue-500/50 bg-blue-500/5"
                              : "hover:border-zinc-600 hover:bg-zinc-800/30"}`}
              >
                <div className={`w-14 h-14 rounded-xl mx-auto mb-4 flex items-center justify-center
                                 border-2 transition-colors
                                 ${dragging
                                   ? "bg-blue-500/10 border-blue-500/40 text-blue-400"
                                   : "bg-zinc-800 border-zinc-700 text-zinc-500"}`}>
                  {validating ? <Spinner /> : <UploadIcon />}
                </div>
                <p className="text-sm font-semibold text-zinc-200 mb-1">
                  {validating
                    ? t("Validating file…")
                    : dragging
                      ? t("Drop to upload")
                      : t("Drag & drop or click to browse")}
                </p>
                <p className="text-xs text-zinc-600">
                  {SUPPORTED.join(" · ")} · {t("Max 10 MB")}
                </p>
                <input
                  ref={inputRef}
                  type="file"
                  className="hidden"
                  accept={SUPPORTED.join(",")}
                  onChange={e => e.target.files[0] && pickFile(e.target.files[0])}
                />
              </div>
            ) : (
              <div className="card px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-blue-500/10 border border-blue-500/20
                                  flex items-center justify-center text-blue-400 flex-shrink-0">
                    <FileIcon />
                  </div>
                  <div>
                    <p className="text-sm text-zinc-200 font-medium">{file.name}</p>
                    <p className="text-xs text-zinc-500">{(file.size / 1024).toFixed(1)} KB</p>
                  </div>
                  {/* Validation passed badge */}
                  <span className="ml-2 px-2 py-0.5 rounded-full text-xs bg-green-500/10
                                   border border-green-500/20 text-green-400 font-medium">
                    ✓ Valid
                  </span>
                </div>
                <button type="button" onClick={removeFile}
                  className="text-zinc-600 hover:text-zinc-400 transition-colors p-1 rounded hover:bg-zinc-800">
                  <XIcon />
                </button>
              </div>
            )}

            {/* Error — template mismatch or upload failure */}
            {error && (
              <div className="flex items-start gap-3 px-4 py-3 rounded-lg
                              bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                <span className="mt-0.5 flex-shrink-0">⚠</span>
                <span>{error}</span>
              </div>
            )}

            <button type="submit" disabled={!file} className="btn-primary w-full py-2.5">
              {t("Parse & Generate Schema")} <ArrowIcon />
            </button>
          </form>

          {/* Supported formats */}
          <div className="mt-4">
            <p className="section-label mb-3">{t("Supported Formats")}</p>
            <div className="grid grid-cols-2 gap-2">
              {[
                { fmt: "OpenAPI / Swagger", ext: ".yaml · .json",  descKey: "Full spec parsing" },
                { fmt: t("Plain Text"),     ext: ".txt · .md",     descKey: "Natural language description" },
                { fmt: t("PDF Document"),   ext: ".pdf",           descKey: "API documentation" },
                { fmt: t("JSON Schema"),    ext: ".json",          descKey: "Existing schema files" },
              ].map(({ fmt, ext, descKey }) => (
                <div key={fmt} className="card px-4 py-3 hover:border-zinc-700 transition-colors">
                  <p className="text-sm text-zinc-200 font-medium">{fmt}</p>
                  <p className="text-xs text-zinc-600 font-mono mt-0.5">{ext}</p>
                  <p className="text-xs text-zinc-600 mt-0.5">{t(descKey)}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT — OpenAPI template reference */}
        <div className="w-96 flex-shrink-0">
          <div className="card overflow-hidden">
            {/* Template header */}
            <div className="flex items-center justify-between px-4 py-3
                            border-b border-zinc-800 bg-zinc-800/40">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wide">
                  OpenAPI Template
                </span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-mono
                                 bg-blue-500/10 border border-blue-500/20 text-blue-400">
                  required format
                </span>
              </div>
              <button
                onClick={copyTemplate}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs
                           text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700/50 transition-all"
              >
                {copied ? <CheckIcon /> : <CopyIcon />}
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>

            {/* Validation rules */}
            <div className="px-4 py-3 border-b border-zinc-800 bg-zinc-900/60 space-y-1.5">
              <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wide mb-2">
                Validation Rules
              </p>
              {[
                { icon: "✓", color: "text-green-400", rule: '.yaml/.yml must have "openapi:" or "swagger:"' },
                { icon: "✓", color: "text-green-400", rule: 'Must include "info:" and "paths:" sections' },
                { icon: "✓", color: "text-green-400", rule: '.json must be valid OpenAPI or JSON Schema' },
                { icon: "✓", color: "text-green-400", rule: '.txt, .md, .pdf pass without validation' },
              ].map(({ icon, color, rule }) => (
                <div key={rule} className="flex items-start gap-2">
                  <span className={`text-xs mt-0.5 flex-shrink-0 ${color}`}>{icon}</span>
                  <span className="text-xs text-zinc-500">{rule}</span>
                </div>
              ))}
            </div>

            {/* Code block */}
            <div className="overflow-auto max-h-[420px]">
              <pre className="px-4 py-4 text-[11px] leading-relaxed font-mono text-zinc-300
                              whitespace-pre overflow-x-auto">
                {OPENAPI_TEMPLATE.split("\n").map((line, i) => {
                  // Colour YAML keys vs values for readability
                  const keyMatch = line.match(/^(\s*)([\w$]+)(:)(.*)$/);
                  if (keyMatch) {
                    const [, indent, key, colon, value] = keyMatch;
                    return (
                      <span key={i} className="block">
                        <span className="text-zinc-600">{indent}</span>
                        <span className="text-blue-400">{key}</span>
                        <span className="text-zinc-600">{colon}</span>
                        <span className="text-amber-300/80">{value}</span>
                      </span>
                    );
                  }
                  return (
                    <span key={i} className="block text-zinc-500">{line}</span>
                  );
                })}
              </pre>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

function UploadIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path d="M12 15V3M8 7l4-4 4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
    </svg>
  );
}
function FileIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
      <path d="M4 1h5.5L11 2.5V14H4V1Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/>
      <path d="M8.5 1v3H11" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/>
    </svg>
  );
}
function XIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 15 15" fill="none">
      <path d="M3 3l9 9M12 3l-9 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}
function ArrowIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 15 15" fill="none">
      <path d="M3 7.5h9M9 4.5l3 3-3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}
function CopyIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 15 15" fill="none">
      <rect x="5" y="5" width="8" height="8" rx="1" stroke="currentColor" strokeWidth="1.3"/>
      <path d="M3 10H2a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h7a1 1 0 0 1 1 1v1" stroke="currentColor" strokeWidth="1.3"/>
    </svg>
  );
}
function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 15 15" fill="none">
      <path d="M3 7.5l3 3 6-6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}
