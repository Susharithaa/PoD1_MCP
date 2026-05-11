import { useEffect, useRef, useState } from "react";
import { chatgptApi, subscriptionApi, registryApi } from "../lib/api";
import { PageSpinner } from "../components/Spinner";
import Spinner from "../components/Spinner";
import { useLanguage } from "../context/LanguageContext";
import { useAuth } from "../context/AuthContext";

function now() { return Date.now(); }
function fmtTime(ts) {
  if (!ts) return "";
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function ChatGPTHub() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const [apis,           setApis]           = useState([]);
  const [subStatus,      setSubStatus]      = useState(null);
  const [loading,        setLoading]        = useState(true);
  const [toggling,       setToggling]       = useState(null);
  const [search,         setSearch]         = useState("");
  const [activeSession,  setActiveSession]  = useState(null);
  const [requesting,     setRequesting]     = useState(false);
  const [recentSessions, setRecentSessions] = useState([]);

  const isAdmin = user?.role === "admin";

  async function refreshAll() {
    const [s, a, recent] = await Promise.all([
      chatgptApi.getStats(),
      chatgptApi.getRegistry(),
      chatgptApi.listSessions(20),
    ]);
    setApis(a);
    setRecentSessions(recent || []);
    return a;
  }

  useEffect(() => {
    const loads = [chatgptApi.getStats(), chatgptApi.getRegistry(), chatgptApi.listSessions(20)];
    if (!isAdmin) loads.push(subscriptionApi.getStatus());
    Promise.all(loads)
      .then(async ([_s, a, recent, sub]) => {
        setRecentSessions(recent || []);
        if (sub) setSubStatus(sub);
        // Disconnect any APIs that were left connected from a previous session
        const connected = (a || []).filter(api => api.is_connected);
        if (connected.length > 0) {
          await Promise.allSettled(connected.map(api => chatgptApi.disconnect(api.id)));
          const fresh = await chatgptApi.getRegistry();
          setApis(fresh);
        } else {
          setApis(a);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  async function handleRequestAccess() {
    setRequesting(true);
    try {
      await subscriptionApi.requestAccess();
      setSubStatus(s => ({ ...s, chat_status: "pending" }));
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to submit request");
    } finally {
      setRequesting(false);
    }
  }

  async function toggle(api) {
    setToggling(api.id);
    try {
      if (api.is_connected) {
        await chatgptApi.disconnect(api.id);
        setActiveSession(null);
      } else {
        await chatgptApi.connect(api.id);
      }
      await refreshAll();
    } finally {
      setToggling(null);
    }
  }

  const filtered      = apis.filter(a =>
    !search ||
    a.name.toLowerCase().includes(search.toLowerCase()) ||
    a.description?.toLowerCase().includes(search.toLowerCase())
  );
  const connectedApis = apis.filter(a => a.is_connected);

  if (loading) return <PageSpinner />;

  if (!isAdmin && subStatus?.chat_status !== "approved") {
    return <AccessGate status={subStatus?.chat_status || "none"} onRequest={handleRequestAccess} requesting={requesting} t={t} />;
  }
  if (!isAdmin && subStatus?.credits <= 0) {
    return <NoCreditsGate t={t} />;
  }

  return (
    <div className="animate-slide-up space-y-6">

      {/* Page header */}
      <div>
        <p className="eyebrow">{t("Validate")}</p>
        <h1 className="h-page mt-2">{t("MCP Validation")}</h1>
        <p className="lead mt-2">
          {t("Connect your registered APIs and chat with them to validate tool behavior.")}
        </p>
      </div>

      {/* Main content: tool list + chat */}
      <div className="grid grid-cols-[320px_1fr] gap-5 items-start">

        {/* ── Left: Tool list ── */}
        <div className="card p-0 overflow-hidden flex flex-col" style={{ maxHeight: "calc(100vh - 200px)" }}>

          {/* Panel header */}
          <div className="px-4 py-3.5 border-b border-[var(--line)]">
            <div className="flex items-center justify-between">
              <div>
                <p className="eyebrow">Tools</p>
                <p className="text-xs text-[var(--muted)] mt-0.5">
                  {connectedApis.length > 0
                    ? <><span className="text-[var(--ok)] font-medium">{connectedApis.length} active</span> · {apis.length} total</>
                    : <>{apis.length} available · none active</>
                  }
                </p>
              </div>
              {connectedApis.length > 0 && (
                <span className="flex items-center gap-1.5 text-[10px] font-medium text-[var(--ok)] px-2 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Live
                </span>
              )}
            </div>

            {/* Search */}
            {apis.length > 3 && (
              <div className="relative mt-3">
                <svg width="13" height="13" viewBox="0 0 15 15" fill="none"
                  className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none">
                  <circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" strokeWidth="1.4"/>
                  <path d="M10 10l3 3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                </svg>
                <input
                  type="text"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder={t("Search tools…")}
                  className="field-input pl-8 text-xs py-1.5"
                />
              </div>
            )}
          </div>

          {/* Tool rows */}
          <div className="flex-1 overflow-y-auto divide-y divide-[var(--line)]">
            {filtered.length === 0 ? (
              <div className="px-4 py-10 text-center">
                <p className="text-sm text-[var(--muted)]">
                  {apis.length === 0 ? t("No APIs in registry yet.") : t("No matching APIs.")}
                </p>
                {apis.length === 0 && (
                  <p className="text-xs text-[var(--muted)] mt-1 opacity-60">
                    {t("Onboard an API first.")}
                  </p>
                )}
              </div>
            ) : (
              filtered.map(api => (
                <ApiRow
                  key={api.id}
                  api={api}
                  toggling={toggling === api.id}
                  onToggle={() => toggle(api)}
                  t={t}
                />
              ))
            )}
          </div>

          {/* Panel footer hint */}
          {apis.length > 0 && connectedApis.length === 0 && (
            <div className="px-4 py-3 border-t border-[var(--line)] bg-amber-500/5">
              <p className="text-[11px] text-amber-500/80 text-center">
                ↑ Add a tool above to start chatting
              </p>
            </div>
          )}
        </div>

        {/* ── Right: Chat panel ── */}
        <div className="sticky top-6">
          <ChatPanel
            connectedApis={connectedApis}
            chatHeight="calc(100vh - 200px)"
            t={t}
            onStatsRefresh={() => chatgptApi.getStats().catch(() => {})}
            onSessionsRefresh={() => chatgptApi.listSessions(20).then(setRecentSessions).catch(() => {})}
            activeSession={activeSession}
            onSessionChange={setActiveSession}
          />
        </div>
      </div>

      {/* Chat History — full width below */}
      <div className="card p-0 overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--line)] flex items-center justify-between">
          <div>
            <p className="eyebrow">Chat History</p>
            <p className="text-xs text-[var(--muted)] mt-0.5">Recent validation sessions</p>
          </div>
          <span className="pill">{recentSessions.length}</span>
        </div>
        <div className="max-h-72 overflow-y-auto divide-y divide-[var(--line)]">
          {recentSessions.length === 0 ? (
            <div className="px-5 py-8 text-center text-sm text-[var(--muted)]">
              No chat sessions yet. Start a conversation above.
            </div>
          ) : (
            recentSessions.map(session => (
              <button
                key={session.session_id}
                type="button"
                onClick={() => setActiveSession(session.session_id)}
                className={`w-full text-left px-5 py-3.5 transition-colors hover:bg-[var(--hover)]
                  ${activeSession === session.session_id
                    ? "bg-[var(--hover)] border-l-2 border-[var(--ok)]"
                    : ""}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-[var(--ink)] truncate">
                        {session.user_name || session.user_email || "Unknown user"}
                      </p>
                      {session.model && session.model !== "mock" && (
                        <span className="text-[10px] font-mono text-[var(--muted)] flex-shrink-0 px-1.5 py-0.5 rounded border border-[var(--line)]">
                          {session.model}
                        </span>
                      )}
                    </div>
                    {session.message && (
                      <p className="text-xs text-[var(--muted)] mt-1 line-clamp-1">
                        {session.message}
                      </p>
                    )}
                  </div>
                  <span className="text-[11px] text-[var(--muted)] flex-shrink-0 mt-0.5">
                    {fmtSessionAge(session.created_at)}
                  </span>
                </div>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

/* ── API / Tool row ── */
function ApiRow({ api, toggling, onToggle, t }) {
  const [expanded, setExpanded] = useState(false);
  const connected = api.is_connected;

  return (
    <div className={`transition-colors ${connected ? "bg-emerald-500/3" : "hover:bg-[var(--hover)]"}`}>
      <div className="px-4 py-3.5 flex items-start gap-3">

        {/* Status indicator */}
        <div className="mt-1 flex-shrink-0">
          <div className={`w-2 h-2 rounded-full transition-all ${
            connected
              ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]"
              : "bg-[var(--line)]"
          }`} />
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-[var(--ink)] truncate">{api.name}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--panel)] text-[var(--muted)] border border-[var(--line)] font-mono flex-shrink-0">
              {api.endpoint_count ?? 0} {api.endpoint_count === 1 ? "tool" : "tools"}
            </span>
          </div>
          {api.description && (
            <p className="text-xs text-[var(--muted)] mt-0.5 line-clamp-2 leading-relaxed">
              {api.description}
            </p>
          )}
          {api.created_by && (
            <p className="text-[10px] text-[var(--muted)] opacity-60 mt-0.5">by {api.created_by}</p>
          )}

          {/* Tool names (expandable) */}
          {api.tools?.length > 0 && (
            <button
              onClick={() => setExpanded(o => !o)}
              className="mt-1.5 text-[10px] text-[var(--muted)] hover:text-[var(--ink)] transition-colors flex items-center gap-1"
            >
              <svg width="9" height="9" viewBox="0 0 15 15" fill="none"
                className={`transition-transform ${expanded ? "rotate-90" : ""}`}>
                <path d="M5 3l5 4.5L5 12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              {expanded ? "Hide tools" : `View ${api.tools.length} tools`}
            </button>
          )}
        </div>

        {/* Connect / Disconnect */}
        <div className="flex-shrink-0">
          {connected ? (
            <button
              onClick={onToggle}
              disabled={toggling}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg font-medium
                         border border-red-500/25 bg-red-500/8 text-red-400
                         hover:bg-red-500/15 hover:border-red-500/40
                         transition-all disabled:opacity-50"
            >
              {toggling ? <Spinner size={10} /> : (
                <svg width="10" height="10" viewBox="0 0 15 15" fill="none">
                  <path d="M3 3l9 9M12 3l-9 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              )}
              {toggling ? "…" : "Remove"}
            </button>
          ) : (
            <button
              onClick={onToggle}
              disabled={toggling}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg font-medium
                         border border-[var(--line)] bg-[var(--surface)] text-[var(--muted)]
                         hover:bg-emerald-500/10 hover:text-emerald-400 hover:border-emerald-500/30
                         transition-all disabled:opacity-50"
            >
              {toggling ? <Spinner size={10} /> : (
                <svg width="10" height="10" viewBox="0 0 15 15" fill="none">
                  <path d="M7.5 1v13M1 7.5h13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              )}
              {toggling ? "…" : "Add"}
            </button>
          )}
        </div>
      </div>

      {/* Expanded tool list */}
      {expanded && api.tools?.length > 0 && (
        <div className="mx-4 mb-3 rounded-lg border border-[var(--line)] bg-[var(--panel)] divide-y divide-[var(--line)] overflow-hidden">
          {api.tools.map((tool, i) => (
            <div key={i} className="px-3 py-2">
              <span className="text-[11px] font-mono font-semibold text-blue-400">{tool.function.name}</span>
              {tool.function.description && (
                <p className="text-[10px] text-[var(--muted)] mt-0.5 leading-relaxed">{tool.function.description}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════════════
   Chat Panel
═══════════════════════════════════════════════════════════════════════════ */
function ChatPanel({
  connectedApis, onStatsRefresh, onSessionsRefresh,
  chatHeight, t, activeSession, onSessionChange,
}) {
  const [messages,       setMessages]       = useState([]);
  const [input,          setInput]          = useState("");
  const [sending,        setSending]        = useState(false);
  const [loadingSession, setLoadingSession] = useState(false);
  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  useEffect(() => {
    if (!activeSession) { setMessages([]); return; }
    setLoadingSession(true);
    chatgptApi.getSession(activeSession)
      .then(info => {
        const transcript = Array.isArray(info?.history) ? info.history : [];
        setMessages(transcript.map(normalizeMessage));
      })
      .catch(() => {
        setMessages([{ role: "error", content: "Unable to load this chat history.", ts: now() }]);
      })
      .finally(() => setLoadingSession(false));
  }, [activeSession]);

  async function send() {
    const text = input.trim();
    if (!text || sending) return;

    setMessages(m => [...m, { role: "user", content: text, ts: now() }]);
    setInput("");
    setSending(true);

    if (connectedApis.length === 0) {
      setSending(false);
      setMessages(m => [...m, { role: "system", type: "no_tools", ts: now() }]);
      return;
    }

    try {
      const res = await chatgptApi.chat(text, [], activeSession);
      if (res.session_id) onSessionChange(res.session_id);

      if (res.status === "NO_TOOLS_CONNECTED") {
        setMessages(m => [...m, { role: "system", type: "no_tools", ts: now() }]);
      } else if (res.status === "NO_RELEVANT_TOOL") {
        setMessages(m => [...m, {
          role: "system", type: "no_relevant_tool",
          available_tools: res.available_tools, query: text, ts: now(),
        }]);
      } else {
        setMessages(m => [...m, {
          role: "assistant", content: res.response,
          tool_calls: res.tool_calls, model: res.model, ts: now(),
        }]);
        onStatsRefresh();
        onSessionsRefresh();
      }
    } catch (err) {
      setMessages(m => [...m, {
        role: "error",
        content: err.response?.data?.detail || t("Request failed."),
        ts: now(),
      }]);
    } finally {
      setSending(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }

  const noTools  = connectedApis.length === 0;
  const toolNames = connectedApis.flatMap(a => a.tools?.map(tool => tool.function.name) || []);

  return (
    <div className="card p-0 flex flex-col overflow-hidden" style={{ height: chatHeight || "680px" }}>

      {/* Chat header */}
      <div className="px-4 py-3.5 border-b border-[var(--line)] flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className={`w-2 h-2 rounded-full flex-shrink-0 transition-all ${
            noTools
              ? "bg-[var(--line)]"
              : "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)] animate-pulse"
          }`} />
          <span className="text-sm font-semibold text-[var(--ink)]">{t("MCP Chat")}</span>
          {!noTools && (
            <span className="text-[10px] font-medium px-2 py-0.5 rounded-full
                             bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              {connectedApis.length} {connectedApis.length === 1 ? "tool" : "tools"} active
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 text-[10px] text-[var(--muted)]">
          <span className="font-mono">GPT-4o</span>
          <span className="opacity-40">·</span>
          <span>MCP Hub</span>
        </div>
      </div>

      {/* Connected tools summary bar */}
      {!noTools && (
        <div className="px-4 py-2 border-b border-[var(--line)] bg-emerald-500/3 flex items-center gap-2 flex-wrap flex-shrink-0">
          <span className="text-[10px] text-[var(--muted)] font-medium uppercase tracking-wider">Active:</span>
          {connectedApis.map(api => (
            <span key={api.id} className="text-[10px] px-2 py-0.5 rounded-full
                                           border border-emerald-500/20 bg-emerald-500/8 text-emerald-400 font-medium">
              {api.name}
            </span>
          ))}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-5 space-y-5">
        {loadingSession && (
          <div className="flex items-center gap-2 text-sm text-[var(--muted)] justify-center py-6">
            <Spinner size={13} /> Loading history…
          </div>
        )}
        {!loadingSession && messages.length === 0 && (
          <EmptyState noTools={noTools} toolNames={toolNames} t={t} />
        )}
        {messages.map((msg, i) => <MessageRow key={i} msg={msg} t={t} />)}
        {sending && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="px-4 py-3.5 border-t border-[var(--line)] flex-shrink-0 bg-[var(--surface)]">
        {noTools && (
          <div className="flex items-center gap-2 mb-2.5 px-3 py-2 rounded-lg
                          bg-amber-500/8 border border-amber-500/15">
            <svg width="12" height="12" viewBox="0 0 15 15" fill="none" className="text-amber-400 flex-shrink-0">
              <path d="M7.5 1.5L13 13H2L7.5 1.5Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
              <path d="M7.5 6v3.5M7.5 11h.01" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
            </svg>
            <p className="text-xs text-amber-400/90">
              {t("No tools added — click Add on an API from the panel on the left")}
            </p>
          </div>
        )}
        <div className="flex gap-2 items-end">
          <textarea
            ref={inputRef}
            rows={1}
            value={input}
            onChange={e => {
              setInput(e.target.value);
              e.target.style.height = "auto";
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
            }}
            onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
            }}
            disabled={sending}
            placeholder={noTools ? t("Add a tool first…") : t("Ask anything about your added tools…")}
            className="field-input flex-1 resize-none overflow-hidden min-h-[42px] disabled:opacity-40 leading-relaxed py-2.5 text-sm"
            style={{ lineHeight: "1.5" }}
          />
          <button
            onClick={send}
            disabled={sending || !input.trim()}
            className="btn-primary h-[42px] px-4 flex-shrink-0 disabled:opacity-40 flex items-center gap-1.5"
          >
            {sending ? <Spinner size={13} /> : (
              <svg width="14" height="14" viewBox="0 0 15 15" fill="none">
                <path d="M1 7.5h13M9 3l5 4.5L9 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            )}
          </button>
        </div>
        <p className="text-[10px] text-[var(--muted)] opacity-50 mt-1.5 text-right">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}

/* ── Message row ── */
function MessageRow({ msg, t }) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end items-end gap-2 group">
        <div className="flex flex-col items-end gap-1">
          <div className="max-w-md px-4 py-2.5 rounded-2xl rounded-br-sm
                          bg-blue-600 text-white text-sm leading-relaxed">
            {msg.content}
          </div>
          <span className="text-[10px] text-[var(--muted)] opacity-0 group-hover:opacity-100 transition-opacity pr-1">
            {fmtTime(msg.ts)}
          </span>
        </div>
        <div className="w-7 h-7 rounded-full bg-blue-600/20 border border-blue-500/20
                        flex items-center justify-center flex-shrink-0 mb-4">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="1.8"/>
            <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
          </svg>
        </div>
      </div>
    );
  }

  if (msg.role === "assistant") {
    return (
      <div className="flex items-end gap-2 group">
        <div className="w-7 h-7 rounded-full bg-[var(--surface)] border border-[var(--line)]
                        flex items-center justify-center flex-shrink-0 mb-4">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="8" width="18" height="12" rx="3" stroke="currentColor" strokeWidth="1.6"/>
            <path d="M9 12h.01M15 12h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <path d="M12 8V4M9 4h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
          </svg>
        </div>
        <div className="flex flex-col gap-1.5 max-w-md flex-1">
          {msg.tool_calls?.length > 0 && (
            <div className="space-y-1">
              {msg.tool_calls.map((tc, j) => <ToolCallPill key={j} tc={tc} t={t} />)}
            </div>
          )}
          {msg.content && (
            <div className="px-4 py-2.5 rounded-2xl rounded-bl-sm
                            bg-[var(--surface)] border border-[var(--line)]
                            text-[var(--ink)] text-sm leading-relaxed whitespace-pre-wrap">
              {msg.content}
            </div>
          )}
          <div className="flex items-center gap-2 pl-1">
            <span className="text-[10px] text-[var(--muted)] opacity-0 group-hover:opacity-100 transition-opacity">
              {fmtTime(msg.ts)}
            </span>
            {msg.model && msg.model !== "mock" && (
              <span className="text-[10px] text-[var(--muted)] font-mono opacity-60">{msg.model}</span>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (msg.role === "system" && msg.type === "no_tools") {
    return (
      <div className="flex justify-center">
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/8 px-5 py-3 text-center max-w-xs">
          <p className="text-xs font-semibold text-amber-400 mb-1">{t("No tools connected")}</p>
          <p className="text-xs text-[var(--muted)]">
            {t("Connect an API from the list on the left to enable tool-powered responses.")}
          </p>
        </div>
      </div>
    );
  }

  if (msg.role === "system" && msg.type === "no_relevant_tool") {
    return (
      <div className="flex justify-center">
        <div className="rounded-xl border border-[var(--line)] bg-[var(--panel)] px-5 py-3 max-w-xs w-full">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[var(--muted)] text-sm">⊘</span>
            <p className="text-xs font-semibold text-[var(--ink)]">{t("No matching tool")}</p>
          </div>
          <p className="text-xs text-[var(--muted)] mb-3">
            {t("Your question doesn't relate to any connected tool. Available tools:")}
          </p>
          <div className="space-y-1">
            {(msg.available_tools || []).map((name, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="w-1 h-1 rounded-full bg-[var(--muted)] flex-shrink-0" />
                <span className="text-xs font-mono text-[var(--muted)]">{name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (msg.role === "error") {
    return (
      <div className="flex justify-center">
        <span className="text-xs text-red-400 px-3 py-1.5 rounded-full bg-red-500/10 border border-red-500/20">
          {msg.content}
        </span>
      </div>
    );
  }

  return null;
}

/* ── Tool call pill ── */
function ToolCallPill({ tc, t }) {
  const [open, setOpen] = useState(false);
  const isMissing = (() => {
    try { return JSON.parse(tc.result)?.status === "MISSING_REQUIRED_PARAMETERS"; }
    catch { return false; }
  })();

  const statusColor = isMissing
    ? "text-amber-400 bg-amber-500/10 border-amber-500/20"
    : tc.success
      ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
      : "text-red-400 bg-red-500/10 border-red-500/20";
  const statusIcon  = isMissing ? "?" : tc.success ? "✓" : "✕";

  return (
    <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] text-xs overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-[var(--hover)] transition-colors"
      >
        <span className={`w-4 h-4 rounded flex items-center justify-center text-[9px] font-bold flex-shrink-0 border ${statusColor}`}>
          {statusIcon}
        </span>
        <span className="flex-1 font-mono text-[var(--muted)] truncate">
          {tc.api_name}<span className="opacity-40 mx-1">›</span>{tc.endpoint}
        </span>
        <svg width="11" height="11" viewBox="0 0 15 15" fill="none"
          className={`text-[var(--muted)] transition-transform flex-shrink-0 ${open ? "rotate-180" : ""}`}>
          <path d="M3 5l4.5 5L12 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>
      {open && (
        <div className="border-t border-[var(--line)] px-3 py-2.5 space-y-2.5">
          <div>
            <p className="text-[10px] font-semibold text-[var(--muted)] uppercase tracking-wider mb-1">{t("Arguments")}</p>
            <pre className="font-mono text-[var(--muted)] overflow-x-auto text-[11px] leading-relaxed">
              {JSON.stringify(tc.arguments, null, 2)}
            </pre>
          </div>
          <div>
            <p className="text-[10px] font-semibold text-[var(--muted)] uppercase tracking-wider mb-1">{t("Result")}</p>
            <pre className={`font-mono overflow-x-auto text-[11px] leading-relaxed max-h-36 ${isMissing ? "text-amber-400/80" : "text-[var(--muted)]"}`}>
              {(() => { try { return JSON.stringify(JSON.parse(tc.result), null, 2); } catch { return tc.result; } })()}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Typing indicator ── */
function TypingIndicator() {
  return (
    <div className="flex items-end gap-2">
      <div className="w-7 h-7 rounded-full bg-[var(--surface)] border border-[var(--line)]
                      flex items-center justify-center flex-shrink-0">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
          <rect x="3" y="8" width="18" height="12" rx="3" stroke="currentColor" strokeWidth="1.6"/>
          <path d="M9 12h.01M15 12h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          <path d="M12 8V4M9 4h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
        </svg>
      </div>
      <div className="px-4 py-3 rounded-2xl rounded-bl-sm bg-[var(--surface)] border border-[var(--line)] flex items-center gap-1.5">
        {[0, 1, 2].map(i => (
          <span
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-[var(--muted)]"
            style={{ animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite` }}
          />
        ))}
      </div>
    </div>
  );
}

/* ── Empty chat state ── */
function EmptyState({ noTools, toolNames, t }) {
  return (
    <div className="h-full flex flex-col items-center justify-center text-center px-6 py-8">
      <div className="w-14 h-14 rounded-2xl bg-[var(--panel)] border border-[var(--line)]
                      flex items-center justify-center mb-4 text-[var(--muted)]">
        <svg width="22" height="22" viewBox="0 0 15 15" fill="none">
          <path d="M2 2h11a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H5l-3 3V3a1 1 0 0 1 1-1Z"
                stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
        </svg>
      </div>

      {noTools ? (
        <>
          <p className="text-sm font-semibold text-[var(--ink)] mb-1">{t("No tools connected")}</p>
          <p className="text-xs text-[var(--muted)] max-w-[200px] leading-relaxed">
            {t("Select and connect an API from the panel on the left to start validating.")}
          </p>
          <div className="mt-4 flex items-center gap-2 text-[10px] text-[var(--muted)] bg-[var(--panel)] border border-[var(--line)] rounded-lg px-3 py-2">
            <svg width="10" height="10" viewBox="0 0 15 15" fill="none" className="text-amber-400 flex-shrink-0">
              <path d="M7.5 1L13 13H2L7.5 1Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
              <path d="M7.5 6v3M7.5 11h.01" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
            </svg>
            Click "Add" on any tool to begin
          </div>
        </>
      ) : (
        <>
          <p className="text-sm font-semibold text-[var(--ink)] mb-1">{t("Ready to validate")}</p>
          <p className="text-xs text-[var(--muted)] max-w-[210px] mb-5 leading-relaxed">
            {t("Ask anything related to your connected tools.")}
          </p>
          {toolNames.length > 0 && (
            <div className="w-full max-w-xs space-y-1.5 text-left">
              <p className="text-[10px] font-semibold text-[var(--muted)] uppercase tracking-wider mb-2">
                {t("Available tools")}
              </p>
              {toolNames.slice(0, 6).map((name, i) => (
                <div key={i} className="flex items-center gap-2 px-3 py-1.5 rounded-lg
                                        bg-[var(--panel)] border border-[var(--line)]">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0" />
                  <span className="text-xs font-mono text-[var(--muted)] truncate">{name}</span>
                </div>
              ))}
              {toolNames.length > 6 && (
                <p className="text-xs text-[var(--muted)] text-center pt-1 opacity-60">
                  +{toolNames.length - 6} more
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ── Subscription gates ── */
function AccessGate({ status, onRequest, requesting, t }) {
  const states = {
    none:     { icon: "🔒", title: "Chat Access Required",  desc: "Request access to use MCP Chat. An admin will review and approve your request.", action: true },
    pending:  { icon: "⏳", title: "Request Pending",        desc: "Your access request has been submitted. You'll be able to chat once an admin approves it.", action: false },
    rejected: { icon: "✕",  title: "Access Denied",          desc: "Your request was not approved. Contact an admin if you believe this is a mistake.", action: true },
  };
  const s = states[status] || states.none;
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="card p-8 max-w-sm w-full text-center space-y-4">
        <div className="text-4xl">{s.icon}</div>
        <div>
          <p className="text-base font-semibold text-[var(--ink)]">{s.title}</p>
          <p className="text-sm text-[var(--muted)] mt-1">{s.desc}</p>
        </div>
        {s.action && (
          <button onClick={onRequest} disabled={requesting}
            className="btn-primary w-full justify-center disabled:opacity-60">
            {requesting ? <Spinner size={14} /> : "Request Access"}
          </button>
        )}
      </div>
    </div>
  );
}

function NoCreditsGate({ t }) {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="card p-8 max-w-sm w-full text-center space-y-4">
        <div className="text-4xl">💳</div>
        <div>
          <p className="text-base font-semibold text-[var(--ink)]">No Credits Remaining</p>
          <p className="text-sm text-[var(--muted)] mt-1">Your credit balance is $0.00. Contact an admin to top up your account.</p>
        </div>
      </div>
    </div>
  );
}

/* ── Helpers ── */
function fmtSessionAge(iso) {
  const secs = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (secs < 60)   return `${secs}s ago`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  return `${Math.floor(secs / 3600)}h ago`;
}

function normalizeMessage(msg) {
  if (!msg || typeof msg !== "object") return { role: "system", type: "no_tools", ts: now() };
  const ts = msg.ts ? Date.parse(msg.ts) : now();
  if (msg.role === "assistant") return { role: "assistant", content: msg.content || "", tool_calls: msg.tool_calls || [], model: msg.model, ts };
  if (msg.role === "tool")      return { role: "tool", tool_call_id: msg.tool_call_id, content: msg.content || "", ts };
  if (msg.role === "error")     return { role: "error", content: msg.content || "Error", ts };
  if (msg.role === "system" && msg.type) return { role: "system", type: msg.type, available_tools: msg.available_tools || [], query: msg.query, ts };
  return { role: "user", content: msg.content || "", ts };
}
