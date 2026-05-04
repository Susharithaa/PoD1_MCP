import { useEffect, useState } from "react";
import { adminApi, adminOpsApi, subscriptionApi, systemApi } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Navigate } from "react-router-dom";
import Spinner from "../components/Spinner";

export default function Admin() {
  const { user } = useAuth();
  if (user?.role !== "admin") return <Navigate to="/" replace />;
  return <AdminPanel />;
}

function AdminPanel() {
  const { user: me } = useAuth();
  const [tab,     setTab]     = useState("users");
  const [users,   setUsers]   = useState([]);
  const [chatUsers, setChatUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const [busy,    setBusy]    = useState({});
  const [topUpAmt, setTopUpAmt] = useState({});

  async function load() {
    setLoading(true);
    try {
      const [u, cu] = await Promise.all([adminApi.listUsers(), subscriptionApi.adminAllUsers()]);
      setUsers(u);
      setChatUsers(cu);
    }
    catch { setError("Failed to load users."); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function toggleRole(u) {
    setBusy(b => ({ ...b, [u.id]: true }));
    try {
      const updated = await adminApi.updateRole(u.id, u.role === "admin" ? "user" : "admin");
      setUsers(us => us.map(x => x.id === updated.id ? updated : x));
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to update role");
    } finally {
      setBusy(b => ({ ...b, [u.id]: false }));
    }
  }

  async function handleApprove(userId) {
    setBusy(b => ({ ...b, [userId + "_chat"]: true }));
    try {
      await subscriptionApi.approve(userId);
      setChatUsers(cs => cs.map(u => u.user_id === userId ? { ...u, chat_status: "approved" } : u));
    } catch (e) { alert(e.response?.data?.detail || "Failed"); }
    finally { setBusy(b => ({ ...b, [userId + "_chat"]: false })); }
  }

  async function handleReject(userId) {
    setBusy(b => ({ ...b, [userId + "_chat"]: true }));
    try {
      await subscriptionApi.reject(userId);
      setChatUsers(cs => cs.map(u => u.user_id === userId ? { ...u, chat_status: "rejected" } : u));
    } catch (e) { alert(e.response?.data?.detail || "Failed"); }
    finally { setBusy(b => ({ ...b, [userId + "_chat"]: false })); }
  }

  async function handleTopUp(userId) {
    const amt = parseFloat(topUpAmt[userId]);
    if (!amt || amt <= 0) return alert("Enter a valid amount");
    setBusy(b => ({ ...b, [userId + "_topup"]: true }));
    try {
      const res = await subscriptionApi.topUp(userId, amt);
      setChatUsers(cs => cs.map(u => u.user_id === userId ? { ...u, credits: res.new_balance } : u));
      setTopUpAmt(a => ({ ...a, [userId]: "" }));
    } catch (e) { alert(e.response?.data?.detail || "Failed"); }
    finally { setBusy(b => ({ ...b, [userId + "_topup"]: false })); }
  }

  async function toggleActive(u) {
    setBusy(b => ({ ...b, [u.id + "_a"]: true }));
    try {
      const updated = await adminApi.setActive(u.id, !u.is_active);
      setUsers(us => us.map(x => x.id === updated.id ? updated : x));
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to update status");
    } finally {
      setBusy(b => ({ ...b, [u.id + "_a"]: false }));
    }
  }

  const pendingCount = chatUsers.filter(u => u.chat_status === "pending").length;

  return (
    <div className="max-w-5xl animate-slide-up">
      <div className="mb-6">
        <h1 className="page-title">Admin</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-5 border-b border-zinc-800">
        {[
          { key: "users", label: "Users", count: users.length },
          { key: "chat-access", label: "Chat Access", count: pendingCount },
          { key: "plugins", label: "Plugins" },
          { key: "rbac", label: "RBAC" },
          { key: "ops", label: "Operations" },
        ].map(({ key, label, count }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2 text-sm font-medium transition-colors relative -mb-px
              ${tab === key
                ? "text-zinc-100 border-b-2 border-blue-500"
                : "text-zinc-500 hover:text-zinc-300"}`}
          >
            {label}
            {count > 0 && (
              <span className={`ml-2 text-[10px] px-1.5 py-0.5 rounded-full font-semibold
                ${key === "chat-access" && count > 0
                  ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                  : "bg-zinc-800 text-zinc-500"}`}>
                {count}
              </span>
            )}
          </button>
        ))}
      </div>

      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size={24} /></div>
      ) : tab === "users" ? (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800">
                {["User", "Role", "Status", "Joined", "Actions"].map(h => (
                  <th key={h} className="text-left text-[10px] font-semibold text-zinc-600 uppercase tracking-wider px-4 py-3">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60">
              {users.map(u => (
                <tr key={u.id} className="hover:bg-zinc-900/40 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-blue-600/20 border border-blue-500/30 flex items-center justify-center flex-shrink-0">
                        <span className="text-[10px] font-semibold text-blue-400 uppercase">{u.email[0]}</span>
                      </div>
                      <div>
                        <p className="text-zinc-200 text-xs font-medium">{u.email}</p>
                        {u.full_name && <p className="text-zinc-600 text-[11px]">{u.full_name}</p>}
                      </div>
                      {u.id === me?.id && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30 font-semibold">you</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${u.role === "admin" ? "bg-amber-500/15 text-amber-400 border-amber-500/30" : "bg-zinc-800 text-zinc-500 border-zinc-700"}`}>
                      {u.role}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${u.is_active ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" : "bg-red-500/10 text-red-400 border-red-500/20"}`}>
                      {u.is_active ? "active" : "inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-zinc-500 text-xs">{new Date(u.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    {u.id !== me?.id && (
                      <div className="flex items-center gap-2">
                        <button onClick={() => toggleRole(u)} disabled={busy[u.id]}
                          className="text-xs px-2.5 py-1 rounded border border-zinc-700 text-zinc-400 hover:border-amber-500/40 hover:text-amber-300 transition-colors disabled:opacity-40">
                          {busy[u.id] ? <Spinner size={10} /> : u.role === "admin" ? "Demote" : "Make Admin"}
                        </button>
                        <button onClick={() => toggleActive(u)} disabled={busy[u.id + "_a"]}
                          className={`text-xs px-2.5 py-1 rounded border transition-colors disabled:opacity-40 ${u.is_active ? "border-zinc-700 text-zinc-500 hover:border-red-500/40 hover:text-red-400" : "border-zinc-700 text-zinc-500 hover:border-emerald-500/40 hover:text-emerald-400"}`}>
                          {busy[u.id + "_a"] ? <Spinner size={10} /> : u.is_active ? "Deactivate" : "Activate"}
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : tab === "chat-access" ? (
        <div className="space-y-3">
          {chatUsers.length === 0 ? (
            <p className="text-sm text-zinc-600 py-8 text-center">No chat access requests yet.</p>
          ) : chatUsers.map(u => (
            <div key={u.user_id} className="card px-4 py-4 flex items-center gap-4">
              <div className="w-8 h-8 rounded-full bg-blue-600/20 border border-blue-500/30 flex items-center justify-center flex-shrink-0">
                <span className="text-xs font-semibold text-blue-400 uppercase">{u.email[0]}</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-zinc-200 truncate">{u.email}</p>
                {u.full_name && <p className="text-xs text-zinc-600">{u.full_name}</p>}
              </div>

              {/* Status badge */}
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border flex-shrink-0 ${
                u.chat_status === "approved" ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                : u.chat_status === "pending"  ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
                : "bg-red-500/10 text-red-400 border-red-500/20"
              }`}>
                {u.chat_status}
              </span>

              {/* Credits + top-up (approved only) */}
              {u.chat_status === "approved" && (
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="text-xs text-zinc-400 font-mono">${u.credits.toFixed(4)}</span>
                  <input
                    type="number" min="0.01" step="0.01" placeholder="$"
                    value={topUpAmt[u.user_id] || ""}
                    onChange={e => setTopUpAmt(a => ({ ...a, [u.user_id]: e.target.value }))}
                    className="input w-20 text-xs py-1"
                  />
                  <button
                    onClick={() => handleTopUp(u.user_id)}
                    disabled={busy[u.user_id + "_topup"]}
                    className="text-xs px-2.5 py-1 rounded border border-zinc-700 text-zinc-400 hover:border-emerald-500/40 hover:text-emerald-300 transition-colors disabled:opacity-40"
                  >
                    {busy[u.user_id + "_topup"] ? <Spinner size={10} /> : "Top Up"}
                  </button>
                </div>
              )}

              {/* Approve / Reject (pending only) */}
              {u.chat_status === "pending" && (
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button onClick={() => handleApprove(u.user_id)} disabled={busy[u.user_id + "_chat"]}
                    className="text-xs px-2.5 py-1 rounded border border-zinc-700 text-zinc-400 hover:border-emerald-500/40 hover:text-emerald-300 transition-colors disabled:opacity-40">
                    {busy[u.user_id + "_chat"] ? <Spinner size={10} /> : "Approve"}
                  </button>
                  <button onClick={() => handleReject(u.user_id)} disabled={busy[u.user_id + "_chat"]}
                    className="text-xs px-2.5 py-1 rounded border border-zinc-700 text-zinc-400 hover:border-red-500/40 hover:text-red-400 transition-colors disabled:opacity-40">
                    Reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : tab === "plugins" ? (
        <PluginSettings />
      ) : tab === "rbac" ? (
        <RbacSettings />
      ) : (
        <OperationsDashboard />
      )}
    </div>
  );
}

function PluginSettings() {
  const [plugins, setPlugins] = useState([]);
  const [name, setName] = useState("default-search");
  const [config, setConfig] = useState("{}");
  const [enabled, setEnabled] = useState(true);
  const [message, setMessage] = useState("");

  async function load() {
    setPlugins(await adminOpsApi.plugins());
  }

  useEffect(() => { load(); }, []);

  async function save() {
    try {
      await adminOpsApi.savePlugin(name, { enabled, config: JSON.parse(config || "{}") });
      setMessage("Saved");
      load();
    } catch {
      setMessage("Invalid JSON or save failed");
    }
  }

  async function exportConfig() {
    const data = await adminOpsApi.exportConfig();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "mcp-hub-config.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function importConfig(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    await adminOpsApi.importConfig(JSON.parse(text));
    setMessage("Imported");
    load();
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
      <div className="card p-4 space-y-3">
        <h2 className="text-sm font-semibold text-zinc-100">Plugin Settings</h2>
        <input className="input w-full" value={name} onChange={e => setName(e.target.value)} placeholder="Plugin name" />
        <label className="flex items-center gap-2 text-sm text-zinc-400">
          <input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} />
          Enabled
        </label>
        <textarea className="input w-full h-32 font-mono text-xs" value={config} onChange={e => setConfig(e.target.value)} />
        <button className="btn-primary w-full" onClick={save}>Save Plugin</button>
        <div className="flex gap-2">
          <button className="btn-secondary flex-1" onClick={exportConfig}>Export</button>
          <label className="btn-secondary flex-1 text-center cursor-pointer">
            Import
            <input type="file" accept="application/json" className="hidden" onChange={importConfig} />
          </label>
        </div>
        {message && <p className="text-xs text-zinc-500">{message}</p>}
      </div>
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-zinc-800"><th className="text-left px-4 py-3 text-zinc-500">Name</th><th className="text-left px-4 py-3 text-zinc-500">Enabled</th><th className="text-left px-4 py-3 text-zinc-500">Config</th></tr></thead>
          <tbody>{plugins.map(p => (
            <tr key={p.id || p.name} className="border-b border-zinc-800/60">
              <td className="px-4 py-3 text-zinc-200">{p.name}</td>
              <td className="px-4 py-3 text-zinc-400">{String(p.enabled)}</td>
              <td className="px-4 py-3 text-zinc-500 font-mono text-xs">{JSON.stringify(p.config)}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}

function RbacSettings() {
  const [text, setText] = useState("{}");
  const [message, setMessage] = useState("");

  useEffect(() => {
    adminOpsApi.rbac().then(data => setText(JSON.stringify(data, null, 2)));
  }, []);

  async function save() {
    try {
      await adminOpsApi.saveRbac(JSON.parse(text));
      setMessage("Saved");
    } catch {
      setMessage("Invalid JSON or save failed");
    }
  }

  return (
    <div className="card p-4 max-w-2xl space-y-3">
      <h2 className="text-sm font-semibold text-zinc-100">RBAC Settings</h2>
      <textarea className="input w-full h-64 font-mono text-xs" value={text} onChange={e => setText(e.target.value)} />
      <button className="btn-primary" onClick={save}>Save RBAC</button>
      {message && <p className="text-xs text-zinc-500">{message}</p>}
    </div>
  );
}

function OperationsDashboard() {
  const [audit, setAudit] = useState([]);
  const [costs, setCosts] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [controls, setControls] = useState(null);

  async function load() {
    const [a, c, i, s] = await Promise.all([
      adminOpsApi.liveLogs(50),
      adminOpsApi.costs(),
      adminOpsApi.incidents(),
      systemApi.controls(),
    ]);
    setAudit(a);
    setCosts(c);
    setIncidents(i);
    setControls(s);
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, []);

  async function aggregate() {
    await adminOpsApi.aggregate();
    load();
  }

  async function saveControls(next) {
    const saved = await systemApi.saveControls(next);
    setControls(saved);
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        <Metric label="LLM Requests" value={costs?.request_count ?? 0} />
        <Metric label="Tokens" value={costs?.prompt_tokens + costs?.completion_tokens || 0} />
        <Metric label="Cost USD" value={`$${(costs?.cost_usd ?? 0).toFixed(4)}`} />
      </div>
      {controls && (
        <div className="card p-4">
          <h2 className="text-sm font-semibold text-zinc-100 mb-3">Safe Mode Controls</h2>
          <div className="grid gap-3 md:grid-cols-3">
            <label className="flex items-center justify-between rounded border border-zinc-800 px-3 py-2 text-sm text-zinc-400">
              Emergency stop
              <input type="checkbox" checked={!!controls.emergency_stop}
                onChange={e => saveControls({ ...controls, emergency_stop: e.target.checked })} />
            </label>
            <label className="flex items-center justify-between rounded border border-zinc-800 px-3 py-2 text-sm text-zinc-400">
              Dry-run tools
              <input type="checkbox" checked={!!controls.dry_run_tools}
                onChange={e => saveControls({ ...controls, dry_run_tools: e.target.checked })} />
            </label>
            <label className="rounded border border-zinc-800 px-3 py-2 text-sm text-zinc-400">
              Tool budget ms
              <input className="input mt-2 w-full" type="number" min="1" value={controls.max_tool_execution_ms || 5000}
                onChange={e => setControls({ ...controls, max_tool_execution_ms: Number(e.target.value) })}
                onBlur={() => saveControls(controls)} />
            </label>
          </div>
        </div>
      )}
      <div className="card p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-zinc-100">Incidents</h2>
          <button className="btn-secondary" onClick={aggregate}>Aggregate</button>
        </div>
        <div className="space-y-2">
          {incidents.length === 0 ? <p className="text-xs text-zinc-600">No incidents.</p> : incidents.map(i => (
            <div key={i.id} className="rounded border border-zinc-800 px-3 py-2 text-sm">
              <span className="text-zinc-200">{i.title}</span>
              <span className="ml-2 text-xs text-zinc-500">{i.severity} / {i.status}</span>
              <p className="text-xs text-zinc-500 mt-1">{i.summary}</p>
            </div>
          ))}
        </div>
      </div>
      <div className="card overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800 text-sm font-semibold text-zinc-100">Real-time Audit Log</div>
        <table className="w-full text-xs">
          <tbody>
            {audit.map(row => (
              <tr key={row.id} className="border-b border-zinc-800/60">
                <td className="px-4 py-2 text-zinc-500">{new Date(row.created_at).toLocaleTimeString()}</td>
                <td className="px-4 py-2 text-zinc-300">{row.actor_email || "system"}</td>
                <td className="px-4 py-2 text-zinc-400">{row.action}</td>
                <td className="px-4 py-2 text-zinc-600">{row.resource_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="card p-4">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-zinc-100">{value}</p>
    </div>
  );
}
