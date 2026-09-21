import streamlit as st
import requests
import html as _html
from typing import Any, Dict, List, Optional

BACKEND_URL = "http://127.0.0.1:8000"

PAGE_ASK = "💬 Ask IT Agent"
PAGE_TICKETS = "🎫 Tickets Queue"
PAGE_AUDIT = "📜 Audit Trail"
PAGE_KB = "📚 Knowledge Base"
PAGE_REQS = "📋 Employee Requests Data Pack"

DECISION_STYLES = {
    "RESOLVE": {"icon": "✅", "color": "#16a34a", "bg": "#dcfce7", "label": "Resolved"},
    "ASK_CLARIFICATION": {"icon": "❓", "color": "#d97706", "bg": "#fef3c7", "label": "Clarification Needed"},
    "ESCALATE": {"icon": "🚨", "color": "#dc2626", "bg": "#fee2e2", "label": "Escalated to Human IT"},
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
    "Finance": "💰",
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
    if isinstance(data, dict):
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
        "Backend service is currently unreachable. Start it with:  \n"
        "`python -m uvicorn backend.main:app --reload`",
        icon="⚠️",
    )


def http_error_warning(status: int, detail: Optional[str] = None) -> None:
    msg = f"Backend returned HTTP {status}"
    if detail:
        msg += f": {detail}"
    st.warning(msg, icon="🌐")


def render_header() -> None:
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #0284c7 100%);
            padding: 22px 28px;
            border-radius: 14px;
            margin-bottom: 24px;
            box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25);
            color: white;
            display: flex;
            align-items: center;
            justify-content: space-between;
        ">
            <div style="display: flex; align-items: center; gap: 18px;">
                <div style="
                    width: 52px; height: 52px;
                    background: rgba(255, 255, 255, 0.15);
                    backdrop-filter: blur(10px);
                    border-radius: 14px;
                    display: flex; align-items: center; justify-content: center;
                    font-size: 26px;
                    border: 1px solid rgba(255, 255, 255, 0.25);
                ">🛡️</div>
                <div>
                    <div style="font-size: 24px; font-weight: 800; tracking-tight: -0.02em;">
                        Veridian Corp
                    </div>
                    <div style="font-size: 15px; opacity: 0.9; font-weight: 500;">
                        AI IT Support & Resolution Agent
                    </div>
                </div>
            </div>
            <div style="text-align: right; font-size: 12px; opacity: 0.8;">
                <div>Assignment 2 Data Pack Verified</div>
                <div>LangGraph + RAG Policy Engine</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 10px 0 16px 0;">
                <div style="font-size: 16px; font-weight: 800; color: #0f172a; display: flex; align-items: center; gap: 8px;">
                    🛡️ Navigation
                </div>
                <div style="color: #64748b; font-size: 12px; margin-top: 2px;">
                    Internal Support Dashboard
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        page = st.radio(
            "Main Menu",
            [PAGE_ASK, PAGE_TICKETS, PAGE_AUDIT, PAGE_KB, PAGE_REQS],
            label_visibility="collapsed",
        )
        
        st.markdown("---")
        
        # New Chat Button
        if st.button("➕ Start New Chat Session", use_container_width=True, type="secondary"):
            st.session_state["chat_messages"] = []
            st.session_state["current_employee"] = None
            st.rerun()

        st.markdown("---")
        
        # System Stats & Status
        st.markdown("<div style='font-size: 12px; font-weight: 700; color: #475569; margin-bottom: 8px;'>SYSTEM MONITORING</div>", unsafe_allow_html=True)
        
        backend_online = False
        try:
            resp = requests.get(f"{BACKEND_URL}/health", timeout=2)
            if resp.status_code == 200:
                backend_online = True
        except Exception:
            backend_online = False
            
        if backend_online:
            st.success("Backend API: Online", icon="🟢")
        else:
            st.error("Backend API: Offline", icon="🔴")

        # Quick stats fetch
        tickets_count = 0
        audits_count = 0
        if backend_online:
            tix = _safe_get(f"{BACKEND_URL}/tickets", timeout=3)
            if isinstance(tix, list):
                tickets_count = len(tix)
            aud = _safe_get(f"{BACKEND_URL}/audit-logs", timeout=3)
            if isinstance(aud, list):
                audits_count = len(aud)

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Tickets", tickets_count)
        with c2:
            st.metric("Audit Logs", audits_count)

        st.caption(f"Endpoint: `{BACKEND_URL}`")
        st.caption("Veridian AI v2.0 · Confidential")

    return page


