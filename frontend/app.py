import streamlit as st
import requests
from typing import Any, Dict, List, Optional

BACKEND_URL = "http://127.0.0.1:8000"

PAGE_ASK = "Ask IT Agent"
PAGE_TICKETS = "Tickets"
PAGE_AUDIT = "Audit Trail"

DECISION_STYLES = {
    "RESOLVE": {"icon": "✅", "color": "#16a34a", "label": "Resolved"},
    "ASK_CLARIFICATION": {"icon": "❓", "color": "#d97706", "label": "Clarification Needed"},
    "ESCALATE": {"icon": "🚨", "color": "#dc2626", "label": "Escalated to Human IT"},
}

PRIORITY_STYLES = {
    "HIGH": {"bg": "#fee2e2", "fg": "#991b1b"},
    "MEDIUM": {"bg": "#fef3c7", "fg": "#92400e"},
    "LOW": {"bg": "#dcfce7", "fg": "#166534"},
}

STATUS_STYLES = {
    "OPEN": {"bg": "#dbeafe", "fg": "#1e40af"},
    "IN PROGRESS": {"bg": "#fef3c7", "fg": "#92400e"},
    "PENDING": {"bg": "#e5e7eb", "fg": "#374151"},
    "RESOLVED": {"bg": "#dcfce7", "fg": "#166534"},
    "CLOSED": {"bg": "#e5e7eb", "fg": "#374151"},
    "ESCALATED": {"bg": "#fee2e2", "fg": "#991b1b"},
}

TEAM_ICONS = {
    "Security": "🛡️",
    "Human IT Review": "💼",
    "Network": "🌐",
    "Infrastructure": "🖥️",
    "Help Desk": "🎧",
}


