# Veridian AI — Internal IT Resolution Agent

## Project Name
Veridian AI

## Purpose
An internal IT-support AI agent for Veridian Corp. The agent will eventually understand employee IT issues, retrieve relevant company policies, ask follow-up questions, resolve simple requests, escalate risky or unauthorized requests, create structured tickets, show source/policy references, and maintain an audit trail.

## Current Development Stage
**Prompt 5 — Complete: Streamlit UI, End-to-End Agent Flow**

All five initial implementation stages are complete:
1. **Stage 1** — Knowledge base, policies, retrieval API
2. **Stage 2** — LLM integration, structured AgentDecision output
3. **Stage 3** — LangGraph agent workflow with RETRIEVE/REASON/DECIDE
4. **Stage 4** — SQLite persistence: ticket creation + audit trail
5. **Stage 5** — Streamlit chat UI with Dashboard, Tickets, Audit Trail pages

All core functionality is implemented:
- FastAPI backend with `/retrieve-policy`, `/agent/chat`, `/tickets`, `/audit-logs` endpoints
- LangGraph agent workflow (understand → retrieve → reason → decide → [ticket] → audit)
- TF-IDF RAG policy retrieval with KB-01 through KB-11 policies
- SQLite `veridian.db` with tickets table (IT-1001+ sequential) + audit_logs table
- Three-page Streamlit UI: Ask IT Agent / Tickets / Audit Trail
- Security routing: KB-09/phishing → assigned_team=Security, priority=HIGH

## Tech Stack
- Python 3.11+
- FastAPI (backend API)
- Streamlit (frontend UI)
- scikit-learn (TF-IDF + cosine similarity for retrieval)
- LangGraph (agent decision workflow graph)
- Google Gemini SDK (LLM structured reasoning; swapable)
- **SQLite (now active — local persistent database for tickets + audit)**
- LLM integration: implemented (Gemini via env var)

## Folder Structure
```
veridian-ai/
│
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI entry point (/retrieve-policy, /agent/chat, /tickets, /audit-logs)
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── knowledge_base.py  # Loads & validates data/policies.json
│   │   └── retriever.py       # TF-IDF PolicyRetriever class
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── state.py           # AgentState TypedDict
│   │   ├── system_prompt.py   # Grounding rules for the LLM
│   │   ├── nodes.py            # understand_request / retrieve_policy / reason / decision / create_ticket / create_audit
│   │   └── graph.py           # LangGraph compile + run_agent()
│   └── database/
│       ├── __init__.py
│       ├── db.py              # SQLite connection, init + table creation
│       └── models.py           # create_ticket(), list_tickets(), create_audit_log(), list_audit_logs()
│
├── frontend/
│   └── app.py               # Streamlit UI entry point
│
├── data/
│   ├── policies.json        # KB-01 through KB-10 + Asset Management
│   ├── employee_requests.json  # REQ-01 through REQ-15
│   └── tickets.json         # TK-1042 through TK-1051  (reference data, NOT written to)
│
├── tests/
│   ├── test_setup.py        # Foundation smoke tests
│   ├── test_retriever.py    # RAG retrieval tests
│   ├── test_agent.py        # Agent workflow tests (LLM mocked)
│   └── test_tickets.py     # Ticket & audit tests (SQLite + mocked LLM)
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## How to Create a Virtual Environment
```bash
# From the project root
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (Command Prompt)
.venv\Scripts\activate.bat

# macOS / Linux
source .venv/bin/activate
```

## How to Install Requirements
```bash
pip install -r requirements.txt
```

## How to Start FastAPI (Backend)
```bash
# From project root
python -m uvicorn backend.main:app --reload
```

Once running, visit:
- Root: http://localhost:8000/
- Health check: http://localhost:8000/health
- Auto docs: http://localhost:8000/docs

## Frontend UI Overview

The Streamlit frontend (`frontend/app.py`) exposes five interactive views via the polished sidebar:

1. **💬 Ask IT Agent (Interactive Multi-Turn Chat)**
   - Full conversational chat interface powered by `st.chat_message` and `st.chat_input`
   - Real-time multi-turn conversation support: when the agent asks a clarification question (`ASK_CLARIFICATION`), the user can directly type their reply in the chat input
   - Maintains full conversation context sent to backend `/agent/chat`
   - Displays: decision badges (`RESOLVE` green, `ASK_CLARIFICATION` yellow, `ESCALATE` red), intent summaries, referenced policy tags, escalation reasons, and embedded Ticket Cards (`IT-XXXX`)

2. **🎫 Tickets Queue**
   - Live SQLite Escalated Tickets + Historical Baseline Tickets (TK-1042 through TK-1051)
   - Status, priority, and assigned team badges with detail drawer expanders

3. **📜 Audit Trail**
   - Real-time immutable audit records linking every turn, decision, and ticket

4. **📚 Knowledge Base**
   - Interactive viewer for all 11 Veridian Corp IT Policies (KB-01 to KB-11) with live search

5. **📋 Employee Requests Data Pack**
   - Complete Data Pack list (REQ-01 to REQ-15) with 1-click "Test with Agent" buttons


## How to Start Streamlit (Frontend)
Open a second terminal with the virtual environment active:
```bash
streamlit run frontend/app.py
```

Streamlit will open in your default browser (usually http://localhost:8501).

## How to Run Tests
```bash
# Foundation tests (7 tests)
pytest tests/test_setup.py -v

