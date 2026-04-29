"""
MCP Hub — Use Case 3: Using a Created Tool in MCP Chat
Renders to: Docs/images/usecase3_mcp_chat.png
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import os

W, H = 22, 15
BG = "#f6f8fa"

C = {
    "user":     {"bg": "#ffffff", "bd": "#94a3b8", "hi": "#1e293b", "lo": "#64748b"},
    "frontend": {"bg": "#eff6ff", "bd": "#3b82f6", "hi": "#1d4ed8", "lo": "#2563eb"},
    "backend":  {"bg": "#f0fdf4", "bd": "#16a34a", "hi": "#14532d", "lo": "#166534"},
    "agent":    {"bg": "#f5f3ff", "bd": "#7c3aed", "hi": "#4c1d95", "lo": "#6d28d9"},
    "external": {"bg": "#fffbeb", "bd": "#d97706", "hi": "#78350f", "lo": "#92400e"},
    "db":       {"bg": "#f0f9ff", "bd": "#0284c7", "hi": "#0c4a6e", "lo": "#0369a1"},
    "extapi":   {"bg": "#fff7ed", "bd": "#ea580c", "hi": "#7c2d12", "lo": "#9a3412"},
    "comp_fe":  {"bg": "#dbeafe", "bd": "#93c5fd", "hi": "#1e40af", "lo": "#2563eb"},
    "comp_be":  {"bg": "#dcfce7", "bd": "#86efac", "hi": "#14532d", "lo": "#15803d"},
    "comp_ag":  {"bg": "#ede9fe", "bd": "#c4b5fd", "hi": "#3b0764", "lo": "#6d28d9"},
    "comp_ext": {"bg": "#fef3c7", "bd": "#fcd34d", "hi": "#451a03", "lo": "#92400e"},
    "comp_db":  {"bg": "#e0f2fe", "bd": "#7dd3fc", "hi": "#0c4a6e", "lo": "#0369a1"},
    "comp":     {"bg": "#f8fafc", "bd": "#cbd5e1", "hi": "#1e293b", "lo": "#64748b"},
    "llm":      {"bg": "#fef3c7", "bd": "#f59e0b", "hi": "#78350f", "lo": "#92400e"},
}
TEXT  = "#0f172a"
MUTED = "#475569"
DIM   = "#94a3b8"

fig = plt.figure(figsize=(W, H), facecolor=BG, dpi=200)
ax  = fig.add_subplot(111, facecolor=BG)
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.set_aspect("equal")
ax.axis("off")
fig.subplots_adjust(0, 0, 1, 1)

def box(x, y, w, h, key="comp", lw=1.3, z=3, r=0.15):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={r}",
        fc=C[key]["bg"], ec=C[key]["bd"], lw=lw,
        zorder=z, clip_on=False,
    ))

def txt(x, y, s, color=TEXT, sz=7, w="normal", ha="center", va="center", z=10, mono=False):
    ax.text(x, y, s, color=color, fontsize=sz, fontweight=w,
            ha=ha, va=va, zorder=z, clip_on=False,
            fontfamily="monospace" if mono else "sans-serif")

def arrow(x1, y1, x2, y2, color=DIM, lw=1.3, dash=False):
    props = dict(arrowstyle="->", color=color, lw=lw, mutation_scale=10)
    if dash:
        props["linestyle"] = "dashed"
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=props, zorder=6, annotation_clip=False)

def hline(y, color="#cbd5e1", lw=0.8):
    ax.plot([0.4, W - 0.4], [y, y], color=color, lw=lw, zorder=1)

def step_badge(x, y, num, color):
    ax.add_patch(FancyBboxPatch((x - 0.22, y - 0.22), 0.44, 0.44,
        boxstyle="round,pad=0,rounding_size=0.1",
        fc=color, ec="none", zorder=12, clip_on=False))
    ax.text(x, y, str(num), color="white", fontsize=7, fontweight="bold",
            ha="center", va="center", zorder=13, clip_on=False)

def llm_tag(x, y):
    box(x, y, 1.3, 0.34, "llm", lw=0.5, z=8, r=0.06)
    txt(x + 0.65, y + 0.17, "GPT-4o", C["external"]["hi"], sz=6, w="bold")

# ── Title ──────────────────────────────────────────────────────────────────────
txt(W / 2, 14.55, "MCP HUB  —  Use Case 3", TEXT, sz=18, w="bold", mono=True)
txt(W / 2, 14.05, "Using a Created Tool in MCP Chat  ·  Agentic loop  ·  2× GPT-4o calls per turn", MUTED, sz=9.5)
hline(13.78)

step_x = 0.55
ROW = [12.6, 10.8, 9.0, 7.2, 5.4, 3.6, 1.75]
RH  = 1.2

# ── Step 1 — Frontend: Connect API + Send Chat ────────────────────────────────
r = 0
box(1.0, ROW[r], 20.0, RH, "frontend", lw=1.6, z=2, r=0.18)
txt(11.0, ROW[r] + RH - 0.22, "FRONTEND  ·  ChatGPT Hub  (/chatgpt)", C["frontend"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH / 2, 1, C["frontend"]["bd"])

items = [
    ("Connect API", "POST /api/chatgpt/connect\nselect from registry"),
    ("Tool badges", "shows connected APIs\nas colored chips"),
    ("Chat input",  "user types natural\nlanguage question"),
    ("POST /chat",  "POST /api/chatgpt/chat\nmessage + session_id"),
]
iw = 4.6
for i, (label, detail) in enumerate(items):
    ix = 1.2 + i * (iw + 0.1)
    box(ix, ROW[r] + 0.1, iw, 0.72, "comp_fe", lw=0.7, z=4, r=0.09)
    txt(ix + iw / 2, ROW[r] + 0.58, label,  C["frontend"]["hi"], sz=7, w="bold")
    txt(ix + iw / 2, ROW[r] + 0.26, detail, DIM,                sz=6.2, mono=True)
arrow(11.0, ROW[r], 11.0, ROW[r] - 0.28, C["backend"]["bd"])

# ── Step 2 — Backend: load connections + build tools ─────────────────────────
r = 1
box(1.0, ROW[r], 20.0, RH, "backend", lw=1.6, z=2, r=0.18)
txt(11.0, ROW[r] + RH - 0.22, "BACKEND  ·  POST /api/chatgpt/chat  →  agentic_chat()", C["backend"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH / 2, 2, C["backend"]["bd"])

items2 = [
    ("Load connections", "ChatGPTConnections\nfor this user"),
    ("api_to_tools()", "ApiEndpoint rows →\nOpenAI function schema"),
    ("Tool name", 't_{api[:8]}_{ep[:8]}\nOpenAI-safe ≤64 chars'),
    ("_is_query_relevant()", "keyword intersection\nskip irrelevant tools"),
]
for i, (label, detail) in enumerate(items2):
    ix = 1.2 + i * (iw + 0.1)
    box(ix, ROW[r] + 0.1, iw, 0.72, "comp_be", lw=0.7, z=4, r=0.09)
    txt(ix + iw / 2, ROW[r] + 0.58, label,  C["backend"]["hi"], sz=7, w="bold", mono=True)
    txt(ix + iw / 2, ROW[r] + 0.26, detail, MUTED,              sz=6.2)
arrow(11.0, ROW[r], 11.0, ROW[r] - 0.28, C["external"]["bd"])

# ── Step 3 — GPT-4o: tool selection ──────────────────────────────────────────
r = 2
box(1.0, ROW[r], 20.0, RH, "external", lw=1.6, z=2, r=0.18)
txt(11.0, ROW[r] + RH - 0.22, "GPT-4o  ·  Call #1  —  Tool Selection  (agentic loop, max 5 iterations)", C["external"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH / 2, 3, C["external"]["bd"])
llm_tag(19.3, ROW[r] + 0.78)

items3 = [
    ("messages[]",  "system + history\n+ user message"),
    ("tools[]",      "OpenAI function\nschema array"),
    ("Response",     "tool_calls[] or\nfinal text answer"),
    ("tool_call",    "function name +\narguments JSON"),
    ("Loop check",   "if tool_calls:\n  execute  else: break"),
]
iw3 = 3.7
for i, (label, detail) in enumerate(items3):
    ix = 1.2 + i * (iw3 + 0.08)
    box(ix, ROW[r] + 0.1, iw3, 0.72, "comp_ext", lw=0.7, z=4, r=0.09)
    txt(ix + iw3 / 2, ROW[r] + 0.58, label,  C["external"]["hi"], sz=7, w="bold", mono=True)
    txt(ix + iw3 / 2, ROW[r] + 0.26, detail, MUTED,               sz=6)
arrow(11.0, ROW[r], 11.0, ROW[r] - 0.28, C["agent"]["bd"])

# ── Step 4 — resolve + decrypt + execute ──────────────────────────────────────
r = 3
box(1.0, ROW[r], 20.0, RH, "agent", lw=1.6, z=2, r=0.18)
txt(11.0, ROW[r] + RH - 0.22, "BACKEND  ·  Tool Execution  —  resolve → decrypt → httpx", C["agent"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH / 2, 4, C["agent"]["bd"])

exec_items = [
    ("resolve_tool_call()", 'split "t_a3f9_d7e4"\n.like() DB query'),
    ("_missing_required\n_params()", "check required fields\nfail fast if missing"),
    ("decrypt_creds()", "Fernet.decrypt()\n{_enc:gAAAA}→plain"),
    ("_build_auth()", "BasicAuth or\nBearer header"),
    ("httpx.request()", "GET/POST to\nexternal API URL"),
]
ew = 3.7
for i, (label, detail) in enumerate(exec_items):
    ex = 1.2 + i * (ew + 0.08)
    box(ex, ROW[r] + 0.1, ew, 0.72, "comp_ag", lw=0.7, z=4, r=0.09)
    txt(ex + ew / 2, ROW[r] + 0.62, label,  C["agent"]["hi"], sz=6.5, w="bold", mono=True)
    txt(ex + ew / 2, ROW[r] + 0.26, detail, MUTED,            sz=6)
    if i < len(exec_items) - 1:
        ax.annotate("", xy=(ex + ew + 0.08, ROW[r] + 0.46),
                    xytext=(ex + ew, ROW[r] + 0.46),
                    arrowprops=dict(arrowstyle="->", color=C["agent"]["lo"], lw=0.7),
                    zorder=7, annotation_clip=False)
arrow(11.0, ROW[r], 11.0, ROW[r] - 0.28, C["extapi"]["bd"])

# ── Step 5 — External API call ────────────────────────────────────────────────
r = 4
box(1.0, ROW[r], 20.0, RH, "extapi", lw=1.6, z=2, r=0.18)
txt(11.0, ROW[r] + RH - 0.22, "EXTERNAL REST API  ·  Real HTTP Call", C["extapi"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH / 2, 5, C["extapi"]["bd"])

ext_items = [
    ("URL built",    "base_url + path\npath params substituted"),
    ("Query params", "GET: added to URL\nPOST: JSON body"),
    ("Auth applied", "Bearer / Basic /\nX-API-Key header"),
    ("Response",     "resp.text[:2000]\ntruncated for context"),
    ("ToolCallLog",  "success · result\ntimestamp · saved"),
]
for i, (label, detail) in enumerate(ext_items):
    ix = 1.2 + i * (iw + 0.1)
    box(ix, ROW[r] + 0.1, iw, 0.72, "extapi", lw=0.5, z=4, r=0.09)
    txt(ix + iw / 2, ROW[r] + 0.58, label,  C["extapi"]["hi"], sz=7, w="bold")
    txt(ix + iw / 2, ROW[r] + 0.26, detail, MUTED,             sz=6.2)
arrow(11.0, ROW[r], 11.0, ROW[r] - 0.28, C["external"]["bd"])

# ── Step 6 — GPT-4o final answer ──────────────────────────────────────────────
r = 5
box(1.0, ROW[r], 20.0, RH, "external", lw=1.6, z=2, r=0.18)
txt(11.0, ROW[r] + RH - 0.22, "GPT-4o  ·  Call #2  —  Final Answer Synthesis", C["external"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH / 2, 6, C["external"]["bd"])
llm_tag(19.3, ROW[r] + 0.78)

synth_items = [
    ("tool result", 'appended as\n{"role":"tool",...}'),
    ("Loop continues", "up to 5 iterations\nif more tools needed"),
    ("Final text",  "no more tool_calls\nnatural language answer"),
    ("Streamed",    "response sent back\nto frontend"),
]
sw = 4.6
for i, (label, detail) in enumerate(synth_items):
    sx = 1.2 + i * (sw + 0.1)
    box(sx, ROW[r] + 0.1, sw, 0.72, "comp_ext", lw=0.7, z=4, r=0.09)
    txt(sx + sw / 2, ROW[r] + 0.58, label,  C["external"]["hi"], sz=7, w="bold", mono=True)
    txt(sx + sw / 2, ROW[r] + 0.26, detail, MUTED,               sz=6.2)
arrow(11.0, ROW[r], 11.0, ROW[r] - 0.28, C["frontend"]["bd"])

# ── Step 7 — Frontend renders result ──────────────────────────────────────────
r = 6
box(1.0, ROW[r], 20.0, RH - 0.1, "frontend", lw=1.6, z=2, r=0.18)
txt(11.0, ROW[r] + RH - 0.22, "FRONTEND  ·  Render Response", C["frontend"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + (RH - 0.1) / 2, 7, C["frontend"]["bd"])

render_items = [
    ("Chat bubble",   "assistant message\nMarkdown rendered"),
    ("Tool call pills", "expandable chips\nshowing API called"),
    ("Arguments",     "JSON params sent\ncollapsible view"),
    ("DB logged",     "ToolCallLog row\npersisted for audit"),
]
rw = 4.6
for i, (label, detail) in enumerate(render_items):
    rx = 1.2 + i * (rw + 0.1)
    box(rx, ROW[r] + 0.1, rw, 0.72, "comp_fe", lw=0.7, z=4, r=0.09)
    txt(rx + rw / 2, ROW[r] + 0.58, label,  C["frontend"]["hi"], sz=7, w="bold")
    txt(rx + rw / 2, ROW[r] + 0.26, detail, MUTED,               sz=6.2)

# ── Footer ─────────────────────────────────────────────────────────────────────
hline(0.55)
txt(0.6,  0.38, "MCP Hub  ·  Use Case 3  ·  Agentic loop executes real HTTP calls against registered APIs via GPT-4o tool-calling", DIM, sz=6.5, ha="left")
txt(W - 0.6, 0.38, "Max 5 loop iterations per user message", DIM, sz=6.5, ha="right")

out = os.path.join(os.path.dirname(__file__), "usecase3_mcp_chat.png")
plt.savefig(out, dpi=200, bbox_inches="tight", facecolor=BG, edgecolor="none")
plt.close()
print(f"Saved: {out}")
