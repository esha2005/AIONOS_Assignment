# Veridian AI — Internal IT Resolution Agent

## Project Name
Veridian AI

## Purpose
An internal IT-support AI agent for Veridian Corp. The agent will eventually understand employee IT issues, retrieve relevant company policies, ask follow-up questions, resolve simple requests, escalate risky or unauthorized requests, create structured tickets, show source/policy references, and maintain an audit trail.

## Current Development Stage
**Step 4 — Escalation, Ticket Creation & Audit Trail (SQLite)**

This stage adds:
- **SQLite database** with `tickets` and `audit_logs` tables
- **Ticket creation** only when the agent decides **ESCALATE**
- **Audit log** entry for every agent decision
- Three new API endpoints: `GET /tickets`, `GET /tickets/{id}`, `GET /audit-logs`

The existing agent workflow is preserved. RESOLVE / ASK_CLARIFICATION / ESCALATE, with a new conditional branch: if ESCALATE → create structured ticket → create audit record → end; otherwise → audit record only → end.

Not yet implemented: final Streamlit chat UI, audit dashboard pages.

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
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Once running, visit:
- Root: http://localhost:8000/
- Health check: http://localhost:8000/health
- Auto docs: http://localhost:8000/docs

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

## Next Steps (Not Yet Implemented)
- Full Streamlit chat UI
- Audit dashboard pages