# RAG retrieval tests (6 tests)
pytest tests/test_retriever.py -v

# Agent workflow tests (7 tests; LLM is mocked)
pytest tests/test_agent.py -v

# Ticket & audit tests (8 tests; SQLite temp DB + mocked LLM)
pytest tests/test_tickets.py -v

# All tests (7 + 6 + 7 + 8 = 28 tests)
pytest tests/ -v
```

## Knowledge Base Retrieval

**What RAG means:** RAG stands for *Retrieval-Augmented Generation*. It is a pattern where we first *retrieve* the most relevant source documents (in this project, Veridian Corp IT policies) and then later pass those documents to an LLM so the LLM can ground its answer in real, supplied source material — instead of inventing answers.

**Why this project needs retrieval:** The final IT agent must cite the actual company policy it used to answer an employee. Retrieval finds the right policy quickly from the policy library, which then becomes context for the next stage (LLM + LangGraph agent).

**Where policies live:** All policies are stored as structured JSON in `data/policies.json`. This JSON file is the single source of truth; policies are never hardcoded in Python.

**How retrieval currently works:** We use **TF-IDF vectorization + cosine similarity** via scikit-learn:

1. Each policy is combined (`policy_id` + `title` + `content`) into one searchable text.
2. `TfidfVectorizer` builds a vocabulary and numeric vectors for every policy document.
3. When a query arrives, it is transformed with the same TF-IDF vocabulary.
4. Cosine similarity scores the query vector against each policy vector.
5. Scores are sorted; any score below the threshold is discarded, and the top `k` are returned.

This is lightweight, fast, and easy to explain — a good fit for the small assignment dataset. We can swap it for a dedicated vector database later if needed.

**What a retrieved result includes:** Each result always carries its provenance:
- `policy_id` (e.g. KB-02)
- `title` (e.g. VPN Access)
- `content` (full text from policies.json)
- `source` (e.g. "Assignment 2 Data Pack")
- `similarity_score` (float 0–1)

If nothing is above the configured threshold the endpoint returns `found: false` and an empty results list, so unrelated queries do not produce a misleading "match."

**How the LLM/agent fits in next:** In a later step we will wire an LLM + LangGraph agent that calls this retrieval component, reads the returned policy, reasons about it, asks follow-up questions, and finally generates an answer or escalates — always citing the exact policy it used.

### Retrieval Endpoint: POST /retrieve-policy

```bash
# Example curl request
curl -X POST http://localhost:8000/retrieve-policy \
  -H "Content-Type: application/json" \
  -d '{"query":"My VPN stopped working"}'
```

Example response shape:
```json
{
  "query": "My VPN stopped working",
  "found": true,
  "results": [
    {
      "policy_id": "KB-02",
      "title": "VPN Access",
      "content": "... full policy text from policies.json ...",
      "source": "Assignment 2 Data Pack",
      "similarity_score": 0.72
    }
  ],
  "error": null
}
```

## Agent Architecture

### High-Level Flow
```
Employee Query
      ↓
Understand Request (intent summary)
      ↓
Policy Retrieval (TF-IDF → top-k relevant policies)
      ↓
LLM Reasoning (system prompt + query + retrieved policies)
      ↓
Decision Validation (structured AgentDecision schema)
      ├─ RESOLVE ─────────────┐
      │                       │
      ├─ ASK_CLARIFICATION ───┤
      │                       ▼
      └─ ESCALATE ──▶ Create Ticket ──▶ Create Audit Record ──▶ END
