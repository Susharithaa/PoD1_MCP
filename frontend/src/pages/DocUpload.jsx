import { useState, useRef } from "react";
import { agentApi } from "../lib/api";
import Spinner from "../components/Spinner";
import { useLanguage } from "../context/LanguageContext";
import { useUpload } from "../context/UploadContext";

const SUPPORTED = [".yaml", ".yml", ".json", ".txt", ".md", ".pdf"];

export default function DocUpload() {
  const { t } = useLanguage();
  const { beginUpload, sessionReady, uploadFailed } = useUpload();
  const [file,     setFile]     = useState(null);
  const [dragging, setDragging] = useState(false);
  const [error,    setError]    = useState(null);
  const inputRef  = useRef(null);

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;
    setError(null);

    // Capture file ref before clearing state
    const fileToUpload = file;

    // ① Show overlay IMMEDIATELY — freezes all pages before the HTTP call starts
    beginUpload(fileToUpload.name);
    setFile(null);

    try {
      // ② HTTP call — may take 10–30 s for large docs / LLM pipeline
      const session = await agentApi.startUpload(fileToUpload);
      // ③ Session id ready — transition overlay to pipeline stage checklist + polling
      sessionReady(session.id, fileToUpload.name);
    } catch (err) {
      uploadFailed();
      setError(err.response?.data?.detail || t("Upload failed. Please try again."));
    }
  }

  function removeFile() { setFile(null); setError(null); }

  return (
    <div className="max-w-2xl animate-slide-up">
      {/* Header */}
      <div className="mb-8">
        <h1 className="page-title">{t("Document Upload")}</h1>
        <p className="page-subtitle mt-1.5">
          {t("Upload an API specification or description. The system will parse endpoints, parameters, and schema automatically.")}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Drop zone */}
        {!file ? (
          <div
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            className={`card p-12 text-center cursor-pointer transition-all
                        ${dragging
                          ? "border-blue-500/50 bg-blue-500/5"
                          : "hover:border-zinc-600 hover:bg-zinc-800/30"}`}
          >
            <div className={`w-14 h-14 rounded-xl mx-auto mb-4 flex items-center justify-center
                             border-2 transition-colors
                             ${dragging
                               ? "bg-blue-500/10 border-blue-500/40 text-blue-400"
                               : "bg-zinc-800 border-zinc-700 text-zinc-500"}`}>
              <UploadIcon />
            </div>
            <p className="text-sm font-semibold text-zinc-200 mb-1">
              {dragging ? t("Drop to upload") : t("Drag & drop or click to browse")}
            </p>
            <p className="text-xs text-zinc-600">
              {SUPPORTED.join(" · ")} · {t("Max 10 MB")}
            </p>
            <input
              ref={inputRef}
              type="file"
              className="hidden"
              accept={SUPPORTED.join(",")}
              onChange={e => e.target.files[0] && setFile(e.target.files[0])}
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
            </div>
            <button type="button" onClick={removeFile}
              className="text-zinc-600 hover:text-zinc-400 transition-colors p-1 rounded hover:bg-zinc-800">
              <XIcon />
            </button>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-3 px-4 py-3 rounded-lg
                          bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            <span className="mt-0.5 flex-shrink-0">⚠</span>
            {error}
          </div>
        )}

        <button type="submit" disabled={!file} className="btn-primary w-full py-2.5">
          {t("Parse & Generate Schema")} <ArrowIcon />
        </button>
      </form>

      {/* Supported formats */}
      <div className="mt-8">
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
