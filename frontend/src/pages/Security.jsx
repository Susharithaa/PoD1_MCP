import { useEffect, useState } from "react";
import { securityApi } from "../lib/api";
import { PageSpinner } from "../components/Spinner";

const DEFAULT_SCOPE = "mcp:read";

export default function Security() {
  const [tokens, setTokens] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("Codex MCP token");
  const [createdToken, setCreatedToken] = useState(null);
  const [error, setError] = useState("");

  async function refresh() {
    const rows = await securityApi.listTokens();
    setTokens(rows || []);
  }

  useEffect(() => {
    refresh()
      .catch(err => setError(err.response?.data?.detail || "Failed to load API tokens."))
      .finally(() => setLoading(false));
  }, []);

  async function createToken(e) {
    e.preventDefault();
    setCreating(true);
    setError("");
    try {
      const row = await securityApi.createToken(name.trim() || "Codex MCP token", [DEFAULT_SCOPE]);
      setCreatedToken(row.token);
      setName("Codex MCP token");
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to create API token.");
    } finally {
      setCreating(false);
    }
  }

  async function rotateToken(token) {
    if (!confirm(`Rotate "${token.name}"? The old token will stop working.`)) return;
    setError("");
    try {
      const row = await securityApi.rotateToken(token.id);
      setCreatedToken(row.token);
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to rotate API token.");
    }
  }

  async function revokeToken(token) {
    if (!confirm(`Revoke "${token.name}"?`)) return;
    setError("");
    try {
      await securityApi.revokeToken(token.id);
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to revoke API token.");
    }
  }

  async function copyToken() {
    if (!createdToken) return;
    await navigator.clipboard?.writeText(createdToken);
  }

  if (loading) return <PageSpinner />;

  return (
    <div className="max-w-6xl mx-auto animate-slide-up space-y-6">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <p className="eyebrow">Security</p>
          <h1 className="h-page mt-2">API Tokens</h1>
          <p className="lead mt-2">Create bearer tokens for Codex and MCP clients.</p>
        </div>
        <span className="pill">Required scope: {DEFAULT_SCOPE}</span>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {createdToken && (
        <div className="card p-5 border-emerald-500/30">
          <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
            <div className="min-w-0 flex-1">
              <p className="eyebrow">New Token</p>
              <p className="text-sm text-[var(--muted)] mt-2">
                This value is shown once. Use it as a Bearer token for MCP Hub.
              </p>
              <code className="mt-3 block rounded-lg border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-xs font-mono text-[var(--ink)] break-all">
                {createdToken}
              </code>
            </div>
            <button type="button" className="btn-secondary shrink-0" onClick={copyToken}>
              Copy Token
            </button>
          </div>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[360px_1fr]">
        <section className="card p-5">
          <p className="eyebrow">Create</p>
          <h2 className="h-section mt-2">MCP API Token</h2>
          <form onSubmit={createToken} className="mt-4 space-y-4">
            <label className="block">
              <span className="block text-xs font-medium text-[var(--muted)] mb-1">Token name</span>
              <input
                className="field-input"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="Codex MCP token"
              />
            </label>

            <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-3 py-2">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-medium text-[var(--ink)]">{DEFAULT_SCOPE}</span>
                <span className="pill pill-ok">enabled</span>
              </div>
              <p className="text-xs text-[var(--muted)] mt-1">
                Allows MCP tool discovery and tool execution through `/mcp`.
              </p>
            </div>

            <button type="submit" className="btn-primary w-full" disabled={creating}>
              {creating ? "Creating..." : "Create Token"}
            </button>
          </form>
        </section>

        <section className="card p-5">
          <div className="flex items-center justify-between gap-3 mb-3">
            <div>
              <p className="eyebrow">Existing</p>
              <h2 className="h-section mt-2">Tokens</h2>
            </div>
            <button type="button" className="btn-ghost text-xs" onClick={refresh}>
              Refresh
            </button>
          </div>

          {tokens.length === 0 ? (
            <p className="text-sm text-[var(--muted)] py-8">No API tokens created yet.</p>
          ) : (
            <div className="divide-y divide-[var(--line)]">
              {tokens.map(token => (
                <div key={token.id} className="py-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-[var(--ink)] truncate">{token.name}</p>
                      {token.revoked_at && <span className="pill">revoked</span>}
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-[var(--muted)]">
                      <span className="font-mono">{token.token_prefix}...</span>
                      <span>{formatDate(token.created_at)}</span>
                      {token.scopes?.map(scope => (
                        <span key={scope} className="rounded border border-[var(--line)] px-1.5 py-0.5 font-mono text-[10px]">
                          {scope}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button type="button" className="btn-secondary text-xs px-3 py-1.5" onClick={() => rotateToken(token)}>
                      Rotate
                    </button>
                    <button type="button" className="btn-danger text-xs px-3 py-1.5" onClick={() => revokeToken(token)}>
                      Revoke
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function formatDate(value) {
  if (!value) return "";
  return new Date(value).toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