```

### Why LangGraph is used
**LangGraph is used to represent the agent's decision workflow as explicit states and transitions.** This keeps the reasoning pipeline transparent, beginner-understandable, and easy to extend (ticket-creation and audit-trail nodes were added as *new edges* rather than rewriting a big function).

### Why an LLM is used
**The LLM interprets the employee's natural-language request and reasons over the retrieved company policy.** Retrieval only finds *which* policy matches; the LLM then reads the actual policy text, checks whether enough info is present, decides between RESOLVE / ASK_CLARIFICATION / ESCALATE, and produces the employee-facing text. It returns a strict JSON schema (`AgentDecision`) so we never rely on free-form prose to determine action.

### Why retrieval happens before reasoning
**Retrieval grounds the agent's response in the company's supplied policies and reduces unsupported answers.** The LLM only sees the exact policy text from `data/policies.json` (never general world knowledge for company rules). If no policy is retrieved, the LLM is explicitly told "[No relevant company policy was retrieved]" and must either ask for clarification or escalate rather than guess.

### Structured Output Contract (`AgentDecision`)
The LLM is forced to respond with exactly this shape (validated via Pydantic):
- `decision` — `RESOLVE | ASK_CLARIFICATION | ESCALATE`
- `intent` — short employee intent summary
- `response` — employee-facing answer (required for RESOLVE/ESCALATE)
- `clarification_question` — one concise question (ASK_CLARIFICATION only)
- `escalation_reason` — why human handling needed (ESCALATE only)
- `source_policy_ids` — only the KB IDs the agent actually used

Invalid or missing decisions are normalized into an ESCALATE by the decision node so the backend never misbehaves.

### Agent API: POST /agent/chat

```bash
# Example curl request
curl -X POST http://localhost:8000/agent/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"My VPN stopped working. It says my credentials expired.\"}"
```

Example response shape (Case 1 — VPN / RESOLVE):
```json
{
  "decision": "RESOLVE",
  "intent": "VPN credentials expired",
  "response": "Per KB-02 (VPN Access), VPN credentials expire every 90 days and must be renewed. Visit the password/VPN renewal portal to regenerate credentials. This system did not modify any credentials.",
  "clarification_question": null,
  "escalation_reason": null,
  "source_policy_ids": ["KB-02"],
  "ticket": null,
  "error": null
}
```

Example response shape (Case 3 — Phishing / ESCALATE):
```json
{
  "decision": "ESCALATE",
  "intent": "Suspected phishing email",
  "response": "Suspected phishing must be reported immediately. Your request has been escalated to the Security team per KB-09.",
  "clarification_question": null,
  "escalation_reason": "KB-09 requires suspected phishing to be handled by the Security/SOC team directly.",
  "source_policy_ids": ["KB-09"],
  "ticket": {
    "ticket_id": "IT-1001",
    "status": "OPEN",
    "assigned_team": "Security"
  },
  "error": null
}
```

## Escalation, Ticket Creation & Audit Trail

### When tickets are created
A SQLite ticket is created **only** when the agent's decision is **ESCALATE** after the decision validation node. RESOLVE and ASK_CLARIFICATION never produce tickets. A single execution produces at most one ticket (duplicate-creation guard in the `create_ticket_node` checks `if state.get('ticket')` and skips).

### What a ticket contains (`tickets` table)
- `ticket_id` — auto-generated, format `IT-1001`, `IT-1002`, … (sequential, unique)
- `issue` / `category` — derived from the employee's request + agent intent
- `priority` — **HIGH** if assigned to Security (KB-09 phishing/security incidents per the supplied policy), otherwise **MEDIUM**
- `status` — `OPEN` on creation
- `assigned_team` — **Security** for KB-09 / phishing / security incidents (policy-supported); otherwise **Human IT Review** (safe fallback; no invented departments)
- `escalation_reason` — the structured escalation_reason from the agent decision
- `source_policy_ids` — JSON list of the policy IDs the agent actually used
- `employee_name` / `employee_email` — nullable (not collected from bare chat)
- `created_at` — ISO-8601 UTC timestamp

The existing `data/tickets.json` file (TK-1042..TK-1051 reference data from the assignment) is **never overwritten** — new tickets live only in SQLite.

### What the audit trail records (`audit_logs` table)
One row for every agent execution (regardless of decision):
- `audit_id` — auto-incremented PK
- `ticket_id` — linked FK if a ticket was created, else NULL
- `action` — one of `AGENT_RESOLVED | AGENT_ASKED_CLARIFICATION | AGENT_ESCALATED | AGENT_UNKNOWN`
- `decision` — RESOLVE / ASK_CLARIFICATION / ESCALATE
- `issue` — the intent or user query
- `source_policy_ids` — JSON list of KB IDs cited
- `reason` — escalation_reason / clarification_question / response
- `timestamp` — ISO-8601 UTC

### How escalation works
The workflow runs:
```
START → understand → retrieve policy → LLM reason → validate decision
    ├─ decision==ESCALATE → create_ticket_node → create_audit_node → END
    └─ decision==RESOLVE or ASK_CLARIFICATION → create_audit_node → END
