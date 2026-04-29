import { useEffect } from "react";
import { useUpload, STAGE_LABELS, PIPELINE_STAGES } from "../context/UploadContext";
import Spinner from "./Spinner";

export default function UploadOverlay() {
  const { overlay, sendToBackground, dismissOverlay } = useUpload();

  // Must call useEffect unconditionally (hooks rules), but only apply the
  // overflow lock when the overlay is actually visible.
  useEffect(() => {
    if (!overlay) return;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, [overlay]);

  if (!overlay) return null;

  const { id, filename, status, redirecting } = overlay;

  const isUploading = status === "UPLOADING";
  const isDone      = status === "HITL_PENDING" || redirecting;
  const isError     = status === "ERROR" || status === "FAILED";
  const stageIdx    = PIPELINE_STAGES.indexOf(status);

  return (
    /* Full-screen backdrop — blocks all interaction behind it */
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/90 backdrop-blur-sm">
      <div className="w-full max-w-md mx-4 bg-zinc-900 border border-zinc-700/60 rounded-2xl shadow-2xl overflow-hidden">

        {/* ── Top accent bar ── */}
        <div className={`h-1 w-full ${isError ? "bg-red-500" : isDone ? "bg-green-500" : "bg-blue-500 animate-pulse"}`} />

        <div className="p-7">
          {/* ── Header ── */}
          <div className="flex items-start gap-4 mb-7">
            <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 border
              ${isDone  ? "bg-green-500/10 border-green-500/30"
              : isError ? "bg-red-500/10   border-red-500/30"
                        : "bg-blue-500/10  border-blue-500/20"}`}>
              {isDone  ? <CheckIcon   /> :
               isError ? <ErrorIcon   /> :
                         <Spinner size={18} />}
            </div>
            <div className="min-w-0 flex-1 pt-1">
              <p className={`font-semibold text-sm leading-snug
                ${isDone  ? "text-green-400"
                : isError ? "text-red-400"
                          : "text-zinc-100"}`}>
                {isDone
                  ? "Schema ready! Redirecting to review…"
                  : isError
                    ? "Processing failed"
                    : isUploading
                      ? "File upload started — this will take a moment"
                      : "Processing document…"}
              </p>
              <p className="text-xs text-zinc-500 truncate mt-1">{filename}</p>
            </div>
          </div>

          {/* ── UPLOADING phase: simple message + spinner ── */}
          {isUploading && (
            <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-zinc-800/60 border border-zinc-700/40 mb-6">
              <Spinner size={14} />
              <p className="text-xs text-zinc-400 leading-relaxed">
                Uploading and analysing your document. All other pages are paused while processing is in progress.
              </p>
            </div>
          )}

          {/* ── Pipeline stages (visible once session id is known) ── */}
          {!isUploading && (
            <div className="space-y-2.5 mb-6">
              {PIPELINE_STAGES.map((stage, i) => {
                const done   = isDone || stageIdx > i;
                const active = !isDone && stageIdx === i && !isError;
                return (
                  <div key={stage} className="flex items-center gap-3">
                    <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0
                      text-[9px] font-bold transition-all duration-300
                      ${done   ? "bg-blue-500 text-white"
                      : active ? "bg-blue-500/15 border border-blue-400 text-blue-400"
                               : "bg-zinc-800 border border-zinc-700 text-zinc-600"}`}>
                      {done ? "✓" : i + 1}
                    </div>
                    <span className={`text-xs flex-1 transition-colors duration-200
                      ${done   ? "text-zinc-400"
                      : active ? "text-zinc-200 font-medium"
                               : "text-zinc-600"}`}>
                      {STAGE_LABELS[stage]}
                    </span>
                    {active && <Spinner size={10} />}
                  </div>
                );
              })}
            </div>
          )}

          {/* ── Actions ── */}
          {!isDone && !isError && (
            <div className="space-y-2.5">
              <button
                onClick={() => sendToBackground(id, filename, status)}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
                  bg-blue-600/10 border border-blue-500/20 text-blue-400 text-sm font-semibold
                  hover:bg-blue-600/20 hover:border-blue-500/40 transition-all">
                <BellIcon />
                Notify Once Done
              </button>
              <p className="text-center text-[11px] text-zinc-600 leading-relaxed">
                Navigate freely — we'll alert you when HITL review is ready.
              </p>
            </div>
          )}

          {isError && (
            <button
              onClick={dismissOverlay}
              className="w-full px-4 py-2.5 rounded-xl bg-zinc-800 border border-zinc-700
                         text-zinc-300 text-sm font-medium hover:bg-zinc-700 transition-colors">
              Dismiss
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function CheckIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 15 15" fill="none">
      <path d="M3 7.5l3 3 6-6" stroke="#4ade80" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}
function ErrorIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 15 15" fill="none">
      <path d="M4 4l7 7M11 4l-7 7" stroke="#f87171" strokeWidth="1.8" strokeLinecap="round"/>
    </svg>
  );
}
function BellIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 15 15" fill="none">
      <path d="M7.5 1.5a5 5 0 0 1 5 5v3l1 1.5H1.5L2.5 10V6.5a5 5 0 0 1 5-5Z"
        stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
      <path d="M6 11.5a1.5 1.5 0 0 0 3 0" stroke="currentColor" strokeWidth="1.4"/>
    </svg>
  );
}
