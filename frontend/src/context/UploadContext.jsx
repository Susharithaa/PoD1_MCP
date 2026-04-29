import { createContext, useContext, useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { agentApi } from "../lib/api";

const UploadContext = createContext(null);

export const STAGE_LABELS = {
  UPLOADING:          "Uploading document…",
  INIT:               "Initializing…",
  CLASSIFYING:        "Detecting file type…",
  PARSING:            "Extracting endpoints…",
  SCHEMA_GENERATING:  "Generating schema…",
  RECONCILING:        "Reconciling endpoints…",
  CONFIDENCE_SCORING: "Scoring confidence…",
  HITL_PENDING:       "Ready for HITL review",
  VALIDATING:         "Validating…",
  API_TESTING:        "Testing endpoints…",
  SAVING:             "Saving…",
  SAVED:              "Saved successfully",
  FAILED:             "Processing failed",
  ERROR:              "Processing failed",
};

const TERMINAL_STATES = new Set(["HITL_PENDING", "SAVED", "FAILED", "ERROR"]);

// Stages shown in the progress checklist
export const PIPELINE_STAGES = [
  "CLASSIFYING",
  "PARSING",
  "SCHEMA_GENERATING",
  "RECONCILING",
  "CONFIDENCE_SCORING",
  "HITL_PENDING",
];

/* ── localStorage persistence ──────────────────────────────────────────── */
const STORAGE_KEY = "mcp_hub_bg_uploads";

const PENDING_TTL = 3 * 60 * 1000; // 3 min — discard if HTTP call was cancelled by refresh

function loadPersistedUploads() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    const now = Date.now();
    return parsed.filter(u => {
      if (!u.id) return false;
      // Keep __pending__ only within TTL (after that the HTTP call was likely cancelled)
      if (u.id === "__pending__") return u._ts && (now - u._ts) < PENDING_TTL;
      return true;
    });
  } catch {
    return [];
  }
}

function persistUploads(uploads) {
  try {
    const now = Date.now();
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(
        uploads
          .filter(u => u.id)
          // Stamp __pending__ entries with creation time so TTL works on reload
          .map(u => u.id === "__pending__" ? { ...u, _ts: u._ts ?? now } : u)
      )
    );
  } catch {}
}

