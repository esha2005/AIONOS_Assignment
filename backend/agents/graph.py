from typing import Any, Callable, Dict, List, Optional


from langgraph.graph import END, START, StateGraph

from backend.agents.state import AgentState
from backend.agents.nodes import (
    understand_request_node,
    retrieve_policy_node,
    reason_node,
    decision_node,
    create_ticket_node,
    create_audit_node,
    LLMProvider,
)

_GRAPH_NODE_UNDERSTAND = "understand_request_node"
_GRAPH_NODE_RETRIEVE = "retrieve_policy_node"
_GRAPH_NODE_REASON = "reason_node"
_GRAPH_NODE_DECISION = "validate_decision_node"
_GRAPH_NODE_CREATE_TICKET = "create_ticket_node"
_GRAPH_NODE_AUDIT = "create_audit_node"


def _route_after_decision(state: AgentState) -> str:
    if state.get("decision") == "ESCALATE":
        return _GRAPH_NODE_CREATE_TICKET
    return _GRAPH_NODE_AUDIT


def build_agent_graph(llm_provider: Optional[LLMProvider] = None):
    workflow = StateGraph(AgentState)

    workflow.add_node(_GRAPH_NODE_UNDERSTAND, understand_request_node)
    workflow.add_node(_GRAPH_NODE_RETRIEVE, retrieve_policy_node)

    def _reason(state: AgentState) -> AgentState:
        return reason_node(state, llm_provider=llm_provider)

    workflow.add_node(_GRAPH_NODE_REASON, _reason)
    workflow.add_node(_GRAPH_NODE_DECISION, decision_node)
    workflow.add_node(_GRAPH_NODE_CREATE_TICKET, create_ticket_node)
    workflow.add_node(_GRAPH_NODE_AUDIT, create_audit_node)

    workflow.add_edge(START, _GRAPH_NODE_UNDERSTAND)
    workflow.add_edge(_GRAPH_NODE_UNDERSTAND, _GRAPH_NODE_RETRIEVE)
    workflow.add_edge(_GRAPH_NODE_RETRIEVE, _GRAPH_NODE_REASON)
    workflow.add_edge(_GRAPH_NODE_REASON, _GRAPH_NODE_DECISION)

    workflow.add_conditional_edges(
        _GRAPH_NODE_DECISION,
        _route_after_decision,
        {
            _GRAPH_NODE_CREATE_TICKET: _GRAPH_NODE_CREATE_TICKET,
            _GRAPH_NODE_AUDIT: _GRAPH_NODE_AUDIT,
        },
    )

    workflow.add_edge(_GRAPH_NODE_CREATE_TICKET, _GRAPH_NODE_AUDIT)
    workflow.add_edge(_GRAPH_NODE_AUDIT, END)

    compiled = workflow.compile()
    return compiled


def run_agent(
    user_query: str,
    history: Optional[List[Dict[str, str]]] = None,
    employee_name: Optional[str] = None,
    employee_email: Optional[str] = None,
    llm_provider: Optional[LLMProvider] = None,
) -> Dict[str, Any]:
    initial_state: AgentState = {
        "user_query": (user_query or "").strip(),
        "history": history or [],
        "employee_name": employee_name,
        "employee_email": employee_email,
        "intent": "",
        "retrieved_policies": [],
        "source_policy_ids": [],
    }
    graph = build_agent_graph(llm_provider=llm_provider)
    result = graph.invoke(initial_state)
    return result

