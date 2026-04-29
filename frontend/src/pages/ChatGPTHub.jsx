import { useEffect, useRef, useState } from "react";
import { chatgptApi, subscriptionApi } from "../lib/api";
import { PageSpinner } from "../components/Spinner";
import Spinner from "../components/Spinner";
import { useLanguage } from "../context/LanguageContext";
import { useAuth } from "../context/AuthContext";

function now() { return Date.now(); }
function fmtTime(ts) {
  if (!ts) return "";
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

const CHAT_HEIGHT_NORMAL   = "calc(100vh - 220px)";
const CHAT_HEIGHT_EXPANDED = "calc(100vh - 84px)";

export default function ChatGPTHub() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const [stats,         setStats]         = useState(null);
  const [apis,          setApis]          = useState([]);
  const [subStatus,     setSubStatus]     = useState(null);
  const [loading,       setLoading]       = useState(true);
  const [toggling,      setToggling]      = useState(null);
  const [search,        setSearch]        = useState("");
  const [expanded,      setExpanded]      = useState(false);
  const [activeSession, setActiveSession] = useState(null);
  const [requesting,    setRequesting]    = useState(false);

  const isAdmin = user?.role === "admin";

  useEffect(() => {
    const loads = [chatgptApi.getStats(), chatgptApi.getRegistry()];
    if (!isAdmin) loads.push(subscriptionApi.getStatus());
    Promise.all(loads)
      .then(([s, a, sub]) => { setStats(s); setApis(a); if (sub) setSubStatus(sub); })
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
        setActiveSession(null); // stale tool history must not persist
      } else {
        await chatgptApi.connect(api.id);
      }
      const [s, a] = await Promise.all([chatgptApi.getStats(), chatgptApi.getRegistry()]);
      setStats(s); setApis(a);
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

  // ── Subscription gate (non-admins only) ──────────────────────────────────
  if (!isAdmin && subStatus?.chat_status !== "approved") {
    return <AccessGate status={subStatus?.chat_status || "none"} onRequest={handleRequestAccess} requesting={requesting} t={t} />;
  }
  if (!isAdmin && subStatus?.credits <= 0) {
    return <NoCreditsGate t={t} />;
  }

  /* ── Expanded (full-screen chat) mode ── */
  if (expanded) {
    return (
      <div className="animate-slide-up">
        {/* Compact header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <h1 className="text-base font-semibold text-zinc-100">{t("MCP Chat")}</h1>
            {connectedApis.length > 0 && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10
                               border border-emerald-500/20 text-emerald-400">
                {connectedApis.length} {connectedApis.length === 1 ? t("tool active") : t("tools active")}
              </span>
            )}
          </div>
          <button
            onClick={() => setExpanded(false)}
            className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300
                       px-3 py-1.5 rounded-lg border border-zinc-800 hover:border-zinc-700
                       bg-zinc-900 transition-colors"
          >
            <ShrinkIcon /> {t("Split view")}
          </button>
        </div>
        <ChatPanel
          connectedApis={connectedApis}
          chatHeight={CHAT_HEIGHT_EXPANDED}
          expanded
          onToggleExpand={() => setExpanded(false)}
          t={t}
          onStatsRefresh={() => chatgptApi.getStats().then(setStats)}
          activeSession={activeSession}
          onSessionChange={setActiveSession}
        />
      </div>
    );
  }

  /* ── Normal split view ── */
  return (
    <div className="animate-slide-up">
      {/* Header */}
      <div className="mb-6">
        <h1 className="page-title">{t("ChatGPT Integration")}</h1>
        <p className="page-subtitle mt-1">
          {t("Connect API tools to ChatGPT and run a live conversation with them.")}
        </p>
      </div>

      {/* Stats */}
      <div className={`grid gap-3 mb-4 ${isAdmin ? "grid-cols-3" : "grid-cols-4"}`}>
        <StatCard label={t("Total APIs")}           value={stats?.total_apis ?? 0}       icon={<LayersIcon />} />
        <StatCard label={t("Connected to ChatGPT")} value={stats?.connected_apis ?? 0}   icon={<PlugIcon />}  accent="emerald" />
        <StatCard label={t("Tool Calls Made")}      value={stats?.total_tool_calls ?? 0} icon={<BoltIcon />}  accent="blue" />
        {!isAdmin && (
          <StatCard
            label={t("Credits")}
            value={`$${(subStatus?.credits ?? 0).toFixed(4)}`}
            icon={<CreditIcon />}
            accent="violet"
          />
        )}
      </div>

      <div className="grid grid-cols-[1fr_460px] gap-5 items-start">
        {/* Left — API list, scrolls independently */}
        <div
          className="overflow-y-auto pr-1"
          style={{ maxHeight: CHAT_HEIGHT_NORMAL }}
        >
          <div className="flex items-center justify-between mb-3">
            <p className="section-title">{t("Available APIs")}</p>
            <span className="text-xs text-zinc-600">
              {connectedApis.length} {t("connected")}
            </span>
          </div>

          {apis.length > 0 && (
            <div className="relative mb-3">
              <SearchIcon />
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder={t("Search APIs…")}
                className="input pl-9"
              />
            </div>
          )}

          {filtered.length === 0 ? (
            <div className="card p-10 text-center">
              <p className="text-zinc-500 text-sm">{t("No APIs in registry yet.")}</p>
              <p className="text-zinc-600 text-xs mt-1">{t("Create one via Chat Builder or Doc Upload.")}</p>
            </div>
          ) : (
            <div className="space-y-2 pb-2">
              {filtered.map(api => (
                <ApiRow key={api.id} api={api} toggling={toggling === api.id}
                  onToggle={() => toggle(api)} t={t} />
              ))}
            </div>
          )}
        </div>

        {/* Right — Chat panel, sticky so it never scrolls off screen */}
        <div className="sticky top-8">
          <ChatPanel
            connectedApis={connectedApis}
            chatHeight={CHAT_HEIGHT_NORMAL}
            onToggleExpand={() => setExpanded(true)}
            t={t}
            onStatsRefresh={() => chatgptApi.getStats().then(setStats)}
            activeSession={activeSession}
            onSessionChange={setActiveSession}
          />
        </div>
      </div>
    </div>
  );
}

/* ── API row ── */
function ApiRow({ api, toggling, onToggle, t }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className={`card transition-all ${api.is_connected
      ? "border-emerald-500/25 bg-emerald-500/3"
      : "hover:border-zinc-700"}`}>
      <div className="px-4 py-3 flex items-center gap-3">
        <div className={`w-2 h-2 rounded-full flex-shrink-0 transition-colors ${
          api.is_connected ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)]" : "bg-zinc-700"
        }`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-zinc-100 truncate">{api.name}</span>
            <span className="text-xs px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-500 font-mono flex-shrink-0">
              {api.endpoint_count} {api.endpoint_count !== 1 ? "tools" : "tool"}
            </span>
          </div>
          {api.description && (
            <p className="text-xs text-zinc-600 truncate mt-0.5">{api.description}</p>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {api.tools?.length > 0 && (
            <button onClick={() => setExpanded(e => !e)}
              className="text-xs text-zinc-600 hover:text-zinc-400 px-2 py-1 rounded hover:bg-zinc-800 transition-colors">
              {expanded ? t("Hide") : t("Schema")}
            </button>
          )}
          <button onClick={onToggle} disabled={toggling}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg font-medium
                        transition-all disabled:opacity-50
                        ${api.is_connected
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/25"
                          : "bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-blue-500/10 hover:text-blue-400 hover:border-blue-500/25"}`}>
            {toggling ? <Spinner size={11} /> : api.is_connected ? <UnplugIcon /> : <PlugSmIcon />}
            {api.is_connected ? t("Connected") : t("Connect")}
          </button>
        </div>
      </div>
      {expanded && api.tools?.length > 0 && (
        <div className="border-t border-zinc-800 px-4 py-3 space-y-2 animate-fade-in">
          {api.tools.map((tool, i) => (
            <div key={i} className="rounded-lg bg-zinc-950 border border-zinc-800 p-3">
              <span className="text-xs font-mono text-blue-400">{tool.function.name}</span>
              <p className="text-xs text-zinc-500 mt-1">{tool.function.description}</p>
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
function ChatPanel({ connectedApis, onStatsRefresh, chatHeight, expanded, onToggleExpand, t, activeSession, onSessionChange }) {
  const [messages, setMessages] = useState([]);
  const [input,    setInput]    = useState("");
  const [sending,  setSending]  = useState(false);
  const bottomRef  = useRef(null);
  const inputRef   = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function send() {
    const text = input.trim();
    if (!text || sending) return;

    const userMsg = { role: "user", content: text, ts: now() };
    setMessages(m => [...m, userMsg]);
    setInput("");
    setSending(true);

    // Pre-flight: no tools connected at all
    if (connectedApis.length === 0) {
      setSending(false);
      setMessages(m => [...m, {
        role: "system",
        type: "no_tools",
        ts: now(),
      }]);
      return;
    }

    try {
      const res = await chatgptApi.chat(text, [], activeSession);

      if (res.session_id) onSessionChange(res.session_id);

      if (res.status === "NO_TOOLS_CONNECTED") {
        setMessages(m => [...m, { role: "system", type: "no_tools", ts: now() }]);
      } else if (res.status === "NO_RELEVANT_TOOL") {
        setMessages(m => [...m, {
          role: "system",
          type: "no_relevant_tool",
          available_tools: res.available_tools,
          query: text,
          ts: now(),
        }]);
      } else {
        setMessages(m => [...m, {
          role: "assistant",
          content: res.response,
          tool_calls: res.tool_calls,
          model: res.model,
          ts: now(),
        }]);
        onStatsRefresh();
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

  const noTools     = connectedApis.length === 0;
  const toolNames   = connectedApis.flatMap(a => a.tools?.map(t => t.function.name) || []);

  return (
    <div className="card flex flex-col overflow-hidden" style={{ height: chatHeight || "680px" }}>

      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className={`w-2 h-2 rounded-full transition-colors ${
            noTools ? "bg-zinc-600" : "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)]"
          }`} />
          <span className="text-sm font-semibold text-zinc-100">{t("MCP Chat")}</span>
          {!noTools && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              {connectedApis.length} {connectedApis.length === 1 ? t("tool active") : t("tools active")}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-zinc-600 font-mono">GPT-4o</span>
          <div className="w-1 h-1 rounded-full bg-zinc-700" />
          <span className="text-[10px] text-zinc-600">MCP Hub</span>
          {onToggleExpand && (
            <button
              onClick={onToggleExpand}
              title={expanded ? t("Split view") : t("Expand")}
              className="ml-1 p-1.5 rounded-lg text-zinc-600 hover:text-zinc-300
                         hover:bg-zinc-800 transition-colors"
            >
              {expanded ? <ShrinkIcon /> : <ExpandIcon />}
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-5 space-y-5">
        {messages.length === 0 && (
          <EmptyState noTools={noTools} toolNames={toolNames} t={t} />
        )}

        {messages.map((msg, i) => (
          <MessageRow key={i} msg={msg} t={t} />
        ))}

        {sending && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-zinc-800 flex-shrink-0">
        {noTools && (
          <div className="flex items-center gap-2 mb-2.5 px-3 py-2 rounded-lg
                          bg-amber-500/8 border border-amber-500/15">
            <span className="text-amber-400 text-xs">⚠</span>
            <p className="text-xs text-amber-400/80">
              {t("No tools connected — connect an API on the left first")}
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
            placeholder={noTools ? t("Connect an API first…") : t("Ask anything about your connected tools…")}
            className="input flex-1 resize-none overflow-hidden min-h-[40px] disabled:opacity-40
                       leading-relaxed py-2.5"
            style={{ lineHeight: "1.5" }}
          />
          <button
            onClick={send}
            disabled={sending || !input.trim()}
            className="btn-primary px-4 h-10 flex-shrink-0 disabled:opacity-40"
          >
            {sending ? <Spinner size={13} /> : <SendIcon />}
          </button>
        </div>
        <p className="text-[10px] text-zinc-700 mt-1.5 text-right">
          {t("Enter to send")} · Shift+Enter {t("for new line")}
        </p>
      </div>
    </div>
  );
}

/* ── Individual message row ── */
function MessageRow({ msg, t }) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end items-end gap-2 group">
        <div className="flex flex-col items-end gap-1">
          <div className="max-w-sm px-4 py-2.5 rounded-2xl rounded-br-sm
                          bg-blue-600 text-white text-sm leading-relaxed">
            {msg.content}
          </div>
          <span className="text-[10px] text-zinc-700 opacity-0 group-hover:opacity-100 transition-opacity pr-1">
            {fmtTime(msg.ts)}
          </span>
        </div>
        <div className="w-7 h-7 rounded-full bg-blue-600/20 border border-blue-500/20
                        flex items-center justify-center flex-shrink-0 mb-4">
          <UserIcon />
        </div>
      </div>
    );
  }

  if (msg.role === "assistant") {
    return (
      <div className="flex items-end gap-2 group">
        <div className="w-7 h-7 rounded-full bg-zinc-800 border border-zinc-700
                        flex items-center justify-center flex-shrink-0 mb-4">
          <BotIcon />
        </div>
        <div className="flex flex-col gap-1 max-w-sm">
          {msg.tool_calls?.length > 0 && (
            <div className="space-y-1 mb-1">
              {msg.tool_calls.map((tc, j) => (
                <ToolCallPill key={j} tc={tc} t={t} />
              ))}
            </div>
          )}
          {msg.content && (
            <div className="px-4 py-2.5 rounded-2xl rounded-bl-sm
                            bg-zinc-800 border border-zinc-700 text-zinc-100 text-sm
                            leading-relaxed whitespace-pre-wrap">
              {msg.content}
            </div>
          )}
          <div className="flex items-center gap-2 pl-1">
            <span className="text-[10px] text-zinc-700 opacity-0 group-hover:opacity-100 transition-opacity">
              {fmtTime(msg.ts)}
            </span>
            {msg.model && msg.model !== "mock" && (
              <span className="text-[10px] text-zinc-700 font-mono">{msg.model}</span>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (msg.role === "system" && msg.type === "no_tools") {
    return (
      <div className="flex justify-center">
        <div className="max-w-xs w-full rounded-xl border border-amber-500/20
                        bg-amber-500/8 px-4 py-3 text-center">
          <p className="text-xs font-semibold text-amber-400 mb-1">
            {t("No tools connected")}
          </p>
          <p className="text-xs text-zinc-500">
            {t("Connect an API from the list on the left to enable tool-powered responses.")}
          </p>
        </div>
      </div>
    );
  }

  if (msg.role === "system" && msg.type === "no_relevant_tool") {
    return (
      <div className="flex justify-center">
        <div className="max-w-xs w-full rounded-xl border border-zinc-700
                        bg-zinc-900 px-4 py-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-zinc-500 text-sm">⊘</span>
            <p className="text-xs font-semibold text-zinc-300">
              {t("No matching tool")}
            </p>
          </div>
          <p className="text-xs text-zinc-500 mb-3">
            {t("Your question doesn't relate to any connected tool. Available tools:")}
          </p>
          <div className="space-y-1">
            {(msg.available_tools || []).map((name, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="w-1 h-1 rounded-full bg-zinc-600 flex-shrink-0" />
                <span className="text-xs font-mono text-zinc-400">{name}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-zinc-600 mt-3 border-t border-zinc-800 pt-2">
            {t("Try asking something related to the tools above.")}
          </p>
        </div>
      </div>
    );
  }

  if (msg.role === "error") {
    return (
      <div className="flex justify-center">
        <span className="text-xs text-red-400 px-3 py-1.5 rounded-full
                         bg-red-500/10 border border-red-500/20">
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

  const statusIcon = isMissing ? "?" : tc.success ? "✓" : "✕";

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950 text-xs overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left
                   hover:bg-zinc-900/60 transition-colors"
      >
        <span className={`w-4 h-4 rounded flex items-center justify-center text-[9px]
                          font-bold flex-shrink-0 border ${statusColor}`}>
          {statusIcon}
        </span>
        <span className="flex-1 font-mono text-zinc-400 truncate">
          {tc.api_name}
          <span className="text-zinc-600 mx-1">›</span>
          {tc.endpoint}
        </span>
        <span className="text-zinc-700 text-[10px]">{t("details")}</span>
        <ChevronSmIcon open={open} />
      </button>

      {open && (
        <div className="border-t border-zinc-800 px-3 py-2.5 space-y-2.5 animate-fade-in">
          <div>
            <p className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider mb-1">
              {t("Arguments")}
            </p>
            <pre className="font-mono text-zinc-400 overflow-x-auto text-[11px] leading-relaxed">
              {JSON.stringify(tc.arguments, null, 2)}
            </pre>
          </div>
          <div>
            <p className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider mb-1">
              {t("Result")}
            </p>
            <pre className={`font-mono overflow-x-auto text-[11px] leading-relaxed max-h-36
                             ${isMissing ? "text-amber-400/80" : "text-zinc-400"}`}>
              {(() => {
                try { return JSON.stringify(JSON.parse(tc.result), null, 2); }
                catch { return tc.result; }
              })()}
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
      <div className="w-7 h-7 rounded-full bg-zinc-800 border border-zinc-700
                      flex items-center justify-center flex-shrink-0">
        <BotIcon />
      </div>
      <div className="px-4 py-3 rounded-2xl rounded-bl-sm bg-zinc-800 border border-zinc-700
                      flex items-center gap-1.5">
        {[0, 1, 2].map(i => (
          <span key={i} className="w-1.5 h-1.5 rounded-full bg-zinc-500"
            style={{ animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite` }} />
        ))}
      </div>
    </div>
  );
}

/* ── Empty state ── */
function EmptyState({ noTools, toolNames, t }) {
  return (
    <div className="h-full flex flex-col items-center justify-center text-center px-4 py-8">
      <div className="w-12 h-12 rounded-2xl bg-zinc-900 border border-zinc-800
                      flex items-center justify-center mb-4 text-zinc-600">
        <ChatBubbleIcon />
      </div>
      {noTools ? (
        <>
          <p className="text-sm font-medium text-zinc-400 mb-1">{t("No tools connected")}</p>
          <p className="text-xs text-zinc-600 max-w-[200px]">
            {t("Connect an API on the left to start chatting with tools.")}
          </p>
        </>
      ) : (
        <>
          <p className="text-sm font-medium text-zinc-300 mb-1">{t("Ready to assist")}</p>
          <p className="text-xs text-zinc-600 max-w-[210px] mb-4">
            {t("Ask anything related to your connected tools.")}
          </p>
          {toolNames.length > 0 && (
            <div className="w-full max-w-xs space-y-1 text-left">
              <p className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider mb-2">
                {t("Available tools")}
              </p>
              {toolNames.slice(0, 5).map((name, i) => (
                <div key={i} className="flex items-center gap-2 px-3 py-1.5 rounded-lg
                                        bg-zinc-900 border border-zinc-800">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0" />
                  <span className="text-xs font-mono text-zinc-400 truncate">{name}</span>
                </div>
              ))}
              {toolNames.length > 5 && (
                <p className="text-xs text-zinc-700 text-center pt-1">
                  +{toolNames.length - 5} {t("more")}
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ── Subscription gate components ── */
function AccessGate({ status, onRequest, requesting, t }) {
  const states = {
    none: {
      icon: "🔒",
      title: "Chat Access Required",
      desc: "Request access to use MCP Chat. An admin will review and approve your request.",
      action: true,
    },
    pending: {
      icon: "⏳",
      title: "Request Pending",
      desc: "Your access request has been submitted. You'll be able to chat once an admin approves it.",
      action: false,
    },
    rejected: {
      icon: "✕",
      title: "Access Denied",
      desc: "Your request was not approved. Contact an admin if you believe this is a mistake.",
      action: true,
    },
  };
  const s = states[status] || states.none;
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="card p-8 max-w-sm w-full text-center space-y-4">
        <div className="text-4xl">{s.icon}</div>
        <div>
          <p className="text-base font-semibold text-zinc-100">{s.title}</p>
          <p className="text-sm text-zinc-500 mt-1">{s.desc}</p>
        </div>
        {s.action && (
          <button
            onClick={onRequest}
            disabled={requesting}
            className="btn-primary w-full justify-center disabled:opacity-60"
          >
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
          <p className="text-base font-semibold text-zinc-100">No Credits Remaining</p>
          <p className="text-sm text-zinc-500 mt-1">
            Your credit balance is $0.00. Contact an admin to top up your account.
          </p>
        </div>
      </div>
    </div>
  );
}

/* ── Stat card ── */
function StatCard({ label, value, icon, accent }) {
  const colors = { emerald: "text-emerald-400", blue: "text-blue-400", violet: "text-violet-400" };
  return (
    <div className="card px-4 py-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-zinc-600">{icon}</span>
        <span className={`text-2xl font-bold tabular-nums ${colors[accent] || "text-zinc-200"}`}>{value}</span>
      </div>
      <p className="text-xs text-zinc-500">{label}</p>
    </div>
  );
}

/* ── Icons ── */
function LayersIcon()   { return <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><path d="M7.5 1.5L13 4.5L7.5 7.5L2 4.5L7.5 1.5Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/><path d="M2 7.5L7.5 10.5L13 7.5" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/></svg>; }
function PlugIcon()     { return <svg width="13" height="13" viewBox="0 0 15 15" fill="none"><path d="M5 1v3M10 1v3M3 7h9M4 4h7v3a3.5 3.5 0 0 1-7 0V4Z" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/><path d="M7.5 10.5v3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>; }
function PlugSmIcon()   { return <svg width="12" height="12" viewBox="0 0 15 15" fill="none"><path d="M5 1v3M10 1v3M3 7h9M4 4h7v3a3.5 3.5 0 0 1-7 0V4Z" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/><path d="M7.5 10.5v3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>; }
function UnplugIcon()   { return <svg width="12" height="12" viewBox="0 0 15 15" fill="none"><path d="M3 3l9 9M5 1v3M10 1v3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>; }
function BoltIcon()     { return <svg width="13" height="13" viewBox="0 0 15 15" fill="none"><path d="M8.5 1.5l-5 7h5l-2 5 6-8H8l.5-4Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/></svg>; }
function SendIcon()     { return <svg width="14" height="14" viewBox="0 0 15 15" fill="none"><path d="M1 7.5h13M9 3l5 4.5L9 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>; }
function SearchIcon()   { return <svg width="14" height="14" viewBox="0 0 15 15" fill="none" className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600 pointer-events-none"><circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" strokeWidth="1.4"/><path d="M10 10l3 3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>; }
function ChatBubbleIcon(){ return <svg width="20" height="20" viewBox="0 0 15 15" fill="none"><path d="M2 2h11a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H5l-3 3V3a1 1 0 0 1 1-1Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/></svg>; }
function BotIcon()      { return <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><rect x="3" y="8" width="18" height="12" rx="3" stroke="currentColor" strokeWidth="1.6"/><path d="M9 12h.01M15 12h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/><path d="M12 8V4M9 4h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>; }
function UserIcon()     { return <svg width="11" height="11" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="1.8"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>; }
function ChevronSmIcon({ open }) { return <svg width="11" height="11" viewBox="0 0 15 15" fill="none" className={`text-zinc-600 transition-transform flex-shrink-0 ${open ? "rotate-180" : ""}`}><path d="M3 5l4.5 5L12 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>; }
function ExpandIcon()   { return <svg width="13" height="13" viewBox="0 0 15 15" fill="none"><path d="M9 1h5v5M6 9l8-8M1 6V1h5M6 9L1 14M9 14h5v-5M9 6l5 5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>; }
function ShrinkIcon()   { return <svg width="13" height="13" viewBox="0 0 15 15" fill="none"><path d="M9 6V1M9 6h5M6 9H1M6 9v5M14 1l-5 5M1 14l5-5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>; }
function CreditIcon()   { return <svg width="13" height="13" viewBox="0 0 15 15" fill="none"><rect x="1" y="3.5" width="13" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.4"/><path d="M1 6.5h13" stroke="currentColor" strokeWidth="1.4"/><path d="M4 9.5h2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>; }
