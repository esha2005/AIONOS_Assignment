import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict

from backend.database.db import get_connection


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


class TicketRecord(TypedDict, total=False):
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


class AuditRecord(TypedDict, total=False):
    audit_id: int
    ticket_id: Optional[str]
    action: str
    decision: str
    issue: Optional[str]
    source_policy_ids: List[str]
    reason: Optional[str]
    timestamp: str


def _row_to_ticket(row: sqlite3.Row) -> TicketRecord:
    raw_ids: str = row["source_policy_ids"] or "[]"
    try:
        ids: List[str] = json.loads(raw_ids)
        if not isinstance(ids, list):
            ids = []
    except (TypeError, ValueError):
        ids = []
    return TicketRecord(
        ticket_id=row["ticket_id"],
        employee_name=row["employee_name"],
        employee_email=row["employee_email"],
        issue=row["issue"],
        category=row["category"],
        priority=row["priority"],
        status=row["status"],
        assigned_team=row["assigned_team"],
        escalation_reason=row["escalation_reason"],
        source_policy_ids=ids,
        created_at=row["created_at"],
    )


def _row_to_audit(row: sqlite3.Row) -> AuditRecord:
    raw_ids: str = row["source_policy_ids"] or "[]"
    try:
        ids: List[str] = json.loads(raw_ids)
        if not isinstance(ids, list):
            ids = []
    except (TypeError, ValueError):
        ids = []
    return AuditRecord(
        audit_id=row["audit_id"],
        ticket_id=row["ticket_id"],
        action=row["action"],
        decision=row["decision"],
        issue=row["issue"],
        source_policy_ids=ids,
        reason=row["reason"],
        timestamp=row["timestamp"],
    )


def _next_ticket_id(db_path: Optional[str] = None) -> str:
    with get_connection(db_path=db_path) as conn:
        cursor = conn.execute(
            "SELECT ticket_id FROM tickets ORDER BY ticket_id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row is None:
            return "IT-1001"
        current: str = row["ticket_id"] or "IT-1000"
        if current.startswith("IT-") and current[3:].isdigit():
            num = int(current[3:]) + 1
        else:
            num = 1001
        return f"IT-{num:04d}"


def _detect_assigned_team(
    source_policy_ids: List[str],
    escalation_reason: Optional[str],
    intent: Optional[str],
) -> str:
    haystack_parts = []
    haystack_parts.extend([str(x) for x in source_policy_ids if x])
    if escalation_reason:
        haystack_parts.append(escalation_reason)
    if intent:
        haystack_parts.append(intent)
    haystack = " ".join(haystack_parts).lower()
    if "kb-09" in haystack:
        return "Security"
    security_tokens = ("phish", "security", "malware", "suspicious email", "incident", "report to security")
    for token in security_tokens:
        if token in haystack:
            return "Security"
    return "Human IT Review"


def _detect_priority(assigned_team: str) -> str:
    if assigned_team == "Security":
        return "HIGH"
    return "MEDIUM"


def create_ticket(
    issue: str,
    escalation_reason: Optional[str] = None,
    source_policy_ids: Optional[List[str]] = None,
    category: Optional[str] = None,
    employee_name: Optional[str] = None,
    employee_email: Optional[str] = None,
    intent: Optional[str] = None,
    status: str = "OPEN",
    db_path: Optional[str] = None,
) -> TicketRecord:
    if issue is None:
        issue = ""
    issue = str(issue).strip()
    if not issue:
        raise ValueError("create_ticket requires a non-empty issue value")

    ids_list: List[str] = list(source_policy_ids or [])
    assigned_team = _detect_assigned_team(ids_list, escalation_reason, intent)
    priority = _detect_priority(assigned_team)

    with get_connection(db_path=db_path) as conn:
        ticket_id = _next_ticket_id(db_path=db_path)
        created_at = _utcnow_iso()
        conn.execute(
            """
            INSERT INTO tickets (
                ticket_id, employee_name, employee_email, issue, category,
                priority, status, assigned_team, escalation_reason,
                source_policy_ids, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticket_id,
                employee_name,
                employee_email,
                issue,
                category,
                priority,
                status,
                assigned_team,
                escalation_reason,
                json.dumps(ids_list),
                created_at,
            ),
        )
        cursor = conn.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
        )
        row = cursor.fetchone()
        return _row_to_ticket(row)


def get_ticket(ticket_id: str, db_path: Optional[str] = None) -> Optional[TicketRecord]:
    with get_connection(db_path=db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_ticket(row)


def list_tickets(db_path: Optional[str] = None) -> List[TicketRecord]:
    with get_connection(db_path=db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM tickets ORDER BY created_at DESC, ticket_id DESC"
        )
        return [_row_to_ticket(r) for r in cursor.fetchall()]


def create_audit_log(
    action: str,
    decision: str,
    ticket_id: Optional[str] = None,
    issue: Optional[str] = None,
    source_policy_ids: Optional[List[str]] = None,
    reason: Optional[str] = None,
    db_path: Optional[str] = None,
) -> AuditRecord:
    if not action:
        raise ValueError("create_audit_log requires a non-empty action")
    if not decision:
        raise ValueError("create_audit_log requires a non-empty decision")

    ids_list: List[str] = list(source_policy_ids or [])
    timestamp = _utcnow_iso()

    with get_connection(db_path=db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO audit_logs (
                ticket_id, action, decision, issue,
                source_policy_ids, reason, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticket_id,
                action,
                decision,
                issue,
                json.dumps(ids_list),
                reason,
                timestamp,
            ),
        )
        audit_id = cursor.lastrowid
        row_cursor = conn.execute(
            "SELECT * FROM audit_logs WHERE audit_id = ?", (audit_id,)
        )
        row = row_cursor.fetchone()
        return _row_to_audit(row)


def list_audit_logs(db_path: Optional[str] = None) -> List[AuditRecord]:
    with get_connection(db_path=db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM audit_logs ORDER BY timestamp DESC, audit_id DESC"
        )
        return [_row_to_audit(r) for r in cursor.fetchall()]
