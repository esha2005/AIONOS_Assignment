from typing import Any, Dict, List, Optional, TypedDict, Literal


DecisionType = Literal["RESOLVE", "ASK_CLARIFICATION", "ESCALATE"]


class RetrievedPolicyRef(TypedDict, total=False):
    policy_id: str
    title: str
    content: str
    source: str
    similarity_score: float


class TicketRef(TypedDict, total=False):
    ticket_id: str
    employee_name: Optional[str]
    employee_email: Optional[str]
    issue: str
    category: Optional[str]
    priority: str
    status: str
    assigned_team: str
    escalation_reason: Optional[str]
    source_policy_ids: List[str]
    created_at: str


class AuditRef(TypedDict, total=False):
    audit_id: int
    ticket_id: Optional[str]
    action: str
    decision: str
    issue: Optional[str]
    source_policy_ids: List[str]
    reason: Optional[str]
    timestamp: str


class AgentState(TypedDict, total=False):
    user_query: str
    history: List[Dict[str, str]]
    employee_name: Optional[str]
    employee_email: Optional[str]
    intent: str
    retrieved_policies: List[RetrievedPolicyRef]
    decision: DecisionType
    response: Optional[str]
    clarification_question: Optional[str]
    escalation_reason: Optional[str]
    source_policy_ids: List[str]
    ticket: TicketRef
    audit_record: AuditRef
    error: Optional[str]