def _decision_badge(decision: str) -> str:
    style = DECISION_STYLES.get(decision, {"icon": "ℹ️", "color": "#64748b", "bg": "#f1f5f9", "label": decision})
    return (
        f"<span style='display:inline-flex; align-items:center; gap:6px; "
        f"padding:5px 12px; border-radius:9999px; background:{style['bg']}; "
        f"color:{style['color']}; font-weight:700; font-size:12px; "
        f"border:1px solid {style['color']}44;'>"
        f"{style['icon']} {style['label']}</span>"
    )


def _priority_badge(priority: str) -> str:
    p = (priority or "").upper()
    s = PRIORITY_STYLES.get(p, PRIORITY_STYLES["MEDIUM"])
    return (
        f"<span style='padding:3px 10px; border-radius:6px; "
        f"background:{s['bg']}; color:{s['fg']}; font-weight:700; font-size:11px;'>"
        f"{p or 'MEDIUM'}</span>"
    )


def _status_badge(status: str) -> str:
    s_val = (status or "").upper()
    s = STATUS_STYLES.get(s_val, STATUS_STYLES["OPEN"])
    return (
        f"<span style='padding:3px 10px; border-radius:6px; "
        f"background:{s['bg']}; color:{s['fg']}; font-weight:700; font-size:11px;'>"
        f"{status or 'OPEN'}</span>"
    )


def _html_escape(text: Any) -> str:
    return _html.escape(str(text if text is not None else ""))