def page_config() -> None:
    st.set_page_config(
        page_title="Veridian Corp - AI IT Support Agent",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def _safe_post(url: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
    except (requests.ConnectionError, requests.Timeout):
        return {"_error": "conn"}
    try:
        data = resp.json()
    except ValueError:
        data = {"_raw": resp.text}
    data["_status"] = resp.status_code
    return data


def _safe_get(url: str, timeout: int = 15) -> Any:
    try:
        resp = requests.get(url, timeout=timeout)
    except (requests.ConnectionError, requests.Timeout):
        return {"_error": "conn"}
    try:
        data = resp.json()
    except ValueError:
        data = {"_raw": resp.text}
    if isinstance(data, dict):
        data["_status"] = resp.status_code
    return data


def backend_down_warning() -> None:
    st.error(
        "Backend is not running. Start it with:  \n"
        "`python -m uvicorn backend.main:app --reload`",
        icon="⚠️",
    )


def http_error_warning(status: int, detail: Optional[str] = None) -> None:
    msg = f"Backend returned HTTP {status}"
    if detail:
        msg += f": {detail}"
    st.warning(msg, icon="🌐")


def render_header() -> None:
    c1, c2 = st.columns([0.9, 0.1])
    with c1:
        st.markdown(
            """
            <div style="padding: 10px 0;">
                <div style="display: flex; align-items: center; gap: 14px;">
                    <div style="
                        width: 46px; height: 46px;
                        background: linear-gradient(135deg, #1e3a8a, #0ea5e9);
                        border-radius: 12px;
                        display: flex; align-items: center; justify-content: center;
                        font-size: 22px;
                    ">🛡️</div>
                    <div>
                        <div style="font-size: 22px; font-weight: 700; color: #0f172a;">
                            Veridian Corp
                        </div>
                        <div style="font-size: 15px; color: #334155; font-weight: 600;">
                            AI IT Support Agent
                        </div>
                    </div>
                </div>
                <div style="margin-top: 8px; color: #475569; font-size: 14px;">
                    Internal IT support and resolution assistant
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.divider()


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            """
            <div style="margin-bottom: 6px; font-size: 15px; font-weight: 700; color: #0f172a;">
                🛡️ Veridian IT
            </div>
            <div style="color: #64748b; font-size: 12px; margin-bottom: 18px;">
                Internal Support Dashboard
            </div>
            """,
            unsafe_allow_html=True,
        )
        page = st.radio(
            "Navigation",
            [PAGE_ASK, PAGE_TICKETS, PAGE_AUDIT],
            label_visibility="collapsed",
        )
        st.markdown("---")
        st.caption(f"Backend: `{BACKEND_URL}`")
        try:
            requests.get(f"{BACKEND_URL}/health", timeout=2)
            st.success("Backend online", icon="🟢")
        except Exception:
            st.warning("Backend offline", icon="🔴")
    return page


def _decision_badge(decision: str) -> str:
    style = DECISION_STYLES.get(decision, {"icon": "ℹ️", "color": "#64748b", "label": decision})
    return (
        f"<span style='display:inline-flex; align-items:center; gap:6px; "
        f"padding:6px 12px; border-radius:9999px; background:{style['color']}15; "
        f"color:{style['color']}; font-weight:600; font-size:13px; "
        f"border:1px solid {style['color']}33;'>"
        f"{style['icon']} {style['label']} ({decision})</span>"
    )


def _priority_badge(priority: str) -> str:
    p = (priority or "").upper()
    s = PRIORITY_STYLES.get(p, PRIORITY_STYLES["MEDIUM"])
    return (
        f"<span style='padding:3px 10px; border-radius:6px; "
        f"background:{s['bg']}; color:{s['fg']}; font-weight:600; font-size:12px;'>"
        f"{p or 'MEDIUM'}</span>"
    )


def _status_badge(status: str) -> str:
    s_val = (status or "").upper()
    s = STATUS_STYLES.get(s_val, STATUS_STYLES["OPEN"])
    return (
        f"<span style='padding:3px 10px; border-radius:6px; "
        f"background:{s['bg']}; color:{s['fg']}; font-weight:600; font-size:12px;'>"
        f"{status or 'OPEN'}</span>"
    )


def render_ask_page() -> None:
    st.subheader("💬 Ask the IT Agent", anchor=False)
    st.caption("Describe your IT issue below and the agent will look up company policies.")

    if "last_chat" not in st.session_state:
        st.session_state["last_chat"] = None

    with st.form("chat_form", clear_on_submit=False):
        query = st.text_area(
            "Your IT request",
            placeholder="Type your IT issue or request here. For example: My VPN credentials expired and I can't connect.",
            height=110,
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("🔍 Ask IT Agent", type="primary", use_container_width=True)

    if submitted:
        message = (query or "").strip()
        if not message:
            st.error("Please enter a non-empty IT issue.")
        else:
            with st.spinner("Agent is retrieving policies and reasoning..."):
                result = _safe_post(
                    f"{BACKEND_URL}/agent/chat",
                    {"message": message},
                    timeout=45,
                )
            st.session_state["last_chat"] = {"query": message, "result": result}

    last = st.session_state.get("last_chat")
    if last:
        st.markdown("---")
        _render_chat_result(last["query"], last["result"])


def _render_chat_result(query: str, result: Dict[str, Any]) -> None:
    if result.get("_error") == "conn":
        backend_down_warning()
        return

    status = result.get("_status")
    if status and status >= 400:
        detail = None
        if isinstance(result, dict):
            detail = result.get("detail")
        http_error_warning(status, detail)
        return

    st.markdown("#### 📋 Your Request")
    st.info(query, icon="👤")

    decision = (result.get("decision") or "UNKNOWN").upper()
    st.markdown("#### 🤖 Agent Decision")
    st.markdown(_decision_badge(decision), unsafe_allow_html=True)
    st.markdown("<div style='margin-top: 10px'></div>", unsafe_allow_html=True)

    intent = result.get("intent") or ""
    if intent:
        st.caption(f"**Interpreted intent:** {intent}")

    response_text = result.get("response")
    clarification = result.get("clarification_question")
    escalation_reason = result.get("escalation_reason")
    policy_ids = result.get("source_policy_ids") or []

    if response_text:
        st.markdown("#### ✉️ Agent Response")
        st.success(response_text, icon="📝")

    if clarification:
        st.markdown("#### ❓ Clarification Question")
        st.warning(clarification, icon="❓")

    if escalation_reason:
        st.markdown("#### ⚠️ Escalation Reason")
        st.error(escalation_reason, icon="🚨")

    if policy_ids:
        st.markdown("#### 📚 Referenced Policies")
        tags_html = " ".join(
            f"<span style='display:inline-block; padding:4px 10px; "
            f"background:#eff6ff; color:#1d4ed8; border-radius:6px; "
            f"font-size:12px; font-weight:600; border:1px solid #bfdbfe;'>{pid}</span>"
            for pid in policy_ids
        )
        st.markdown(tags_html, unsafe_allow_html=True)
    else:
        st.caption("No specific policies were referenced.")

    ticket = result.get("ticket")
    if ticket:
        st.markdown("#### 🎫 Created Ticket")
        cols = st.columns(4)
        with cols[0]:
            st.metric("Ticket ID", ticket.get("ticket_id", "-"))
        with cols[1]:
            st_val = ticket.get("status", "-")
            st.markdown(
                f"<div style='margin-bottom:4px; color:#64748b; font-size:12px;'>Status</div>"
                f"{_status_badge(st_val)}",
                unsafe_allow_html=True,
            )
        with cols[2]:
            team = ticket.get("assigned_team", "-")
            icon = TEAM_ICONS.get(team, "👥")
            st.metric(f"{icon} Assigned Team", team)
        with cols[3]:
            pr = ticket.get("priority", "MEDIUM")
            st.markdown(
                f"<div style='margin-bottom:4px; color:#64748b; font-size:12px;'>Priority</div>"
                f"{_priority_badge(pr)}",
                unsafe_allow_html=True,
            )
        if escalation_reason:
            st.caption(f"**Escalation reason:** {escalation_reason}")


def _fetch_tickets() -> Any:
    return _safe_get(f"{BACKEND_URL}/tickets", timeout=15)


def _fetch_audit() -> Any:
    return _safe_get(f"{BACKEND_URL}/audit-logs", timeout=15)


def _html_escape(text: Any) -> str:
    import html as _html
    return _html.escape(str(text if text is not None else ""))


def _render_tickets_html_table(tickets: List[Dict[str, Any]]) -> None:
    headers = [
        "Ticket ID", "Issue", "Category", "Priority",
        "Status", "Assigned Team", "Created",
    ]
    rows_html = []
    for t in tickets:
        issue = str(t.get("issue") or "-")
        if len(issue) > 90:
            issue = issue[:87] + "..."
        cat = str(t.get("category") or "-")
        if len(cat) > 30:
            cat = cat[:27] + "..."
        team_val = t.get("assigned_team") or "-"
        team_icon = TEAM_ICONS.get(str(team_val), "👥")
        cells = [
            f"<strong style='color:#1e3a8a;'>{_html_escape(t.get('ticket_id','-'))}</strong>",
            f"<span style='max-width:300px; display:inline-block;'>{_html_escape(issue)}</span>",
            _html_escape(cat),
            _priority_badge(t.get("priority") or "MEDIUM"),
            _status_badge(t.get("status") or "OPEN"),
            f"{team_icon} {_html_escape(team_val)}",
            f"<span style='color:#64748b; font-size:12px;'>{_html_escape(t.get('created_at','-'))}</span>",
        ]
        rows_html.append("<tr>" + "".join(f"<td style='padding:8px 12px; border-bottom:1px solid #f1f5f9;'>{c}</td>" for c in cells) + "</tr>")

    thead = (
        "<thead><tr>"
        + "".join(
            f"<th style='padding:10px 12px; background:#f8fafc; text-align:left; "
            f"font-weight:600; font-size:12px; color:#475569; border-bottom:2px solid #e2e8f0;'>{h}</th>"
            for h in headers
        )
        + "</tr></thead>"
    )
    table_html = (
        f"<div style='border:1px solid #e2e8f0; border-radius:10px; overflow:hidden; "
        f"margin-top:8px;'><table style='width:100%; border-collapse:collapse; font-size:13px;'>"
        f"{thead}<tbody>{''.join(rows_html)}</tbody></table></div>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


def render_tickets_page() -> None:
    st.subheader("🎫 Tickets", anchor=False)
    st.caption("All tickets created via escalated agent requests.")

    with st.spinner("Loading tickets..."):
        tickets = _fetch_tickets()

    if isinstance(tickets, dict) and tickets.get("_error") == "conn":
        backend_down_warning()
        return

    status = None
    if isinstance(tickets, dict):
        status = tickets.get("_status")
        if status and status >= 400:
            http_error_warning(status, tickets.get("detail"))
            return

    if not isinstance(tickets, list):
        st.warning("Unexpected response from /tickets endpoint.")
        return

    if len(tickets) == 0:
        st.info("No tickets have been created yet. Escalated requests will appear here.", icon="📭")
        return

    st.markdown(f"**{len(tickets)} ticket(s) found.**")
    _render_tickets_html_table(tickets)

    with st.expander("🔍 View ticket details"):
        ids = [t["ticket_id"] for t in tickets]
        sel = st.selectbox("Select a ticket", ids)
        if sel:
            tix = next((t for t in tickets if t["ticket_id"] == sel), None)
            if tix:
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**Ticket ID:**", tix.get("ticket_id"))
                    st.markdown("**Status:** " + _status_badge(tix.get("status") or "OPEN"), unsafe_allow_html=True)
                    st.markdown("**Priority:** " + _priority_badge(tix.get("priority") or "MEDIUM"), unsafe_allow_html=True)
                    st.write("**Assigned Team:**", TEAM_ICONS.get(tix.get("assigned_team") or "", "👥"), tix.get("assigned_team"))
                    st.write("**Category:**", tix.get("category") or "-")
                with c2:
                    st.write("**Employee Name:**", tix.get("employee_name") or "-")
                    st.write("**Employee Email:**", tix.get("employee_email") or "-")
                    st.write("**Created At:**", tix.get("created_at") or "-")
                    esc = tix.get("escalation_reason")
                    if esc:
                        st.write("**Escalation Reason:**", esc)
                st.write("**Issue:**")
                st.info(tix.get("issue") or "-")
                sp = tix.get("source_policy_ids") or []
                if sp:
                    st.write("**Source Policies:**", ", ".join(str(s) for s in sp))


def _render_audits_html_table(audits: List[Dict[str, Any]]) -> None:
    headers = [
        "#", "Ticket ID", "Action", "Decision",
        "Issue", "Policy IDs", "Reason", "Timestamp",
    ]
    rows_html = []
    for a in audits:
        decision = (a.get("decision") or "").upper()
        ds = DECISION_STYLES.get(decision, {"icon": "ℹ️", "color": "#64748b", "label": decision})
        decision_cell = (
            f"<span style='color:{ds['color']}; font-weight:600;'>"
            f"{ds['icon']} {decision}</span>"
        )
        issue = str(a.get("issue") or "-")
        if len(issue) > 100:
            issue = issue[:97] + "..."
        pids = ", ".join(str(p) for p in (a.get("source_policy_ids") or [])) or "-"
        reason = str(a.get("reason") or "-")
        if len(reason) > 110:
            reason = reason[:107] + "..."
        cells = [
            f"<span style='color:#94a3b8;'>{a.get('audit_id','-')}</span>",
            f"<strong style='color:#1e3a8a;'>{_html_escape(a.get('ticket_id') or '-')}</strong>",
            f"<code style='background:#f1f5f9; padding:2px 6px; border-radius:4px; font-size:12px;'>{_html_escape(a.get('action') or '-')}</code>",
            decision_cell,
            _html_escape(issue),
            _html_escape(pids),
            _html_escape(reason),
            f"<span style='color:#64748b; font-size:12px;'>{_html_escape(a.get('timestamp') or '-')}</span>",
        ]
        rows_html.append(
            "<tr>"
            + "".join(
                f"<td style='padding:8px 12px; border-bottom:1px solid #f1f5f9; vertical-align:top;'>{c}</td>"
                for c in cells
            )
            + "</tr>"
        )

    thead = (
        "<thead><tr>"
        + "".join(
            f"<th style='padding:10px 12px; background:#f8fafc; text-align:left; "
            f"font-weight:600; font-size:12px; color:#475569; border-bottom:2px solid #e2e8f0;'>{h}</th>"
            for h in headers
        )
        + "</tr></thead>"
    )
    table_html = (
        f"<div style='border:1px solid #e2e8f0; border-radius:10px; overflow:hidden; "
        f"margin-top:8px; overflow-x:auto;'><table style='width:100%; border-collapse:collapse; font-size:13px;'>"
        f"{thead}<tbody>{''.join(rows_html)}</tbody></table></div>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


def render_audit_page() -> None:
    st.subheader("📜 Audit Trail", anchor=False)
    st.caption("Complete log of every agent action, decision, and escalation.")

    with st.spinner("Loading audit logs..."):
        audits = _fetch_audit()

    if isinstance(audits, dict) and audits.get("_error") == "conn":
        backend_down_warning()
        return

    status = None
    if isinstance(audits, dict):
        status = audits.get("_status")
        if status and status >= 400:
            http_error_warning(status, audits.get("detail"))
            return

    if not isinstance(audits, list):
        st.warning("Unexpected response from /audit-logs endpoint.")
        return

    if len(audits) == 0:
        st.info("No audit records yet. Chat with the IT agent to generate entries.", icon="📭")
        return

    st.markdown(f"**{len(audits)} audit record(s) found.**")
    _render_audits_html_table(audits)


def main() -> None:
    page_config()
    page = render_sidebar()
    render_header()

    if "last_chat" not in st.session_state:
        st.session_state["last_chat"] = None

    if page == PAGE_ASK:
        render_ask_page()
    elif page == PAGE_TICKETS:
        render_tickets_page()
    elif page == PAGE_AUDIT:
        render_audit_page()

    st.markdown(
        "<div style='margin-top: 40px; padding-top: 16px; border-top: 1px solid #e2e8f0; "
        "color: #94a3b8; font-size: 12px; text-align: center;'>"
        "Veridian Corp · Internal IT Support · Confidential</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
