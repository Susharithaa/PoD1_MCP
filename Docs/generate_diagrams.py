# -*- coding: utf-8 -*-
"""MCP Hub - Professional Architecture & Sequence Diagrams
Tech stack: FastAPI backend, React Router frontend, SQLite DB
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
BG      = "#0D1117"
SURFACE = "#161B22"
BORDER  = "#30363D"

BLUE    = "#58A6FF"
PURPLE  = "#BC8CFF"
TEAL    = "#39D3C3"
ORANGE  = "#F0883E"
RED     = "#F85149"
GREEN   = "#3FB950"
YELLOW  = "#E3B341"
GRAY    = "#8B949E"
WHITE   = "#F0F6FC"

FONT = "DejaVu Sans"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def new_fig(w, h, title=""):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    if title:
        ax.text(w / 2, h - 0.28, title,
                ha="center", va="top", fontsize=13, fontweight="bold",
                color=WHITE, fontfamily=FONT,
                bbox=dict(boxstyle="round,pad=0.4", fc=SURFACE, ec=BORDER, lw=1))
    return fig, ax


def rect(ax, x, y, w, h, label, sublabel="",
         fc=SURFACE, ec=BLUE, lw=1.5, fs=9, sfs=7.5,
         r=0.18, lc=WHITE, slc=GRAY):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle=f"round,pad=0,rounding_size={r}",
                                linewidth=lw, edgecolor=ec,
                                facecolor=ec + "25"))
    cy = y + h / 2 + (0.13 if sublabel else 0)
    ax.text(x + w / 2, cy, label, ha="center", va="center",
            fontsize=fs, fontweight="bold", color=lc, fontfamily=FONT)
    if sublabel:
        ax.text(x + w / 2, y + h / 2 - 0.16, sublabel,
                ha="center", va="center", fontsize=sfs,
                color=slc, fontfamily=FONT, style="italic")


def band(ax, x, y, w, h, color, alpha=0.07, radius=0.25, label="", lfs=8):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle=f"round,pad=0,rounding_size={radius}",
                                lw=1, ec=color + "50", fc=color,
                                alpha=alpha))
    if label:
        ax.text(x + 0.18, y + h - 0.22, label,
                ha="left", va="top", fontsize=lfs, color=color,
                fontfamily=FONT, fontweight="bold")


def arr(ax, x1, y1, x2, y2, color=GRAY, lw=1.4,
        rad=0.0, style="-|>", dashed=False):
    ls = (0, (4, 3)) if dashed else "solid"
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(
                    arrowstyle=style, color=color, lw=lw,
                    mutation_scale=10,
                    connectionstyle=f"arc3,rad={rad}",
                    linestyle=ls))


def arr_label(ax, x, y, text, color=GRAY, fs=7.2, bg=True):
    kw = {}
    if bg:
        kw["bbox"] = dict(boxstyle="round,pad=0.15", fc=BG, ec="none")
    ax.text(x, y, text, ha="center", va="center",
            fontsize=fs, color=color, fontfamily=FONT, **kw)


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  Saved: {name}")


# ===========================================================================
# 1. SYSTEM ARCHITECTURE
# ===========================================================================
def d1_system_architecture():
    fig, ax = new_fig(18, 12, "MCP Hub  -  System Architecture")

    # ---- layer bands -------------------------------------------------------
    band(ax, 0.4, 10.2, 17.2, 1.4, BLUE,   label="USER / CLIENT LAYER")
    band(ax, 0.4,  8.0, 17.2, 2.0, PURPLE, label="FRONTEND  (React Router SPA)")
    band(ax, 0.4,  5.0, 17.2, 2.8, TEAL,   label="BACKEND  (FastAPI)")
    band(ax, 0.4,  2.5, 17.2, 2.3, ORANGE, label="AI / AGENT LAYER")
    band(ax, 0.4,  0.3, 17.2, 2.0, GREEN,  label="DATA LAYER  (SQLite + FileStore)")

    # ---- USER LAYER --------------------------------------------------------
    for i, (lbl, sub) in enumerate([
        ("Browser", "React Router SPA"),
        ("ChatGPT / Claude", "LLM Client (MCP)"),
        ("API Consumer", "SDK / curl"),
    ]):
        rect(ax, 1.2 + i * 5.8, 10.35, 4.8, 1.1, lbl, sub, ec=BLUE, fs=9.5)

    # ---- FRONTEND LAYER ----------------------------------------------------
    pages = [
        ("Chat Builder", "Conversational UI"),
        ("Doc Upload", "File + Paste UI"),
        ("HITL Validator", "Review & Edit UI"),
        ("API Registry", "Browse & Search"),
        ("Settings", "Auth & Workspace"),
    ]
    for i, (lbl, sub) in enumerate(pages):
        rect(ax, 0.7 + i * 3.42, 8.18, 3.1, 1.5, lbl, sub, ec=PURPLE, fs=8.8)

    # ---- BACKEND LAYER (FastAPI) -------------------------------------------
    svc = [
        ("Chat\nService",    "/api/chat",      TEAL),
        ("Upload\nService",  "/api/upload",    TEAL),
        ("HITL\nService",    "/api/validate",  TEAL),
        ("Registry\nService","/api/registry",  TEAL),
        ("Exec\nEngine",     "/api/execute",   TEAL),
        ("MCP\nBridge",      "/mcp",           ORANGE),
    ]
    for i, (lbl, sub, col) in enumerate(svc):
        rect(ax, 0.7 + i * 2.9, 5.15, 2.55, 1.65, lbl, sub, ec=col, fs=8.5)

    # auth bar under services
    rect(ax, 0.7, 4.88, 17.0, 0.32, "Auth Middleware  (API Key / JWT)", "",
         ec=RED, fs=8, lc=RED, r=0.1)

    # ---- AI LAYER ----------------------------------------------------------
    ai_items = [
        ("Parsing\nAgent",     "Doc -> Schema",  ORANGE),
        ("Schema\nGenerator",  "Draft API",      ORANGE),
        ("Confidence\nScorer", "Field scoring",  YELLOW),
        ("Conversation\nAgent","Q&A flow",       ORANGE),
        ("LLM Client",         "Claude / GPT",   PURPLE),
    ]
    for i, (lbl, sub, col) in enumerate(ai_items):
        rect(ax, 0.8 + i * 3.4, 2.62, 3.0, 1.65, lbl, sub, ec=col, fs=8.5)

    # ---- DATA LAYER --------------------------------------------------------
    data = [
        ("SQLite DB",          "api_definitions, endpoints\nauth_configs, exec_logs",  GREEN),
        ("File Store",         "Uploaded docs\nOpenAPI / PDFs / text",                 TEAL),
        ("Redis (optional)",   "Session cache\nQueue for async jobs",                  ORANGE),
        ("External APIs",      "Target endpoints\ncalled by Exec Engine",              RED),
    ]
    for i, (lbl, sub, col) in enumerate(data):
        rect(ax, 0.7 + i * 4.35, 0.42, 3.9, 1.9, lbl, sub, ec=col, fs=8.5)

    # ---- ARROWS: user -> frontend ------------------------------------------
    for x in [3.6, 9.4, 15.2]:
        arr(ax, x, 10.35, x, 9.68, BLUE)

    # ---- ARROWS: frontend -> backend ---------------------------------------
    fe_mid = [2.25, 5.67, 9.09, 12.51, 15.93]
    be_mid = [1.975, 4.875, 7.775, 10.675, 13.575, 16.475]
    for fx in fe_mid[:5]:
        closest = min(be_mid, key=lambda bx: abs(bx - fx))
        arr(ax, fx, 8.18, closest, 6.8, PURPLE, lw=1.2)

    # ChatGPT -> MCP Bridge directly
    ax.annotate("", xy=(16.475, 6.8), xytext=(9.4, 10.35),
                arrowprops=dict(arrowstyle="-|>", color=ORANGE, lw=1.3,
                                connectionstyle="arc3,rad=-0.28",
                                linestyle=(0, (4, 3))))
    arr_label(ax, 13.5, 8.9, "MCP Protocol", ORANGE)

    # ---- ARROWS: backend -> AI layer ---------------------------------------
    for bx, ax_ in [(1.975, 2.3), (4.875, 5.5), (7.775, 8.9), (10.675, 12.3)]:
        arr(ax, bx, 5.15, ax_, 4.27, TEAL, lw=1.2)

    # AI -> LLM client
    arr(ax, 14.3, 2.62, 14.3, 4.27, PURPLE, lw=1.3)
    arr_label(ax, 15.1, 3.4, "LLM calls", PURPLE)

    # ---- ARROWS: backend/AI -> data ----------------------------------------
    arr(ax, 10.675, 5.15, 2.65, 2.32, GREEN, lw=1.1)
    arr(ax, 4.875,  5.15, 4.65, 2.32, TEAL,  lw=1.1)
    arr(ax, 1.975,  5.15, 2.65, 2.32, GREEN, lw=1.1)
    arr(ax, 13.575, 5.15, 13.5, 2.32, RED,   lw=1.1, dashed=True)
    arr_label(ax, 14.4, 3.7, "proxy call", RED)

    save(fig, "01_system_architecture.png")


# ===========================================================================
# 2. COMPONENT MAP (FastAPI internals)
# ===========================================================================
def d2_component_map():
    fig, ax = new_fig(17, 11, "MCP Hub  -  Component Interaction Map")

    nodes = {
        # label              : (color,   cx,   cy,  w,   h)
        "React Router\nSPA"         : (BLUE,    2.0,  9.5, 2.8, 1.2),
        "ChatGPT /\nLLM Client"     : (PURPLE, 13.5,  9.5, 2.8, 1.2),
        # FastAPI services
        "Chat Service"              : (TEAL,    1.2,  7.3, 2.5, 1.0),
        "Upload Service"            : (TEAL,    4.0,  7.3, 2.5, 1.0),
        "HITL Service"              : (TEAL,    6.8,  7.3, 2.5, 1.0),
        "Registry Service"          : (TEAL,    9.6,  7.3, 2.5, 1.0),
        "Exec Engine"               : (TEAL,   12.4,  7.3, 2.5, 1.0),
        "MCP Bridge"                : (ORANGE, 12.4,  9.5, 2.5, 1.0),
        # AI agents
        "Conversation\nAgent"       : (ORANGE,  1.2,  5.1, 2.5, 1.1),
        "Parsing Agent"             : (ORANGE,  4.0,  5.1, 2.5, 1.1),
        "Schema\nGenerator"         : (ORANGE,  6.8,  5.1, 2.5, 1.1),
        "Confidence\nScorer"        : (YELLOW,  9.6,  5.1, 2.5, 1.1),
        "Auth Manager"              : (RED,    12.4,  5.1, 2.5, 1.1),
        # LLM
        "LLM\n(Claude / GPT)"       : (PURPLE,  7.6,  2.9, 2.8, 1.0),
        # Data
        "SQLite DB"                 : (GREEN,   2.8,  0.9, 2.8, 1.0),
        "File Store"                : (TEAL,    6.3,  0.9, 2.8, 1.0),
        "Secrets Store"             : (RED,     9.8,  0.9, 2.8, 1.0),
        "External APIs"             : (RED,    13.2,  2.9, 2.8, 1.0),
    }

    def cx(n): return nodes[n][1] + nodes[n][3] / 2
    def cy(n): return nodes[n][2] + nodes[n][4] / 2

    for lbl, (col, x, y, w, h) in nodes.items():
        rect(ax, x, y, w, h, lbl, "", ec=col, fs=8.5)

    edges = [
        # (from, to, color, rad, label, dashed)
        ("React Router\nSPA",      "Chat Service",       BLUE,   0.0,  "chat",        False),
        ("React Router\nSPA",      "Upload Service",     BLUE,   0.0,  "upload",      False),
        ("React Router\nSPA",      "HITL Service",       BLUE,   0.0,  "validate",    False),
        ("React Router\nSPA",      "Registry Service",   BLUE,   0.0,  "browse",      False),
        ("ChatGPT /\nLLM Client",  "MCP Bridge",         PURPLE, 0.0,  "MCP call",    False),
        ("MCP Bridge",             "Registry Service",   ORANGE, 0.1,  "list tools",  False),
        ("MCP Bridge",             "Exec Engine",        ORANGE,-0.1,  "invoke",      False),
        ("Chat Service",           "Conversation\nAgent",TEAL,   0.0,  "",            False),
        ("Upload Service",         "Parsing Agent",      TEAL,   0.0,  "",            False),
        ("HITL Service",           "Schema\nGenerator",  TEAL,   0.0,  "",            False),
        ("HITL Service",           "Confidence\nScorer", TEAL,   0.1,  "",            False),
        ("Registry Service",       "SQLite DB",          GREEN,  0.0,  "read/write",  False),
        ("Conversation\nAgent",    "LLM\n(Claude / GPT)",ORANGE, 0.1,  "prompt",      False),
        ("Parsing Agent",          "LLM\n(Claude / GPT)",ORANGE, 0.0,  "parse doc",   False),
        ("Schema\nGenerator",      "LLM\n(Claude / GPT)",ORANGE,-0.1,  "generate",    False),
        ("Schema\nGenerator",      "SQLite DB",          GREEN,  0.1,  "save draft",  False),
        ("Confidence\nScorer",     "SQLite DB",          GREEN,  0.0,  "",            False),
        ("Exec Engine",            "Auth Manager",       RED,    0.1,  "get creds",   False),
        ("Exec Engine",            "External APIs",      RED,    0.0,  "HTTP proxy",  False),
        ("Auth Manager",           "Secrets Store",      RED,    0.0,  "fetch",       False),
        ("Parsing Agent",          "File Store",         TEAL,   0.1,  "read file",   False),
        ("Upload Service",         "File Store",         TEAL,   0.0,  "store",       False),
    ]

    for frm, to, col, rad, lbl, dash in edges:
        x1, y1 = cx(frm), cy(frm)
        x2, y2 = cx(to),  cy(to)
        arr(ax, x1, y1, x2, y2, col, rad=rad, dashed=dash)
        if lbl:
            mx, my = (x1 + x2) / 2 + 0.05, (y1 + y2) / 2 + 0.1
            arr_label(ax, mx, my, lbl, col)

    # legend
    legend = [(BLUE,"Frontend"),(TEAL,"FastAPI Service"),(ORANGE,"AI Agent"),
              (YELLOW,"Scoring"),(RED,"Security / External"),(GREEN,"Data"),
              (PURPLE,"LLM / Client")]
    for i, (col, lbl) in enumerate(legend):
        lx, ly = 0.25, 10.5 - i * 0.52
        ax.add_patch(FancyBboxPatch((lx, ly - 0.16), 0.35, 0.32,
                                   boxstyle="round,pad=0",
                                   fc=col + "55", ec=col, lw=1.2))
        ax.text(lx + 0.5, ly, lbl, fontsize=7.5, color=GRAY,
                fontfamily=FONT, va="center")

    save(fig, "02_component_map.png")


# ===========================================================================
# 3. SEQUENCE: Conversational API Creation
# ===========================================================================
def d3_seq_conversational():
    fig, ax = new_fig(17, 10, "Sequence  -  Conversational API Creation Flow")

    actors = [
        ("User",           BLUE,    1.3),
        ("React UI\n(Chat Builder)", PURPLE, 3.9),
        ("FastAPI\nChat Service",    TEAL,   6.5),
        ("Conversation\nAgent",      ORANGE, 9.1),
        ("LLM\n(Claude)",            PURPLE,11.7),
        ("HITL UI\n(Validator)",     YELLOW,14.3),
        ("SQLite DB",                GREEN, 16.4),
    ]

    H = 9.3
    for lbl, col, x in actors:
        rect(ax, x - 0.75, H, 1.5, 0.85, lbl, "", ec=col, fs=7.8, r=0.14)
        ax.plot([x, x], [H, 0.3], color=col + "55", lw=1, linestyle=(0,(5,4)))

    steps = [
        # y,   x1,    x2,    label,                                  col,     ret
        (8.7,  1.3,   3.9,  "Type intent (natural language)",        BLUE,   False),
        (8.2,  3.9,   6.5,  "POST /api/chat  {message}",             PURPLE, False),
        (7.7,  6.5,   9.1,  "start_session(intent)",                 TEAL,   False),
        (7.2,  9.1,  11.7,  "prompt: extract intent + ask Q1",       ORANGE, False),
        (6.7, 11.7,   9.1,  "Q1: What is the data source?",          PURPLE, True),
        (6.2,  9.1,   6.5,  "question: Q1",                          ORANGE, True),
        (5.7,  6.5,   3.9,  "{question: 'What is data source?'}",    TEAL,   True),
        (5.2,  3.9,   1.3,  "Display question to user",              PURPLE, True),
        (4.7,  1.3,   3.9,  "User answers Q1, Q2, Q3...",            BLUE,   False),
        (4.2,  3.9,   6.5,  "POST /api/chat  {answers}",             PURPLE, False),
        (3.7,  6.5,   9.1,  "generate_schema(answers)",              TEAL,   False),
        (3.2,  9.1,  11.7,  "prompt: build OpenAPI schema",          ORANGE, False),
        (2.7, 11.7,   9.1,  "draft schema JSON",                     PURPLE, True),
        (2.2,  9.1,   6.5,  "draft_api (schema + confidence)",       ORANGE, True),
        (1.7,  6.5,  14.3,  "redirect to HITL Validator",            TEAL,   False),
        (1.2, 14.3,   1.3,  "Show HITL Validation UI",               YELLOW, True),
    ]

    for (y, x1, x2, lbl, col, ret) in steps:
        dx = 1 if x2 > x1 else -1
        pad = 0.78
        ls = (0, (4, 3)) if ret else "solid"
        ax.annotate("", xy=(x2 + dx * pad, y), xytext=(x1 - dx * pad, y),
                    arrowprops=dict(arrowstyle="-|>", color=col, lw=1.4,
                                   mutation_scale=9, linestyle=ls))
        mx = (x1 + x2) / 2
        ax.text(mx, y + 0.14, lbl, ha="center", va="bottom",
                fontsize=7, color=col, fontfamily=FONT,
                bbox=dict(boxstyle="round,pad=0.1", fc=BG + "CC", ec="none"))

    # activation bars
    for x, y0, y1, col in [
        (3.9,  1.1, 8.75, PURPLE),
        (6.5,  1.6, 8.25, TEAL),
        (9.1,  2.6, 7.75, ORANGE),
        (11.7, 2.6, 7.25, PURPLE),
        (14.3, 1.1, 1.75, YELLOW),
    ]:
        ax.add_patch(FancyBboxPatch((x - 0.1, y0), 0.2, y1 - y0,
                                   boxstyle="square,pad=0",
                                   fc=col + "50", ec=col, lw=1.2))

    save(fig, "03_seq_conversational.png")


# ===========================================================================
# 4. SEQUENCE: Document Upload + HITL Validation
# ===========================================================================
def d4_seq_document_hitl():
    fig, ax = new_fig(17, 11,
        "Sequence  -  Document Upload + HITL Validation Flow")

    actors = [
        ("User",               BLUE,    1.3),
        ("React UI\n(Upload)", PURPLE,  3.8),
        ("FastAPI\nUpload Svc",TEAL,    6.3),
        ("Parsing\nAgent",     ORANGE,  8.8),
        ("LLM\n(Claude)",      PURPLE, 11.3),
        ("Confidence\nScorer", YELLOW, 13.6),
        ("HITL UI\n(Validator)",RED,   15.8),
        ("SQLite DB",          GREEN,  17.0),
    ]

    H = 10.3
    for lbl, col, x in actors:
        rect(ax, x - 0.72, H, 1.44, 0.85, lbl, "", ec=col, fs=7.5, r=0.14)
        ax.plot([x, x], [H, 0.3], color=col + "55", lw=1, linestyle=(0,(5,4)))

    steps = [
        (9.8,  1.3,  3.8, "Upload doc (PDF/Swagger/text)",      BLUE,   False),
        (9.3,  3.8,  6.3, "POST /api/upload  multipart",        PURPLE, False),
        (8.8,  6.3,  8.8, "store_file(doc)",                    TEAL,   False),
        (8.3,  6.3,  8.8, "parse(file_path)",                   TEAL,   False),
        (7.8,  8.8, 11.3, "prompt: extract endpoints/params",   ORANGE, False),
        (7.3, 11.3,  8.8, "raw_schema JSON",                    PURPLE, True),
        (6.8,  8.8,  6.3, "extracted_schema",                   ORANGE, True),
        (6.3,  6.3, 13.6, "score(schema)",                      TEAL,   False),
        (5.8, 13.6,  6.3, "confidence_map {field: pct}",        YELLOW, True),
        (5.3,  6.3, 15.8, "draft_api + confidence_map",         TEAL,   False),
        (4.8, 15.8,  3.8, "render Validation UI",               RED,    True),
        (4.3,  3.8,  1.3, "Show HITL: fields + confidence",     PURPLE, True),
        (3.7,  1.3,  3.8, "User edits uncertain fields",        BLUE,   False),
        (3.2,  3.8,  6.3, "PUT /api/validate  {edits}",         PURPLE, False),
        (2.7,  6.3, 15.8, "update_draft(edits)",                TEAL,   False),
        (2.2,  1.3,  3.8, "User clicks Confirm & Publish",      BLUE,   False),
        (1.7,  3.8,  6.3, "POST /api/validate/confirm",         PURPLE, False),
        (1.2,  6.3, 17.0, "INSERT api_definition",              GREEN,  False),
        (0.7, 17.0,  6.3, "api_id",                             GREEN,  True),
        (0.35, 6.3,  1.3, "API saved  (ready to attach)",       TEAL,   True),
    ]

    for (y, x1, x2, lbl, col, ret) in steps:
        dx = 1 if x2 > x1 else -1
        pad = 0.75
        ls = (0, (4, 3)) if ret else "solid"
        ax.annotate("", xy=(x2 + dx * pad, y), xytext=(x1 - dx * pad, y),
                    arrowprops=dict(arrowstyle="-|>", color=col, lw=1.3,
                                   mutation_scale=8, linestyle=ls))
        mx = (x1 + x2) / 2
        ax.text(mx, y + 0.13, lbl, ha="center", va="bottom",
                fontsize=6.8, color=col, fontfamily=FONT,
                bbox=dict(boxstyle="round,pad=0.1", fc=BG + "CC", ec="none"))

    # activation bars
    for x, y0, y1, col in [
        (3.8,  0.3, 9.85, PURPLE),
        (6.3,  0.65, 9.35, TEAL),
        (8.8,  6.65, 9.35, ORANGE),
        (11.3, 6.65, 7.85, PURPLE),
        (13.6, 5.65, 6.35, YELLOW),
        (15.8, 1.55, 5.35, RED),
        (17.0, 1.1,  1.25, GREEN),
    ]:
        ax.add_patch(FancyBboxPatch((x - 0.1, y0), 0.2, y1 - y0,
                                   boxstyle="square,pad=0",
                                   fc=col + "50", ec=col, lw=1.2))

    # HITL note box
    ax.add_patch(FancyBboxPatch((0.45, 3.55), 3.0, 1.55,
                                boxstyle="round,pad=0,rounding_size=0.18",
                                lw=1.2, ec=YELLOW + "90", fc=YELLOW + "15"))
    ax.text(1.95, 5.02, "HITL Validation",
            ha="center", va="center", fontsize=7.5,
            color=YELLOW, fontfamily=FONT, fontweight="bold")
    ax.text(1.95, 4.68, "User reviews confidence scores",
            ha="center", va="center", fontsize=7, color=GRAY, fontfamily=FONT)
    ax.text(1.95, 4.35, "Edits uncertain / missing fields",
            ha="center", va="center", fontsize=7, color=GRAY, fontfamily=FONT)
    ax.text(1.95, 4.02, "Confirms before API is saved",
            ha="center", va="center", fontsize=7, color=GRAY, fontfamily=FONT)

    save(fig, "04_seq_document_hitl.png")


# ===========================================================================
# 5. SEQUENCE: ChatGPT / LLM API Execution
# ===========================================================================
def d5_seq_execution():
    fig, ax = new_fig(16, 9.5,
        "Sequence  -  LLM-to-API Execution via MCP Bridge")

    actors = [
        ("ChatGPT /\nLLM Client", PURPLE,  1.4),
        ("MCP\nBridge",           ORANGE,  3.8),
        ("Registry\nService",     TEAL,    6.2),
        ("Exec\nEngine",          TEAL,    8.6),
        ("Auth\nManager",         RED,    11.0),
        ("SQLite DB",             GREEN,  13.2),
        ("External\nAPI",         BLUE,   15.4),
    ]

    H = 8.9
    for lbl, col, x in actors:
        rect(ax, x - 0.75, H, 1.5, 0.85, lbl, "", ec=col, fs=7.8, r=0.14)
        ax.plot([x, x], [H, 0.4], color=col + "55", lw=1, linestyle=(0,(5,4)))

    steps = [
        (8.4,  1.4,  3.8, "GET tools/list",                         PURPLE, False),
        (7.9,  3.8,  6.2, "list_apis(workspace_id)",                 ORANGE, False),
        (7.4,  6.2, 13.2, "SELECT published apis",                   TEAL,   False),
        (6.9, 13.2,  6.2, "api_definitions[]",                       GREEN,  True),
        (6.4,  6.2,  3.8, "tool_schemas[]",                          TEAL,   True),
        (5.9,  3.8,  1.4, "[tool definitions list]",                 ORANGE, True),
        (5.3,  1.4,  3.8, "tools/call  {tool, params}",              PURPLE, False),
        (4.8,  3.8,  8.6, "execute(tool_id, params)",                ORANGE, False),
        (4.3,  8.6,  6.2, "validate params vs input_schema",         TEAL,   False),
        (3.8,  6.2,  8.6, "schema OK",                               TEAL,   True),
        (3.3,  8.6, 11.0, "get_credentials(auth_config_id)",         RED,    False),
        (2.8, 11.0, 13.2, "SELECT secret_ref",                       RED,    False),
        (2.3, 13.2, 11.0, "secret_ref",                              GREEN,  True),
        (1.8, 11.0,  8.6, "injected headers / token",                RED,    True),
        (1.3,  8.6, 15.4, "HTTP request (with auth injected)",       TEAL,   False),
        (0.9, 15.4,  8.6, "HTTP 200 + JSON response",                BLUE,   True),
        (0.5,  8.6,  1.4, "tool result  ->  LLM",                    ORANGE, True),
    ]

    for (y, x1, x2, lbl, col, ret) in steps:
        dx = 1 if x2 > x1 else -1
        pad = 0.78
        ls = (0, (4, 3)) if ret else "solid"
        ax.annotate("", xy=(x2 + dx * pad, y), xytext=(x1 - dx * pad, y),
                    arrowprops=dict(arrowstyle="-|>", color=col, lw=1.4,
                                   mutation_scale=9, linestyle=ls))
        mx = (x1 + x2) / 2
        ax.text(mx, y + 0.14, lbl, ha="center", va="bottom",
                fontsize=7, color=col, fontfamily=FONT,
                bbox=dict(boxstyle="round,pad=0.1", fc=BG + "CC", ec="none"))

    for x, y0, y1, col in [
        (3.8,  0.4, 8.95, ORANGE),
        (6.2,  3.7, 7.95, TEAL),
        (8.6,  0.8, 4.85, TEAL),
        (11.0, 1.7, 3.85, RED),
        (13.2, 2.2, 7.45, GREEN),
        (15.4, 0.8, 1.35, BLUE),
    ]:
        ax.add_patch(FancyBboxPatch((x - 0.1, y0), 0.2, y1 - y0,
                                   boxstyle="square,pad=0",
                                   fc=col + "50", ec=col, lw=1.2))

    save(fig, "05_seq_execution.png")


# ===========================================================================
# 6. TECH STACK OVERVIEW
# ===========================================================================
def d6_tech_stack():
    fig, ax = new_fig(16, 9, "MCP Hub  -  Technology Stack")

    layers = [
        {
            "title": "Frontend",
            "color": BLUE,
            "y": 6.8,
            "items": [
                ("React 18", "UI library"),
                ("React Router v6", "SPA routing"),
                ("TailwindCSS", "Styling"),
                ("React Query", "Server state"),
                ("Zod", "Schema validation"),
            ],
        },
        {
            "title": "Backend  (FastAPI)",
            "color": TEAL,
            "y": 4.5,
            "items": [
                ("FastAPI", "REST + async"),
                ("Pydantic v2", "Data validation"),
                ("SQLAlchemy", "ORM"),
                ("Alembic", "DB migrations"),
                ("LangChain / LlamaIndex", "AI orchestration"),
            ],
        },
        {
            "title": "AI & Agents",
            "color": ORANGE,
            "y": 2.3,
            "items": [
                ("Anthropic SDK", "Claude API"),
                ("OpenAI SDK", "GPT fallback"),
                ("Custom agents", "Parse / Score / Chat"),
                ("Prompt caching", "Cost optimisation"),
                ("Structured output", "JSON schema enforce"),
            ],
        },
        {
            "title": "Data & Infra",
            "color": GREEN,
            "y": 0.25,
            "items": [
                ("SQLite", "Primary DB (v1)"),
                ("File system / S3", "Document storage"),
                ("Uvicorn", "ASGI server"),
                ("Docker", "Containerisation"),
                ("GitHub Actions", "CI / CD"),
            ],
        },
    ]

    for layer in layers:
        col = layer["color"]
        y   = layer["y"]
        # band
        band(ax, 0.4, y, 15.2, 2.0, col, alpha=0.08,
             label=layer["title"], lfs=9)
        # item boxes
        for i, (tech, desc) in enumerate(layer["items"]):
            rect(ax, 0.7 + i * 3.0, y + 0.35, 2.65, 1.35,
                 tech, desc, ec=col, fs=8.5, sfs=7.5)

    # "Why this stack" callout
    ax.add_patch(FancyBboxPatch((12.8, 4.6), 2.9, 3.95,
                                boxstyle="round,pad=0,rounding_size=0.22",
                                lw=1.2, ec=YELLOW + "80", fc=YELLOW + "12"))
    ax.text(14.25, 8.42, "Why this stack?",
            ha="center", fontsize=8.5, color=YELLOW,
            fontfamily=FONT, fontweight="bold")
    notes = [
        "FastAPI: async, auto OpenAPI",
        "React Router: lightweight SPA",
        "SQLite: zero-config for v1",
        "Pydantic: schema = source of truth",
        "LangChain: agent orchestration",
        "Anthropic SDK: best-in-class LLM",
    ]
    for i, n in enumerate(notes):
        ax.text(13.0, 8.05 - i * 0.55, f"  {n}",
                ha="left", fontsize=7.5, color=GRAY,
                fontfamily=FONT)

    save(fig, "06_tech_stack.png")


# ===========================================================================
# RUN ALL
# ===========================================================================
if __name__ == "__main__":
    print("Generating MCP Hub architecture diagrams...")
    d1_system_architecture()
    d2_component_map()
    d3_seq_conversational()
    d4_seq_document_hitl()
    d5_seq_execution()
    d6_tech_stack()
    print(f"\nDone. All images in: {OUT}")