# ==============================================================================
# PAGE 1: INTERACTIVE MULTI-TURN CHAT AGENT
# ==============================================================================
def render_ask_page() -> None:
    st.markdown("### 💬 Interactive IT Support Agent")
    st.caption("Multi-turn conversational assistant. Ask any IT question, answer follow-up questions, and track resolution or ticket creation.")

    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []

    # Display Chat History Thread
    chat_container = st.container()
    with chat_container:
        if not st.session_state["chat_messages"]:
            st.info(
                "👋 Hello! I am the Veridian AI Support Agent. Type your IT request below to get started.",
                icon="🤖",
            )
        else:
            for msg in st.session_state["chat_messages"]:
                role = msg["role"]
                content = msg["content"]
                result = msg.get("result")
                
                with st.chat_message(role, avatar="👤" if role == "user" else "🛡️"):
                    st.markdown(content)
                    
                    if result and role == "assistant":
                        decision = (result.get("decision") or "").upper()
                        if decision:
                            st.markdown(_decision_badge(decision), unsafe_allow_html=True)
                        
                        policy_ids = result.get("source_policy_ids") or []
                        if policy_ids:
                            tags_html = " ".join(
                                f"<span style='display:inline-block; padding:3px 8px; "
                                f"background:#eff6ff; color:#1d4ed8; border-radius:6px; "
                                f"font-size:11px; font-weight:600; border:1px solid #bfdbfe;'>{pid}</span>"
                                for pid in policy_ids
                            )
                            st.markdown(f"**Referenced Policies:** {tags_html}", unsafe_allow_html=True)
                        
                        ticket = result.get("ticket")
                        if ticket and decision == "ESCALATE":
                            st.markdown(
                                f"""
                                <div style="
                                    background: #f8fafc;
                                    border: 1px solid #e2e8f0;
                                    border-left: 4px solid #dc2626;
                                    border-radius: 8px;
                                    padding: 12px 16px;
                                    margin-top: 10px;
                                ">
                                    <div style="font-weight: 700; color: #0f172a; font-size: 13px;">
                                        🎫 Escalated Ticket Created: <code>{ticket.get('ticket_id')}</code>
                                    </div>
                                    <div style="font-size: 12px; color: #475569; margin-top: 4px;">
                                        Assigned Team: <strong>{ticket.get('assigned_team')}</strong> | 
                                        Status: <strong>{ticket.get('status')}</strong> | 
                                        Priority: <strong>{ticket.get('priority', 'MEDIUM')}</strong>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

    # Chat Input
    user_input = st.chat_input("Type your IT request or reply to the agent...")
    
    if user_input:
        user_text = user_input.strip()
        if user_text:
            # 1. Append user message
            st.session_state["chat_messages"].append({"role": "user", "content": user_text})
            
            # 2. Build history for API
            history_payload = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state["chat_messages"][:-1]
            ]
            
            # 3. Call backend /agent/chat
            with st.spinner("Agent is retrieving policies and reasoning..."):
                resp = _safe_post(
                    f"{BACKEND_URL}/agent/chat",
                    {
                        "message": user_text,
                        "history": history_payload,
                    },
                    timeout=45,
                )
            
            if resp.get("_error") == "conn":
                backend_down_warning()
            elif resp.get("_status") and resp["_status"] >= 400:
                http_error_warning(resp["_status"], resp.get("detail"))
            else:
                decision = (resp.get("decision") or "UNKNOWN").upper()
                response_text = resp.get("response")
                clarification = resp.get("clarification_question")
                escalation_reason = resp.get("escalation_reason")
                
                # Determine display text for assistant
                if decision == "RESOLVE":
                    assistant_text = response_text or "Your request has been resolved per company policy."
                elif decision == "ASK_CLARIFICATION":
                    assistant_text = clarification or "Could you please provide more details?"
                elif decision == "ESCALATE":
                    assistant_text = f"{response_text or 'Your request has been escalated to IT support.'}\n\n**Reason:** {escalation_reason or 'Requires human review.'}"
                else:
                    assistant_text = response_text or "Processing complete."
                
                # Append assistant message
                st.session_state["chat_messages"].append({
                    "role": "assistant",
                    "content": assistant_text,
                    "result": resp,
                })
            
            st.rerun()


# ==============================================================================
# PAGE 2: TICKETS QUEUE
# ==============================================================================
def render_tickets_page() -> None:
    st.markdown("### 🎫 Tickets Queue")
    st.caption("Comprehensive ticketing database showing active escalations and historical baseline records.")

    t1, t2 = st.tabs(["⚡ Live Escalated Tickets (SQLite)", "📚 Historical Ticket Queue (Assignment baseline)"])
    
    with t1:
        with st.spinner("Loading live tickets..."):
            tickets = _safe_get(f"{BACKEND_URL}/tickets", timeout=15)

        if isinstance(tickets, dict) and tickets.get("_error") == "conn":
            backend_down_warning()
        elif isinstance(tickets, list):
            if len(tickets) == 0:
                st.info("No live tickets created yet. When the agent escalates a request, it will appear here.", icon="📭")
            else:
                st.markdown(f"**{len(tickets)} live escalated ticket(s)**")
                _render_tickets_html_table(tickets)
                
                with st.expander("🔍 View Live Ticket Details & Metadata"):
                    ids = [t["ticket_id"] for t in tickets]
                    sel = st.selectbox("Select Ticket ID", ids)
                    if sel:
                        tix = next((t for t in tickets if t["ticket_id"] == sel), None)
                        if tix:
                            c1, c2 = st.columns(2)
                            with c1:
                                st.write("**Ticket ID:**", tix.get("ticket_id"))
                                st.markdown("**Status:** " + _status_badge(tix.get("status") or "OPEN"), unsafe_allow_html=True)
                                st.markdown("**Priority:** " + _priority_badge(tix.get("priority") or "MEDIUM"), unsafe_allow_html=True)
                                st.write("**Assigned Team:**", TEAM_ICONS.get(tix.get("assigned_team") or "", "👥"), tix.get("assigned_team"))
                            with c2:
                                st.write("**Category:**", tix.get("category") or "-")
                                st.write("**Created At:**", tix.get("created_at") or "-")
                                if tix.get("escalation_reason"):
                                    st.write("**Escalation Reason:**", tix.get("escalation_reason"))
                            st.write("**Issue Summary / Response:**")
                            st.info(tix.get("issue") or "-")

    with t2:
        with st.spinner("Loading baseline tickets..."):
            base_tickets = _safe_get(f"{BACKEND_URL}/tickets-history", timeout=15)
        if isinstance(base_tickets, list):
            st.markdown(f"**{len(base_tickets)} baseline records from Assignment 2 Data Pack**")
            _render_baseline_tickets_table(base_tickets)


def _render_tickets_html_table(tickets: List[Dict[str, Any]]) -> None:
    headers = ["Ticket ID", "Issue Summary", "Category", "Priority", "Status", "Assigned Team", "Created"]
    rows_html = []
    for t in tickets:
        issue = str(t.get("issue") or "-")
        if len(issue) > 80:
            issue = issue[:77] + "..."
        cat = str(t.get("category") or "-")
        team_val = t.get("assigned_team") or "-"
        team_icon = TEAM_ICONS.get(str(team_val), "👥")
        cells = [
            f"<strong style='color:#1e3a8a;'>{_html_escape(t.get('ticket_id','-'))}</strong>",
            f"<span>{_html_escape(issue)}</span>",
            _html_escape(cat),
            _priority_badge(t.get("priority") or "MEDIUM"),
            _status_badge(t.get("status") or "OPEN"),
            f"{team_icon} {_html_escape(team_val)}",
            f"<span style='color:#64748b; font-size:12px;'>{_html_escape(t.get('created_at','-'))}</span>",
        ]
        rows_html.append("<tr>" + "".join(f"<td style='padding:8px 12px; border-bottom:1px solid #f1f5f9;'>{c}</td>" for c in cells) + "</tr>")

    thead = "<thead><tr>" + "".join(f"<th style='padding:10px 12px; background:#f8fafc; text-align:left; font-weight:600; font-size:12px; color:#475569; border-bottom:2px solid #e2e8f0;'>{h}</th>" for h in headers) + "</tr></thead>"
    table_html = f"<div style='border:1px solid #e2e8f0; border-radius:10px; overflow:hidden; margin-top:8px;'><table style='width:100%; border-collapse:collapse; font-size:13px;'>{thead}<tbody>{''.join(rows_html)}</tbody></table></div>"
    st.markdown(table_html, unsafe_allow_html=True)


def _render_baseline_tickets_table(tickets: List[Dict[str, Any]]) -> None:
    headers = ["Ticket ID", "Employee", "Issue Summary", "Status"]
    rows_html = []
    for t in tickets:
        cells = [
            f"<strong style='color:#1e3a8a;'>{_html_escape(t.get('ticket_id'))}</strong>",
            _html_escape(t.get("employee")),
            _html_escape(t.get("issue_summary")),
            _status_badge(t.get("status")),
        ]
        rows_html.append("<tr>" + "".join(f"<td style='padding:8px 12px; border-bottom:1px solid #f1f5f9;'>{c}</td>" for c in cells) + "</tr>")

    thead = "<thead><tr>" + "".join(f"<th style='padding:10px 12px; background:#f8fafc; text-align:left; font-weight:600; font-size:12px; color:#475569; border-bottom:2px solid #e2e8f0;'>{h}</th>" for h in headers) + "</tr></thead>"
    table_html = f"<div style='border:1px solid #e2e8f0; border-radius:10px; overflow:hidden; margin-top:8px;'><table style='width:100%; border-collapse:collapse; font-size:13px;'>{thead}<tbody>{''.join(rows_html)}</tbody></table></div>"
    st.markdown(table_html, unsafe_allow_html=True)


# ==============================================================================
# PAGE 3: AUDIT TRAIL
# ==============================================================================
def render_audit_page() -> None:
    st.markdown("### 📜 Audit Trail")
    st.caption("Immutable system audit logs recording every agent execution turn, decision, and ticket linkage.")

    with st.spinner("Loading audit records..."):
        audits = _safe_get(f"{BACKEND_URL}/audit-logs", timeout=15)

    if isinstance(audits, dict) and audits.get("_error") == "conn":
        backend_down_warning()
        return

    if isinstance(audits, list):
        if len(audits) == 0:
            st.info("No audit logs recorded yet. Interact with the chat agent to generate audit entries.", icon="📭")
        else:
            st.markdown(f"**{len(audits)} audit record(s) logged.**")
            _render_audits_html_table(audits)


def _render_audits_html_table(audits: List[Dict[str, Any]]) -> None:
    headers = ["#", "Ticket ID", "Action", "Decision", "Issue Summary", "Policy IDs", "Reason / Response", "Timestamp"]
    rows_html = []
    for a in audits:
        decision = (a.get("decision") or "").upper()
        ds = DECISION_STYLES.get(decision, {"icon": "ℹ️", "color": "#64748b", "label": decision})
        decision_cell = f"<span style='color:{ds['color']}; font-weight:700;'>{ds['icon']} {decision}</span>"
        issue = str(a.get("issue") or "-")
        if len(issue) > 70:
            issue = issue[:67] + "..."
        pids = ", ".join(str(p) for p in (a.get("source_policy_ids") or [])) or "-"
        reason = str(a.get("reason") or "-")
        if len(reason) > 70:
            reason = reason[:67] + "..."
        cells = [
            f"<span style='color:#94a3b8;'>{a.get('audit_id','-')}</span>",
            f"<strong style='color:#1e3a8a;'>{_html_escape(a.get('ticket_id') or '-')}</strong>",
            f"<code style='background:#f1f5f9; padding:2px 6px; border-radius:4px; font-size:11px;'>{_html_escape(a.get('action') or '-')}</code>",
            decision_cell,
            _html_escape(issue),
            _html_escape(pids),
            _html_escape(reason),
            f"<span style='color:#64748b; font-size:11px;'>{_html_escape(a.get('timestamp') or '-')}</span>",
        ]
        rows_html.append("<tr>" + "".join(f"<td style='padding:8px 12px; border-bottom:1px solid #f1f5f9; vertical-align:top;'>{c}</td>" for c in cells) + "</tr>")

    thead = "<thead><tr>" + "".join(f"<th style='padding:10px 12px; background:#f8fafc; text-align:left; font-weight:600; font-size:12px; color:#475569; border-bottom:2px solid #e2e8f0;'>{h}</th>" for h in headers) + "</tr></thead>"
    table_html = f"<div style='border:1px solid #e2e8f0; border-radius:10px; overflow:hidden; margin-top:8px; overflow-x:auto;'><table style='width:100%; border-collapse:collapse; font-size:13px;'>{thead}<tbody>{''.join(rows_html)}</tbody></table></div>"
    st.markdown(table_html, unsafe_allow_html=True)


# ==============================================================================
# PAGE 4: KNOWLEDGE BASE VIEWER
# ==============================================================================
def render_kb_page() -> None:
    st.markdown("### 📚 Veridian Corp Knowledge Base Policies")
    st.caption("Official company policies retrieved during the RAG workflow (KB-01 to KB-11).")

    with st.spinner("Loading Knowledge Base..."):
        policies = _safe_get(f"{BACKEND_URL}/policies", timeout=15)

    if isinstance(policies, dict) and policies.get("_error") == "conn":
        backend_down_warning()
        return

    if isinstance(policies, list):
        search = st.text_input("🔍 Search Policies", placeholder="e.g. VPN, Password, Laptop, Phishing, Printer...")
        
        filtered = policies
        if search.strip():
            kw = search.strip().lower()
            filtered = [
                p for p in policies
                if kw in p.get("policy_id", "").lower()
                or kw in p.get("title", "").lower()
                or kw in p.get("content", "").lower()
            ]

        st.markdown(f"**Showing {len(filtered)} policy document(s)**")
        
        for p in filtered:
            with st.expander(f"📌 {p.get('policy_id')} — {p.get('title')}", expanded=True):
                st.markdown(f"**Source:** `{p.get('source', 'Data Pack')}`")
                st.info(p.get("content"))


# ==============================================================================
# PAGE 5: EMPLOYEE REQUESTS DATA PACK RUNNER
# ==============================================================================
def render_reqs_page() -> None:
    st.markdown("### 📋 Employee Requests Data Pack (REQ-01 to REQ-15)")
    st.caption("Run any of the 15 official assignment requests through the agent workflow with one click.")

    with st.spinner("Loading Employee Requests..."):
        reqs = _safe_get(f"{BACKEND_URL}/employee-requests", timeout=15)

    if isinstance(reqs, list) and len(reqs) > 0:
        for r in reqs:
            rid = r.get("request_id")
            emp = r.get("employee_name")
            email = r.get("employee_email")
            date = r.get("date_opened")
            text = r.get("request")
            action = r.get("initial_action")
            
            with st.container():
                c1, c2 = st.columns([0.8, 0.2])
                with c1:
                    st.markdown(f"#### {rid}: {emp} (`{email}`)")
                    st.caption(f"📅 Opened: {date} | Initial Action: {action}")
                    st.warning(f"“{text}”")
                with c2:
                    if st.button(f"⚡ Test {rid}", key=f"btn_{rid}", use_container_width=True):
                        st.session_state["chat_messages"] = [
                            {"role": "user", "content": text}
                        ]
                        # Immediate API call
                        with st.spinner("Running agent..."):
                            resp = _safe_post(
                                f"{BACKEND_URL}/agent/chat",
                                {"message": text, "employee_name": emp, "employee_email": email},
                                timeout=45,
                            )
                        decision = (resp.get("decision") or "").upper()
                        resp_text = resp.get("response") or resp.get("clarification_question") or ""
                        st.session_state["chat_messages"].append({
                            "role": "assistant",
                            "content": resp_text,
                            "result": resp,
                        })
                        st.switch_page = PAGE_ASK
                        st.rerun()
                st.markdown("---")


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
def main() -> None:
    page_config()
    page = render_sidebar()
    render_header()

    if page == PAGE_ASK:
        render_ask_page()
    elif page == PAGE_TICKETS:
        render_tickets_page()
    elif page == PAGE_AUDIT:
        render_audit_page()
    elif page == PAGE_KB:
        render_kb_page()
    elif page == PAGE_REQS:
        render_reqs_page()

    st.markdown(
        """
        <div style="
            margin-top: 50px; padding-top: 20px; border-top: 1px solid #e2e8f0;
            color: #94a3b8; font-size: 12px; text-align: center;
        ">
            Veridian Corp · Internal IT Support AI Agent · Assignment 2 Data Pack Verified
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
