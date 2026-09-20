"""Case queue + detail view for clinic volunteers."""
import json

import pandas as pd
import streamlit as st

from db import db

STATUSES = ["new", "in_progress", "filed", "closed"]
MODULES = ["consumer", "police", "tenant", "labour", "other"]
URGENCIES = ["high", "medium", "low"]


def _badge(days):
    if days is None:
        return ""
    return "🔴 <10d" if days < 10 else ("⚠️ <30d" if days < 30 else "")


def _volunteer_names():
    return {v["id"]: v["name"] for v in db.volunteers()}


def render():
    st.title("Case queue")
    qp_case = st.query_params.get("case")
    if qp_case:
        try:
            return _detail(int(qp_case))
        except ValueError:
            st.error(f"Bad case id in URL: {qp_case}")

    c1, c2, c3 = st.columns(3)
    status = c1.multiselect("Status", STATUSES)
    module = c2.multiselect("Module", MODULES)
    urgency = c3.multiselect("Urgency", URGENCIES)

    cases = db.list_cases(status=status or None, module=module or None, urgency=urgency or None)
    if not cases:
        st.info("No cases match these filters.")
        return

    names = _volunteer_names()
    rows = []
    for c in cases:
        days = db.days_to_deadline(c.get("deadline"))
        rows.append({"id": c["id"], "client": c.get("client_name"), "module": c.get("module"),
                     "urgency": c.get("urgency"), "status": c.get("status"),
                     "volunteer": names.get(c.get("assigned_to"), "—"),
                     "deadline": c.get("deadline"), "days_left": days, "flag": _badge(days)})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    chosen = st.selectbox("Open case", [c["id"] for c in cases],
                          format_func=lambda i: f"#{i} · {next(c['client_name'] for c in cases if c['id'] == i)}")
    if chosen:
        _detail(chosen)


def _detail(case_id: int):
    case = db.get_case(case_id)
    if not case:
        st.error(f"Case #{case_id} not found.")
        return

    names = _volunteer_names()
    st.header(f"Case #{case_id} · {case.get('client_name')}")
    st.caption(f"{case.get('module')} · urgency {case.get('urgency')} · status {case.get('status')} "
               f"· {names.get(case.get('assigned_to'), 'unassigned')}")

    days = db.days_to_deadline(case.get("deadline"))
    if days is not None and days < 30:
        st.markdown(f":red[**limitation in {days} days** ({case.get('deadline')})]")
    elif case.get("deadline"):
        st.caption(f"Limitation: {case['deadline']} ({days} days left)")

    if case.get("eligible_aid"):
        st.success(f"Free legal aid: eligible — {case.get('eligibility_reason') or ''}")
    else:
        st.warning(f"Free legal aid: not established — {case.get('eligibility_reason') or ''}")

    st.markdown(case.get("draft_md") or "_No draft stored._")

    sections = _loads(case.get("sections_json"), [])
    if sections:
        st.subheader("Sections relied on")
        st.dataframe(pd.DataFrame(sections), use_container_width=True, hide_index=True)

    trace = _loads(case.get("trace_json"), [])
    if trace:
        with st.expander(f"Agent trace ({case.get('intake_seconds') or 0:.1f}s)"):
            st.dataframe(pd.DataFrame(trace), use_container_width=True, hide_index=True)

    from pdf.qr import qr_for_case                      # stage4: QR back to this case
    from pdf.render import draft_to_pdf
    st.download_button("Download PDF",
                       draft_to_pdf(case.get("draft_md") or "",
                                    {"deadline_iso": case.get("deadline")},
                                    qr_png=qr_for_case(case_id)),
                       file_name=f"nyaya-case-{case_id}.pdf", mime="application/pdf",
                       key=f"pdf{case_id}")

    a, b = st.columns(2)
    if a.button("Mark filed", disabled=case.get("status") == "filed"):
        db.update_case(case_id, status="filed")
        st.rerun()
    ids = list(names)
    new_owner = b.selectbox("Reassign to", ids, index=ids.index(case["assigned_to"])
                            if case.get("assigned_to") in ids else 0,
                            format_func=lambda i: names[i])
    if b.button("Reassign", disabled=new_owner == case.get("assigned_to")):
        db.update_case(case_id, assigned_to=new_owner)
        st.rerun()

    from ui import hooks
    extra = getattr(hooks, "extra_case_actions", None)
    if callable(extra):
        extra(case)

    st.subheader("Feedback")
    note = st.text_input("Note (what the advocate corrected)", key=f"note{case_id}")
    f1, f2 = st.columns(2)
    if f1.button("👍", key=f"up{case_id}"):
        db.add_feedback(case_id, "up", note)
        st.rerun()
    if f2.button("👎", key=f"down{case_id}"):
        db.add_feedback(case_id, "down", note)
        st.rerun()
    for f in db.list_feedback(case_id):
        st.caption(f"{f['created_at']} · {f['rating']} · {f['note'] or ''}")

    with st.expander("History"):
        for e in db.list_events(case_id):
            st.caption(f"{e['ts']} · {e['type']} · {e['payload'] or ''}")


def _loads(raw, default):
    try:
        return json.loads(raw) if raw else default
    except (ValueError, TypeError):
        return default
