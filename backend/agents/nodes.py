import json
import os
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError

from backend.agents.state import AgentState, DecisionType
from backend.agents.system_prompt import SYSTEM_PROMPT

VALID_DECISIONS: set = {"RESOLVE", "ASK_CLARIFICATION", "ESCALATE"}


class AgentDecision(BaseModel):
    decision: DecisionType = Field(description="RESOLVE | ASK_CLARIFICATION | ESCALATE")
    intent: str = Field(default="", description="Short employee intent summary")
    response: Optional[str] = Field(default=None, description="Employee-facing answer (RESOLVE/ESCALATE)")
    clarification_question: Optional[str] = Field(
        default=None, description="Single concise question (ASK_CLARIFICATION only)"
    )
    escalation_reason: Optional[str] = Field(
        default=None, description="Why escalation is needed (ESCALATE only)"
    )
    source_policy_ids: List[str] = Field(
        default_factory=list, description="Only policy IDs actually used"
    )


class LLMCallError(Exception):
    pass


class APIKeyMissingError(Exception):
    pass


def _require_gemini_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("LLM_API_KEY")
    if not key or not str(key).strip():
        raise APIKeyMissingError(
            "No LLM API key configured. Set GEMINI_API_KEY (or LLM_API_KEY) in your .env file."
        )
    return str(key).strip()


def _call_gemini_structured(system_prompt: str, user_prompt: str) -> AgentDecision:
    try:
        import google.generativeai as genai  # type: ignore
    except ImportError as exc:
        raise LLMCallError(
            "google-generativeai package is not installed. Install requirements.txt."
        ) from exc

    api_key = _require_gemini_key()
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("gemini-1.5-flash")
    full_prompt = f"{system_prompt}\n\n---\nTASK INPUT:\n{user_prompt}\n\n---\nReturn ONLY the valid JSON object matching the schema above, no extra commentary, no markdown, no code fences."

    try:
        response = model.generate_content(
            full_prompt,
            generation_config={"response_mime_type": "application/json"},
        )
    except Exception as exc:  # pragma: no cover - network failure
        raise LLMCallError(f"Gemini API call failed: {exc}") from exc

    raw_text = (response.text or "").strip()
    if not raw_text:
        raise LLMCallError("Gemini returned empty content.")

    return _parse_structured_output(raw_text)


def _parse_structured_output(raw_text: str) -> AgentDecision:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMCallError(f"LLM returned invalid JSON: {exc} | raw: {raw_text}") from exc

    if not isinstance(data, dict):
        raise LLMCallError(f"LLM JSON response is not an object: {data}")

    decision_val = data.get("decision")
    if decision_val not in VALID_DECISIONS:
        raise LLMCallError(f"Invalid decision from LLM: {decision_val!r}")

    try:
        parsed = AgentDecision(**data)
    except ValidationError as exc:
        raise LLMCallError(f"LLM response failed schema validation: {exc}") from exc

    return parsed


LLMProvider = Callable[[str, str], AgentDecision]


def default_llm_provider(system_prompt: str, user_prompt: str) -> AgentDecision:
    return _call_gemini_structured(system_prompt, user_prompt)


def understand_request_node(state: AgentState) -> AgentState:
    query = (state.get("user_query") or "").strip()
    intent_chars = [c for c in query if c.isalnum() or c in " '-"]
    intent = "".join(intent_chars).strip()
    if len(intent) > 120:
        intent = intent[:117] + "..."
    state["intent"] = intent or "Unclear request"
    return state


def retrieve_policy_node(state: AgentState) -> AgentState:
    from backend.rag.retriever import PolicyRetriever

    query = (state.get("user_query") or "").strip()
    if not query:
        state["retrieved_policies"] = []
        return state

    try:
        retriever = PolicyRetriever()
        res = retriever.retrieve(query=query, top_k=3)
    except Exception as exc:
        state["retrieved_policies"] = []
        state["error"] = f"Retrieval failed: {exc}"
        return state

    state["retrieved_policies"] = res.get("results", []) if res.get("found") else []
    return state


def _build_user_prompt(query: str, policies: List[Dict[str, Any]]) -> str:
    if not policies:
        policies_section = "[No relevant company policy was retrieved for this request.]"
    else:
        parts = []
        for idx, p in enumerate(policies, 1):
            parts.append(
                f"Policy #{idx}:\n"
                f"  policy_id: {p.get('policy_id','')}\n"
                f"  title: {p.get('title','')}\n"
                f"  source: {p.get('source','')}\n"
                f"  content:\n{p.get('content','')}\n"
            )
        policies_section = "\n".join(parts)
    return (
        f"Employee request:\n{query}\n\n"
        f"Retrieved company policies (use only these):\n{policies_section}"
    )


