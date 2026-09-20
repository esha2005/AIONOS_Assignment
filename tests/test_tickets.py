import os
import tempfile
from typing import Any, Dict, List

from backend.agents.nodes import AgentDecision
from backend.agents.graph import run_agent


def _make_mock_llm(decision_obj: AgentDecision):
    def mock_provider(system_prompt: str, user_prompt: str) -> AgentDecision:
        return decision_obj
    return mock_provider


class TempDbFixture:
    def __init__(self):
        self._tmpdir = tempfile.mkdtemp(prefix="veridian_db_")
        self.db_path = os.path.join(self._tmpdir, "veridian_tests.db")
        self._orig = os.environ.get("VERIDIAN_DB_PATH")

    def __enter__(self):
        os.environ["VERIDIAN_DB_PATH"] = self.db_path
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._orig is None:
            os.environ.pop("VERIDIAN_DB_PATH", None)
        else:
            os.environ["VERIDIAN_DB_PATH"] = self._orig
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except OSError:
            pass
        try:
            os.rmdir(self._tmpdir)
        except OSError:
            pass


class TestDirectTicketBehavior:
    def test_resolve_does_not_create_ticket(self):
        with TempDbFixture():
            from backend.database.models import list_tickets, list_audit_logs

            mock = AgentDecision(
                decision="RESOLVE",
                intent="VPN credentials expired",
                response="KB-02: VPN credentials expire every 90 days. Renew online.",
                source_policy_ids=["KB-02"],
            )
            result = run_agent(
                "My VPN stopped working. My credentials expired.",
                llm_provider=_make_mock_llm(mock),
            )
            assert result.get("decision") == "RESOLVE"
            assert result.get("ticket") in (None, {}, [])
            tickets: List[Dict[str, Any]] = list_tickets()
            assert len(tickets) == 0
            audits = list_audit_logs()
            assert len(audits) == 1
            assert audits[0]["decision"] == "RESOLVE"
            assert audits[0]["action"] == "AGENT_RESOLVED"

    def test_ask_clarification_does_not_create_ticket(self):
        with TempDbFixture():
            from backend.database.models import list_tickets, list_audit_logs

            mock = AgentDecision(
                decision="ASK_CLARIFICATION",
                intent="Unclear request",
                clarification_question="What isn't working — VPN, email, laptop?",
                source_policy_ids=[],
            )
            result = run_agent(
                "Hey, it's not working.",
                llm_provider=_make_mock_llm(mock),
            )
            assert result.get("decision") == "ASK_CLARIFICATION"
            assert result.get("ticket") in (None, {}, [])
            assert len(list_tickets()) == 0
            audits = list_audit_logs()
            assert len(audits) == 1
            assert audits[0]["action"] == "AGENT_ASKED_CLARIFICATION"

    def test_escalate_creates_exactly_one_ticket_and_audit(self):
        with TempDbFixture():
            from backend.database.models import list_tickets, list_audit_logs

            mock = AgentDecision(
                decision="ESCALATE",
                intent="Suspected phishing email",
                response=(
                    "Suspected phishing reported to Security. Do not click links in the message."
                ),
                escalation_reason=(
                    "KB-09 requires phishing incidents to be handled by Security."
                ),
                source_policy_ids=["KB-09"],
            )
            result = run_agent(
                "I received a phishing email asking for my login.",
                llm_provider=_make_mock_llm(mock),
            )
            assert result.get("decision") == "ESCALATE"
            ticket = result.get("ticket") or {}
            assert ticket.get("ticket_id", "").startswith("IT-")
            assert ticket.get("status") == "OPEN"
            assert ticket.get("issue")
            assert ticket.get("escalation_reason")
            assert "KB-09" in ticket.get("source_policy_ids", [])

            tickets = list_tickets()
            assert len(tickets) == 1
            assert tickets[0]["ticket_id"] == ticket["ticket_id"]

            audits = list_audit_logs()
            assert len(audits) == 1
            assert audits[0]["decision"] == "ESCALATE"
            assert audits[0]["action"] == "AGENT_ESCALATED"
            assert audits[0]["ticket_id"] == ticket["ticket_id"]
            assert "KB-09" in audits[0]["source_policy_ids"]

    def test_escalate_phishing_routes_to_security_team(self):
        with TempDbFixture():
            from backend.database.models import list_tickets

            mock = AgentDecision(
                decision="ESCALATE",
                intent="Suspected phishing",
                response="Escalating to Security team per KB-09.",
                escalation_reason="Phishing / security incident per KB-09.",
                source_policy_ids=["KB-09"],
            )
            result = run_agent(
                "I received a phishing email asking for my login.",
                llm_provider=_make_mock_llm(mock),
            )
            ticket = result.get("ticket") or {}
            assert ticket.get("assigned_team") == "Security"
            assert ticket.get("priority") == "HIGH"
            tickets = list_tickets()
            assert tickets[0]["assigned_team"] == "Security"
            assert tickets[0]["priority"] == "HIGH"

    def test_no_ticket_duplicate_on_double_invoke(self):
        with TempDbFixture():
            from backend.database.models import list_tickets, create_ticket

            # Make two separate escalated agent invocations to ensure two
            # separate tickets are created (i.e. one run = one ticket).
            mock_a = AgentDecision(
                decision="ESCALATE",
                intent="Unknown",
                response="Escalated to IT.",
                escalation_reason="Policy-supported escalation.",
                source_policy_ids=["KB-01"],
            )
            run_agent("Some escalated issue A.", llm_provider=_make_mock_llm(mock_a))
            run_agent("Some escalated issue B.", llm_provider=_make_mock_llm(mock_a))
            tickets = list_tickets()
            assert len(tickets) == 2
            assert tickets[0]["ticket_id"] != tickets[1]["ticket_id"]


