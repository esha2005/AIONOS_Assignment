import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI()

from backend.database.db import initialize_database  # noqa: E402

initialize_database()


# ============== RETRIEVAL MODELS (Prompt 2) ==============
class RetrievePolicyRequest(BaseModel):
    query: str = Field(..., description="Employee IT question to search against policies")
    top_k: Optional[int] = Field(default=None, ge=1, le=20, description="Override number of results to return")
    threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Override minimum similarity threshold")


class RetrievedPolicyResult(BaseModel):
    policy_id: str
    title: str
    content: str
    source: str
    similarity_score: float


class RetrievePolicyResponse(BaseModel):
    query: str
    found: bool
    results: List[RetrievedPolicyResult] = []
    error: Optional[str] = None


# ============== AGENT / TICKET MODELS (Prompt 3 + 4) ==============
DecisionType = str


class ChatHistoryItem(BaseModel):
    role: str
    content: str


class AgentChatRequest(BaseModel):
    message: str = Field(..., description="Employee IT support request")
    history: Optional[List[ChatHistoryItem]] = Field(default=None, description="Prior conversation history")
    employee_name: Optional[str] = Field(default=None, description="Employee name")
    employee_email: Optional[str] = Field(default=None, description="Employee email")



class TicketSummary(BaseModel):
    ticket_id: str
    status: str
    assigned_team: str
    priority: Optional[str] = None


class AgentChatResponse(BaseModel):
    decision: DecisionType = Field(description="RESOLVE | ASK_CLARIFICATION | ESCALATE")
    intent: str = Field(description="Short employee intent summary")
    response: Optional[str] = Field(default=None, description="Employee-facing answer (RESOLVE/ESCALATE)")
    clarification_question: Optional[str] = Field(
        default=None, description="Single question when decision=ASK_CLARIFICATION"
    )
    escalation_reason: Optional[str] = Field(
        default=None, description="Why escalation is required when decision=ESCALATE"
    )
    source_policy_ids: List[str] = Field(
        default_factory=list, description="Policy IDs actually used for decision"
    )
    ticket: Optional[TicketSummary] = Field(
        default=None, description="Short ticket summary when decision=ESCALATE, else null"
    )
    error: Optional[str] = Field(default=None)


class TicketRecordResponse(BaseModel):
    ticket_id: str
    employee_name: Optional[str] = None
    employee_email: Optional[str] = None
    issue: str
    category: Optional[str] = None
    priority: str
    status: str
    assigned_team: str
    escalation_reason: Optional[str] = None
    source_policy_ids: List[str] = []
    created_at: str


class AuditRecordResponse(BaseModel):
    audit_id: int
    ticket_id: Optional[str] = None
    action: str
    decision: str
    issue: Optional[str] = None
    source_policy_ids: List[str] = []
    reason: Optional[str] = None
    timestamp: str


# ============== BASIC ENDPOINTS ==============
@app.get("/")
def read_root():
    return {"message": "Veridian AI backend is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/policies")
def get_policies_endpoint():
    from backend.rag.knowledge_base import load_policies
    return load_policies()


@app.get("/employee-requests")
def get_employee_requests_endpoint():
    path = os.path.join(PROJECT_ROOT, "data", "employee_requests.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@app.get("/tickets-history")
def get_tickets_history_endpoint():
    path = os.path.join(PROJECT_ROOT, "data", "tickets.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []



# ============== RETRIEVAL ENDPOINT (Prompt 2) ==============
@app.post("/retrieve-policy", response_model=RetrievePolicyResponse)
def retrieve_policy(req: RetrievePolicyRequest):
    try:
        from backend.rag.retriever import PolicyRetriever
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load PolicyRetriever: {exc}",
        )

    query = (req.query or "").strip()
    if not query:
        return RetrievePolicyResponse(
            query="",
            found=False,
            results=[],
            error="query must be a non-empty string",
        )

    try:
        retriever = PolicyRetriever()
        result = retriever.retrieve(query=query, top_k=req.top_k, threshold=req.threshold)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"Policy file missing: {exc}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid data or query: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected retrieval error: {exc}")

    return RetrievePolicyResponse(
        query=query,
        found=bool(result.get("found", False)),
        results=result.get("results", []),
    )


# ============== AGENT ENDPOINT (Prompt 3 + 4) ==============
@app.post("/agent/chat", response_model=AgentChatResponse)
def agent_chat(req: AgentChatRequest):
    message = (req.message or "").strip()

    if not message:
        return AgentChatResponse(
            decision="ASK_CLARIFICATION",
            intent="Unclear request",
            clarification_question="What IT issue or service do you need help with?",
            source_policy_ids=[],
            ticket=None,
            error="message must be a non-empty string",
        )

    try:
        from backend.agents.graph import run_agent
        from backend.agents.nodes import APIKeyMissingError, LLMCallError
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load agent module: {exc}",
        )

    history_list = [h.dict() for h in req.history] if req.history else None
    try:
        final_state = run_agent(
            user_query=message,
            history=history_list,
            employee_name=req.employee_name,
            employee_email=req.employee_email,
        )

    except APIKeyMissingError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"LLM API key missing. Set GEMINI_API_KEY or LLM_API_KEY in .env: {exc}",
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"Policy file missing: {exc}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid data or query: {exc}")
    except LLMCallError as exc:
        raise HTTPException(status_code=502, detail=f"LLM provider error: {exc}")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected agent error: {exc}")

    decision = final_state.get("decision") or "ESCALATE"
    ticket_summary: Optional[TicketSummary] = None
    ticket_obj = final_state.get("ticket") or None
    if ticket_obj and decision == "ESCALATE":
        ticket_summary = TicketSummary(
            ticket_id=str(ticket_obj.get("ticket_id", "")),
            status=str(ticket_obj.get("status", "OPEN")),
            assigned_team=str(ticket_obj.get("assigned_team", "Human IT Review")),
            priority=ticket_obj.get("priority"),
        )

    return AgentChatResponse(
        decision=str(decision),
        intent=str(final_state.get("intent", "")),
        response=final_state.get("response"),
        clarification_question=final_state.get("clarification_question"),
        escalation_reason=final_state.get("escalation_reason"),
        source_policy_ids=list(final_state.get("source_policy_ids") or []),
        ticket=ticket_summary,
        error=final_state.get("error"),
    )


# ============== TICKET & AUDIT ENDPOINTS (Prompt 4) ==============
@app.get("/tickets", response_model=List[TicketRecordResponse])
def list_tickets_endpoint():
    try:
        from backend.database.models import list_tickets
        return list(list_tickets())
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list tickets: {exc}")


@app.get("/tickets/{ticket_id}", response_model=TicketRecordResponse)
def get_ticket_endpoint(ticket_id: str):
    try:
        from backend.database.models import get_ticket
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load ticket module: {exc}")

    try:
        ticket = get_ticket(ticket_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load ticket: {exc}")

    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket


@app.get("/audit-logs", response_model=List[AuditRecordResponse])
def list_audit_logs_endpoint():
    try:
        from backend.database.models import list_audit_logs
        return list(list_audit_logs())
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list audit logs: {exc}")
