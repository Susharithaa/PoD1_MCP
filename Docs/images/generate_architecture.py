"""
MCP Hub — System Architecture v2
Renders to: Docs/images/01_system_architecture.png

Changes from v1:
  - Social OAuth2 (Google + GitHub) with OTP 2FA
  - Subscription system: chat_status, credits, admin approval
  - Smart Chunking: Type A (no LLM) + Type B (2-pass LLM)
  - token_usage DB table
  - GPT-4o Engine with Subscription Gate + cost formula
  - /api/subscription router
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import os

W, H = 30, 30
BG   = "#f6f8fa"

C = {
    "frontend": {"bg": "#eff6ff", "bd": "#3b82f6", "hi": "#1e40af", "lo": "#dbeafe"},
    "backend":  {"bg": "#f0fdf4", "bd": "#16a34a", "hi": "#14532d", "lo": "#dcfce7"},
    "agent":    {"bg": "#f5f3ff", "bd": "#7c3aed", "hi": "#4c1d95", "lo": "#ede9fe"},
    "llm":      {"bg": "#fef3c7", "bd": "#f59e0b", "hi": "#78350f", "lo": "#fde68a"},
    "db":       {"bg": "#f0f9ff", "bd": "#0284c7", "hi": "#0c4a6e", "lo": "#e0f2fe"},
    "external": {"bg": "#fffbeb", "bd": "#d97706", "hi": "#78350f", "lo": "#fef3c7"},
    "green":    {"bg": "#f0fdf4", "bd": "#22c55e", "hi": "#14532d", "lo": "#dcfce7"},
    "red":      {"bg": "#fef2f2", "bd": "#ef4444", "hi": "#7f1d1d", "lo": "#fecaca"},
    "violet":   {"bg": "#fdf4ff", "bd": "#a855f7", "hi": "#581c87", "lo": "#f3e8ff"},
    "comp_fe":  {"bg": "#dbeafe", "bd": "#93c5fd", "hi": "#1e40af", "lo": "#eff6ff"},
    "comp_be":  {"bg": "#dcfce7", "bd": "#86efac", "hi": "#14532d", "lo": "#f0fdf4"},
    "comp_ag":  {"bg": "#ede9fe", "bd": "#c4b5fd", "hi": "#4c1d95", "lo": "#f5f3ff"},
    "comp_db":  {"bg": "#e0f2fe", "bd": "#7dd3fc", "hi": "#0c4a6e", "lo": "#f0f9ff"},
    "comp_ext": {"bg": "#fef3c7", "bd": "#fcd34d", "hi": "#78350f", "lo": "#fffbeb"},
    "comp":     {"bg": "#f8fafc", "bd": "#cbd5e1", "hi": "#1e293b", "lo": "#e2e8f0"},
    "mw":       {"bg": "#dcfce7", "bd": "#16a34a", "hi": "#14532d", "lo": "#f0fdf4"},
}
TEXT  = "#0f172a"
MUTED = "#475569"
DIM   = "#94a3b8"

fig = plt.figure(figsize=(W, H), facecolor=BG, dpi=180)
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


def bidirectional(x1, y1, x2, y2, color=DIM, lw=1.2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="<->", color=color, lw=lw, mutation_scale=10),
                zorder=6, annotation_clip=False)


def hline(y, color="#cbd5e1", lw=0.8):
    ax.plot([0.4, W - 0.4], [y, y], color=color, lw=lw, zorder=1)


def step_badge(x, y, n, color):
    ax.add_patch(FancyBboxPatch((x - 0.22, y - 0.22), 0.44, 0.44,
        boxstyle="round,pad=0,rounding_size=0.1",
        fc=color, ec="none", zorder=15, clip_on=False))
    ax.text(x, y, str(n), color="white", fontsize=6.5, fontweight="bold",
            ha="center", va="center", zorder=16, clip_on=False)


def llm_tag(x, y, label="GPT-4o"):
    box(x, y, 1.45, 0.32, "llm", lw=0.5, z=9, r=0.06)
    txt(x + 0.72, y + 0.16, label, C["llm"]["hi"], sz=5.5, w="bold")


def mini_tag(x, y, label, key):
    box(x, y, 1.3, 0.28, key, lw=0.4, z=9, r=0.05)
    txt(x + 0.65, y + 0.14, label, C[key]["hi"], sz=5, w="bold")


# ══════════════════════════════════════════════════════════════════════════════
# TITLE
# ══════════════════════════════════════════════════════════════════════════════
txt(W / 2, 29.55, "MCP HUB  —  SYSTEM ARCHITECTURE  v2", TEXT, sz=17, w="bold", mono=True)
txt(W / 2, 29.0,  "OAuth2 (Google + GitHub)  ·  OTP 2FA  ·  Smart Chunking (Type A + B)  ·  Subscription & Credits  ·  GPT-4o Tool Engine", MUTED, sz=8.5)
hline(28.7)

# ══════════════════════════════════════════════════════════════════════════════
# FRONTEND  y=26.2–28.4
# ══════════════════════════════════════════════════════════════════════════════
FX, FY, FW, FH = 0.4, 26.2, 29.2, 2.2
box(FX, FY, FW, FH, "frontend", lw=1.8, z=2, r=0.22)
txt(FX + 0.4, FY + FH - 0.28, "FRONTEND  ·  React 18 + Vite + Tailwind + Axios",
    C["frontend"]["hi"], sz=8.5, w="bold", ha="left", z=8)

# 4 page groups
groups = [
    ("Authentication",
     ["Login — 2-step OTP", "Register", "AuthCallback (OAuth)", "Social buttons (Google/GitHub)"]),
    ("API Creation",
     ["ChatBuilder (NL chat)", "DocUpload (file upload)", "HITLValidator (review)", "Confidence dots"]),
    ("GPT-4o Chat Hub",
     ["ChatGPTHub", "AccessGate (none/pending/rejected)", "NoCreditsGate", "Credit balance card"]),
    ("Management",
     ["Registry", "Monitor", "Admin — Users tab", "Admin — Chat Access tab"]),
]
gw = (FW - 0.35) / 4
for i, (title, items) in enumerate(groups):
    gx = FX + 0.18 + i * gw
    box(gx, FY + 0.14, gw - 0.12, FH - 0.52, "comp_fe", lw=0.7, z=4, r=0.09)
    txt(gx + (gw - 0.12) / 2, FY + FH - 0.58, title, C["frontend"]["hi"], sz=7, w="bold")
    for j, item in enumerate(items):
        txt(gx + 0.18, FY + FH - 0.85 - j * 0.26, "· " + item, MUTED, sz=5.8, ha="left")

# Context bar
ctx = [
    "AuthContext (JWT · user · role)",
    "ThemeContext (dark/light)",
    "LanguageContext (EN/JA)",
    "api.js — Axios + JWT Bearer",
]
ciw = (FW - 0.3) / len(ctx)
for i, c in enumerate(ctx):
    cix = FX + 0.15 + i * ciw
    box(cix, FY + 0.0, ciw - 0.06, 0.1, "frontend", lw=0.3, z=3, r=0.04)
    # just inline text
txt(FX + FW / 2, FY + 0.06, "  ·  ".join(ctx), C["frontend"]["hi"], sz=6, ha="center")

bidirectional(W / 2, FY, W / 2, FY - 0.28, C["frontend"]["bd"])
txt(W / 2 + 0.2, FY - 0.14, "HTTP REST + JWT Bearer", DIM, sz=6, ha="left")

# ══════════════════════════════════════════════════════════════════════════════
# BACKEND  y=11.5–25.7
# ══════════════════════════════════════════════════════════════════════════════
BKX, BKY, BKW, BKH = 0.4, 11.5, 29.2, 14.4
box(BKX, BKY, BKW, BKH, "backend", lw=1.8, z=2, r=0.22)
txt(BKX + 0.4, BKY + BKH - 0.3, "BACKEND  ·  FastAPI + SQLAlchemy + Python 3.13 + Alembic + Pydantic v2",
    C["backend"]["hi"], sz=8.5, w="bold", ha="left", z=8)

# Middleware banner
box(BKX + 0.18, BKY + BKH - 0.74, BKW - 0.36, 0.38, "mw", lw=0.6, z=4, r=0.07)
mw_items = ["CORS Middleware", "slowapi Rate Limiting (5–60 req/min)", "JWT Auth Guard (get_current_user)", "Global Exception Handlers"]
mww = (BKW - 0.36) / len(mw_items)
for i, m in enumerate(mw_items):
    txt(BKX + 0.18 + (i + 0.5) * mww, BKY + BKH - 0.55, m, C["backend"]["hi"], sz=6.5, w="bold")

# ── Routers  ──────────────────────────────────────────────────────────────────
ROUTERS = [
    ("/api/auth",       "register · login (OTP step 1)\nverify-otp · me\nadmin: users · role · active"),
    ("/api/auth OAuth", "GET /google → redirect\nGET /google/callback → JWT\nGET /github → callback\nemail fallback /user/emails"),
    ("/api/agent",      "POST manual · chat · upload\nGET /{id} poll state\nPOST /{id}/hitl · confirm"),
    ("/api/chatgpt",    "POST connect · DELETE disconnect\nGET registry · tools\nPOST chat (agentic)\nGET stats"),
    ("/api/subscription", "POST request · GET status\nadmin: requests · all-users\napprove · reject · top-up"),
    ("/api/registry\n/api/monitor", "registry: list · get · delete\nmonitor: overview · active\nsessions · tool-calls · pipeline"),
]
rw = (BKW - 0.36 - 0.15 * 5) / 6
ry = BKY + BKH - 2.0
rh = 1.15
for i, (route, desc) in enumerate(ROUTERS):
    rx = BKX + 0.18 + i * (rw + 0.15)
    key = "violet" if "OAuth" in route else ("violet" if "subscription" in route else "comp_be")
    box(rx, ry, rw, rh, key, lw=0.9, z=4, r=0.1)
    txt(rx + rw / 2, ry + rh - 0.22, route, C["backend"]["hi"], sz=6.5, w="bold", mono=True)
    txt(rx + rw / 2, ry + rh * 0.42,  desc,  MUTED,              sz=5.8,            mono=False)

# ── Agent Pipeline  ───────────────────────────────────────────────────────────
APX, APY, APW, APH = BKX + 0.18, BKY + 4.8, BKW - 0.36, 6.4
box(APX, APY, APW, APH, "agent", lw=1.4, z=3, r=0.15)
txt(APX + 0.3, APY + APH - 0.28,
    "AGENT PIPELINE  ·  Async State Machine  ·  INIT → CLASSIFYING → PARSING → SCHEMA → CONFIDENCE → HITL → VALIDATING → TESTING → SAVING → SAVED",
    C["agent"]["hi"], sz=7, w="bold", ha="left", z=8)

STAGES = [
    ("1", "InputClassifier",                    "CLASSIFYING",      "comp_ag", False,
     "DOC vs CHAT\nfile_path or\nraw_input"),
    ("2", "ParsingAgent\n+doc_extractor\n+smart_chunker", "PARSING", "comp_ag", False,
     "Type A: OpenAPI\nPostman → 0 LLM\nType B: PDF/DOCX/TXT\n2-pass LLM extract"),
    ("3", "SchemaAgent",                        "SCHEMA_GENERATING", "llm",    True,
     "asyncio.gather()\n1 call per endpoint\n≤2048 tok each\n+ 1 meta call"),
    ("4", "ConfidenceAgent",                    "CONFIDENCE_SCORING","llm",    True,
     "Score 0–100 /field\nGREEN ≥70\nYELLOW 40–69\nRED <40"),
    ("5", "HITL Pause",                         "HITL_PENDING",     "red",    False,
     "PAUSE: human\nreview + edit\nfields · endpoints\nauth creds"),
    ("6", "SchemaValidator",                    "VALIDATING",       "comp_ag", False,
     "Rule-based only\nname · url · paths\nmethods · fields\nNo LLM"),
    ("7", "ApiTestAgent",                       "API_TESTING",      "llm",    True,
     "httpx live GET\nGPT-4o assess\nresponse quality\nstore results"),
    ("8", "ApiSaver",                           "SAVING→SAVED",     "comp_ag", False,
     "Fernet encrypt\ncreds · write\nApiDefinition\n+ ApiEndpoints"),
]
sw = (APW - 0.3 - 0.1 * 7) / 8
sh = APH - 0.72
sy = APY + 0.18
for i, (num, name, state, key, is_llm, detail) in enumerate(STAGES):
    sx = APX + 0.15 + i * (sw + 0.1)
    box(sx, sy, sw, sh, key, lw=0.9, z=5, r=0.1)
    step_badge(sx + 0.22, sy + sh - 0.18, num, C["agent"]["bd"] if key != "red" else C["red"]["bd"])
    txt(sx + sw / 2, sy + sh - 0.55, name,  C["agent"]["hi"] if key not in ("llm","red") else C[key]["hi"], sz=6.3, w="bold")
    txt(sx + sw / 2, sy + sh - 0.88, state, C["agent"]["bd"] if key not in ("llm","red") else C[key]["bd"], sz=5.5, mono=True)
    txt(sx + sw / 2, sy + sh * 0.38, detail, MUTED, sz=5.5)
    if is_llm:
        llm_tag(sx + sw * 0.07, sy + 0.08)
    if i < len(STAGES) - 1:
        ax.annotate("", xy=(sx + sw + 0.1, sy + sh / 2),
                    xytext=(sx + sw, sy + sh / 2),
                    arrowprops=dict(arrowstyle="->", color=C["agent"]["lo"], lw=0.6),
                    zorder=7, annotation_clip=False)

# ── GPT-4o Engine  ────────────────────────────────────────────────────────────
GEX, GEY, GEW, GEH = BKX + 0.18, BKY + 0.8, BKW - 0.36, 3.8
box(GEX, GEY, GEW, GEH, "llm", lw=1.4, z=3, r=0.15)
txt(GEX + 0.3, GEY + GEH - 0.28, "GPT-4o TOOL ENGINE  ·  ChatGPTHub Feature  ·  Subscription Gate (v2)",
    C["llm"]["hi"], sz=7.5, w="bold", ha="left", z=8)

gw3 = (GEW - 0.3 - 0.2 * 2) / 3
gpt_cards = [
    ("Subscription Gate (v2)",
     "chat_status: none/pending/\nrejected → 403\ncredits=0 → 402\nAdmins bypass"),
    ("Context Layer",
     "Per-session history\nSystem prompt from\nconnected APIs\nAuto-expire 2 h"),
    ("Tool Orchestrator",
     "ApiDefinition → OpenAI\ntool schema · parallel\nexecute + retry\nLog → tool_call_logs"),
]
for i, (name, detail) in enumerate(gpt_cards):
    gx = GEX + 0.15 + i * (gw3 + 0.2)
    box(gx, GEY + 0.85, gw3, GEH - 1.06, "comp_ext", lw=0.8, z=5, r=0.1)
    txt(gx + gw3 / 2, GEY + GEH - 0.50, name,   C["llm"]["hi"], sz=6.5, w="bold")
    txt(gx + gw3 / 2, GEY + GEH - 1.05, detail, MUTED,          sz=5.8)

# cost formula bar
box(GEX + 0.15, GEY + 0.16, GEW - 0.3, 0.55, "comp", lw=0.5, z=5, r=0.07)
txt(GEX + GEW / 2, GEY + 0.44,
    "Cost: (prompt_tokens × $2.50 + completion_tokens × $10.00) / 1,000,000  ·  Deducted from User.credits after full loop  ·  Logged to token_usage",
    C["llm"]["hi"], sz=6, w="bold", mono=True)

# vertical arrows from routers → pipeline → gpt engine
for ax_x in [2.5, 8.5, 14.0, 20.5, 26.0]:
    arrow(ax_x, ry, ax_x, APY + APH, C["backend"]["lo"], lw=0.7)
    arrow(ax_x, APY, ax_x, GEY + GEH, C["agent"]["lo"], lw=0.7)

# ══════════════════════════════════════════════════════════════════════════════
# CONNECTOR ARROWS
# ══════════════════════════════════════════════════════════════════════════════
# backend → DB (left)
bidirectional(7.0, BKY, 7.0, BKY - 0.32, C["db"]["bd"])
txt(7.4, BKY - 0.15, "SQL / ORM", DIM, sz=6, ha="left")

# backend → External (right)
bidirectional(23.0, BKY, 23.0, BKY - 0.32, C["external"]["bd"])
txt(23.4, BKY - 0.15, "HTTPS", DIM, sz=6, ha="left")

# ══════════════════════════════════════════════════════════════════════════════
# DATABASE  y=4.2–11.0  x=0.4–14.8
# ══════════════════════════════════════════════════════════════════════════════
DBX, DBY, DBW, DBH = 0.4, 4.2, 14.4, 7.0
box(DBX, DBY, DBW, DBH, "db", lw=1.8, z=2, r=0.22)
txt(DBX + 0.4, DBY + DBH - 0.28, "DATABASE  ·  PostgreSQL  /  SQLite (dev)  ·  Alembic migrations",
    C["db"]["hi"], sz=8, w="bold", ha="left", z=8)

DB_TABLES = [
    ("users",              "email · hashed_password(nullable)\nrole · is_active · auth_provider\nchat_status · credits(float)",  True),
    ("agent_sessions",     "mode · state · user_id\nextracted_schema · draft_api\nconfidence_map · final_api",                  False),
    ("api_definitions",    "name · base_url · version\nvisibility · tags · user_id\nsource_session_id",                         False),
    ("api_endpoints",      "path · method · input_schema\noutput_schema · headers\nauth_credentials (encrypted)",               False),
    ("chatgpt_connections","api_definition_id · user_id\nis_active · connected_at",                                             False),
    ("tool_call_logs",     "endpoint_name · arguments\nresult (1000 char) · success\ncalled_at",                                False),
    ("token_usage ★",     "user_id · session_id\nprompt/completion_tokens\ncost_usd · created_at",                             True),
    ("auth_config",        "provider · client_id\nencrypted secrets\nredirect_uri",                                             False),
]
dtw = (DBW - 0.36 - 0.15 * 3) / 4
dth = 1.45
for i, (name, fields, is_new) in enumerate(DB_TABLES):
    col = i % 4
    row = i // 4
    dx = DBX + 0.18 + col * (dtw + 0.15)
    dy = DBY + DBH - 1.0 - row * (dth + 0.18) - dth
    key = "violet" if is_new else "comp_db"
    box(dx, dy, dtw, dth, key, lw=0.9, z=4, r=0.1)
    txt(dx + dtw / 2, dy + dth - 0.28, name,   C["db"]["hi"], sz=6.5, w="bold", mono=True)
    txt(dx + dtw / 2, dy + dth * 0.40, fields, MUTED,         sz=5.6)

# ══════════════════════════════════════════════════════════════════════════════
# EXTERNAL SERVICES  y=4.2–11.0  x=15.2–29.6
# ══════════════════════════════════════════════════════════════════════════════
EX, EY, EW, EH = 15.2, 4.2, 14.4, 7.0
box(EX, EY, EW, EH, "external", lw=1.8, z=2, r=0.22)
txt(EX + 0.4, EY + EH - 0.28, "EXTERNAL SERVICES",
    C["external"]["hi"], sz=8, w="bold", ha="left", z=8)

EXT_SERVICES = [
    ("OpenAI GPT-4o",
     "AsyncOpenAI SDK\nSchemaAgent (stage 3)\nConfidenceAgent (stage 4)\nApiTestAgent (stage 7)\nChatGPTHub agentic loop"),
    ("Google OAuth2  ★",
     "accounts.google.com/o/oauth2\nAuthorization code flow\nid_token → email decode\nfind_or_create user"),
    ("GitHub OAuth2  ★",
     "github.com/login/oauth\nAuthorization code flow\n/user/emails fallback\nfind_or_create user"),
    ("SMTP Gmail  ★",
     "Port 587 STARTTLS\nOTP email on login\n6-digit · 10-min expiry\n5-attempt OTPStore"),
    ("User APIs (Testing)",
     "httpx async client\nLive GET calls during\nApiTestAgent (stage 7)\nResponse → GPT-4o assess"),
    ("Rate Limits",
     "slowapi limiter\n/login: 5/min\n/register: 10/min\n/chat: 60/min"),
]
ew2 = (EW - 0.36 - 0.15 * 2) / 3
eh2 = (EH - 0.72 - 0.15) / 2
for i, (name, detail) in enumerate(EXT_SERVICES):
    col = i % 3
    row = i // 3
    ex2 = EX + 0.18 + col * (ew2 + 0.15)
    ey2 = EY + EH - 0.72 - row * (eh2 + 0.15) - eh2
    is_new = "★" in name
    key = "violet" if is_new else "comp_ext"
    box(ex2, ey2, ew2, eh2, key, lw=0.9, z=4, r=0.1)
    txt(ex2 + ew2 / 2, ey2 + eh2 - 0.28, name.replace("  ★",""), C["external"]["hi"], sz=6.5, w="bold")
    txt(ex2 + ew2 / 2, ey2 + eh2 * 0.42, detail, MUTED, sz=5.7)
    if is_new:
        mini_tag(ex2 + ew2 - 1.4, ey2 + eh2 - 0.34, "v2", "violet")

# dashed arrows: backend → external services
for src_x, dst_x in [(14.5, 15.5), (14.5, 20.0), (14.5, 24.5)]:
    arrow(src_x, 7.5, dst_x, 7.5, C["external"]["lo"], lw=0.8, dash=True)

# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
hline(3.9)
txt(0.6, 3.65, "MCP Hub v2  ·  Smart Chunking (Type A + B)  ·  Social OAuth2  ·  OTP 2FA  ·  Subscription & Credits  ·  Fernet encrypted creds",
    DIM, sz=6.5, ha="left")
txt(W - 0.6, 3.65, "System Architecture  ·  2026-04-23", DIM, sz=6.5, ha="right")

# ── Legend boxes ─────────────────────────────────────────────────────────────
legend_items = [
    ("Frontend",   "frontend"),
    ("Backend",    "backend"),
    ("Agents",     "agent"),
    ("LLM/GPT-4o", "llm"),
    ("Database",   "db"),
    ("External",   "external"),
    ("Type A / no LLM", "green"),
    ("New in v2",  "violet"),
]
lx = 0.6
for label, key in legend_items:
    box(lx, 0.3, 2.5, 0.42, key, lw=0.8, z=5, r=0.06)
    txt(lx + 1.25, 0.51, label, C[key]["hi"], sz=5.8, w="bold")
    lx += 2.65

# ── Save ───────────────────────────────────────────────────────────────────────
out = os.path.join(os.path.dirname(__file__), "01_system_architecture.png")
plt.savefig(out, dpi=180, bbox_inches="tight", facecolor=BG, edgecolor="none")
plt.close()
print(f"Saved: {out}")
