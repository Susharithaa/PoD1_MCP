# MCP Hub — User Guide

A step-by-step walkthrough for building, validating, and connecting APIs to ChatGPT using MCP Hub.

---

## Table of Contents

1. [Overview](#overview)
2. [Method 1 — API Builder (Conversational)](#method-1--api-builder-conversational)
3. [Method 2 — Doc Upload](#method-2--doc-upload)
   - [Uploading employee_api.yaml — What Happens Step by Step](#uploading-employee_apiyaml--what-happens-step-by-step)
   - [Stage-by-Stage Agent Pipeline](#stage-by-stage-agent-pipeline)
   - [HITL Validation Screen — What to Verify](#hitl-validation-screen--what-to-verify)
   - [Adding Authentication](#adding-authentication)
   - [Building the MCP Tool](#building-the-mcp-tool)
4. [ChatGPT Tools — Using Your APIs in Chat](#chatgpt-tools--using-your-apis-in-chat)
   - [How Tool Routing Works](#how-tool-routing-works)
   - [Example Queries](#example-queries)
5. [VM Deployment — Connecting via MCP Token](#vm-deployment--connecting-via-mcp-token)
   - [Step 1: Create an MCP Token in the UI](#step-1-create-an-mcp-token-in-the-ui)
   - [Step 2: Verify the Token with curl](#step-2-verify-the-token-with-curl)
   - [Step 3: Set the Environment Variable](#step-3-set-the-environment-variable)
   - [Step 4: Add MCP Hub to Codex CLI](#step-4-add-mcp-hub-to-codex-cli)
   - [Step 5: Test in Codex CLI](#step-5-test-in-codex-cli)

---

## Overview

MCP Hub does three things:

| Step | What you do | What MCP Hub does |
|---|---|---|
| **Register** | Upload a YAML / upload a doc / chat to describe an API | AI parses it into a structured tool definition |
| **Validate** | Review the extracted schema in the HITL screen | You confirm endpoints, auth, and parameters are correct |
| **Connect** | Go to ChatGPT Tools and start chatting | ChatGPT automatically picks the right registered tool per query |

---

## Method 1 — API Builder (Conversational)

Use this when you want to describe an API in plain language and let the AI build the schema interactively.

### How to use it

1. Log in to MCP Hub and click **API Builder** in the left sidebar.
2. In the chat window, describe the API you want to register.

   **Example prompts:**
   ```
   I want to register a weather API that returns the current temperature for a city.
   ```
   ```
   Add an employee search API at http://localhost:8000/employees/search/{keyword}
   ```

3. The AI will ask follow-up questions:
   - What is the base URL?
   - What method does it use? (GET / POST)
   - What parameters does it accept?
   - Is authentication required? If yes, what type?
   - What does the response look like?

4. Answer each question. After all details are collected the AI generates a draft API schema.

5. The screen transitions to the **HITL Validation Screen** (see [HITL section below](#hitl-validation-screen--what-to-verify)).

6. After you confirm and save, the API appears in **My APIs**.

---

## Method 2 — Doc Upload

Use this when you already have an API spec file (YAML, JSON, PDF, plain text) and want to register it automatically.

### Uploading employee_api.yaml — What Happens Step by Step

**File:** `testing/employee_api.yaml`  
**Format:** OpenAPI 3.0.3  
**APIs covered:** Employees, Departments, Assets, Inventory

#### Step 1 — Open Doc Upload

Click **Doc Upload** in the left sidebar.

#### Step 2 — Upload the file

- Click **Choose File** (or drag and drop).
- Select `employee_api.yaml` from your machine.
- Click **Upload & Parse**.

> The screen immediately shows a progress tracker. Do not refresh the page — the pipeline runs in the background.

---

### Stage-by-Stage Agent Pipeline

Once uploaded, an 8-stage AI pipeline processes your file. You can watch each stage progress in real time.

| Stage | What the AI is doing | What you see |
|---|---|---|
| **1. Classifying** | Detects the file type (OpenAPI YAML) and API category | `CLASSIFYING…` spinner |
| **2. Parsing** | Extracts all endpoints, HTTP methods, paths, parameters, request bodies, and responses | `PARSING…` spinner |
| **3. Schema Generating** | Converts extracted info into a structured JSON schema per endpoint | `SCHEMA_GENERATING…` |
| **4. Confidence Scoring** | Rates how confident it is in each extracted field (0–100%) | `CONFIDENCE_SCORING…` |
| **5. Schema Validating** | Checks the schema is valid and complete | `VALIDATING…` |
| **6. API Testing** | Makes a live test call to verify the endpoint is reachable | `API_TESTING…` |
| **7. HITL Pending** | Pauses and waits for your review | `HITL_PENDING` — **action required** |
| **8. Saving** | After your approval, persists the API to the registry | `SAVING…` → `DONE` |

> Stage 7 (`HITL_PENDING`) does **not** auto-advance. You must review and approve before the API is saved.

---

### HITL Validation Screen — What to Verify

When the pipeline reaches `HITL_PENDING`, a validation screen opens. For `employee_api.yaml` you will see the following sections. Check each one carefully.

#### API Overview

| Field | Expected value | Action if wrong |
|---|---|---|
| **Name** | `Company Asset Management API` | Click to edit |
| **Description** | Summary of employees/assets/inventory | Edit to make it clearer for ChatGPT |
| **Base URL** | `http://localhost:8000` | Update to VM IP for hosted deployment, e.g. `http://10.126.104.12:8000` |
| **Version** | `1.0.0` | Leave as-is |

#### Endpoints

You should see **15 endpoints** extracted across 4 groups:

**System (1)**
- `GET /health`

**Employees (7)**
- `GET /employees`
- `GET /employees/{employee_id}`
- `GET /employees/department/{department}`
- `GET /employees/search/{keyword}`
- `POST /employees`
- `PUT /employees/{employee_id}`
- `DELETE /employees/{employee_id}`

**Departments (1)**
- `GET /departments/headcount`

**Assets (4)**
- `GET /assets/available`
- `POST /assets/assign`
- `POST /assets/unassign/{asset_id}`
- `GET /employees/{employee_id}/assets`

**Inventory (2)**
- `GET /inventory`
- `POST /inventory`

> If any endpoint is missing, click **Add Endpoint** and fill in the details manually.

#### Parameters

For each endpoint, verify the parameter details match the YAML:

| Endpoint | Parameters to verify |
|---|---|
| `GET /employees` | Optional query params: `department`, `location`, `designation` |
| `POST /employees` | Body: `name` (string, required), `department` (string, required), `email` (string, required) |
| `PUT /employees/{employee_id}` | Path: `employee_id` (integer); Body: `name`, `department`, `email` (all optional) |
| `POST /assets/assign` | Body: `asset_id` (integer, required), `employee_id` (integer, required) |
| `POST /inventory` | Body: `item_name` (string, required), `quantity` (integer, required), `supplier` (string, optional) |

#### Confidence Scores

Each field will show a colour-coded confidence badge:

| Colour | Meaning | What to do |
|---|---|---|
| 🟢 Green (80–100%) | Highly confident | Review quickly, likely correct |
| 🟡 Yellow (50–79%) | Uncertain | Read carefully and correct if needed |
| 🔴 Red (< 50%) | Low confidence | Almost certainly needs manual edit |

Common low-confidence areas for `employee_api.yaml`:
- **Response schemas** — the AI may have inferred the shape; compare against your actual API responses.
- **Error codes** — confirm `404` vs `400` where applicable.

---

### Adding Authentication

`employee_api.yaml` has **no authentication** (all endpoints are public). You can skip this section unless your deployment requires it.

If you ever need to add auth:

1. In the HITL screen, find the **Authentication** section.
2. Click **Add Auth**.
3. Choose the type:

| Auth type | When to use | Fields to fill |
|---|---|---|
| **API Key (header)** | Like the Bakuraku API | Header name (e.g. `x-api-key`), value |
| **API Key (query)** | Key passed in URL | Parameter name, value |
| **HTTP Basic** | Username + password | Username, password |
| **Bearer Token** | JWT / OAuth2 token | Token value |
| **OAuth2** | Full OAuth flow | Client ID, secret, token URL, scopes |

4. The credential is stored encrypted — it is never visible in logs or responses.
5. Click **Save Auth** to attach it to all endpoints, or apply per-endpoint if different endpoints use different credentials.

---

### Building the MCP Tool

After reviewing all endpoints and parameters:

1. Click **Confirm & Save** at the bottom of the HITL screen.
2. The pipeline resumes at stage 8 (`SAVING`) and saves the API to the registry.
3. You land on the **API Detail** page which shows:
   - The registered API name and description
   - All endpoints listed
   - A green **MCP Ready** badge
4. Note the **API ID** shown on this page — you may need it to attach the API in ChatGPT settings.

> **The API is now a registered MCP tool.** ChatGPT can discover and call it automatically.

---

## ChatGPT Tools — Using Your APIs in Chat

### How to Open the Chat

1. Click **ChatGPT Tools** (or **Chat Builder**) in the left sidebar.
2. The chat window opens with your registered tools listed in the right panel.
3. All tools marked **Active** are automatically available to the AI — no manual attachment needed.

### How Tool Routing Works

The AI reads the **name** and **description** of each registered tool and decides which one to call based on your question. This is why the description you set during HITL matters.

| Your query contains… | Tool that gets called | Why |
|---|---|---|
| Stock prices, candlestick data, market data, OHLCV, J-Quants | **JQuants Daily Bars API** | Description mentions stock/financial data |
| Employee names, departments, headcount, who works in… | **Company Asset Management API** (`/employees` endpoints) | Description mentions employee records |
| Assets assigned to someone, available laptops, who has device… | **Company Asset Management API** (`/assets` endpoints) | Description mentions asset assignment |
| Inventory levels, stock of items, supplier info | **Company Asset Management API** (`/inventory` endpoints) | Description mentions inventory |

### Example Queries

#### Stock / Market Data (→ JQuants tool)

```
What was Toyota's closing price last Friday?
Show me the candlestick data for Sony for the past week.
What are the top 5 gainers on the TSE today?
Give me OHLCV data for ticker 7203 for May 2025.
```

#### Employee Data (→ Employee API tool)

```
How many employees do we have in Engineering?
Who are all the employees in the Finance department?
Find employees with "Alice" in their name.
What is the headcount per department?
Add a new employee: Carol White, Finance, carol@company.com
```

#### Asset Management (→ Employee API tool)

```
Which assets are currently available to assign?
What assets does employee 1 have?
Assign asset 101 to employee 3.
Unassign asset 101 from its current employee.
```

#### Inventory (→ Employee API tool)

```
Show me the current inventory list.
How many USB-C hubs do we have in stock?
Add 25 Mechanical Keyboards from Logitech to inventory.
```

> **Important:** The AI decides which tool to call automatically. You do not need to prefix your question with the tool name — just ask naturally.

---

## VM Deployment — Connecting via MCP Token

Once MCP Hub is hosted on a VM (e.g. at IP `10.126.104.12`), external clients like the Codex CLI can connect to it using an MCP token.

### Step 1: Create an MCP Token in the UI

1. Log in to the hosted MCP Hub at `http://10.126.104.12:5173`.
2. Go to **Settings → API Tokens** (or **MCP Tokens**) in the sidebar.
3. Click **Generate New Token**.
4. Give it a name (e.g. `codex-cli`) and click **Create**.
5. **Copy the token immediately** — it is only shown once.

> For this guide, the token is:
> ```
> mcp_IiSKvVqCWb86j_8T-sQ7ABg15ni7ZkqKi2Xtzmcmu2k
> ```

---

### Step 2: Verify the Token with curl

Before connecting any client, confirm the MCP endpoint is reachable and your token works.

Open a terminal (Command Prompt, PowerShell, or bash) and run:

```bash
curl -X POST "http://10.126.104.12:8000/mcp" \
  -H "Authorization: Bearer mcp_IiSKvVqCWb86j_8T-sQ7ABg15ni7ZkqKi2Xtzmcmu2k" \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\",\"params\":{}}"
```

**On Windows Command Prompt:**
```cmd
curl -X POST "http://10.126.104.12:8000/mcp" -H "Authorization: Bearer mcp_IiSKvVqCWb86j_8T-sQ7ABg15ni7ZkqKi2Xtzmcmu2k" -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\",\"params\":{}}"
```

**Expected response — what you should see:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "listEmployees",
        "description": "Returns all employee records...",
        "inputSchema": { ... }
      },
      {
        "name": "getEmployee",
        "description": "Fetch a single employee record by their numeric employee ID...",
        "inputSchema": { ... }
      },
      ...
    ]
  }
}
```

If you see a list of tools in the response, the server is working and your token is valid.

**If you get an error:**

| Error | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Wrong or expired token | Regenerate the token in the UI |
| `Connection refused` | Backend not running | SSH to the VM and run `uvicorn main:app --host 0.0.0.0 --port 8000` |
| `404 Not Found` | Wrong URL | Check the VM IP and port |

---

### Step 3: Set the Environment Variable

The Codex CLI reads the token from an environment variable so you never hardcode it.

**Windows Command Prompt (current session only):**
```cmd
set MCP_HUB_TOKEN=mcp_IiSKvVqCWb86j_8T-sQ7ABg15ni7ZkqKi2Xtzmcmu2k
```

**Windows PowerShell (current session only):**
```powershell
$env:MCP_HUB_TOKEN = "mcp_IiSKvVqCWb86j_8T-sQ7ABg15ni7ZkqKi2Xtzmcmu2k"
```

**Persist across sessions (Windows):**
```cmd
setx MCP_HUB_TOKEN "mcp_IiSKvVqCWb86j_8T-sQ7ABg15ni7ZkqKi2Xtzmcmu2k"
```
> After `setx`, open a new terminal for the variable to take effect.

**Linux / macOS:**
```bash
export MCP_HUB_TOKEN=mcp_IiSKvVqCWb86j_8T-sQ7ABg15ni7ZkqKi2Xtzmcmu2k
# Add to ~/.bashrc or ~/.zshrc to persist
```

Verify the variable is set:
```cmd
echo %MCP_HUB_TOKEN%          # Windows CMD
echo $env:MCP_HUB_TOKEN       # PowerShell
echo $MCP_HUB_TOKEN            # bash/zsh
```

---

### Step 4: Add MCP Hub to Codex CLI

Register MCP Hub as a global MCP server in Codex so it is available in every session:

```bash
codex mcp add mcp-hub --url "http://10.126.104.12:8000/mcp" --bearer-token-env-var "MCP_HUB_TOKEN"
```

**What this command does:**

| Flag | Value | Meaning |
|---|---|---|
| `mcp-hub` | (server name) | Friendly name used inside Codex to identify this server |
| `--url` | `http://10.126.104.12:8000/mcp` | MCP endpoint on the VM |
| `--bearer-token-env-var` | `MCP_HUB_TOKEN` | Codex reads the token from this env var at runtime |

**Expected output:**
```
✓ MCP server "mcp-hub" added globally.
  URL:   http://10.126.104.12:8000/mcp
  Auth:  Bearer $MCP_HUB_TOKEN
```

To confirm it was registered:
```bash
codex mcp list
```

You should see `mcp-hub` in the list.

---

### Step 5: Test in Codex CLI

Open Codex CLI and ask questions that should trigger your registered tools.

```bash
codex
```

Once the Codex prompt is open, try:

#### Test 1 — Check tools are connected
```
What tools do you have access to?
```
Codex should list all the tools from MCP Hub — `listEmployees`, `getEmployee`, `listAvailableAssets`, `getDepartmentHeadcount`, JQuants tools, etc.

#### Test 2 — Employee query (→ Employee API)
```
How many employees are in the Engineering department?
```
Expected: Codex calls `getDepartmentHeadcount` or `listEmployees?department=Engineering` and returns the count.

#### Test 3 — Asset query (→ Employee API)
```
What assets are currently available?
```
Expected: Codex calls `listAvailableAssets` and lists available assets.

#### Test 4 — Stock query (→ JQuants tool)
```
What was Toyota's stock closing price last Friday?
```
Expected: Codex calls the JQuants daily bars tool with Toyota's ticker and returns price data.

#### Test 5 — Mixed query
```
Who is in the Finance department and what assets do they have?
```
Expected: Codex calls `getEmployeesByDepartment` first, then `getEmployeeAssets` for each employee, and combines the answer.

---

## Quick Reference

### Key URLs (VM deployment)

| Resource | URL |
|---|---|
| MCP Hub UI | `http://10.126.104.12:5173` |
| Backend API | `http://10.126.104.12:8000` |
| MCP endpoint | `http://10.126.104.12:8000/mcp` |
| Swagger docs | `http://10.126.104.12:8000/docs` |

### Key Commands

```bash
# Verify MCP token and list tools
curl -X POST "http://10.126.104.12:8000/mcp" \
  -H "Authorization: Bearer mcp_IiSKvVqCWb86j_8T-sQ7ABg15ni7ZkqKi2Xtzmcmu2k" \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\",\"params\":{}}"

# Set token env var (Windows CMD)
set MCP_HUB_TOKEN=mcp_IiSKvVqCWb86j_8T-sQ7ABg15ni7ZkqKi2Xtzmcmu2k

# Register MCP Hub in Codex
codex mcp add mcp-hub --url "http://10.126.104.12:8000/mcp" --bearer-token-env-var "MCP_HUB_TOKEN"

# List registered MCP servers in Codex
codex mcp list

# Open Codex CLI
codex
```

### Token

```
mcp_IiSKvVqCWb86j_8T-sQ7ABg15ni7ZkqKi2Xtzmcmu2k
```