export function UploadProvider({ children }) {
  const [overlay, setOverlay]     = useState(null);
  const [bgUploads, setBgUploads] = useState(loadPersistedUploads);   // lazy init from localStorage

  // When user clicks "Notify Once Done" BEFORE the HTTP response arrives,
  // we can't move to background yet (no session id). We store the intent here.
  const backgroundPendingRef = useRef(false);

  const pollRefs = useRef({});
  const navigate = useNavigate();

  /* ── Sync bgUploads → localStorage on every change ───────────────────── */
  useEffect(() => {
    persistUploads(bgUploads);
  }, [bgUploads]);

  /* ── helpers ─────────────────────────────────────────────────────────── */
  const stopPoll = useCallback((id) => {
    if (pollRefs.current[id]) {
      clearInterval(pollRefs.current[id]);
      delete pollRefs.current[id];
    }
  }, []);

  const startPoll = useCallback((id) => {
    pollRefs.current[id] = setInterval(async () => {
      try {
        const session = await agentApi.getSession(id);
        setOverlay(prev =>
          prev?.id === id ? { ...prev, status: session.state } : prev
        );
        if (TERMINAL_STATES.has(session.state)) stopPoll(id);
      } catch {
        stopPoll(id);
        setOverlay(prev => prev?.id === id ? { ...prev, status: "ERROR" } : prev);
      }
    }, 2000);
  }, [stopPoll]);

  const startBgPoll = useCallback((id) => {
    pollRefs.current[id] = setInterval(async () => {
      try {
        const session = await agentApi.getSession(id);
        const patch = { status: session.state };
        if (session.state === "FAILED" || session.state === "ERROR") {
          const last = session.error_log?.at?.(-1) ?? session.error_log?.[session.error_log.length - 1];
          if (last) patch.error = `${last.step}: ${last.error}`;
        }
        setBgUploads(prev =>
          prev.map(u => u.id === id ? { ...u, ...patch } : u)
        );
        if (TERMINAL_STATES.has(session.state)) stopPoll(id);
      } catch {
        stopPoll(id);
        setBgUploads(prev =>
          prev.map(u => u.id === id ? { ...u, status: "ERROR", error: "Could not reach server" } : u)
        );
      }
    }, 3000);
  }, [stopPoll]);

  /* ── On mount: resume polling for uploads that survived a page refresh ── */
  useEffect(() => {
    const persisted = loadPersistedUploads();
    persisted.forEach(u => {
      // __pending__ has no real session ID — can't poll, just show card as-is
      if (u.id !== "__pending__" && !TERMINAL_STATES.has(u.status)) {
        startBgPoll(u.id);
      }
    });
    return () => {
      Object.values(pollRefs.current).forEach(clearInterval);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /* ── Phase 1: called immediately when user clicks submit ─────────────── */
  const beginUpload = useCallback((filename) => {
    backgroundPendingRef.current = false;
    setOverlay({ id: null, filename, status: "UPLOADING", redirecting: false });
  }, []);

  /* ── Phase 2: called when HTTP response arrives with session id ──────── */
  const sessionReady = useCallback((id, filename) => {
    if (backgroundPendingRef.current) {
      // User already clicked "Notify Once Done" before we had the id — replace placeholder
      backgroundPendingRef.current = false;
      setOverlay(null);
      setBgUploads(prev => [
        ...prev.filter(u => u.id !== "__pending__" && u.id !== id),
        { id, filename, status: "PARSING" },
      ]);
      startBgPoll(id);
      return;
    }
    // Normal foreground: transition overlay to pipeline phase and start polling
    setOverlay(prev =>
      prev
        ? { ...prev, id, status: "CLASSIFYING" }
        : { id, filename, status: "CLASSIFYING", redirecting: false }
    );
    startPoll(id);
  }, [startPoll, startBgPoll]);

  /* ── User clicked "Notify Once Done" ─────────────────────────────────── */
  const sendToBackground = useCallback((id, filename, currentStatus) => {
    if (!id) {
      // HTTP not yet returned — mark intent; sessionReady() will handle it.
      // Show a placeholder card immediately so the user sees feedback right away.
      backgroundPendingRef.current = true;
      setOverlay(null);
      setBgUploads(prev => [
        ...prev.filter(u => u.id !== "__pending__"),
        { id: "__pending__", filename, status: "UPLOADING" },
      ]);
      return;
    }
    // Session id known — move to background immediately
    stopPoll(id);
    setOverlay(null);
    setBgUploads(prev => [
      ...prev.filter(u => u.id !== id),
      { id, filename, status: currentStatus || "PARSING" },
    ]);
    startBgPoll(id);
  }, [stopPoll, startBgPoll]);

  /* ── Dismiss overlay (e.g. on error) ─────────────────────────────────── */
  const dismissOverlay = useCallback(() => {
    if (overlay?.id) stopPoll(overlay.id);
    backgroundPendingRef.current = false;
    setOverlay(null);
  }, [overlay, stopPoll]);

  /* ── Dismiss a background notification ───────────────────────────────── */
  const dismissNotification = useCallback((id) => {
    stopPoll(id);
    setBgUploads(prev => prev.filter(u => u.id !== id));
  }, [stopPoll]);

  /* ── Navigate to HITL from notification ──────────────────────────────── */
  const navigateToHITL = useCallback((id) => {
    dismissNotification(id);
    navigate(`/validate/${id}`);
  }, [dismissNotification, navigate]);

  /* ── Auto-redirect when foreground overlay reaches HITL_PENDING ─────── */
  useEffect(() => {
    if (overlay?.status === "HITL_PENDING" && !overlay.redirecting && overlay.id) {
      setOverlay(prev => prev ? { ...prev, redirecting: true } : prev);
      const id = overlay.id;
      setTimeout(() => {
        setOverlay(null);
        navigate(`/validate/${id}`);
      }, 1000);
    }
  }, [overlay?.status, overlay?.id, overlay?.redirecting, navigate]);

  /* ── Upload failed ───────────────────────────────────────────────────── */
  const uploadFailed = useCallback(() => {
    backgroundPendingRef.current = false;
    setOverlay(prev => prev ? { ...prev, status: "ERROR" } : prev);
    // Also mark the placeholder card as failed if in background mode
    setBgUploads(prev =>
      prev.map(u => u.id === "__pending__" ? { ...u, status: "ERROR" } : u)
    );
  }, []);

  // Notifications = bg uploads at terminal state
  const notifications       = bgUploads.filter(u => TERMINAL_STATES.has(u.status));
  const hasActiveBackground = bgUploads.some(u => !TERMINAL_STATES.has(u.status));

  return (
    <UploadContext.Provider value={{
      overlay,
      bgUploads,
      notifications,
      hasActiveBackground,
      beginUpload,
      sessionReady,
      sendToBackground,
      dismissOverlay,
      dismissNotification,
      navigateToHITL,
      uploadFailed,
    }}>
      {children}
    </UploadContext.Provider>
  );
}

export const useUpload = () => useContext(UploadContext);
