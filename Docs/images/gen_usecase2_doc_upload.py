"""
MCP Hub — Use Case 2: Tool Creation via Doc Upload (v2 — Smart Chunking Pipeline)
Renders to: Docs/images/usecase2_doc_upload.png
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import os

W, H = 24, 20
BG = "#f6f8fa"

C = {
    "user":     {"bg": "#ffffff", "bd": "#94a3b8", "hi": "#1e293b", "lo": "#64748b"},
    "frontend": {"bg": "#eff6ff", "bd": "#3b82f6", "hi": "#1d4ed8", "lo": "#2563eb"},
    "backend":  {"bg": "#f0fdf4", "bd": "#16a34a", "hi": "#14532d", "lo": "#166534"},
    "agent":    {"bg": "#f5f3ff", "bd": "#7c3aed", "hi": "#4c1d95", "lo": "#6d28d9"},
    "external": {"bg": "#fffbeb", "bd": "#d97706", "hi": "#78350f", "lo": "#92400e"},
    "db":       {"bg": "#f0f9ff", "bd": "#0284c7", "hi": "#0c4a6e", "lo": "#0369a1"},
    "comp_fe":  {"bg": "#dbeafe", "bd": "#93c5fd", "hi": "#1e40af", "lo": "#2563eb"},
    "comp_be":  {"bg": "#dcfce7", "bd": "#86efac", "hi": "#14532d", "lo": "#15803d"},
    "comp_ag":  {"bg": "#ede9fe", "bd": "#c4b5fd", "hi": "#3b0764", "lo": "#6d28d9"},
    "comp_db":  {"bg": "#e0f2fe", "bd": "#7dd3fc", "hi": "#0c4a6e", "lo": "#0369a1"},
    "comp":     {"bg": "#f8fafc", "bd": "#cbd5e1", "hi": "#1e293b", "lo": "#64748b"},
    "llm":      {"bg": "#fef3c7", "bd": "#f59e0b", "hi": "#78350f", "lo": "#92400e"},
    "green":    {"bg": "#f0fdf4", "bd": "#22c55e", "hi": "#14532d", "lo": "#15803d"},
    "blue":     {"bg": "#eff6ff", "bd": "#60a5fa", "hi": "#1e40af", "lo": "#2563eb"},
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

def arrow(x1, y1, x2, y2, color=DIM, lw=1.3):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", color=color, lw=lw, mutation_scale=10),
                zorder=6, annotation_clip=False)

def hline(y, color="#cbd5e1", lw=0.8):
    ax.plot([0.4, W - 0.4], [y, y], color=color, lw=lw, zorder=1)

def step_badge(x, y, num, color):
    ax.add_patch(FancyBboxPatch((x - 0.22, y - 0.22), 0.44, 0.44,
        boxstyle="round,pad=0,rounding_size=0.1",
        fc=color, ec="none", zorder=12, clip_on=False))
    ax.text(x, y, str(num), color="white", fontsize=7, fontweight="bold",
            ha="center", va="center", zorder=13, clip_on=False)

def llm_tag(x, y, label="GPT-4o"):
    box(x, y, 1.5, 0.34, "llm", lw=0.5, z=8, r=0.06)
    txt(x + 0.75, y + 0.17, label, C["external"]["hi"], sz=6, w="bold")

def no_llm_tag(x, y):
    box(x, y, 1.5, 0.34, "green", lw=0.5, z=8, r=0.06)
    txt(x + 0.75, y + 0.17, "No LLM", C["green"]["hi"], sz=6, w="bold")

# ── Title ──────────────────────────────────────────────────────────────────────
txt(W / 2, 19.55, "MCP HUB  —  Use Case 2  (v2)", TEXT, sz=18, w="bold", mono=True)
txt(W / 2, 19.05, "Tool Creation via Doc Upload  ·  Smart Chunking Pipeline  ·  No token overflow", MUTED, sz=9.5)
hline(18.78)

step_x = 0.55
ROW = [17.6, 15.7, 13.8, 11.4, 9.2, 7.2, 5.2, 3.2, 1.2]
RH  = 1.3

# ── Step 1 — Frontend Upload ──────────────────────────────────────────────────
r = 0
box(1.0, ROW[r], 22.0, RH, "frontend", lw=1.6, z=2, r=0.18)
txt(12.0, ROW[r] + RH - 0.22, "FRONTEND  ·  Doc Upload  (/create/upload)", C["frontend"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH / 2, 1, C["frontend"]["bd"])

items = [
    ("Drag & Drop", "PDF · DOCX · JSON\nYAML · TXT · Postman"),
    ("File preview", "filename · size\ntype indicator"),
    ("POST /api/agent/upload", "multipart/form-data\nJWT Bearer"),
    ("Poll status", "GET /api/agent/:id\nevery 2s while processing"),
]
iw = 5.2
for i, (label, detail) in enumerate(items):
    ix = 1.2 + i * (iw + 0.12)
    box(ix, ROW[r] + 0.12, iw, 0.80, "comp_fe", lw=0.7, z=4, r=0.09)
    txt(ix + iw/2, ROW[r] + 0.65, label,  C["frontend"]["hi"], sz=7, w="bold")
    txt(ix + iw/2, ROW[r] + 0.30, detail, DIM, sz=6.2, mono=True)
arrow(12.0, ROW[r], 12.0, ROW[r] - 0.28, C["frontend"]["bd"])

# ── Step 2 — Backend + InputClassifier ───────────────────────────────────────
r = 1
box(1.0, ROW[r], 22.0, RH, "backend", lw=1.6, z=2, r=0.18)
txt(12.0, ROW[r] + RH - 0.22, "BACKEND  ·  InputClassifier  (no LLM)  —  detect mode only", C["backend"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH / 2, 2, C["backend"]["bd"])

items2 = [
    ("File saved to disk", "tmp path stored\nin AgentSession"),
    ("Mode = DOC", "file_path set\nraw_input = path"),
    ("AgentSession", "state = INIT\ncreated in DB"),
    ("No truncation", "chunker handles\nall sizes"),
]
for i, (label, detail) in enumerate(items2):
    ix = 1.2 + i * (iw + 0.12)
    box(ix, ROW[r] + 0.12, iw, 0.80, "comp_be", lw=0.7, z=4, r=0.09)
    txt(ix + iw/2, ROW[r] + 0.65, label,  C["backend"]["hi"], sz=7, w="bold")
    txt(ix + iw/2, ROW[r] + 0.30, detail, MUTED, sz=6.2)
arrow(12.0, ROW[r], 12.0, ROW[r] - 0.28, C["agent"]["bd"])

# ── Step 3 — doc_extractor + smart_chunker ───────────────────────────────────
r = 2
box(1.0, ROW[r], 22.0, RH * 1.4, "agent", lw=1.6, z=2, r=0.18)
txt(12.0, ROW[r] + RH * 1.4 - 0.22, "STAGE 1  ·  PARSING  →  doc_extractor + smart_chunker  (Type A = no LLM  ·  Type B = LLM)", C["agent"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH * 1.4 / 2, 3, C["agent"]["bd"])

# Left branch — Type A (structured)
box(1.2, ROW[r] + 0.12, 9.8, 1.45, "green", lw=1.2, z=4, r=0.12)
txt(6.1, ROW[r] + 1.35, "Type A  —  Structured formats  (no LLM)", C["green"]["hi"], sz=7.5, w="bold")
no_llm_tag(8.9, ROW[r] + 1.28)

opt_a = [
    ("OpenAPI JSON/YAML", "iterate spec.paths\n1 chunk per {method+path}"),
    ("Postman Collection", "iterate items recursively\n1 chunk per request"),
]
for i, (label, detail) in enumerate(opt_a):
    cx = 1.4 + i * 4.8
    box(cx, ROW[r] + 0.22, 4.5, 0.90, "comp_ag", lw=0.6, z=6, r=0.08)
    txt(cx + 2.25, ROW[r] + 0.82, label,  C["agent"]["hi"], sz=6.8, w="bold")
    txt(cx + 2.25, ROW[r] + 0.45, detail, MUTED, sz=6, mono=True)

# Right branch — Type B (unstructured)
box(11.3, ROW[r] + 0.12, 11.5, 1.45, "llm", lw=1.2, z=4, r=0.12)
txt(17.05, ROW[r] + 1.35, "Type B  —  Unstructured  (PDF / DOCX / TXT)", C["external"]["hi"], sz=7.5, w="bold")
llm_tag(20.3, ROW[r] + 1.28)

opt_c = [
    ("Pass 1 — Index", "1 LLM call on full text\nextract [{method, path}]"),
    ("Find sections", "regex window\n±3K chars per endpoint"),
    ("Pass 2 — Extract", "1 LLM call per endpoint\nall run in parallel"),
]
for i, (label, detail) in enumerate(opt_c):
    cx = 11.5 + i * 3.7
    box(cx, ROW[r] + 0.22, 3.5, 0.90, "comp_ag", lw=0.6, z=6, r=0.08)
    txt(cx + 1.75, ROW[r] + 0.82, label,  C["agent"]["hi"], sz=6.8, w="bold")
    txt(cx + 1.75, ROW[r] + 0.45, detail, MUTED, sz=6, mono=True)
    if i < 2:
        arrow(cx + 3.5, ROW[r] + 0.67, cx + 3.7, ROW[r] + 0.67, C["agent"]["lo"], lw=0.8)

arrow(12.0, ROW[r], 12.0, ROW[r] - 0.28, C["agent"]["bd"])

# ── Step 4 — EndpointChunks (result) ─────────────────────────────────────────
r = 3
box(1.0, ROW[r], 22.0, RH, "agent", lw=1.6, z=2, r=0.18)
txt(12.0, ROW[r] + RH - 0.22, "CHUNKS READY  ·  [EndpointChunk]  —  1 chunk = 1 endpoint, zero boundary overlap", C["agent"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH / 2, 4, C["agent"]["bd"])

chunk_items = [
    ("method", "GET · POST\nPUT · DELETE"),
    ("path",   "/resource/{id}\nexact path"),
    ("hint",   "GET /resource/{id}\nhuman label"),
    ("content","raw endpoint JSON\nor text section"),
    ("base_info", "name · base_url\nauth_type"),
]
cw = 4.0
for i, (label, detail) in enumerate(chunk_items):
    cx = 1.4 + i * (cw + 0.22)
    box(cx, ROW[r] + 0.12, cw, 0.80, "comp_ag", lw=0.7, z=5, r=0.09)
    txt(cx + cw/2, ROW[r] + 0.66, label,  C["agent"]["hi"], sz=7, w="bold", mono=True)
    txt(cx + cw/2, ROW[r] + 0.30, detail, MUTED, sz=6.2)
arrow(12.0, ROW[r], 12.0, ROW[r] - 0.28, C["agent"]["bd"])

# ── Step 5 — SchemaAgent parallel ────────────────────────────────────────────
r = 4
box(1.0, ROW[r], 22.0, RH, "agent", lw=1.6, z=2, r=0.18)
txt(12.0, ROW[r] + RH - 0.22, "STAGE 3  ·  SCHEMA_GENERATING  →  SchemaAgent  (parallel, 1 LLM call per endpoint)", C["agent"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH / 2, 5, C["agent"]["bd"])

# meta call
box(1.2, ROW[r] + 0.12, 3.8, 0.80, "llm", lw=0.9, z=5, r=0.09)
txt(3.1, ROW[r] + 0.68, "meta call", C["external"]["hi"], sz=7, w="bold")
txt(3.1, ROW[r] + 0.40, "name · base_url\nauth_type · version", MUTED, sz=6)
txt(3.1, ROW[r] + 0.18, "1 call", DIM, sz=5.5)

# endpoint calls
for i in range(5):
    ex = 5.3 + i * 3.3
    label = f"endpoint {i+1}" if i < 4 else "endpoint N"
    box(ex, ROW[r] + 0.12, 3.1, 0.80, "llm", lw=0.9, z=5, r=0.09)
    txt(ex + 1.55, ROW[r] + 0.62, label, C["external"]["hi"], sz=6.5, w="bold")
    txt(ex + 1.55, ROW[r] + 0.38, "input_schema\nrequired[]", MUTED, sz=5.8)
    txt(ex + 1.55, ROW[r] + 0.17, "≤2048 tokens", DIM, sz=5.5)

txt(21.3, ROW[r] + 0.46, "all\nparallel", C["agent"]["hi"], sz=6.5, w="bold", ha="center")
txt(12.0, ROW[r] + 0.0, "asyncio.gather() — never truncates — scales to any number of endpoints", DIM, sz=6, ha="center")
arrow(12.0, ROW[r], 12.0, ROW[r] - 0.22, C["agent"]["bd"])

# ── Step 6 — ConfidenceAgent ──────────────────────────────────────────────────
r = 5
box(1.0, ROW[r], 22.0, RH, "agent", lw=1.6, z=2, r=0.18)
txt(12.0, ROW[r] + RH - 0.22, "STAGE 4  ·  CONFIDENCE_SCORING  (GPT-4o)  →  state = HITL_PENDING", C["agent"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH / 2, 6, C["agent"]["bd"])

box(1.2, ROW[r] + 0.12, 21.6, 0.80, "llm", lw=1.0, z=4, r=0.09)
conf = [
    ("Score 0-100", "per field"),
    ("HIGH ≥70", "GREEN dot"),
    ("MEDIUM 40-69", "YELLOW dot"),
    ("LOW < 40", "RED dot"),
    ("Suggestion", "fix hint if low"),
    ("confidence_map", "saved to DB"),
]
for i, (label, detail) in enumerate(conf):
    cx = 1.5 + i * 3.6
    txt(cx + 1.5, ROW[r] + 0.62, label,  C["external"]["hi"], sz=6.8, w="bold")
    txt(cx + 1.5, ROW[r] + 0.30, detail, MUTED, sz=6.2)
llm_tag(20.8, ROW[r] + 0.62)
arrow(12.0, ROW[r], 12.0, ROW[r] - 0.22, C["frontend"]["bd"])

# ── Step 7 — HITL ────────────────────────────────────────────────────────────
r = 6
box(1.0, ROW[r], 22.0, RH, "frontend", lw=1.6, z=2, r=0.18)
txt(12.0, ROW[r] + RH - 0.22, "FRONTEND  ·  HITL Validator  (/validate/:id)  —  Human Review", C["frontend"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH / 2, 7, C["frontend"]["bd"])

hitl = [
    ("Confidence dots", "GREEN / YELLOW / RED\nper field"),
    ("Edit fields", "click any field\nto override"),
    ("Endpoints", "add / remove\nendpoints inline"),
    ("POST /hitl", "human_edits\npayload"),
]
for i, (label, detail) in enumerate(hitl):
    ix = 1.2 + i * (iw + 0.1)
    box(ix, ROW[r] + 0.12, iw, 0.80, "comp_fe", lw=0.7, z=4, r=0.09)
    txt(ix + iw/2, ROW[r] + 0.65, label,  C["frontend"]["hi"], sz=7, w="bold")
    txt(ix + iw/2, ROW[r] + 0.30, detail, MUTED, sz=6.2)
arrow(12.0, ROW[r], 12.0, ROW[r] - 0.22, C["agent"]["bd"])

# ── Step 8 — Validate + Test + Save ──────────────────────────────────────────
r = 7
box(1.0, ROW[r], 22.0, RH, "agent", lw=1.6, z=2, r=0.18)
txt(12.0, ROW[r] + RH - 0.22, "STAGE 5+6+7  ·  SchemaValidator → ApiTestAgent → ApiSaver", C["agent"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH / 2, 8, C["agent"]["bd"])

pipeline = [
    ("SchemaValidator", "rule-based checks\nname/url/paths/methods", False),
    ("ApiTestAgent",    "live GET tests\nhttpx + GPT-4o assess", True),
    ("encrypt_creds()", "Fernet encrypt\nauth credentials", False),
    ("ApiSaver", "ApiDefinition +\nApiEndpoint → DB", False),
    ("state = SAVED", "session finalized\nresult_id returned", False),
]
pw = 4.0
for i, (label, detail, is_llm) in enumerate(pipeline):
    px = 1.2 + i * (pw + 0.22)
    key = "llm" if is_llm else "comp_ag"
    box(px, ROW[r] + 0.12, pw, 0.80, key, lw=0.7, z=4, r=0.09)
    txt(px + pw/2, ROW[r] + 0.64, label,  C["agent"]["hi"], sz=7, w="bold")
    txt(px + pw/2, ROW[r] + 0.30, detail, MUTED, sz=6)
    if is_llm:
        llm_tag(px + pw - 1.6, ROW[r] + 0.65)
    if i < len(pipeline) - 1:
        arrow(px + pw, ROW[r] + 0.52, px + pw + 0.22, ROW[r] + 0.52, C["agent"]["lo"], lw=0.7)
arrow(12.0, ROW[r], 12.0, ROW[r] - 0.22, C["db"]["bd"])

# ── Step 9 — DB ───────────────────────────────────────────────────────────────
r = 8
box(1.0, ROW[r], 22.0, RH, "db", lw=1.6, z=2, r=0.18)
txt(12.0, ROW[r] + RH - 0.22, "DATABASE  ·  PostgreSQL", C["db"]["hi"], sz=8, w="bold", ha="center")
step_badge(step_x, ROW[r] + RH / 2, 9, C["db"]["bd"])

db_tables = [
    ("api_definitions",  "name · base_url\nvisibility · user_id"),
    ("api_endpoints",    "path · method\ninput_schema (full)"),
    ("agent_sessions",   "state=SAVED\ndraft_api · confidence_map"),
]
dw = 6.8
for i, (label, detail) in enumerate(db_tables):
    dx = 1.2 + i * (dw + 0.3)
    box(dx, ROW[r] + 0.12, dw, 0.80, "comp_db", lw=0.7, z=4, r=0.09)
    txt(dx + dw/2, ROW[r] + 0.64, label,  C["db"]["hi"], sz=7.5, w="bold", mono=True)
    txt(dx + dw/2, ROW[r] + 0.28, detail, MUTED, sz=6.2)

# ── Footer ────────────────────────────────────────────────────────────────────
hline(0.68)
txt(0.6,  0.46, "v2  ·  Smart Chunking  ·  Type A (structured) = 0 LLM calls for parsing  ·  Type B (unstructured) = parallel targeted extraction", DIM, sz=6.2, ha="left")
txt(W-0.6, 0.46, "LLM stages in amber  ·  No-LLM stages in green", DIM, sz=6.2, ha="right")

out = os.path.join(os.path.dirname(__file__), "usecase2_doc_upload.png")
plt.savefig(out, dpi=200, bbox_inches="tight", facecolor=BG, edgecolor="none")
plt.close()
print(f"Saved: {out}")