```

Team routing and priority are kept minimal and **policy-grounded** — Security routing only triggers for the KB-09/suspicious-email/security/incident/phishing tokens explicitly supported by the assignment data. All other escalations go to `Human IT Review` (no invented teams or routing).

### Ticket & Audit Endpoints
- **GET /tickets** — list all created tickets
- **GET /tickets/{ticket_id}** — one ticket by ID (404 if missing)
- **GET /audit-logs** — list all audit records

```bash
# Example: list tickets
curl http://localhost:8000/tickets

# Example: list audit logs
curl http://localhost:8000/audit-logs
```

The database file path can be overridden by setting the `VERIDIAN_DB_PATH` environment variable; the default is `<project>/veridian.db`.

## Demo Examples

Run the backend + frontend, then try these three scenarios in the Ask IT Agent page to verify all decision paths:

### A. Normal Request — VPN Expired (RESOLVE)
> *"My VPN credentials have expired."*
- **Expected Decision:** RESOLVE (green badge)
- **Expected Policy:** KB-02 (VPN Access)
- **Expected Outcome:** Agent provides renewal instructions referencing KB-02; **no ticket** created; audit record written with `AGENT_RESOLVED`

### B. Clarification Request — Laptop Issue (ASK_CLARIFICATION)
> *"My laptop is not working."*
- **Expected Decision:** ASK_CLARIFICATION (yellow badge)
- **Expected Policy:** Agent asks a specific follow-up (e.g. "What is the make/model? What exactly happens?")
- **Expected Outcome:** Agent cannot resolve due to insufficient info; **no ticket** created; audit record written with `AGENT_ASKED_CLARIFICATION`

### C. Security Request — Phishing Email (ESCALATE)
> *"I received a phishing email asking for my password."*
- **Expected Decision:** ESCALATE (red badge)
- **Expected Policy:** KB-09 (Phishing & Suspicious Emails / Security Incidents)
- **Expected Outcome:** Ticket created (format IT-XXXX sequential, starting IT-1001); assigned_team = **Security**, priority = **HIGH**, status = OPEN; linked audit record written with `AGENT_ESCALATED`

### D. Guest Wi-Fi (RESOLVE — another quick test)
> *"A visitor needs Wi-Fi access for a meeting tomorrow."*
- **Expected Decision:** RESOLVE
- **Expected Policy:** KB-07 (Guest Wi-Fi Access)
- **Expected Outcome:** Agent instructs the employee to submit a Guest Wi-Fi Request via the IT Portal 24h in advance; no ticket created.

## Limitations & Assumptions
- **Local DB Scope:** SQLite `veridian.db` is stored locally and created automatically on startup.
- **RAG Vocabulary:** TF-IDF policy retrieval works over `data/policies.json` text; domain-specific acronyms or synonyms not in the policy text rely on the LLM's understanding.
- **Single Turn Chat:** Each request is submitted independently to `/agent/chat`. Multi-turn conversational session history is maintained in audit logs rather than active chat memory.
- **Authentication:** Employee identity is treated as an optional parameter (`employee_name`/`employee_email`) for internal network support.

## Future Improvements
- **Vector Database:** Upgrade TF-IDF to dense embeddings (e.g. ChromaDB or FAISS with OpenAI / Gemini embeddings) for hybrid semantic retrieval.
- **Multi-turn Chat History:** Persist conversational state across messages using LangGraph checkpoints for full multi-turn clarification loops.
- **Integrations:** Connect ticket creation directly to Jira, ServiceNow, or Zendesk APIs.
- **Role-Based Access Control (RBAC):** Add authentication headers (OAuth2/JWT) for employee and IT admin roles.

