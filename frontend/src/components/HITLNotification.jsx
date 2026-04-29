import { useUpload } from "../context/UploadContext";

export default function HITLNotification() {
  const { notifications, bgUploads, navigateToHITL, dismissNotification } = useUpload();

  // In-progress background uploads shown as a subtle status bar
  const inProgress = bgUploads.filter(u => !["HITL_PENDING","SAVED","FAILED","ERROR"].includes(u.status));

  if (!notifications.length && !inProgress.length) return null;

  return (
    <div className="fixed top-3 left-1/2 -translate-x-1/2 z-40 flex flex-col gap-2 w-full max-w-lg px-4 pointer-events-none">

      {/* In-progress background uploads (subtle pill) */}
      {inProgress.map(({ id, filename, status }) => (
        <div key={id}
          className="flex items-center gap-3 px-4 py-2.5 rounded-xl shadow-lg pointer-events-auto
            bg-zinc-900/95 border border-zinc-700/60 backdrop-blur-md">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-zinc-300 truncate">
              Processing in background — {status.replace(/_/g, " ").toLowerCase()}
            </p>
            <p className="text-[10px] text-zinc-600 truncate">{filename}</p>
          </div>
          <span className="flex-shrink-0">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" className="text-blue-400 animate-spin">
              <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" strokeDasharray="28 56" strokeLinecap="round"/>
            </svg>
          </span>
        </div>
      ))}

      {/* Terminal-state notifications (HITL ready / saved / error) */}
      {notifications.map(({ id, filename, status }) => {
        const isError = status === "ERROR" || status === "FAILED";
        const isSaved = status === "SAVED";
        return (
          <div key={id}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl shadow-xl pointer-events-auto
              border backdrop-blur-md
              ${isError
                ? "bg-red-950/90 border-red-500/30"
                : isSaved
                  ? "bg-green-950/90 border-green-500/30"
                  : "bg-zinc-900/97 border-amber-500/40"}`}>

            {/* Status dot */}
            <span className={`w-2 h-2 rounded-full flex-shrink-0
              ${isError ? "bg-red-400" : isSaved ? "bg-green-400 animate-pulse" : "bg-amber-400 animate-pulse"}`} />

            {/* Text */}
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-semibold
                ${isError ? "text-red-300" : isSaved ? "text-green-300" : "text-amber-300"}`}>
                {isError
                  ? "Processing failed"
                  : isSaved
                    ? "Tool saved successfully"
                    : "Tool creation pending — HITL review required"}
              </p>
              <p className="text-[11px] text-zinc-500 truncate mt-0.5">{filename}</p>
            </div>

            {/* CTA */}
            {!isError && !isSaved && (
              <button
                onClick={() => navigateToHITL(id)}
                className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                  bg-amber-500/20 border border-amber-500/30 text-amber-300 text-xs font-semibold
                  hover:bg-amber-500/30 hover:border-amber-400/50 transition-all">
                <ReviewIcon />
                Review Now
              </button>
            )}

            {/* Dismiss */}
            <button
              onClick={() => dismissNotification(id)}
              className="flex-shrink-0 text-zinc-600 hover:text-zinc-400 transition-colors ml-1 p-0.5 rounded">
              <XIcon />
            </button>
          </div>
        );
      })}
    </div>
  );
}

function ReviewIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 15 15" fill="none">
      <path d="M3 7.5h9M9 4.5l3 3-3 3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}
function XIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 15 15" fill="none">
      <path d="M3 3l9 9M12 3l-9 9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  );
}