def reason_node(
    state: AgentState,
    llm_provider: Optional[LLMProvider] = None,
) -> AgentState:
    provider = llm_provider or default_llm_provider
    query = (state.get("user_query") or "").strip()

    if not query:
        state["error"] = "Empty user_query"
        state["decision"] = "ASK_CLARIFICATION"
        state["clarification_question"] = (
            "What IT service or issue do you need help with?"
        )
        state["source_policy_ids"] = []
        return state

    user_prompt = _build_user_prompt(query, state.get("retrieved_policies") or [])

    try:
        structured: AgentDecision = provider(SYSTEM_PROMPT, user_prompt)
    except APIKeyMissingError as exc:
        state["error"] = str(exc)
        raise
    except LLMCallError as exc:
        state["error"] = f"LLM failure: {exc}"
        state["decision"] = "ESCALATE"
        state["response"] = (
            "Our IT AI agent encountered an issue processing your request. "
            "The request has been escalated to IT support."
        )
        state["escalation_reason"] = f"LLM call error: {exc}"
        state["source_policy_ids"] = [
            p.get("policy_id", "")
            for p in (state.get("retrieved_policies") or [])
            if p.get("policy_id")
        ]
        return state

    state["intent"] = structured.intent or state.get("intent", "")
    state["decision"] = structured.decision
    state["response"] = structured.response
    state["clarification_question"] = structured.clarification_question
    state["escalation_reason"] = structured.escalation_reason
    state["source_policy_ids"] = list(structured.source_policy_ids or [])
    return state


def decision_node(state: AgentState) -> AgentState:
    decision = state.get("decision")
    if decision not in VALID_DECISIONS:
        state["decision"] = "ESCALATE"
        state["response"] = (
            "We couldn't determine a clear action for your request, "
            "so it has been escalated to IT support for review."
        )
        state["escalation_reason"] = (
            f"Invalid or missing agent decision: {decision!r}"
        )
        state["clarification_question"] = None

    if state["decision"] == "RESOLVE":
        if not state.get("response"):
            state["decision"] = "ESCALATE"
            state["escalation_reason"] = "LLM returned RESOLVE without a response."
            state["response"] = (
                "Your request was not able to be resolved automatically "
                "and has been escalated to IT support."
            )
        state["clarification_question"] = None
        state["escalation_reason"] = state["escalation_reason"] if False else None

    if state["decision"] == "ASK_CLARIFICATION":
        if not state.get("clarification_question"):
            state["clarification_question"] = (
                "Could you provide more details about the IT issue you're experiencing?"
            )
        state["response"] = None
        state["escalation_reason"] = None

    if state["decision"] == "ESCALATE":
        if not state.get("escalation_reason"):
            state["escalation_reason"] = "Escalation required per policy or risk assessment."
        if not state.get("response"):
            state["response"] = (
                "Your request has been escalated to IT support for human review."
            )
        state["clarification_question"] = None

    return state


def create_ticket_node(state: AgentState) -> AgentState:
    if state.get("decision") != "ESCALATE":
        return state
    if state.get("ticket") and state["ticket"].get("ticket_id"):
        return state

    from backend.database.models import create_ticket, TicketRecord

    issue = (state.get("response") or "").strip() or (state.get("intent") or "").strip()
    if not issue:
        issue = (state.get("user_query") or "").strip() or "Escalated IT issue"

    category = (state.get("intent") or "").strip() or None

    try:
        ticket: TicketRecord = create_ticket(
            issue=issue,
            escalation_reason=state.get("escalation_reason"),
            source_policy_ids=list(state.get("source_policy_ids") or []),
            category=category,
            intent=state.get("intent") or "",
            status="OPEN",
        )
    except Exception as exc:  # pragma: no cover - unlikely
        state["error"] = f"Ticket creation failed: {exc}"
        return state

    state["ticket"] = dict(ticket)
    return state


def create_audit_node(state: AgentState) -> AgentState:
    from backend.database.models import create_audit_log, AuditRecord

    action = {
        "RESOLVE": "AGENT_RESOLVED",
        "ASK_CLARIFICATION": "AGENT_ASKED_CLARIFICATION",
        "ESCALATE": "AGENT_ESCALATED",
    }.get(state.get("decision") or "", "AGENT_UNKNOWN")

    reason = (
        state.get("escalation_reason")
        or state.get("clarification_question")
        or state.get("response")
        or ""
    )

    ticket_id = None
    if state.get("ticket"):
        ticket_id = state["ticket"].get("ticket_id")

    issue = (state.get("intent") or "") or (state.get("user_query") or "")

    try:
        record: AuditRecord = create_audit_log(
            action=action,
            decision=str(state.get("decision") or "UNKNOWN"),
            ticket_id=ticket_id,
            issue=issue or None,
            source_policy_ids=list(state.get("source_policy_ids") or []),
            reason=reason or None,
        )
    except Exception as exc:  # pragma: no cover - unlikely
        state["error"] = f"Audit logging failed: {exc}"
        return state

    state["audit_record"] = dict(record)
    return state
