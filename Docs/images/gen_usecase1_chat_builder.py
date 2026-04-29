"""
MCP Hub — Use Case 1: Tool Creation via Chat Builder
Renders to: Docs/images/usecase1_chat_builder.png
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import os

W, H = 22, 14
BG = "#f6f8fa"

C = {
    "user":     {"bg": "#ffffff", "bd": "#94a3b8", "hi": "#1e293b", "lo": "#64748b"},
    "frontend": {"bg": "#eff6ff", "bd": "#3b82f6", "hi": "#1d4ed8", "lo": "#2563eb"},
    "backend":  {"bg": "#f0fdf4", "bd": "#16a34a", "hi": "#14532d", "lo": "#166534"},
    "agent":    {"bg": "#f5f3ff", "bd": "#7c3aed", "hi": "#4c1d95", "lo": "#6d28d9"},
    "db":       {"bg": "#f0f9ff", "bd": "#0284c7", "hi": "#0c4a6e", "lo": "#0369a1"},
    "skip":     {"bg": "#f1f5f9", "bd": "#cbd5e1", "hi": "#64748b", "lo": "#94a3b8"},
    "comp_fe":  {"bg": "#dbeafe", "bd": "#93c5fd", "hi": "#1e40af", "lo": "#2563eb"},
    "comp_be":  {"bg": "#dcfce7", "bd": "#86efac", "hi": "#14532d", "lo": "#15803d"},
    "comp_ag":  {"bg": "#ede9fe", "bd": "#c4b5fd", "hi": "#3b0764", "lo": "#6d28d9"},
    "comp_db":  {"bg": "#e0f2fe", "bd": "#7dd3fc", "hi": "#0c4a6e", "lo": "#0369a1"},
    "comp":     {"bg": "#f8fafc", "bd": "#cbd5e1", "hi": "#1e293b", "lo": "#64748b"},
    "active":   {"bg": "#fef3c7", "bd": "#f59e0b", "hi": "#78350f", "lo": "#92400e"},
}
TEXT  = "#0f172a"
MUTED = "#475569"
DIM   = "#94a3b8"
GREEN = "#16a34a"

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

# ── Title ──────────────────────────────────────────────────────────────────────
txt(W / 2, 13.55, "MCP HUB  —  Use Case 1", TEXT, sz=18, w="bold", mono=True)
txt(W / 2, 13.05, "Tool Creation via Chat Builder  ·  No LLM parsing  ·  MANUAL mode", MUTED, sz=9.5)
hline(12.78)

# ── STEP labels column ─────────────────────────────────────────────────────────
step_x = 0.55

# ── Row heights (y bottom of each row) ────────────────────────────────────────
ROW = [11.6, 9.8, 8.0, 6.2, 4.4, 2.6, 0.85]
RH  = 1.2   # row box height

# ── Step 1 — User fills Chat Builder form ─────────────────────────────────────
r = 0
box(1.0, ROW[r], 20.0, RH, "frontend", lw=1.6, z=2, r=0.18)
txt(11.0, ROW[r] + RH - 0.22, "FRONTEND  ·  Chat Builder  (/create/chat)", C["frontend"]["hi"], sz=8, w="bold", ha="center")
# form fields
fields = [
    ("API Name",    "e.g. Weather API"),
    ("Base URL",    "https://api.example.com"),
    ("Auth Type",   "Bearer / API_Key / None"),
    ("Endpoints",   "path · method · params"),
]
fw = 4.5
for i, (label, val) in enumerate(fields):
    fx = 1.2 + i * (fw + 0.1)
    box(fx, ROW[r] + 0.1, fw, 0.72, "comp_fe", lw=0.7, z=4, r=0.09)
    txt(fx + fw / 2, ROW[r] + 0.56, label, C["frontend"]["hi"], sz=7, w="bold")
    txt(fx + fw / 2, ROW[r] + 0.26, val,   DIM,               sz=6.2, mono=True)
step_badge(step_x, ROW[r] + RH / 2, 1, C["frontend"]["bd"])
txt(0.55, ROW[r] - 0.22, "User fills form\nand submits", DIM, sz=6, ha="center", va="top")
arrow(11.0, ROW[r], 11.0, ROW[r] - 0.28, C["frontend"]["bd"])

# ── Step 2 — POST /api/agent/manual ───────────────────────────────────────────
r = 1
box(1.0, ROW[r], 20.0, RH, "backend", lw=1.6, z=2, r=0.18)
txt(5.5, ROW[r] + RH - 0.22, "BACKEND  ·  /api/agent/manual", C["backend"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH / 2, 2, C["backend"]["bd"])

# Endpoint box
box(1.2, ROW[r] + 0.1, 6.5, 0.72, "comp_be", lw=0.7, z=4, r=0.09)
txt(4.45, ROW[r] + 0.56, "POST  /api/agent/manual", C["backend"]["hi"], sz=7.5, w="bold", mono=True)
txt(4.45, ROW[r] + 0.26, "create_manual()  ·  JWT required", MUTED, sz=6.5)

# build draft box
box(8.0, ROW[r] + 0.1, 6.0, 0.72, "comp_be", lw=0.7, z=4, r=0.09)
txt(11.0, ROW[r] + 0.56, "Builds draft_api dict directly", C["backend"]["hi"], sz=7, w="bold")
txt(11.0, ROW[r] + 0.26, "No LLM  ·  uses form fields verbatim", MUTED, sz=6.5)

# session box
box(14.3, ROW[r] + 0.1, 6.5, 0.72, "comp_be", lw=0.7, z=4, r=0.09)
txt(17.55, ROW[r] + 0.56, "AgentSession created", C["backend"]["hi"], sz=7, w="bold")
txt(17.55, ROW[r] + 0.26, "state = HITL_PENDING  ·  saved to DB", MUTED, sz=6.5)

arrow(4.45, ROW[r] + 0.46, 8.0, ROW[r] + 0.46, C["backend"]["lo"])
arrow(14.0, ROW[r] + 0.46, 14.3, ROW[r] + 0.46, C["backend"]["lo"])
arrow(11.0, ROW[r], 11.0, ROW[r] - 0.28, C["backend"]["bd"])

# ── Step 3 — HITL Confirm (no AI, user submits directly) ──────────────────────
r = 2
box(1.0, ROW[r], 20.0, RH, "frontend", lw=1.6, z=2, r=0.18)
txt(11.0, ROW[r] + RH - 0.22, "FRONTEND  ·  HITL Validator  (/validate/:id)  —  Review & Confirm", C["frontend"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH / 2, 3, C["frontend"]["bd"])

# Since no AI confidence scoring in MANUAL mode, show as passthrough
box(1.2, ROW[r] + 0.1, 8.5, 0.72, "comp_fe", lw=0.7, z=4, r=0.09)
txt(5.45, ROW[r] + 0.56, "Confidence dots = all GREEN (not shown in MANUAL)", C["frontend"]["hi"], sz=7, w="bold")
txt(5.45, ROW[r] + 0.26, "No LLM confidence scoring  ·  user reviews form data", MUTED, sz=6.5)

box(10.0, ROW[r] + 0.1, 5.5, 0.72, "comp_fe", lw=0.7, z=4, r=0.09)
txt(12.75, ROW[r] + 0.56, "User clicks Confirm", C["frontend"]["hi"], sz=7, w="bold")
txt(12.75, ROW[r] + 0.26, "POST /api/agent/:id/confirm", MUTED, sz=6.5, mono=True)

box(15.8, ROW[r] + 0.1, 5.0, 0.72, "comp_be", lw=0.7, z=4, r=0.09)
txt(18.3, ROW[r] + 0.56, "orchestrator.confirm({})", C["backend"]["hi"], sz=7, w="bold", mono=True)
txt(18.3, ROW[r] + 0.26, "human_edits = {}  ·  merges draft", MUTED, sz=6.5)

arrow(12.75, ROW[r] + 0.46, 15.8, ROW[r] + 0.46, C["frontend"]["lo"])
arrow(11.0, ROW[r], 11.0, ROW[r] - 0.28, C["agent"]["bd"])

# ── Step 4 — Validation (SchemaValidator) ─────────────────────────────────────
r = 3
box(1.0, ROW[r], 20.0, RH, "agent", lw=1.6, z=2, r=0.18)
txt(11.0, ROW[r] + RH - 0.22, "AGENT PIPELINE  ·  Stage 6: SchemaValidator  (rule-based, no LLM)", C["agent"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH / 2, 4, C["agent"]["bd"])

checks = [
    ("name", "required\nnon-empty"),
    ("base_url", "http / https\nformat"),
    ("endpoints", "non-empty\narray"),
    ("path", "starts with\n/"),
    ("method", "GET POST PUT\nDELETE PATCH"),
    ("auth_type", "BEARER API_KEY\nBASIC NONE"),
]
cw = 3.1
for i, (label, rule) in enumerate(checks):
    cx = 1.2 + i * (cw + 0.06)
    box(cx, ROW[r] + 0.1, cw, 0.72, "comp_ag", lw=0.7, z=4, r=0.09)
    txt(cx + cw / 2, ROW[r] + 0.58, label, C["agent"]["hi"], sz=7, w="bold", mono=True)
    txt(cx + cw / 2, ROW[r] + 0.26, rule,  MUTED,            sz=6)

arrow(11.0, ROW[r], 11.0, ROW[r] - 0.28, C["agent"]["bd"])

# ── Step 5 — ApiTestAgent ──────────────────────────────────────────────────────
r = 4
box(1.0, ROW[r], 20.0, RH, "agent", lw=1.6, z=2, r=0.18)
txt(11.0, ROW[r] + RH - 0.22, "AGENT PIPELINE  ·  Stage 7: ApiTestAgent  (non-blocking)", C["agent"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH / 2, 5, C["agent"]["bd"])

test_items = [
    ("GET only", "Skip POST/PUT\nPATCH/DELETE"),
    ("Name hints", "city→London\nlat→51.5"),
    ("HTTP call", "httpx.get()\ntimeout 8s"),
    ("GPT-4o", "assess response\nPASS/WARN/FAIL"),
    ("Non-blocking", "verdict saved\ndoes not block save"),
]
tw = 3.7
for i, (label, detail) in enumerate(test_items):
    tx = 1.2 + i * (tw + 0.05)
    box(tx, ROW[r] + 0.1, tw, 0.72, "comp_ag", lw=0.7, z=4, r=0.09)
    txt(tx + tw / 2, ROW[r] + 0.58, label,  C["agent"]["hi"], sz=7, w="bold")
    txt(tx + tw / 2, ROW[r] + 0.26, detail, MUTED,            sz=6)

arrow(11.0, ROW[r], 11.0, ROW[r] - 0.28, C["agent"]["bd"])

# ── Step 6 — ApiSaver ─────────────────────────────────────────────────────────
r = 5
box(1.0, ROW[r], 20.0, RH, "agent", lw=1.6, z=2, r=0.18)
txt(11.0, ROW[r] + RH - 0.22, "AGENT PIPELINE  ·  Stage 8: ApiSaver", C["agent"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH / 2, 6, C["agent"]["bd"])

saver_items = [
    ("encrypt_creds()", "Fernet symmetric\nSHA-256 key derive"),
    ("ApiDefinition", "name · base_url\nversion · user_id"),
    ("ApiEndpoint ×N", "path · method\ninput_schema · auth"),
    ("state = SAVED", "session finalized\ncreated_at stamped"),
]
sw = 4.6
for i, (label, detail) in enumerate(saver_items):
    sx = 1.2 + i * (sw + 0.1)
    box(sx, ROW[r] + 0.1, sw, 0.72, "comp_ag", lw=0.7, z=4, r=0.09)
    txt(sx + sw / 2, ROW[r] + 0.58, label,  C["agent"]["hi"], sz=7, w="bold", mono=True)
    txt(sx + sw / 2, ROW[r] + 0.26, detail, MUTED,            sz=6.2)

arrow(11.0, ROW[r], 11.0, ROW[r] - 0.28, C["db"]["bd"])

# ── Step 7 — Database ─────────────────────────────────────────────────────────
r = 6
box(1.0, ROW[r], 20.0, RH - 0.1, "db", lw=1.6, z=2, r=0.18)
txt(11.0, ROW[r] + RH - 0.22, "DATABASE  ·  PostgreSQL", C["db"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + (RH - 0.1) / 2, 7, C["db"]["bd"])

db_items = [
    ("api_definitions", "id · name · base_url\nvisibility · user_id"),
    ("api_endpoints",   "definition_id · path · method\ninput_schema · auth_credentials(enc)"),
    ("agent_sessions",  "state=SAVED · draft_api\nfinal_api · user_id"),
    ("tool_call_logs",  "ready for future\nMCP chat calls"),
]
dw = 4.6
for i, (label, detail) in enumerate(db_items):
    dx = 1.2 + i * (dw + 0.1)
    box(dx, ROW[r] + 0.1, dw, 0.72, "comp_db", lw=0.7, z=4, r=0.09)
    txt(dx + dw / 2, ROW[r] + 0.58, label,  C["db"]["hi"], sz=7, w="bold", mono=True)
    txt(dx + dw / 2, ROW[r] + 0.26, detail, MUTED,         sz=6)

# ── Footer ─────────────────────────────────────────────────────────────────────
hline(0.6)
txt(0.6,  0.42, "MCP Hub  ·  Use Case 1  ·  Chat Builder creates tool directly without LLM parsing", DIM, sz=6.5, ha="left")
txt(W - 0.6, 0.42, "No GPT-4o calls in this flow", DIM, sz=6.5, ha="right")

out = os.path.join(os.path.dirname(__file__), "usecase1_chat_builder.png")
plt.savefig(out, dpi=200, bbox_inches="tight", facecolor=BG, edgecolor="none")
plt.close()
print(f"Saved: {out}")
