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
  const [tab, setTab] = useState("users");
  const [users, setUsers] = useState([]);
  const [chatUsers, setChatUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState({});
  const [topUpAmt, setTopUpAmt] = useState({});

  async function load() {
    setLoading(true);
    try {
      const [u, cu] = await Promise.all([adminApi.listUsers(), subscriptionApi.adminAllUsers()]);
      setUsers(u);
      setChatUsers(cu);
    } catch {
      setError("Failed to load users.");
    } finally {
      setLoading(false);
    }
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
    } catch (e) {
      alert(e.response?.data?.detail || "Failed");
    } finally {
      setBusy(b => ({ ...b, [userId + "_chat"]: false }));
    }
  }

  async function handleReject(userId) {
    setBusy(b => ({ ...b, [userId + "_chat"]: true }));
    try {
      await subscriptionApi.reject(userId);
      setChatUsers(cs => cs.map(u => u.user_id === userId ? { ...u, chat_status: "rejected" } : u));
    } catch (e) {
      alert(e.response?.data?.detail || "Failed");
    } finally {
      setBusy(b => ({ ...b, [userId + "_chat"]: false }));
    }
  }

  async function handleTopUp(userId) {
    const amt = parseFloat(topUpAmt[userId]);
    if (!amt || amt <= 0) return alert("Enter a valid amount");
    setBusy(b => ({ ...b, [userId + "_topup"]: true }));
    try {
      const res = await subscriptionApi.topUp(userId, amt);
      setChatUsers(cs => cs.map(u => u.user_id === userId ? { ...u, credits: res.new_balance } : u));
      setTopUpAmt(a => ({ ...a, [userId]: "" }));
    } catch (e) {
      alert(e.response?.data?.detail || "Failed");
    } finally {
      setBusy(b => ({ ...b, [userId + "_topup"]: false }));
    }
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
    <div className="animate-slide-up space-y-5">
      <div className="card p-6">
        <p className="eyebrow">Admin</p>
        <h1 className="h-page mt-2">Operations and controls</h1>
      </div>

      <div className="flex flex-wrap gap-2">
        {[
          { key: "users", label: "Users", count: users.length },
          { key: "chat-access", label: "Chat Access", count: pendingCount },
          { key: "plugins", label: "Plugins" },
          { key: "rbac", label: "RBAC" },
          { key: "ops", label: "Operations" },
        ].map(({ key, label, count }) => (
          <button key={key} onClick={() => setTab(key)} className={`pill ${tab === key ? "pill-ok" : ""}`}>
            {label}{count > 0 ? ` ${count}` : ""}
          </button>
        ))}
      </div>

      {error && <p className="text-sm text-[var(--err)]">{error}</p>}

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size={24} /></div>
      ) : tab === "users" ? (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--line)] bg-[var(--panel)]">
                {["User", "Role", "Status", "Joined", "Actions"].map(h => (
                  <th key={h} className="text-left text-[10px] font-semibold text-[var(--muted-2)] uppercase tracking-[0.18em] px-4 py-3">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--line)]">
              {users.map(u => (
                <tr key={u.id} className="hover:bg-[var(--hover)]">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-[var(--ink)] text-[var(--bg)] flex items-center justify-center flex-shrink-0">
                        <span className="text-[10px] font-semibold uppercase">{u.email[0]}</span>
                      </div>
                      <div>
                        <p className="text-xs font-medium">{u.email}</p>
                        {u.full_name && <p className="text-[11px] text-[var(--muted)]">{u.full_name}</p>}
                      </div>
                      {u.id === me?.id && <span className="pill">you</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3"><span className="pill">{u.role}</span></td>
                  <td className="px-4 py-3"><span className="pill">{u.is_active ? "active" : "inactive"}</span></td>
                  <td className="px-4 py-3 text-[var(--muted)] text-xs">{new Date(u.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    {u.id !== me?.id && (
                      <div className="flex items-center gap-2">
                        <button onClick={() => toggleRole(u)} disabled={busy[u.id]} className="btn btn-secondary btn-sm">
                          {busy[u.id] ? <Spinner size={10} /> : u.role === "admin" ? "Demote" : "Make Admin"}
                        </button>
                        <button onClick={() => toggleActive(u)} disabled={busy[u.id + "_a"]} className="btn btn-secondary btn-sm">
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
            <p className="text-sm text-[var(--muted)] py-8 text-center">No chat access requests yet.</p>
          ) : chatUsers.map(u => (
            <div key={u.user_id} className="card px-5 py-4 flex items-center gap-4">
              <div className="w-8 h-8 rounded-full bg-[var(--ink)] text-[var(--bg)] flex items-center justify-center flex-shrink-0">
                <span className="text-xs font-semibold uppercase">{u.email[0]}</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{u.email}</p>
                {u.full_name && <p className="text-xs text-[var(--muted)]">{u.full_name}</p>}
              </div>
              <span className="pill">{u.chat_status}</span>
              {u.chat_status === "approved" && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-[var(--muted)] font-mono">${u.credits.toFixed(4)}</span>
                  <input type="number" min="0.01" step="0.01" placeholder="$" value={topUpAmt[u.user_id] || ""} onChange={e => setTopUpAmt(a => ({ ...a, [u.user_id]: e.target.value }))} className="input w-24 text-xs py-1" />
                  <button onClick={() => handleTopUp(u.user_id)} disabled={busy[u.user_id + "_topup"]} className="btn btn-secondary btn-sm">{busy[u.user_id + "_topup"] ? <Spinner size={10} /> : "Top Up"}</button>
                </div>
              )}
              {u.chat_status === "pending" && (
                <div className="flex items-center gap-2">
                  <button onClick={() => handleApprove(u.user_id)} disabled={busy[u.user_id + "_chat"]} className="btn btn-secondary btn-sm">{busy[u.user_id + "_chat"] ? <Spinner size={10} /> : "Approve"}</button>
                  <button onClick={() => handleReject(u.user_id)} disabled={busy[u.user_id + "_chat"]} className="btn btn-secondary btn-sm">Reject</button>
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

  async function load() { setPlugins(await adminOpsApi.plugins()); }
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

  return (
    <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
      <div className="card p-4 space-y-3">
        <h2 className="h-section">Plugin Settings</h2>
        <input className="input" value={name} onChange={e => setName(e.target.value)} placeholder="Plugin name" />
        <label className="flex items-center gap-2 text-sm text-[var(--muted)]"><input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} /> Enabled</label>
        <textarea className="input h-32 font-mono text-xs" value={config} onChange={e => setConfig(e.target.value)} />
        <button className="btn btn-primary w-full" onClick={save}>Save Plugin</button>
        {message && <p className="text-xs text-[var(--muted)]">{message}</p>}
      </div>
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-[var(--line)] bg-[var(--panel)]"><th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.18em] text-[var(--muted-2)]">Name</th><th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.18em] text-[var(--muted-2)]">Enabled</th><th className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.18em] text-[var(--muted-2)]">Config</th></tr></thead>
          <tbody>{plugins.map(p => <tr key={p.id || p.name} className="border-b border-[var(--line)]"><td className="px-4 py-3">{p.name}</td><td className="px-4 py-3">{String(p.enabled)}</td><td className="px-4 py-3 font-mono text-xs">{JSON.stringify(p.config)}</td></tr>)}</tbody>
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
      <h2 className="h-section">RBAC Settings</h2>
      <textarea className="input h-64 font-mono text-xs" value={text} onChange={e => setText(e.target.value)} />
      <button className="btn btn-primary" onClick={save}>Save RBAC</button>
      {message && <p className="text-xs text-[var(--muted)]">{message}</p>}
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
          <h2 className="h-section mb-3">Safe Mode Controls</h2>
          <div className="grid gap-3 md:grid-cols-3">
            <label className="flex items-center justify-between rounded-lg border border-[var(--line)] px-3 py-2 text-sm">
              Emergency stop
              <input type="checkbox" checked={!!controls.emergency_stop} onChange={e => saveControls({ ...controls, emergency_stop: e.target.checked })} />
            </label>
            <label className="flex items-center justify-between rounded-lg border border-[var(--line)] px-3 py-2 text-sm">
              Dry-run tools
              <input type="checkbox" checked={!!controls.dry_run_tools} onChange={e => saveControls({ ...controls, dry_run_tools: e.target.checked })} />
            </label>
            <label className="rounded-lg border border-[var(--line)] px-3 py-2 text-sm">
              Tool budget ms
              <input className="input mt-2 w-full" type="number" min="1" value={controls.max_tool_execution_ms || 5000} onChange={e => setControls({ ...controls, max_tool_execution_ms: Number(e.target.value) })} onBlur={() => saveControls(controls)} />
            </label>
          </div>
        </div>
      )}
      <div className="card p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="h-section">Incidents</h2>
          <button className="btn btn-secondary" onClick={aggregate}>Aggregate</button>
        </div>
        <div className="space-y-2">
          {incidents.length === 0 ? <p className="text-xs text-[var(--muted)]">No incidents.</p> : incidents.map(i => (
            <div key={i.id} className="rounded-lg border border-[var(--line)] px-3 py-2 text-sm">
              <span className="text-[var(--ink)]">{i.title}</span>
              <span className="ml-2 text-xs text-[var(--muted)]">{i.severity} / {i.status}</span>
              <p className="text-xs text-[var(--muted)] mt-1">{i.summary}</p>
            </div>
          ))}
        </div>
      </div>
      <div className="card overflow-hidden">
        <div className="px-4 py-3 border-b border-[var(--line)] text-sm font-semibold">Real-time Audit Log</div>
        <table className="w-full text-xs">
          <tbody>
            {audit.map(row => (
              <tr key={row.id} className="border-b border-[var(--line)]">
                <td className="px-4 py-2 text-[var(--muted)]">{new Date(row.created_at).toLocaleTimeString()}</td>
                <td className="px-4 py-2">{row.actor_email || "system"}</td>
                <td className="px-4 py-2">{row.action}</td>
                <td className="px-4 py-2 text-[var(--muted)]">{row.resource_id}</td>
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
      <p className="text-[10px] uppercase tracking-[0.18em] text-[var(--muted-2)]">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  );
}
