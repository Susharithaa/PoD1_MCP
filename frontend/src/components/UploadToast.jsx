/**
 * Bottom-right toast panel for background upload tracking.
 * Shows live stage progress while upload is running and
 * an amber/green CTA when HITL review is ready.
 */
import { useUpload, STAGE_LABELS, PIPELINE_STAGES } from "../context/UploadContext";

export default function UploadToast() {
  const { bgUploads, navigateToHITL, dismissNotification } = useUpload();

  if (!bgUploads.length) return null;

  return (
    <div className="fixed top-6 right-6 z-50 flex flex-col gap-3 pointer-events-none"
         style={{ minWidth: 320, maxWidth: 360 }}>
      {bgUploads.map(({ id, filename, status, error }) => {
        const isHITL   = status === "HITL_PENDING";
        const isSaved  = status === "SAVED";
        const isError  = status === "ERROR" || status === "FAILED";
        const isDone   = isHITL || isSaved || isError;
        const stageIdx = PIPELINE_STAGES.indexOf(status);

        return (
          <div key={id}
            className="pointer-events-auto rounded-2xl overflow-hidden shadow-2xl border"
            style={{
              background: isHITL  ? "rgba(120,53,15,0.97)"
                        : isSaved ? "rgba(20,83,45,0.97)"
                        : isError ? "rgba(127,29,29,0.97)"
                                  : "rgba(24,24,27,0.97)",
              borderColor: isHITL  ? "#f59e0b"
                         : isSaved ? "#22c55e"
                         : isError ? "#ef4444"
                                   : "#3f3f46",
            }}>

            {/* ── Coloured top bar ── */}
            <div className="h-1" style={{
              background: isHITL  ? "#f59e0b"
                        : isSaved ? "#22c55e"
                        : isError ? "#ef4444"
                                  : "#3b82f6",
            }} />

            <div className="p-4">
              {/* ── Header row ── */}
              <div className="flex items-start gap-3 mb-3">
                <span className="text-lg leading-none mt-0.5 flex-shrink-0">
                  {isHITL ? "🟡" : isSaved ? "🟢" : isError ? "🔴" : "🔵"}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold leading-snug"
                     style={{ color: isHITL ? "#fde68a" : isSaved ? "#86efac" : isError ? "#fca5a5" : "#e4e4e7" }}>
                    {isHITL  ? "HITL Review Required"
                    : isSaved ? "Tool Saved Successfully"
                    : isError ? "Processing Failed"
                              : "Processing in Background…"}
                  </p>
                  <p className="text-xs mt-0.5 truncate text-zinc-400">{filename}</p>
                </div>
                <button onClick={() => dismissNotification(id)}
                  className="flex-shrink-0 text-zinc-600 hover:text-zinc-300 transition-colors mt-0.5 p-0.5 rounded">
                  <XIcon />
                </button>
              </div>

              {/* ── Uploading phase (pre-pipeline, no stage index) ── */}
              {!isDone && stageIdx < 0 && (
                <div className="flex items-center gap-2 mb-3 px-3 py-2 rounded-lg"
                     style={{ background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.2)" }}>
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0 animate-pulse" />
                  <span className="text-xs flex-1" style={{ color: "#93c5fd" }}>
                    Uploading and analysing document…
                  </span>
                  <span className="flex gap-0.5">
                    {[0,1,2].map(j => (
                      <span key={j} className="w-1 h-1 rounded-full bg-blue-400"
                            style={{ animation: `pulse 1.2s ease-in-out ${j * 0.2}s infinite` }} />
                    ))}
                  </span>
                </div>
              )}

              {/* ── In-progress stage list ── */}
              {!isDone && stageIdx >= 0 && (
                <div className="space-y-1.5 mb-3">
                  {PIPELINE_STAGES.map((stage, i) => {
                    const done   = stageIdx > i;
                    const active = stageIdx === i;
                    return (
                      <div key={stage} className="flex items-center gap-2">
                        <span className="text-[11px] w-4 text-center flex-shrink-0"
                              style={{ color: done ? "#60a5fa" : active ? "#fbbf24" : "#52525b" }}>
                          {done ? "✓" : active ? "●" : "○"}
                        </span>
                        <span className="text-xs"
                              style={{ color: done ? "#71717a" : active ? "#fde68a" : "#52525b",
                                       fontWeight: active ? 600 : 400 }}>
                          {STAGE_LABELS[stage]}
                        </span>
                        {active && (
                          <span className="ml-auto flex gap-0.5">
                            {[0,1,2].map(j => (
                              <span key={j} className="w-1 h-1 rounded-full bg-amber-400"
                                    style={{ animation: `pulse 1.2s ease-in-out ${j * 0.2}s infinite` }} />
                            ))}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* ── Error detail ── */}
              {isError && error && (
                <div className="mb-3 px-3 py-2 rounded-lg"
                     style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.25)" }}>
                  <p className="text-[11px] leading-relaxed" style={{ color: "#fca5a5" }}>
                    {error}
                  </p>
                </div>
              )}

              {/* ── CTA for HITL ── */}
              {isHITL && (
                <button onClick={() => navigateToHITL(id)}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
                    font-semibold text-sm transition-all"
                  style={{ background: "#d97706", color: "#fff" }}
                  onMouseEnter={e => e.currentTarget.style.background = "#b45309"}
                  onMouseLeave={e => e.currentTarget.style.background = "#d97706"}>
                  <ReviewIcon />
                  Review Schema Now
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function XIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 15 15" fill="none">
      <path d="M3 3l9 9M12 3l-9 9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  );
}
function ReviewIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 15 15" fill="none">
      <path d="M3 7.5h9M9 4.5l3 3-3 3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}