class TestTicketEndpoints:
    def test_get_tickets_returns_created(self):
        with TempDbFixture():
            from fastapi.testclient import TestClient
            from backend.main import app

            mock = AgentDecision(
                decision="ESCALATE",
                intent="Suspicious email",
                response="Escalating now.",
                escalation_reason="KB-09 requires security handling.",
                source_policy_ids=["KB-09"],
            )

            import backend.agents.nodes as nodes_mod

            orig = nodes_mod.default_llm_provider
            try:
                nodes_mod.default_llm_provider = _make_mock_llm(mock)
                with TestClient(app) as client:
                    resp = client.post(
                        "/agent/chat",
                        json={"message": "Phishing email received."},
                    )
            finally:
                nodes_mod.default_llm_provider = orig

            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["decision"] == "ESCALATE"
            ticket_id = data["ticket"]["ticket_id"]
            assert ticket_id.startswith("IT-")
            assert data["ticket"]["assigned_team"] == "Security"

            from fastapi.testclient import TestClient as TC2
            from backend.main import app as a2

            with TC2(a2) as client:
                list_resp = client.get("/tickets")
                assert list_resp.status_code == 200
                tickets_list = list_resp.json()
                assert len(tickets_list) == 1
                assert tickets_list[0]["ticket_id"] == ticket_id
                assert tickets_list[0]["assigned_team"] == "Security"

                single_resp = client.get(f"/tickets/{ticket_id}")
                assert single_resp.status_code == 200
                assert single_resp.json()["ticket_id"] == ticket_id

                miss_resp = client.get("/tickets/IT-9999")
                assert miss_resp.status_code == 404

    def test_get_audit_logs_returns_created(self):
        with TempDbFixture():
            from fastapi.testclient import TestClient
            from backend.main import app

            mock = AgentDecision(
                decision="ESCALATE",
                intent="Suspicious email",
                response="Escalating to Security.",
                escalation_reason="KB-09 incident.",
                source_policy_ids=["KB-09"],
            )

            import backend.agents.nodes as nodes_mod

            orig = nodes_mod.default_llm_provider
            try:
                nodes_mod.default_llm_provider = _make_mock_llm(mock)
                with TestClient(app) as client:
                    client.post(
                        "/agent/chat",
                        json={"message": "I got a suspicious email asking for login."},
                    )
            finally:
                nodes_mod.default_llm_provider = orig

            from fastapi.testclient import TestClient as TC2
            from backend.main import app as a2

            with TC2(a2) as client:
                audits_resp = client.get("/audit-logs")
                assert audits_resp.status_code == 200
                audits = audits_resp.json()
                assert len(audits) == 1
                assert audits[0]["decision"] == "ESCALATE"
                assert audits[0]["action"] == "AGENT_ESCALATED"
                assert "KB-09" in audits[0]["source_policy_ids"]

    def test_agent_chat_resolve_no_ticket(self):
        with TempDbFixture():
            from fastapi.testclient import TestClient
            from backend.main import app

            mock = AgentDecision(
                decision="RESOLVE",
                intent="VPN credentials expired",
                response="KB-02: VPN credentials expire every 90 days. Renew at the portal.",
                source_policy_ids=["KB-02"],
            )

            import backend.agents.nodes as nodes_mod

            orig = nodes_mod.default_llm_provider
            try:
                nodes_mod.default_llm_provider = _make_mock_llm(mock)
                with TestClient(app) as client:
                    resp = client.post(
                        "/agent/chat",
                        json={"message": "My VPN stopped working. My credentials expired."},
                    )
            finally:
                nodes_mod.default_llm_provider = orig

            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["decision"] == "RESOLVE"
            assert data["ticket"] is None
            assert "KB-02" in data["source_policy_ids"]
